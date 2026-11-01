"""Merge integration into pristine builder outputs, preserving generation evidence."""
from pathlib import Path
import hashlib
import json
import re
import shutil

ROOT=Path(__file__).resolve().parents[1]
COMMON=ROOT/'build/generated/common'
shutil.copy2(ROOT/'examples/hakoniwa_transport/HakoniwaTransport.py',COMMON/'HakoniwaTransport.py')


def replace_method(text,name,body):
    pattern=r'    def '+name+r'\(self, ec_id\):\s*return RTC.RTC_OK'
    value='    def '+name+'(self, ec_id):\n'+body.rstrip()+'\n'
    result,count=re.subn(pattern,lambda match:value,text)
    assert count==1,(name,count)
    return result


for name in ('DroneJoystickGUIRTC','DroneTeleopControllerRTC'):
    folder=ROOT/'build/generated'/name
    source=folder/(name+'.py')
    pristine=folder/(name+'.skeleton.py.txt')
    if pristine.exists():
        raise RuntimeError('Refusing to regenerate over implementation: '+str(source))
    shutil.copy2(source,pristine)
    text=source.read_text(encoding='utf-8').replace('\t','    ')
    state=dict(builder='cuirtcbuilder.bat',language='Python',
        java='C:/Program Files/Java/jdk-26/bin/java.exe',
        toolLibrariesSource='C:/workspace/codex-test2/tool/cuirtcbuilder/lib',
        skeletonSha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        idlSha256=hashlib.sha256((COMMON/'idl/DroneTeleop.idl').read_bytes()).hexdigest(),
        note='Generated before implementation. JAVA bin added before the stalled javapath shim. Required local CUI jars copied into tool/cuirtcbuilder/lib.')
    (folder/'skeleton-generation.json').write_text(json.dumps(state,indent=2)+'\n')
    if name=='DroneJoystickGUIRTC':
        text=text.replace('import DroneTeleop','import DroneTeleop\nfrom JoystickCore import JoystickModel\nfrom JoystickView import JoystickView\nimport tkinter as tk\nimport math')
        text=text.replace('self._pilotOut = OpenRTM_aist.OutPort("pilot", self._d_pilot)',
            'self._pilotOut = OpenRTM_aist.OutPort("pilot", self._d_pilot)\n        self.model = JoystickModel()')
        text=replace_method(text,'onActivated','''        self.model.active = True
        return RTC.RTC_OK''')
        text=replace_method(text,'onDeactivated','''        self.model.active = False
        self.model.disable()
        return RTC.RTC_OK''')
        text=replace_method(text,'onExecute','''        state = self.model.snapshot()
        action = getattr(DroneTeleop, "ACTION_" + state.action)
        msg = DroneTeleop.TimedPilotInput(RTC.Time(0,0), state.serial, state.enabled, *state.axes, action)
        OpenRTM_aist.setTimestamp(msg)
        self._pilotOut.write(msg)
        if self._statusIn.isNew():
            value = self._statusIn.read()
            self.model.update_status((str(value.phase),value.detail,(value.x,value.y,value.z,math.degrees(value.yaw)),value.pending))
        return RTC.RTC_OK''')
        text=text.replace('    comp = manager.createComponent("DroneJoystickGUIRTC" + args)',
            '    global GUI_COMPONENT\n    GUI_COMPONENT = manager.createComponent("DroneJoystickGUIRTC" + args)')
        text=text.replace('mgr = OpenRTM_aist.Manager.init(sys.argv)','mgr = OpenRTM_aist.Manager.init(argv)')
        text=text.replace('def MyModuleInit(manager):','def MyModuleInit(manager):\n    HakoniwaTransportInit(manager)\n    DroneSerializersInit(manager)') if name=='DroneTeleopControllerRTC' else text
        text=text.replace('    mgr.runManager()','''    mgr.runManager(True)
    root = tk.Tk()
    view = JoystickView(root, GUI_COMPONENT.model)
    try:
        root.mainloop()
    finally:
        GUI_COMPONENT.model.active = False
        GUI_COMPONENT.model.disable()
        mgr.shutdown()''')
    else:
        text=text.replace('import DroneTeleop','''import DroneTeleop
import math
import traceback
import hakopy
from TeleopCore import TeleopCore, Pilot, Pose, Command
from HakoniwaTransport import HakoniwaTransportInit
from DroneSerializers import DroneSerializersInit, CODECS''')
        text=text.replace('self._land_requestOut = OpenRTM_aist.OutPort("land_request", self._d_land_request)',
            'self._land_requestOut = OpenRTM_aist.OutPort("land_request", self._d_land_request)\n        self.core = TeleopCore()\n        self._native_ports = []\n        self._last_phase = None')
        text=replace_method(text,'onActivated','''        try:
            self.core = TeleopCore()
            if not hakopy.init_for_external():
                raise RuntimeError("Cannot initialize external PDU client")
            HakoniwaTransportInit(self._manager)
            DroneSerializersInit(self._manager)
            for kind, channel in (("move",7),("takeoff",6),("land",8)):
                codec,datatype,fields,size = CODECS[kind]
                self._bind_native(getattr(self,"_"+kind+"_requestOut"),codec,channel,size)
                self._bind_native(getattr(self,"_"+kind+"_responseIn"),codec,channel,size)
            self._bind_native(self._poseIn,"hakoniwa:geometry_msgs/Twist:pose-metadata72",1,72)
            print("NATIVE_BINDINGS_READY: 7, custom interface hakoniwa",flush=True)
            return RTC.RTC_OK
        except Exception:
            traceback.print_exc()
            for port in self._native_ports: port.disconnect_all()
            self._native_ports = []
            return RTC.RTC_ERROR''')
        text=replace_method(text,'onDeactivated','''        self.core.fault("Deactivated; no new commands")
        for port in self._native_ports:
            port.disconnect_all()
        self._native_ports = []
        return RTC.RTC_OK''')
        text=replace_method(text,'onExecute','''        try:
            wall = time.monotonic()
            sim = hakopy.simulation_time()/1000000.0
            if self._pilotIn.isNew():
                value = self._pilotIn.read()
                self.core.input(Pilot(value.serial,value.enabled,(value.axis_x,value.axis_y,value.axis_z,value.axis_yaw),str(value.action).replace("ACTION_","")),wall)
            if self._poseIn.isNew():
                value = self._poseIn.read().data
                self.core.observe_pose(Pose(value.position.x,value.position.y,value.position.z,value.orientation.r,value.orientation.p,value.orientation.y),wall)
            responses = {}
            for kind in ("move","takeoff","land"):
                port = getattr(self,"_"+kind+"_responseIn")
                if port.isNew():
                    value = port.read()
                    fields = CODECS[kind][2]
                    responses[kind] = Command(kind,{f:getattr(value,f) for f in fields},value.request,value.result,value.result_code)
            for command in self.core.tick(sim,wall,responses):
                codec,datatype,fields,size = CODECS[command.kind]
                value = datatype(RTC.Time(0,0),command.request,command.result,command.result_code,*[command.values[f] for f in fields])
                OpenRTM_aist.setTimestamp(value)
                if not getattr(self,"_"+command.kind+"_requestOut").write(value):
                    raise RuntimeError("Native write failed: "+command.kind)
                print("PDU_WRITE",command.kind,"request",command.request,"result",command.result,command.values,flush=True)
            pose = self.core.pose or Pose()
            status = DroneTeleop.TimedStatus(RTC.Time(0,0),getattr(DroneTeleop,self.core.phase),self.core.detail,self.core.pose is not None,
                       pose.x,pose.y,pose.z,pose.roll,pose.pitch,pose.yaw,self.core.pending is not None,False)
            OpenRTM_aist.setTimestamp(status)
            self._statusOut.write(status)
            state = (self.core.phase,self.core.detail)
            if state != self._last_phase:
                print("CONTROL_STATE",*state,"pose",pose,flush=True)
                self._last_phase = state
            return RTC.RTC_OK
        except Exception:
            traceback.print_exc()
            self.core.fault("Middleware error; see controller log")
            return RTC.RTC_ERROR''')
        insertion='''    def _bind_native(self, port, codec, channel, size):
        prop = OpenRTM_aist.Properties()
        for key,value in {"interface_type":"hakoniwa","dataflow_type":"push","subscription_type":"flush",
                          "marshaling_type":codec,"hakoniwa.robot":"Drone","hakoniwa.channel":str(channel),
                          "hakoniwa.pdu_size":str(size),"hakoniwa.poll_interval":"0.02",
                          "buffer.length":"1","buffer.write.full_policy":"overwrite","sync_readwrite":"NO"}.items():
            prop.setProperty("dataport."+key,value)
        values = []
        OpenRTM_aist.NVUtil.copyFromProperties(values,prop)
        profile = RTC.ConnectorProfile("native-"+port.getName().replace(".","-"),"",[port.getPortRef()],values)
        result,profile = port.connect(profile)
        if result != RTC.RTC_OK:
            raise RuntimeError("Native endpoint binding failed: "+port.getName())
        self._native_ports.append(port)

'''
        text=text.replace('\ndef DroneTeleopControllerRTCInit', '\n'+insertion+'\ndef DroneTeleopControllerRTCInit')
        text=text.replace('mgr = OpenRTM_aist.Manager.init(sys.argv)','mgr = OpenRTM_aist.Manager.init(argv)')
    if name=='DroneTeleopControllerRTC':
        text=text.replace('def MyModuleInit(manager):', 'def MyModuleInit(manager):\n    HakoniwaTransportInit(manager)\n    DroneSerializersInit(manager)')
        text=text.replace('"hakoniwa.pdu_size":str(size),"hakoniwa.poll_interval":"0.02",',
                          '"hakoniwa.pdu_size":str(size),"hakoniwa.poll_interval":"0.02","hakoniwa.skip_zero_packet":"YES",')
    source.write_text(text,encoding='utf-8')
    # Include plain-data implementation modules in generated Python packaging.
    cmake=folder/'CMakeLists.txt'
    content=cmake.read_text()
    modules=['JoystickCore.py','JoystickView.py'] if name=='DroneJoystickGUIRTC' else ['TeleopCore.py']
    content+='\ninstall(FILES '+' '.join(modules)+' DESTINATION "${RTM_DATA_DIR}/${PROJECT_NAME}")\n'
    cmake.write_text(content)
    print('Implemented integration:',source)

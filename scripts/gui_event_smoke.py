"""WSLg Tk widget-event E2E harness for the real generated GUI RTC.

Uses production widgets and ports, not a new runtime control API. Lifecycle and
connections are performed externally by the normal rtshell scripts.
"""
import json
import os
from pathlib import Path
import sys
import subprocess
import time
import traceback
import tkinter as tk
from datetime import datetime,timezone
from verification_evidence import fingerprint

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'build/generated/DroneJoystickGUIRTC'))
import DroneJoystickGUIRTC as G
import OpenRTM_aist as RTM
from JoystickView import JoystickView

run=Path(os.environ['RUN_DIR'])
tested_fingerprint=fingerprint()
started_at=datetime.now(timezone.utc).isoformat()
manager=RTM.Manager.init([a for a in sys.argv if not a.startswith('--instance_name=')])
manager.setModuleInitProc(G.MyModuleInit)
assert manager.activateManager()
manager.runManager(True)
root=tk.Tk()
view=JoystickView(root,G.GUI_COMPONENT.model)
model=G.GUI_COMPONENT.model
result={'passed':False,'method':'WSLg Tk production widget events -> actual typed RTC ports -> custom Hakoniwa PDU -> native simulator',
        'manualWindowsMouseTest':False,'samples':[]}
stage='ready'
start=time.monotonic()
since=start
case_index=0
cases=[('x',0,190,115,0,.07),('y',0,115,45,1,.07),('z',1,115,45,2,.07),('yaw',1,185,115,3,1.)]
baseline=None
settled=None
released_command_count=None
failed=False


def advance(value):
    global stage,since
    stage=value; since=time.monotonic()
    print('GUI_TEST_STAGE',stage,flush=True)


def tick():
    global case_index,baseline,settled,failed,released_command_count
    try:
        wall=time.monotonic()
        if wall-start>180: raise TimeoutError('GUI smoke exceeded 180 seconds')
        status=model.get_status()
        if not status:
            root.after(50,tick); return
        phase,detail,pose,pending=status
        if phase=='FAULT': raise RuntimeError('Controller fault: '+detail)
        if not result['samples'] or wall-result['samples'][-1]['wall']>.2:
            result['samples'].append(dict(wall=wall,phase=phase,pose=pose,pending=pending))
        if stage=='ready' and phase=='READY' and not view.takeoff.instate(['disabled']):
            result['initialPose']=pose
            print('GUI_TEST_ACTION takeoff enabled=',model.active,flush=True)
            view.takeoff.invoke()
            advance('takeoff')
        elif stage=='takeoff' and phase=='ACTIVE' and not pending:
            assert pose[2]>.7,pose
            result['airbornePose']=pose
            baseline=pose
            axis,canvas,x,y,index,threshold=cases[case_index]
            view.canvases[canvas].event_generate('<ButtonPress-1>',x=x,y=y)
            advance('moving-'+axis)
        elif stage.startswith('moving-'):
            axis,canvas,x,y,index,threshold=cases[case_index]
            if pose[index]-baseline[index]>threshold:
                view.canvases[canvas].event_generate('<ButtonRelease-1>',x=x,y=y)
                advance('settle-'+axis)
            elif wall-since>25:
                raise TimeoutError('No measured movement for '+axis+': '+repr(pose))
        elif stage.startswith('settle-') and phase=='ACTIVE' and not pending and wall-since>3.:
            settled=pose
            released_command_count=(run/'controller.out').read_text().count('PDU_WRITE move request True')
            advance('released-'+cases[case_index][0])
        elif stage.startswith('released-') and wall-since>1.:
            axis,canvas,x,y,index,threshold=cases[case_index]
            count=(run/'controller.out').read_text().count('PDU_WRITE move request True')
            assert count==released_command_count,('new command after input release',released_command_count,count)
            result.setdefault('axes',{})[axis]=dict(before=baseline,after=pose,releaseStopsNewCommands=True,
                settlingDrift=pose[index]-settled[index])
            case_index+=1
            if case_index<len(cases):
                baseline=pose
                axis,canvas,x,y,index,threshold=cases[case_index]
                view.canvases[canvas].event_generate('<ButtonPress-1>',x=x,y=y)
                advance('moving-'+axis)
            else:
                assert not view.land.instate(['disabled'])
                view.land.invoke()
                advance('landing')
        elif stage=='landing' and phase=='READY' and not pending:
            assert abs(pose[2])<.2,pose
            result['landedPose']=pose
            result['passed']=True
            print('PASS: GUI takeoff, X/Y/Z/yaw joystick motion, no new commands after release, and landing measured',flush=True)
            root.after(100,view.close)
            return
        root.after(50,tick)
    except Exception:
        failed=True
        traceback.print_exc()
        result['failure']=traceback.format_exc()
        model.disable()
        root.after(100,view.close)


root.after(200,tick)
try:
    root.mainloop()
finally:
    model.active=False; model.disable()
    manager.shutdown()
    result['durationSeconds']=time.monotonic()-start
    result['startedAtUTC']=started_at
    result['finishedAtUTC']=datetime.now(timezone.utc).isoformat()
    result['implementationFingerprint']=tested_fingerprint['sha256']
    result['command']=[sys.executable,*sys.argv]
    if tested_fingerprint!=fingerprint():
        result['passed']=False; result['failure']='Implementation changed during test'
    # These exact deployed port mappings are covered by measured pose and each
    # command's request/completion/ack log, rather than by a global success flag.
    covered_ports=set()
    log=(run/'controller.out').read_text()
    check_command=[sys.executable,str(ROOT/'scripts/single_port_connections.py'),
        '--rtc','/localhost:2809/teleop-controller-1.rtc','--config',str(ROOT/'build/system/teleop/native-connections.ini'),'--action','check']
    check=subprocess.run(check_command,capture_output=True,text=True,timeout=15)
    result['nativeConnectionCheck']={'command':check_command,'exitCode':check.returncode,'stdout':check.stdout,'stderr':check.stderr}
    if check.returncode:
        result['passed']=False
        result['failure']='External native connection verification failed'
    if result['passed'] and check.returncode==0:
        covered_ports.add('pose')
        for kind in ('takeoff','move','land'):
            if ('PDU_WRITE '+kind+' request True') in log and ('PDU_WRITE '+kind+' request False') in log and (kind+' completed') in log:
                covered_ports.update((kind+'_request',kind+'_response'))
    contracts=json.loads((ROOT/'build/system/connection-contracts.json').read_text())
    result['validatedEdgeIds']=[]
    for edge_id,contract in contracts['edges'].items():
        ends=contract['endpoints']
        for side in ('source','target'):
            if ends[side]=='teleop-controller-1' and ends[side+'Handle'] in covered_ports:
                result['validatedEdgeIds'].append(edge_id)
    result['exitCode']=0 if result['passed'] else 1
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    raw=json.dumps(result,indent=2)+'\n'
    (run/('gui-smoke-result-'+stamp+'.json')).write_text(raw)
    (run/'gui-smoke-result.json').write_text(raw)
sys.exit(0 if result['passed'] else 1)

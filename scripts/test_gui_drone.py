"""Behavioral tests for the approved GUI teleoperation implementation."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'build/generated/common'),str(ROOT/'build/generated/DroneTeleopControllerRTC'),
              str(ROOT/'build/generated/DroneJoystickGUIRTC')]
from TeleopCore import TeleopCore, Pilot, Pose, Command
from JoystickCore import JoystickModel


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.core=TeleopCore()
        self.wall=10.
        self.sim=1.
        self.core.observe_pose(Pose(z=1),self.wall)

    def tick(self,responses=None,dt=.05):
        self.wall+=dt; self.sim+=dt
        self.core.observe_pose(self.core.pose or Pose(z=1),self.wall)
        return self.core.tick(self.sim,self.wall,responses)

    def test_takeoff_response_ack_then_move(self):
        self.core.input(Pilot(1,False,action='TAKEOFF'),self.wall)
        command=self.tick()[0]
        self.assertEqual(command.kind,'takeoff')
        self.assertFalse(self.core.airborne)
        ack=self.tick({'takeoff':Command('takeoff',command.values,False,True,0)})[0]
        self.assertFalse(ack.request); self.assertFalse(ack.result)
        self.assertTrue(self.core.pending['ack'])
        self.tick({'takeoff':ack})
        self.assertTrue(self.core.airborne)
        self.core.input(Pilot(2,True,(1,1,1,0)),self.wall)
        move=self.tick(dt=.21)[0]
        self.assertEqual(move.kind,'move')
        self.assertAlmostEqual(sum((move.values[k]-getattr(self.core.pose,k))**2 for k in ('x','y','z'))**.5,.2)

    def test_stale_and_duplicate_input_cannot_move(self):
        self.core.airborne=True
        self.core.input(Pilot(1,True,(1,0,0,0)),self.wall)
        self.assertEqual(self.tick(dt=.31),[])
        self.core.input(Pilot(1,True,(1,0,0,0)),self.wall)
        self.assertEqual(self.tick(),[])

    def test_disable_does_not_overwrite_pending_request(self):
        self.core.airborne=True
        self.core.input(Pilot(1,True,(1,0,0,0)),self.wall)
        self.assertEqual(len(self.tick()),1)
        self.core.input(Pilot(2,False),self.wall)
        self.assertEqual(self.tick(),[])
        self.assertEqual(self.core.pending['command'].kind,'move')

    def test_wrong_response_does_not_complete(self):
        self.core.airborne=True
        self.core.input(Pilot(1,True,(1,0,0,0)),self.wall)
        command=self.tick()[0]
        wrong=dict(command.values,x=99)
        self.assertEqual(self.tick({'move':Command('move',wrong,False,True)}),[])
        self.assertFalse(self.core.pending['ack'])

    def test_timeout_and_reset_latch_fault(self):
        self.core.input(Pilot(1,False,action='TAKEOFF'),self.wall)
        self.tick()
        self.tick(dt=25.1)
        self.assertEqual(self.core.phase,'FAULT')
        self.assertEqual(self.tick(),[])
        core=TeleopCore(); core.tick(10,1); core.tick(0,2)
        self.assertEqual(core.phase,'FAULT')

    def test_land_queued_until_pending_ack_cleared(self):
        self.core.airborne=True
        self.core.input(Pilot(1,True,(1,0,0,0)),self.wall)
        command=self.tick()[0]
        self.core.input(Pilot(2,False,action='LAND'),self.wall)
        self.assertEqual(self.tick(),[])
        ack=self.tick({'move':Command('move',command.values,False,True)})[0]
        self.tick({'move':ack})
        self.assertEqual(self.tick()[0].kind,'land')

    def test_gui_release_and_one_shot_action(self):
        model=JoystickModel(); model.active=True
        model.set_axes(0,2.,-.5)
        self.assertEqual(model.snapshot().axes,(1.,-.5,0.,0.))
        model.disable(); self.assertFalse(model.snapshot().enabled)
        model.request('TAKEOFF'); self.assertEqual(model.snapshot().action,'TAKEOFF')
        self.assertEqual(model.snapshot().action,'NONE')

    def test_gui_status_is_unknown_after_controller_heartbeat_loss(self):
        model=JoystickModel()
        with patch('JoystickCore.time.monotonic',return_value=10):
            model.update_status(('READY','ready',(0,0,0,0),False))
            self.assertIsNotNone(model.get_status())
        with patch('JoystickCore.time.monotonic',return_value=12):
            self.assertIsNone(model.get_status())


class SerializerTests(unittest.TestCase):
    def test_command_bytes_and_padding_match_foundation(self):
        import OpenRTM_aist as R
        import DroneSerializers as S
        import importlib
        S.DroneSerializersInit(None)
        for kind,(name,datatype,fields,size) in S.CODECS.items():
            serializer=R.SerializerFactories.instance().createSerializer(name,datatype)
            data=R.instantiateDataType(datatype)
            data.request=True; data.result=False; data.result_code=0
            for index,field in enumerate(fields): setattr(data,field,.5+index)
            status,raw=serializer.serialize(data)
            self.assertEqual(status,serializer.SERIALIZE_OK)
            self.assertEqual(len(raw),size)
            packet_name='HakoDroneCmd'+kind.title()
            packet=getattr(importlib.import_module('hakoniwa_pdu.pdu_msgs.hako_msgs.pdu_pytype_'+packet_name),packet_name)()
            packet.header.request=True
            for field in fields: setattr(packet,field,getattr(data,field))
            encode=getattr(importlib.import_module('hakoniwa_pdu.pdu_msgs.hako_msgs.pdu_conv_'+packet_name),'py_to_pdu_'+packet_name)
            expected=bytes(encode(packet))
            self.assertEqual(raw,expected+bytes(size-len(expected)))
            decoded=serializer.deserialize(raw,data)[1]
            self.assertEqual([getattr(decoded,f) for f in fields],[getattr(data,f) for f in fields])
            self.assertEqual(serializer.deserialize(raw[:-1],data)[0],serializer.SERIALIZE_ERROR)

    def test_pose_is_position_not_velocity(self):
        import RTC
        import OpenRTM_aist as R
        from DroneSerializers import PoseCodec
        from hakoniwa_pdu.pdu_msgs.geometry_msgs.pdu_pytype_Twist import Twist
        from hakoniwa_pdu.pdu_msgs.geometry_msgs.pdu_conv_Twist import py_to_pdu_Twist
        packet=Twist(); packet.linear.x=2.; packet.angular.z=.4
        codec=PoseCodec()
        status,data=codec.deserialize(py_to_pdu_Twist(packet),R.instantiateDataType(RTC.TimedPose3D))
        self.assertEqual(status,codec.SERIALIZE_OK)
        self.assertEqual(data.data.position.x,2.)
        self.assertEqual(data.data.orientation.y,.4)
        self.assertEqual((data.tm.sec,data.tm.nsec),(0,0))
        self.assertEqual(codec.deserialize(bytes(72),data)[0],codec.SERIALIZE_ERROR)


if __name__=='__main__': unittest.main()

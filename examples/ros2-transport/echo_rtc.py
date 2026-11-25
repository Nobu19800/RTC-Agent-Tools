"""Test RTC that echoes incoming TimedString values."""

import signal
import sys
from threading import Event

import OpenRTM_aist
import RTC
import rclpy


class Echo(OpenRTM_aist.DataFlowComponentBase):
    def onInitialize(self):
        self.input = RTC.TimedString(RTC.Time(0, 0), "")
        self.output = RTC.TimedString(RTC.Time(0, 0), "")
        self.in_port = OpenRTM_aist.InPort("input", self.input)
        self.out_port = OpenRTM_aist.OutPort("output", self.output)
        self.addInPort("input", self.in_port)
        self.addOutPort("output", self.out_port)
        return RTC.RTC_OK

    def onExecute(self, ec_id):
        if self.in_port.isNew():
            self.output.data = "rtc-echo:" + self.in_port.read().data
            self.out_port.write()
        return RTC.RTC_OK


def register(manager):
    profile = OpenRTM_aist.Properties(defaults_str=[
        "implementation_id", "RtsdEcho", "type_name", "RtsdEcho",
        "activity_type", "PERIODIC", "max_instance", "1",
        "language", "Python", "lang_type", "SCRIPT", "",
    ])
    manager.registerFactory(profile, Echo, OpenRTM_aist.Delete)
    manager.createComponent("RtsdEcho")


if __name__ == "__main__":
    manager = OpenRTM_aist.Manager.init(sys.argv)
    manager.setModuleInitProc(register)
    manager.activateManager()
    finished = Event()
    signal.signal(signal.SIGINT, lambda *_: finished.set())
    manager.runManager(no_block=True)
    finished.wait()
    # The installed transport does not join its spin thread before destroying
    # the node. Join it inside this fixture before triggering Manager shutdown.
    transport = sys.modules["ROS2TopicManager"].ROS2TopicManager.instance()
    transport._loop = False
    if transport._thread is not None:
        transport._thread.join()
    manager.terminate()
    manager.join()
    rclpy.try_shutdown()

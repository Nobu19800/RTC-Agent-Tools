"""Map the standard TkJoyStick pos OutPort to a ROS 2 Twist."""

import math

import OpenRTM_aist
import ROS2MessageInfo
import RTC
from geometry_msgs.msg import Twist

MARSHALING_TYPE = "ros2:tkjoystick/Twist"
AXIS_FULL_SCALE = 120.0
LINEAR_LIMIT = 2.0
ANGULAR_LIMIT = 2.0


class TkJoyStickTwistSerializer(OpenRTM_aist.ByteDataStreamBase):
    def serialize(self, data):
        message = Twist()
        axes = data.data
        if len(axes) == 2 and all(math.isfinite(value) for value in axes):
            x, y = (max(-1.0, min(1.0, value / AXIS_FULL_SCALE)) for value in axes)
            message.linear.x = LINEAR_LIMIT * y
            message.angular.z = -ANGULAR_LIMIT * x
        return self.SERIALIZE_OK, message


def TkJoyStickTwistSerializerInit(manager):
    OpenRTM_aist.SerializerFactories.instance().addSerializer(
        MARSHALING_TYPE, TkJoyStickTwistSerializer, RTC.TimedFloatSeq)
    ROS2MessageInfo.ROS2MessageInfoList.instance().addInfo(
        MARSHALING_TYPE, ROS2MessageInfo.ROS2MessageInfo(Twist))

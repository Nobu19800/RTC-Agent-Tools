"""Fixed-layout example: RTC.TimedVelocity3D <-> Hakoniwa Twist (not ROS CDR)."""
import struct
import sys

import OpenRTM_aist
import RTC

MARSHALING_TYPE = "hakoniwa:geometry_msgs/Twist:raw48"
METADATA_MARSHALING_TYPE = "hakoniwa:geometry_msgs/Twist:metadata72"
TWIST = struct.Struct("<6d")
HEADER = struct.Struct("<5I4x")
METADATA = (0x12345678, 1, 24, 72, 72)


class VelocityTwistSerializer(OpenRTM_aist.ByteDataStreamBase):
    def isLittleEndian(self, little_endian):
        # PDU layout is fixed; CORBA connector endian negotiation cannot change it.
        pass

    def serialize(self, data):
        try:
            if sys.byteorder != "little" or not isinstance(data, RTC.TimedVelocity3D):
                return self.SERIALIZE_ERROR, b""
            v = data.data
            return self.SERIALIZE_OK, TWIST.pack(v.vx, v.vy, v.vz, v.vr, v.vp, v.va)
        except (AttributeError, TypeError, ValueError, OverflowError, struct.error):
            return self.SERIALIZE_ERROR, b""

    def deserialize(self, payload, data):
        try:
            if sys.byteorder != "little" or not isinstance(data, RTC.TimedVelocity3D):
                return self.SERIALIZE_ERROR, data
            values = TWIST.unpack(payload)  # Exact length required, before mutation.
            data.data = RTC.Velocity3D(*values)
            # Twist has no acquisition timestamp. Zero explicitly means unknown.
            data.tm = RTC.Time(0, 0)
            return self.SERIALIZE_OK, data
        except (TypeError, ValueError, struct.error):
            return self.SERIALIZE_ERROR, data


class MetadataVelocityTwistSerializer(VelocityTwistSerializer):
    """Pinned hako_binary v1 metadata format, fixed-size Twist only."""
    def serialize(self, data):
        status, payload = super().serialize(data)
        if status != self.SERIALIZE_OK:
            return status, payload
        return status, HEADER.pack(*METADATA) + payload

    def deserialize(self, payload, data):
        try:
            if len(payload) != 72 or HEADER.unpack_from(payload) != METADATA:
                return self.SERIALIZE_ERROR, data
            return super().deserialize(payload[24:], data)
        except (TypeError, ValueError, struct.error):
            return self.SERIALIZE_ERROR, data


def HakoniwaSerializerInit(manager):
    OpenRTM_aist.SerializerFactories.instance().addSerializer(
        MARSHALING_TYPE, VelocityTwistSerializer, RTC.TimedVelocity3D)
    OpenRTM_aist.SerializerFactories.instance().addSerializer(
        METADATA_MARSHALING_TYPE, MetadataVelocityTwistSerializer, RTC.TimedVelocity3D)

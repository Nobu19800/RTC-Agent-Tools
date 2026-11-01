"""Real OpenRTM API tests; only the unavailable Hakoniwa native backend is faked."""
import ctypes
from pathlib import Path
import struct
import sys
import threading
import types
import unittest
from unittest.mock import patch

import OpenRTM_aist as RTM
import RTC

from HakoniwaSerializer import (HakoniwaSerializerInit, MARSHALING_TYPE,
    VelocityTwistSerializer, MetadataVelocityTwistSerializer)
from HakoniwaTransport import (HakoniwaTransportInit, HakoniwaInPortConsumer,
                               HakoniwaInPortProvider, PduEndpoint)


def properties(size=48):
    p = RTM.Properties()
    for key, value in {
        "hakoniwa.robot": "Robot", "hakoniwa.channel": "0",
        "hakoniwa.pdu_size": str(size), "hakoniwa.poll_interval": "0.01",
        "marshaling_type": MARSHALING_TYPE, "subscription_type": "flush",
        "buffer.write.full_policy": "overwrite",
    }.items():
        p.setProperty(key, value)
    return p


class MemoryPdu:
    def __init__(self):
        self.payload = bytearray(48)
        self.fail = False

    def pdu_write(self, robot, channel, payload, size):
        assert isinstance(payload, bytearray)
        assert (robot, channel, len(payload)) == ("Robot", 0, size)
        if self.fail:
            return False
        self.payload = payload[:]
        return True

    def pdu_read(self, robot, channel, size):
        if self.fail:
            raise RuntimeError("test read failure")
        return self.payload[:]


def velocity():
    return RTC.TimedVelocity3D(RTC.Time(12, 34), RTC.Velocity3D(1, -2, 3, -4, 5, -6))


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        RTM.Manager.init(["test_hakoniwa", "-o", "naming.enable:NO",
                          "-o", "logger.enable:NO"])
        HakoniwaTransportInit(None)
        HakoniwaSerializerInit(None)

    def test_factory_and_c_layout(self):
        serializer = RTM.SerializerFactories.instance().createSerializer(MARSHALING_TYPE, velocity())
        status, payload = serializer.serialize(velocity())
        self.assertEqual(status, serializer.SERIALIZE_OK)
        class Vector3(ctypes.LittleEndianStructure):
            _fields_ = [(axis, ctypes.c_double) for axis in ("x", "y", "z")]
        class Twist(ctypes.LittleEndianStructure):
            _fields_ = [("linear", Vector3), ("angular", Vector3)]
        self.assertEqual(ctypes.sizeof(Twist), 48)
        self.assertEqual(Twist.angular.offset, 24)
        self.assertEqual(payload, bytes(Twist(Vector3(1, -2, 3), Vector3(-4, 5, -6))))
        status, result = serializer.deserialize(payload, velocity())
        self.assertEqual(status, serializer.SERIALIZE_OK)
        self.assertEqual((result.tm.sec, result.tm.nsec), (0, 0))
        self.assertEqual(result.data.va, -6)
        self.assertIsNone(RTM.SerializerFactories.instance().createSerializer(
            MARSHALING_TYPE, RTC.TimedLong(RTC.Time(0, 0), 1)))

    def test_malformed_no_partial_mutation(self):
        s = VelocityTwistSerializer()
        for payload in (b"", bytes(47), bytes(49)):
            data = velocity()
            status, result = s.deserialize(payload, data)
            self.assertEqual(status, s.SERIALIZE_ERROR)
            self.assertEqual(result.data.vx, 1)
            self.assertEqual(result.tm.sec, 12)

    def test_metadata_matches_upstream_python_writer(self):
        bindings = Path(__file__).resolve().parents[2] / "build/reference/hakoniwa-core-cpp-client/bindings/python"
        if not bindings.is_dir():
            self.skipTest("upstream reference checkout required for byte compatibility check")
        with patch.object(sys, "path", [str(bindings)] + sys.path):
            from hako_binary import binary_writer, binary_reader, offset_map
            offsets = offset_map.create_offmap(str(bindings / "hako_binary/offset"))
            expected = bytearray(48)
            message = {"linear": dict(x=1, y=-2, z=3), "angular": dict(x=-4, y=5, z=-6)}
            binary_writer.binary_write(offsets, expected, message, "geometry_msgs/Twist")
            serializer = MetadataVelocityTwistSerializer()
            status, payload = serializer.serialize(velocity())
            self.assertEqual(status, serializer.SERIALIZE_OK)
            self.assertEqual(len(expected), 72)
            self.assertEqual(payload, expected)
            self.assertEqual(binary_reader.binary_read(offsets, "geometry_msgs/Twist", bytearray(payload)), message)
            self.assertEqual(serializer.deserialize(expected, velocity())[0], serializer.SERIALIZE_OK)
            for bad in (bytes(72), payload[:48], payload + b"x"):
                self.assertEqual(serializer.deserialize(bad, velocity())[0], serializer.SERIALIZE_ERROR)

    def test_type_independent_bytes_and_size_errors(self):
        for size in (4, 48, 97):
            backend = MemoryPdu()
            endpoint = PduEndpoint(properties(size), backend)
            payload = bytes(range(size))
            self.assertTrue(endpoint.write(payload))
            self.assertEqual(endpoint.read(), payload)
            with self.assertRaises(ValueError):
                endpoint.write(payload + b"x")
        for size in (0, -1):
            with self.assertRaises(ValueError):
                PduEndpoint(properties(size), MemoryPdu())

    def test_real_push_connectors(self):
        backend = MemoryPdu()
        with patch.dict(sys.modules, {"hakopy": backend}):
            p = properties()
            info = RTM.ConnectorInfo("offline-hakoniwa", "test-id", [], p)
            consumer = RTM.InPortConsumerFactory.instance().createObject("hakoniwa")
            provider = RTM.InPortProviderFactory.instance().createObject("hakoniwa")
            listeners = RTM.ConnectorListeners()
            sender = RTM.OutPortPushConnector(info, consumer, listeners)
            receiver = RTM.InPortPushConnector(info, provider, RTM.ConnectorListeners())
            sender.setDataType(velocity())
            receiver.setDataType(velocity())
            # Explicit single step keeps this test deterministic without a poll thread.
            provider._connector = receiver
            try:
                self.assertEqual(sender.write(velocity()), RTM.DataPortStatus.PORT_OK)
                provider.receive_once()
                status, result = receiver.read(velocity())
                self.assertEqual(status, RTM.DataPortStatus.PORT_OK)
                self.assertEqual(result.data.vp, 5)
                self.assertEqual(result.tm.sec, 0)
                backend.fail = True
                self.assertEqual(consumer.put(bytes(48)), RTM.DataPortStatus.PORT_ERROR)
                with self.assertRaises(RuntimeError):
                    provider.receive_once()
            finally:
                receiver.disconnect()
                sender.disconnect()

    def test_connector_subscription_and_invalid_settings(self):
        backend = MemoryPdu()
        consumer = HakoniwaInPortConsumer()
        profile = []
        p = RTM.Properties()
        for key in properties().propertyNames():
            p.setProperty("dataport." + key, properties().getProperty(key))
        RTM.NVUtil.copyFromProperties(profile, p)
        with patch.dict(sys.modules, {"hakopy": backend}):
            self.assertTrue(consumer.subscribeInterface(profile))
            self.assertEqual(consumer.put(bytes(48)), RTM.DataPortStatus.PORT_OK)
            consumer.unsubscribeInterface(profile)
            self.assertEqual(consumer.put(bytes(48)), RTM.DataPortStatus.PORT_ERROR)
            for key, value in (("hakoniwa.poll_interval", "nan"),
                               ("hakoniwa.poll_interval", "0"),
                               ("sync_readwrite", "YES"),
                               ("buffer.write.full_policy", "block")):
                invalid = properties()
                invalid.setProperty(key, value)
                provider = HakoniwaInPortProvider()
                with self.assertRaises(ValueError):
                    provider.init(invalid)
                provider.exit()

    def test_poll_stop_and_read_failure(self):
        backend = MemoryPdu()
        provider = HakoniwaInPortProvider()
        with patch.dict(sys.modules, {"hakopy": backend}):
            provider.init(properties())
        received = threading.Event()
        connector = types.SimpleNamespace(write=lambda payload: (
            received.set() or RTM.BufferStatus.BUFFER_OK))
        try:
            provider.setConnector(connector)
            self.assertTrue(received.wait(1))
        finally:
            provider.exit()
        self.assertIsNone(provider._thread)
        backend.fail = True
        with self.assertLogs("HakoniwaTransport", level="ERROR"):
            provider.setConnector(connector)
            self.assertTrue(provider._stop.wait(1))
            provider.exit()

    def test_metadata_zero_placeholder_is_skipped_only_when_configured(self):
        backend = MemoryPdu()
        provider = HakoniwaInPortProvider()
        prop = properties()
        prop.setProperty("hakoniwa.skip_zero_packet", "YES")
        with patch.dict(sys.modules, {"hakopy": backend}):
            provider.init(prop)
        writes=[]
        provider._connector=types.SimpleNamespace(write=lambda raw: (writes.append(raw) or RTM.BufferStatus.BUFFER_OK))
        provider.receive_once()
        self.assertEqual(writes,[])
        backend.payload[0]=1
        provider.receive_once()
        self.assertEqual(len(writes),1)
        provider.exit()


if __name__ == "__main__":
    unittest.main()

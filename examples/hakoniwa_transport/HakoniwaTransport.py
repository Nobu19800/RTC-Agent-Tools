"""Experimental type-independent push transport over an already registered hakopy asset.

The application owns asset_register/start/stop and simulation timing. Loading this
module neither registers an asset nor starts a simulation. One writer per channel.
"""
import importlib
import logging
import math
import threading

import OpenRTM_aist

LOG = logging.getLogger(__name__)


class PduEndpoint:
    """No RTC/ROS message types: only robot, channel, size and opaque bytes."""
    def __init__(self, prop, backend=None):
        self.robot = prop.getProperty("hakoniwa.robot")
        self.channel = int(prop.getProperty("hakoniwa.channel"))
        self.size = int(prop.getProperty("hakoniwa.pdu_size"))
        if not self.robot or self.channel < 0 or self.size <= 0:
            raise ValueError("robot, nonnegative channel and positive pdu_size required")
        self.backend = backend if backend is not None else importlib.import_module("hakopy")

    def write(self, payload):
        if not isinstance(payload, (bytes, bytearray, memoryview)) or len(payload) != self.size:
            raise ValueError("serialized payload must match configured PDU size")
        # The inspected native binding uses PyArg_ParseTuple 'Y': bytearray required.
        return self.backend.pdu_write(self.robot, self.channel, bytearray(payload), self.size)

    def read(self):
        payload = self.backend.pdu_read(self.robot, self.channel, self.size)
        if not isinstance(payload, (bytes, bytearray)) or len(payload) != self.size:
            raise ValueError("invalid PDU read result")
        return bytes(payload)


class HakoniwaInPortConsumer(OpenRTM_aist.InPortConsumer):
    def __init__(self):
        self._endpoint = None

    def init(self, prop):
        # OpenRTM calls init first with consumer subtree, then full connector props.
        if prop.getProperty("hakoniwa.robot"):
            self._endpoint = PduEndpoint(prop)

    def put(self, data):
        try:
            if self._endpoint is not None and self._endpoint.write(data):
                return self.PORT_OK
        except Exception:
            LOG.exception("Hakoniwa PDU write failed")
        return self.PORT_ERROR

    def publishInterfaceProfile(self, properties):
        pass

    def subscribeInterface(self, properties):
        prop = OpenRTM_aist.Properties()
        OpenRTM_aist.NVUtil.copyToProperties(prop, properties)
        try:
            self.init(prop.getNode("dataport"))
            return self._endpoint is not None
        except (ImportError, TypeError, ValueError):
            LOG.exception("Invalid Hakoniwa connector settings")
            return False

    def unsubscribeInterface(self, properties):
        self._endpoint = None


class HakoniwaInPortProvider(OpenRTM_aist.InPortProvider):
    def __init__(self):
        super().__init__()
        self.setInterfaceType("hakoniwa")
        self._endpoint = None
        self._interval = 0.01
        self._stop = threading.Event()
        self._thread = None
        self._skip_zero_packet = False

    def init(self, prop):
        if prop.getProperty("hakoniwa.robot"):
            interval = float(prop.getProperty("hakoniwa.poll_interval", "0.01"))
            if not math.isfinite(interval) or interval <= 0:
                raise ValueError("poll_interval must be finite and positive")
            if prop.getProperty("sync_readwrite", "NO").upper() == "YES":
                raise ValueError("synchronous read/write is unsupported")
            if prop.getProperty("buffer.write.full_policy", "overwrite") == "block":
                raise ValueError("blocking buffer writes are unsupported")
            self._endpoint = PduEndpoint(prop)
            self._interval = interval
            self._skip_zero_packet = prop.getProperty("hakoniwa.skip_zero_packet", "NO").upper() == "YES"

    def setBuffer(self, buffer):
        pass

    def setListener(self, info, listeners):
        pass

    def setConnector(self, connector):
        if self._thread is not None:
            raise RuntimeError("provider already connected")
        if self._endpoint is None:
            raise ValueError("Hakoniwa connector settings missing")
        super().setConnector(connector)
        self._stop.clear()
        self._thread = threading.Thread(target=self._poll, name="HakoniwaPduPoll", daemon=True)
        self._thread.start()

    def receive_once(self):
        """Sample latest PDU. No freshness/queue guarantee is provided by hakopy."""
        payload = self._endpoint.read()
        # Opt-in contract for metadata-bearing native buffers before first write.
        # Zero is valid for other binary formats, so this is never a default.
        if self._skip_zero_packet and not any(payload):
            return
        result = self._connector.write(payload)
        if result != OpenRTM_aist.BufferStatus.BUFFER_OK:
            raise RuntimeError("OpenRTM receive buffer rejected PDU: %s" % result)

    def _poll(self):
        while not self._stop.wait(self._interval):
            try:
                self.receive_once()
            except Exception:
                # Fail visibly once; avoid a log storm and a silently dead poll loop.
                LOG.exception("Hakoniwa receive stopped; disconnect/reconnect after recovery")
                self._stop.set()

    def exit(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            if self._thread.is_alive():
                raise RuntimeError("Hakoniwa PDU read did not stop within 2 seconds")
            self._thread = None
        self._connector = None


def HakoniwaTransportInit(manager):
    # Push only. Pull/duplex are intentionally not advertised.
    OpenRTM_aist.InPortConsumerFactory.instance().addFactory(
        "hakoniwa", HakoniwaInPortConsumer)
    OpenRTM_aist.InPortProviderFactory.instance().addFactory(
        "hakoniwa", HakoniwaInPortProvider)

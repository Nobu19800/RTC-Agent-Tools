"""Unit checks for the generated DroneJoystickAdapter without middleware."""

import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest


SOURCE = (
    Path(__file__).resolve().parents[2]
    / "build/generated/DroneJoystickAdapter/DroneJoystickAdapter.py"
)


@pytest.fixture
def module(monkeypatch, tmp_path):
    if not SOURCE.is_file():
        pytest.fail(f"Generate the DroneJoystickAdapter first: {SOURCE}")
    for name in ("hakopy", "OpenRTM_aist", "RTC", "DroneTeleop", "HakoniwaTransport"):
        monkeypatch.setitem(sys.modules, name, ModuleType(name))
    rtm = sys.modules["OpenRTM_aist"]
    rtm.DataFlowComponentBase = object
    rtm.ByteDataStreamBase = type(
        "ByteDataStreamBase", (), {"SERIALIZE_OK": 0, "SERIALIZE_ERROR": 1}
    )
    rtm.setTimestamp = Mock()
    sys.modules["RTC"].RTC_OK = 0
    sys.modules["RTC"].RTC_ERROR = 1
    sys.modules["HakoniwaTransport"].HakoniwaTransportInit = Mock()
    spec = importlib.util.spec_from_file_location("DroneJoystickAdapter", SOURCE)
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    monkeypatch.setattr(adapter, "REQUEST", tmp_path / "action.request")
    monkeypatch.setattr(adapter, "time", SimpleNamespace(monotonic=lambda: 10.0))
    return adapter


@pytest.fixture
def adapter(module):
    rtc = module.Adapter()
    rtc.joystick = Mock()
    rtc.joystick.isNew.return_value = False
    rtc.pose = Mock()
    rtc.pose.isNew.return_value = False
    rtc.position = SimpleNamespace(x=1.0, y=2.0)
    rtc.airborne = True
    rtc.pending = None
    rtc.last_input = 10.0
    rtc.axes = (0, 0)
    rtc.send = Mock()
    return rtc


def test_caps_displacement_and_uses_configured_speed(module, adapter):
    adapter.joystick.isNew.return_value = True
    adapter.joystick.read.return_value = SimpleNamespace(data=[240.0, 0.0])
    assert adapter.onExecute(0) == module.RTC.RTC_OK
    adapter.send.assert_called_once_with(
        "move", (1.0 + module.MAX_MOVE_STEP_M, 2.0, 1.0,
                 module.MOVE_SPEED_MPS, 0.0), 10.0
    )


@pytest.mark.parametrize("axes,last_input", [
    ((0, 0), 10.0), ((120, 0), 9.0), ((float("nan"), 0), 10.0),
    ((120,), 10.0),
])
def test_ignores_centered_stale_or_invalid_input(module, adapter, axes, last_input):
    adapter.axes = axes
    adapter.last_input = last_input
    assert adapter.onExecute(0) == module.RTC.RTC_OK
    adapter.send.assert_not_called()


@pytest.mark.parametrize("action,airborne", [("takeoff", False), ("land", True)])
def test_explicit_action(module, adapter, action, airborne):
    adapter.airborne = airborne
    module.REQUEST.write_text(action, encoding="utf-8")
    assert adapter.onExecute(0) == module.RTC.RTC_OK
    assert adapter.send.call_args.args[0] == action
    assert not module.REQUEST.exists()


@pytest.mark.parametrize("result,code,deadline,expected", [
    (True, 0, 11.0, 0), (True, 1, 11.0, 1), (False, 0, 9.0, 1),
])
def test_pending_response(module, adapter, result, code, deadline, expected):
    adapter.pending = ("takeoff", deadline)
    adapter.airborne = False
    port = Mock()
    port.read.return_value = SimpleNamespace(
        result=result, request=False, result_code=code
    )
    adapter.responses = {"takeoff": port}
    assert adapter.onExecute(0) == expected
    adapter.send.assert_not_called()
    assert adapter.airborne is (result and code == 0)


def test_command_serializer_padding_and_round_trip(module, monkeypatch):
    packet = SimpleNamespace(header=SimpleNamespace(), x=0.0)
    encoder = Mock(return_value=b"ab")
    monkeypatch.setattr(module, "codecs", lambda *_: (
        lambda: packet, encoder, lambda _: packet
    ))
    serializer = module.command_serializer("move", 4, ["x"])()
    value = SimpleNamespace(request=True, result=False, result_code=0, x=3.0)
    assert serializer.serialize(value) == (0, b"ab\0\0")
    status, decoded = serializer.deserialize(b"ab\0\0", SimpleNamespace())
    assert status == 0
    assert vars(decoded) == vars(value)
    encoder.return_value = b"oversized"
    assert serializer.serialize(value) == (1, b"")

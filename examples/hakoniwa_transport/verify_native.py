"""Bounded native integration probe, no RTC activation or physical devices.

Uses Hakoniwa's external-I/O mode with a private mmap directory. Starts an empty
simulation to allocate PDU storage; does not verify asset step scheduling.
Run under the Linux Python matching the supplied native library.
"""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time


def load_native(path):
    spec = importlib.util.spec_from_file_location("hakopy", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["hakopy"] = module
    spec.loader.exec_module(module)
    return module


def sample(values):
    import RTC
    return RTC.TimedVelocity3D(RTC.Time(123, 456), RTC.Velocity3D(*values))


def vector(data):
    v = data.data
    return (v.vx, v.vy, v.vz, v.vr, v.vp, v.va)


def peer(args):
    import OpenRTM_aist as RTM
    from HakoniwaTransport import PduEndpoint
    from HakoniwaSerializer import VelocityTwistSerializer, MetadataVelocityTwistSerializer
    native = load_native(args.native_library)
    assert native.init_for_external(), "peer external initialization failed"
    p = RTM.Properties()
    p.setProperty("hakoniwa.robot", "SerializerProbe")
    p.setProperty("hakoniwa.channel", str(args.channel))
    p.setProperty("hakoniwa.pdu_size", str(args.size))
    codec = VelocityTwistSerializer() if args.size == 48 else MetadataVelocityTwistSerializer()
    status, payload = codec.serialize(sample((11, -22, 33, -44, 55, -66)))
    assert status == codec.SERIALIZE_OK
    assert PduEndpoint(p).write(payload), "peer write failed"
    print("PEER_WRITE_PASS", args.channel, args.size, flush=True)


def worker(args):
    import faulthandler
    faulthandler.dump_traceback_later(15)
    import OpenRTM_aist as RTM
    import RTC
    from HakoniwaSerializer import (HakoniwaSerializerInit, MARSHALING_TYPE,
        METADATA_MARSHALING_TYPE, VelocityTwistSerializer, MetadataVelocityTwistSerializer)
    from HakoniwaTransport import HakoniwaTransportInit
    native = load_native(args.native_library)
    print("ENV", sys.version, RTM.__file__, native.__file__, flush=True)
    manager = RTM.Manager.init(["native-probe", "-o", "naming.enable:NO",
                      "-o", "logger.log_level:WARN", "-o", "logger.file_name:STDOUT"])
    assert manager.activateManager(), "OpenRTM manager activation failed"
    manager.runManager(True)
    HakoniwaSerializerInit(None)
    HakoniwaTransportInit(None)
    hako_command = Path(args.native_library).resolve().parents[2] / "core/sample/base-procs/hako-cmd/hako-cmd"
    assert hako_command.is_file(), "build the hako-cmd target first"
    try:
        # Pinned upstream C API returns the implementation's bool as int, while
        # the Python wrapper treats zero as success. Record the return value and
        # establish readiness via external initialization, not this inverted bool.
        reported = native.conductor_start(1000, 1000)
        print("CONDUCTOR_START_REPORTED", reported, flush=True)
        assert native.init_for_external(), "external initialization failed"
        for channel, size in ((0, 48), (1, 72)):
            reported = native.pdu_create("SerializerProbe", channel, size)
            print("PDU_CREATE_REPORTED", channel, reported, flush=True)
        command(hako_command, "start")
        mmap = Path(os.environ["HAKO_CONFIG_PATH"]).parent / "mmap/mmap-0x100.bin"
        deadline = time.monotonic() + 3
        while not mmap.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert mmap.exists(), "PDU backing file not created after start"
        assert "status=running" in command(hako_command, "status")
        for channel, size, marshaling, codec in (
            (0, 48, MARSHALING_TYPE, VelocityTwistSerializer()),
            (1, 72, METADATA_MARSHALING_TYPE, MetadataVelocityTwistSerializer()),
        ):
            initial = sample((1, -2, 3, -4, 5, -6))
            status, initial_payload = codec.serialize(initial)
            assert status == codec.SERIALIZE_OK
            assert native.pdu_write("SerializerProbe", channel, bytearray(initial_payload), size)
            print("NATIVE_INITIAL_WRITE_PASS", channel, flush=True)
            output = RTM.OutPort("probe_out_%d" % channel, initial)
            incoming = RTM.InPort("probe_in_%d" % channel, sample((0, 0, 0, 0, 0, 0)))
            output.init(RTM.Properties())
            incoming.init(RTM.Properties())
            props = RTM.Properties()
            for key, value in {
                "interface_type": "hakoniwa", "dataflow_type": "push",
                "subscription_type": "flush", "marshaling_type": marshaling,
                "hakoniwa.robot": "SerializerProbe", "hakoniwa.channel": str(channel),
                "hakoniwa.pdu_size": str(size), "hakoniwa.poll_interval": "0.01",
                "buffer.write.full_policy": "overwrite", "sync_readwrite": "NO",
            }.items():
                props.setProperty("dataport." + key, value)
            try:
                result = RTM.connect("native-probe-%d" % channel, props,
                                     output.getPortRef(), incoming.getPortRef())
                assert result == RTC.RTC_OK, "DataPort connect failed: %s" % result
                assert len(output.get_connector_profiles()) == 1
                assert output.write(initial), "OutPort.write failed"
                wait_for(incoming, (1, -2, 3, -4, 5, -6))
                assert bytes(native.pdu_read("SerializerProbe", channel, size)) == initial_payload
                print("DATAPORT_NATIVE_PASS", channel, size, flush=True)
                peer_command = [sys.executable, __file__, "--mode", "peer",
                    "--native-library", args.native_library, "--channel", str(channel), "--size", str(size)]
                peer_log = Path(args.output) / ("peer-%d.log" % channel)
                with peer_log.open("w") as log:
                    result = subprocess.run(peer_command, stdout=log, stderr=subprocess.STDOUT, timeout=10)
                assert result.returncode == 0, "peer failed: %s" % peer_log
                wait_for(incoming, (11, -22, 33, -44, 55, -66))
                print("CROSS_PROCESS_PDU_PASS", channel, size, flush=True)
            finally:
                # Disconnect invokes the provider's stop/join.
                assert incoming.disconnect_all() == RTC.RTC_OK
                assert output.disconnect_all() == RTC.RTC_OK
                assert not incoming.get_connector_profiles()
                assert not output.get_connector_profiles()
                # Standalone test ports have no RTObject owner to deactivate them.
                poa = manager.getPOA()
                for port in (incoming, output):
                    poa.deactivate_object(poa.servant_to_id(port))
            print("DISCONNECT_PASS", channel, flush=True)
    finally:
        command(hako_command, "stop")
        time.sleep(0.05)
        assert "status=stopped" in command(hako_command, "status")
        native.conductor_stop()
        print("CONDUCTOR_STOP_PASS", flush=True)
        manager.shutdown()
        assert not any(t.name == "HakoniwaPduPoll" for t in threading.enumerate())
        print("OPENRTM_SHUTDOWN_PASS", flush=True)
        faulthandler.cancel_dump_traceback_later()


def command(executable, operation):
    result = subprocess.run([str(executable), operation], stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, timeout=3)
    print("HAKO_COMMAND", operation, "exit", result.returncode, result.stdout.strip(), flush=True)
    if result.returncode:
        raise RuntimeError("hako-cmd %s failed" % operation)
    return result.stdout


def wait_for(incoming, expected):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        if incoming.isNew():
            data = incoming.read()
            if vector(data) == expected:
                assert (data.tm.sec, data.tm.nsec) == (0, 0)
                return
        time.sleep(0.01)
    raise AssertionError("Timed out waiting for typed DataPort value %r" % (expected,))


def supervise(args):
    repo = Path(__file__).resolve().parents[2]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    output = repo / "build/system/logs" / ("hakoniwa-wsl-" + stamp)
    output.mkdir(parents=True, exist_ok=False)
    # A fresh mmap root isolates both core state and flock synchronization.
    mmap = output / "mmap"
    mmap.mkdir()
    config = output / "cpp_core_config.json"
    config.write_text(json.dumps({"shm_type": "mmap", "core_mmap_path": str(mmap)}))
    env = dict(os.environ, HAKO_CONFIG_PATH=str(config), PYTHONUNBUFFERED="1")
    command = [sys.executable, __file__, "--mode", "worker", "--native-library",
               str(Path(args.native_library).resolve()), "--output", str(output)]
    print("RUN_DIRECTORY", output, flush=True)
    start = datetime.now(timezone.utc).isoformat()
    with (output / "native.log").open("w") as log:
        try:
            result = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=30)
            status = result.returncode
        except subprocess.TimeoutExpired:
            status = 124
    (output / "run.txt").write_text(
        "start_utc=%s\nend_utc=%s\nexit_code=%d\ncommand=%r\nmode=external_io_empty_simulation\n" % (
            start, datetime.now(timezone.utc).isoformat(), status, command))
    print((output / "native.log").read_text(), end="")
    print("EXIT_CODE", status, flush=True)
    return status


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-library", required=True)
    parser.add_argument("--mode", choices=("supervise", "worker", "peer"), default="supervise")
    parser.add_argument("--output")
    parser.add_argument("--channel", type=int)
    parser.add_argument("--size", type=int)
    args = parser.parse_args()
    if args.mode == "supervise":
        sys.exit(supervise(args))
    elif args.mode == "worker":
        worker(args)
    else:
        peer(args)

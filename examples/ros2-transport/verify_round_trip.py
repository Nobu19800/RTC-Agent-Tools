"""Verify the registered ROS2Transport fixture on a sourced ROS 2 host."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import signal
import subprocess
import sys
import tempfile
import time


HERE = Path(__file__).resolve().parent
TOOLS = HERE.parents[1] / "scripts" / "ros2_system.py"
DEFAULT_MODULE = Path("/usr/lib/python3/dist-packages/OpenRTM_aist/ext/transport/ROS2Transport/ROS2Transport.py")
LOCAL_FAST_DDS = """<profiles xmlns="http://www.eprosima.com/XMLSchemas/fastRTPS_Profiles">
  <transport_descriptors>
    <transport_descriptor>
      <transport_id>loopback</transport_id>
      <type>UDPv4</type>
      <maxInitialPeersRange>16</maxInitialPeersRange>
      <interfaceWhiteList><address>127.0.0.1</address></interfaceWhiteList>
    </transport_descriptor>
  </transport_descriptors>
  <participant profile_name="rtsd_echo">
    <domainId>{domain}</domainId>
    <rtps>
      <useBuiltinTransports>false</useBuiltinTransports>
      <userTransports><transport_id>loopback</transport_id></userTransports>
      <builtin>
        <metatrafficUnicastLocatorList><locator><udpv4><address>127.0.0.1</address></udpv4></locator></metatrafficUnicastLocatorList>
        <initialPeersList><locator><udpv4><address>127.0.0.1</address></udpv4></locator></initialPeersList>
      </builtin>
    </rtps>
  </participant>
</profiles>
"""


def fixture_signature(design):
    components = {node["id"]: node["data"] for node in design["components"]}
    edges = sorted(tuple(edge[key] for key in ("source", "sourceHandle", "target", "targetHandle"))
                   for edge in design["edges"])
    return design["version"], len(design["components"]), components, edges


def stop(children):
    for child in reversed(children):
        if child.poll() is None:
            child.send_signal(signal.SIGINT)
    failures = []
    for child in reversed(children):
        try:
            status = child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
            failures.append(f"process {child.pid} required forced cleanup")
        else:
            if status != 0:
                failures.append(f"process {child.pid} exited with status {status}")
    return failures


def verify_named_graph():
    node = "/RtsdEcho0"
    commands = (["ros2", "node", "list", "--no-daemon", "--spin-time", "5"],
                ["ros2", "node", "info", node, "--no-daemon", "--spin-time", "5"],
                ["ros2", "topic", "echo", "/rtsd_bridge_out/chatter", "std_msgs/msg/String", "--once"])
    outputs = []
    for command in commands:
        print("$ " + " ".join(command), flush=True)
        result = subprocess.run(command, text=True, capture_output=True, timeout=15)
        print(result.stdout, end="", flush=True)
        if result.returncode:
            subprocess.run(["ros2", "topic", "info", "/rtsd_bridge_out/chatter", "--verbose",
                            "--no-daemon", "--spin-time", "4"], timeout=15)
            raise RuntimeError(result.stderr.strip() or f"ROS 2 CLI exited with {result.returncode}")
        outputs.append(result.stdout)
    if node not in outputs[0].splitlines():
        raise RuntimeError(f"ROS 2 CLI did not list {node}")
    subscription, publisher = outputs[1].split("  Publishers:", 1)
    if ("/rtsd_bridge_in/chatter: std_msgs/msg/String" not in subscription
            or "/rtsd_bridge_out/chatter: std_msgs/msg/String" not in publisher):
        raise RuntimeError("ROS 2 CLI did not report the named node's input and output topics")
    if "rtc-echo:Hello World:" not in outputs[2]:
        raise RuntimeError("ROS 2 CLI did not receive the RTC echo")


def verify(raw, module, timeout, rtc_executable=None):
    import rclpy
    from std_msgs.msg import String

    design = json.loads(raw)
    fixture = json.loads((HERE / "session.json").read_bytes())
    if fixture_signature(design) != fixture_signature(fixture):
        raise ValueError("The downloaded design must contain the original test nodes and wiring.")
    named = module.name == "ROS2TransportNamed.so"
    if named and not rtc_executable:
        raise ValueError("The named C++ transport requires --rtc-executable.")

    os.environ["ROS_DOMAIN_ID"] = str(random.SystemRandom().randint(40, 100))
    os.environ["ROS_AUTOMATIC_DISCOVERY_RANGE"] = "LOCALHOST"
    os.environ.pop("ROS_STATIC_PEERS", None)
    print(f"Design SHA-256: {hashlib.sha256(raw).hexdigest()}", flush=True)
    print(f"Local ROS_DOMAIN_ID: {os.environ['ROS_DOMAIN_ID']}", flush=True)
    with tempfile.TemporaryDirectory(prefix="ros2-transport-smoke-") as directory:
        work = Path(directory)
        session = work / "registered-session.json"
        session.write_bytes(raw)
        config = work / "base.conf"
        base = ("naming.enable: NO\nmanager.is_master: NO\n"
                "manager.shutdown_on_nortcs: NO\nlogger.enable: NO\n"
                "manager.components.preactivation: RtsdEcho0\n")
        if rtc_executable:
            os.environ["RMW_IMPLEMENTATION"] = "rmw_fastrtps_cpp"
        if rtc_executable:
            profile = work / "fast-dds.xml"
            profile.write_text(LOCAL_FAST_DDS.format(domain=os.environ["ROS_DOMAIN_ID"]), encoding="utf-8")
            interface = "fast-dds" if module.with_name("FastDDSTransport.so").is_file() else "fast-rtps"
            base += f"{interface}.xmlprofile.filename: {profile}\n{interface}.participant.name: rtsd_echo\n"
        config.write_text(base, encoding="utf-8")
        output = work / "rtc-ros2.conf"
        command = [sys.executable, "-B", str(TOOLS)]
        subprocess.run(command + ["transport", str(session), "--rtc-id", "echo",
                                   "--base-conf", str(config), "--module", str(module),
                                   "--output", str(output)], check=True)
        rclpy.init()
        observer = rclpy.create_node("rtsd_transport_test")
        received = set()
        for topic, stream in (("/rtsd_bridge_in/chatter", "input"), ("/rtsd_bridge_out/chatter", "output")):
            observer.create_subscription(String, topic, lambda msg, name=stream:
                                         received.add((name, msg.data)), 10)
        children = []
        result = None
        ros_log = work / "ros.log"
        try:
            rtc_command = ([str(rtc_executable.resolve(strict=True))] if rtc_executable else
                           [sys.executable, "-B", str(HERE / "echo_rtc.py")])
            children.append(subprocess.Popen(rtc_command + ["-f", str(output)]))
            with ros_log.open("w", encoding="utf-8") as log:
                children.append(subprocess.Popen(command + ["run", str(session)],
                                                 stdout=log, stderr=subprocess.STDOUT))
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                rclpy.spin_once(observer, timeout_sec=0.25)
                if any(child.poll() is not None for child in children):
                    raise RuntimeError("The RTC or ROS 2 launcher exited before a round trip completed.")
                listener_present = any(
                    info.node_name == "bridge_sink" and info.node_namespace == "/rtsd_bridge_out"
                    for info in observer.get_subscriptions_info_by_topic("/rtsd_bridge_out/chatter")
                )
                if listener_present:
                    listener_log = ros_log.read_text(encoding="utf-8", errors="replace")
                    result = next((value for stream, value in received if stream == "output"
                                   and value.startswith("rtc-echo:Hello World:")
                                   and ("input", value.removeprefix("rtc-echo:")) in received
                                   and f"I heard: [{value}]" in listener_log), None)
                if result:
                    break
            if not result:
                raise RuntimeError(f"No matching RTC echo after {timeout:g} seconds.")
            if named:
                verify_named_graph()
        finally:
            failures = stop(children)
            observer.destroy_node()
            rclpy.try_shutdown()
            if ros_log.exists():
                print(ros_log.read_text(encoding="utf-8", errors="replace"), end="", flush=True)
            if failures:
                print("Shutdown: " + "; ".join(failures), file=sys.stderr)
        if failures:
            raise RuntimeError("Smoke test processes did not shut down cleanly.")
        print(f"PASS: ROS 2 talker -> RTC InPort -> RTC OutPort -> ROS 2 listener. Echo: {result}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", type=Path, default=DEFAULT_MODULE)
    parser.add_argument("--rtc-executable", type=Path, help="Use a compiled C++ echo RTC")
    parser.add_argument("--timeout", type=float, default=45)
    args = parser.parse_args()
    try:
        verify(sys.stdin.buffer.read(), args.module, args.timeout, args.rtc_executable)
    except (ValueError, RuntimeError, KeyError, OSError, ImportError, subprocess.SubprocessError) as error:
        parser.exit(1, f"ROS2Transport smoke test: {error}\n")

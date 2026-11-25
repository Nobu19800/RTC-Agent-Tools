#!/usr/bin/env bash
# Run the approved Drone pose test in WSL2 using an existing Foundation.
set -eo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
session=$(realpath "${1:?approved session JSON required}")
foundation=$(realpath "${2:?Foundation directory required}")
drone=$(realpath "${3:?Drone source directory required}")
recipe=$(realpath "${4:?Drone recipe work directory required}")
bridge=$(realpath "${5:?hakoniwa-pdu-ros checkout required}")
mode=${6:-verify}
if [[ "$mode" != verify && "$mode" != --keep-running ]]; then
    echo "Expected --keep-running as the optional sixth argument" >&2
    exit 2
fi
out=$(mktemp -d "$PWD/hakoniwa-ros2-run.XXXXXX")
echo "Evidence: $out"
source "$foundation/activate" >/dev/null
source /opt/ros/jazzy/setup.bash
export PYTHONPATH="$bridge:$PYTHONPATH:/usr/lib/python3/dist-packages"
export LD_LIBRARY_PATH="$foundation/install/lib:$drone/lnx:$LD_LIBRARY_PATH"
export HAKO_CONFIG_PATH="$out/core.json"
export ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-91} ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
unset ROS_STATIC_PEERS
py="$foundation/install/python/bin/python"
cp -r "$recipe/config" "$out/"
mmap=$(mktemp -d /tmp/hakoniwa-ros2-mmap.XXXXXX)
cd "$out"
"$py" -B - "$session" "$mmap" <<'PY'
import json
import sys
from pathlib import Path

def load(path):
    return json.loads(Path(path).read_bytes())

def save(path, data):
    Path(path).write_text(json.dumps(data, indent=2) + "\n")

design = load(sys.argv[1])
nodes = {n["id"]: n["data"] for n in design["components"]}
edges = {edge["id"]: edge for edge in design["edges"]}
if "pose-to-ros2-bridge" in edges:
    edge = edges["pose-to-ros2-bridge"]
    ros_edge = edges["ros2-bridge-to-probe"]
    assert (edge["target"], ros_edge["source"]) == ("ros2-bridge", "ros2-bridge")
    assert (edges["pose-to-visual"]["source"], edges["pose-to-visual"]["target"]) == ("drone", "visual-state-publisher")
    assert (edges["visual-to-websocket"]["source"], edges["visual-to-websocket"]["target"]) == ("visual-state-publisher", "web-bridge")
    assert (edges["websocket-to-viewer"]["source"], edges["websocket-to-viewer"]["target"]) == ("web-bridge", "threejs-viewer")
    bridge_node = nodes[ros_edge["source"]]
    ros_port = next(p for p in bridge_node["ports"] if p["id"] == ros_edge["sourceHandle"])
    Path("viewer-enabled").touch()
else:
    edge = ros_edge = edges["drone-pose-to-ros"]
    ros_port = None
assert design["version"] == 2
asset, probe = nodes[edge["source"]], nodes[ros_edge["target"]]
assert (asset["moduleKind"], probe["moduleKind"]) == ("hakoniwa", "ros2")
source = next(p for p in asset["ports"] if p["id"] == edge["sourceHandle"])
target = next(p for p in probe["ports"] if p["id"] == ros_edge["targetHandle"])
assert (source["robot"], source["pduName"], source["channelId"], source["capacityBytes"]) == ("Drone", "pos", 1, 72)
assert (target["name"], target["dataType"]) == ("/pdu/Drone/pos", "geometry_msgs/msg/Twist")
if ros_port is not None:
    assert all(ros_port[k] == target[k] for k in ("name", "dataType"))
fleet = Path("config/drone/fleets/api-1.json")
config = load(fleet)
config["drones"][0]["position_meter"] = [1.25, -2.5, 0]
save(fleet, config)
save("core.json", {"shm_type": "mmap", "core_mmap_path": sys.argv[2], "asset_timeout_usec": 30000000})
save("endpoint.json", {"pdu_def_path": "config/pdudef/drone-pdudef-1.json"})
save("binding.json", {"endpoint_config": "endpoint.json", "bindings": [
    {"direction": "pdu_to_ros", "topic": target["name"].removeprefix("/pdu"),
     "pdu_key": {"robot_name": source["robot"], "pdu_name": source["pduName"]}}]})
PY
drone_pid=
bridge_pid=
observer_pid=
probe_pid=
visual_pid= web_pid= http_pid=
cleanup() {
    for pid in "$http_pid" "$web_pid" "$visual_pid"; do if [[ -n $pid ]]; then kill -TERM "$pid" 2>/dev/null || true; wait "$pid" || true; fi; done
    if [[ -n $probe_pid ]]; then kill -TERM "$probe_pid" 2>/dev/null || true; wait "$probe_pid" || true; fi
    if [[ -n $observer_pid ]]; then kill -TERM "$observer_pid" 2>/dev/null || true; wait "$observer_pid" || true; fi
    if [[ -n $bridge_pid ]]; then kill -TERM "$bridge_pid" 2>/dev/null || true; wait "$bridge_pid" || true; fi
    if [[ -n $drone_pid ]]; then
        timeout 4 hako-cmd stop >> core.log 2>&1 || true
        kill -TERM "$drone_pid" 2>/dev/null || true
        wait "$drone_pid" || true
    fi
}
trap cleanup EXIT
trap 'exit 0' INT TERM
"$drone/lnx/linux-main_hako_drone_service" config/drone/fleets/api-1.json config/pdudef/drone-pdudef-1.json --real-sleep-msec 1 > drone.log 2>&1 &
drone_pid=$!
for attempt in {1..30}; do
    if timeout 2 hako-cmd status > core.log 2>&1 && grep -q 'status=stopped' core.log; then break; fi
    kill -0 "$drone_pid"
    sleep 0.3
done
"$py" -B - > asset.log 2>&1 <<'PY' &
import json
from pathlib import Path
import hakopy

definition = {"robots": [{"name": "Drone", "shm_pdu_writers": [],
    "shm_pdu_readers": [ {"type": "geometry_msgs/Twist", "org_name": "pos", "channel_id": 1, "pdu_size": 72}],
    "rpc_pdu_readers": [], "rpc_pdu_writers": []}]}
path = Path("pose-reader.json").resolve()
path.write_text(json.dumps(definition))
def step(_):
    return 0
callbacks = {"on_initialize": step, "on_simulation_step": step,
             "on_manual_timing_control": None, "on_reset": step}
assert hakopy.asset_register("PoseProbe", str(path), callbacks, 20000, hakopy.HAKO_ASSET_MODEL_CONTROLLER)
hakopy.start()
PY
observer_pid=$!
for attempt in {1..30}; do
    if timeout 2 hako-cmd ls > registration.log 2>&1 && grep -q 'PoseProbe' registration.log; then break; fi
    kill -0 "$observer_pid"
    sleep 0.3
done
grep -q 'PoseProbe' registration.log
if [[ -f viewer-enabled ]]; then
    : "${HAKONIWA_VISUAL_PUBLISHER:?Set the Business Pack visual-state publisher path}"
    : "${HAKONIWA_VIEWER_ROOT:?Set the Three.js Drone checkout path}"
    "$py" -B "$HAKONIWA_VISUAL_PUBLISHER" "$out/config/pdudef/gui-visual.json" > visual.log 2>&1 &
    visual_pid=$!
    "$foundation/install/bin/hakoniwa-pdu-web-bridge" --config-root "$out/config/assets/web_bridge_fleets" --node-name web_bridge_fleets_node1 --delta-time-step-usec 20000 --enable-ondemand > websocket.log 2>&1 &
    web_pid=$!
    "$py" -B -m http.server 8000 --bind 127.0.0.1 --directory "$HAKONIWA_VIEWER_ROOT" > viewer-http.log 2>&1 &
    http_pid=$!
    for attempt in {1..40}; do
        timeout 2 hako-cmd ls > registration.log 2>&1 || true
        if grep -q DroneVisualStatePublisher registration.log && grep -qx WebBridge registration.log; then break; fi
        kill -0 "$visual_pid" "$web_pid" "$http_pid"
        sleep 0.25
    done
    grep -q DroneVisualStatePublisher registration.log
    grep -qx WebBridge registration.log
fi
timeout 5 hako-cmd start >> core.log 2>&1
for attempt in {1..20}; do
    if grep -q "ERROR: hako_asset_start()" drone.log || ! kill -0 "$drone_pid" 2>/dev/null; then
        tail -12 drone.log >&2
        exit 1
    fi
    if timeout 2 hako-cmd status >> core.log 2>&1 && grep -q "status=running" core.log; then break; fi
    sleep 0.2
done
grep -q "status=running" core.log
"$py" -B "$script_dir/drone_pose_bridge.py" "$out/binding.json" > bridge.log 2>&1 &
bridge_pid=$!
timeout 22 "$py" -B - <<'PY' | tee observed.log
import math
import struct
import time

import hakopy
import rclpy
from geometry_msgs.msg import Twist

assert hakopy.init_for_external(), "Cannot attach to private Drone mmap"
rclpy.init()
node = rclpy.create_node("pose_probe")
samples = []
subscription = node.create_subscription(Twist, "/pdu/Drone/pos", samples.append, 10)
deadline = time.monotonic() + 17
try:
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.25)
        if not samples:
            continue
        msg = samples.pop()
        raw = hakopy.pdu_read("Drone", 1, 72)
        if raw is None or len(raw) != 72:
            continue
        values = struct.unpack_from("<6d", bytes(raw), 24)
        received = (msg.linear.x, msg.linear.y, msg.linear.z, msg.angular.x, msg.angular.y, msg.angular.z)
        if abs(values[0]) > 0.1 and abs(values[1]) > 0.1 and struct.unpack_from("<I", bytes(raw))[0] == 0x12345678 and all(
            math.isclose(a, b, abs_tol=1e-8) for a, b in zip(values, received)
        ):
            print("mmap Drone/pos:", values)
            print("ROS 2 /pdu/Drone/pos:", received)
            break
    else:
        raise RuntimeError(f"No matching Drone pose. Last received: {locals().get('received')}")
finally:
    node.destroy_node()
    rclpy.shutdown()
PY
if [[ "$mode" == --keep-running ]]; then
    "$py" -B - > pose-probe.log 2>&1 <<'PY' &
import rclpy
from geometry_msgs.msg import Twist
from rclpy.executors import ExternalShutdownException

rclpy.init()
node = rclpy.create_node("pose_probe")
subscription = node.create_subscription(Twist, "/pdu/Drone/pos", lambda _: None, 10)
try:
    rclpy.spin(node)
except (KeyboardInterrupt, ExternalShutdownException):
    pass
finally:
    node.destroy_node()
    rclpy.try_shutdown()
PY
    probe_pid=$!
    echo "Live on ROS_DOMAIN_ID=$ROS_DOMAIN_ID"
    wait -n "$drone_pid" "$bridge_pid" "$observer_pid" "$probe_pid" ${visual_pid:+"$visual_pid"} ${web_pid:+"$web_pid"} ${http_pid:+"$http_pid"}
fi

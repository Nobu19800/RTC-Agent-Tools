"""Export the approved version 2 teleoperation design without legacy helpers."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SYSTEM = ROOT / "build/system"
SYSTEM.mkdir(parents=True, exist_ok=True)
source = ROOT / "work/final-session.json"
session = json.loads(source.read_text(encoding="utf-8"))
assert session["version"] == 2
assert session["id"] == (ROOT / "work/current_session_id.txt").read_text().strip()
assert len({c["id"] for c in session["components"]}) == len(session["components"])
index = {c["id"]: c for c in session["components"]}
contracts = json.loads((ROOT / "work/connection-contracts.json").read_text(encoding="utf-8"))
for edge in session["edges"]:
    a, b = index[edge["source"]]["data"], index[edge["target"]]["data"]
    pa = next(p for p in a["ports"] if p["id"] == edge["sourceHandle"])
    pb = next(p for p in b["ports"] if p["id"] == edge["targetHandle"])
    assert pa["direction"] == "out" and pb["direction"] == "in"
    if a["moduleKind"] != b["moduleKind"]:
        assert all(contracts["edges"][edge["id"]]["endpoints"][k] == edge[k]
                   for k in ("source", "sourceHandle", "target", "targetHandle"))
    else:
        assert pa["dataType"] == pb["dataType"]
shutil.copy2(source, SYSTEM / "final-session.json")
for filename in ("connection-contracts.json", "source-provenance.json", "recipe-proposal.json"):
    shutil.copy2(ROOT / "work" / filename, SYSTEM / filename)
common = ROOT / "build/generated/common/idl"
common.mkdir(parents=True, exist_ok=True)
idl = common / "DroneTeleop.idl"
idl_text = '''#include "BasicDataType.idl"
module DroneTeleop {
  enum PilotAction { ACTION_NONE, ACTION_TAKEOFF, ACTION_LAND, ACTION_DISABLE };
  enum ControlPhase { OFFLINE, READY, TAKING_OFF, ACTIVE, MOVING, LANDING, FAULT };
  struct TimedPilotInput {
    RTC::Time tm; unsigned long serial; boolean enabled;
    double axis_x; double axis_y; double axis_z; double axis_yaw; PilotAction action;
  };
  struct TimedStatus {
    RTC::Time tm; ControlPhase phase; string detail; boolean pose_valid;
    double x; double y; double z; double roll; double pitch; double yaw;
    boolean pending; boolean pose_time_known;
  };
  struct TimedMovePdu {
    RTC::Time tm; boolean request; boolean result; long result_code;
    double x; double y; double z; double speed; double yaw_deg;
  };
  struct TimedTakeoffPdu {
    RTC::Time tm; boolean request; boolean result; long result_code;
    double height; double speed; double yaw_deg;
  };
  struct TimedLandPdu {
    RTC::Time tm; boolean request; boolean result; long result_code;
    double height; double speed; double yaw_deg;
  };
};
'''
if idl.exists() and idl.read_text() != idl_text:
    raise RuntimeError("Existing shared IDL differs; review before replacing")
idl.write_text(idl_text, encoding="utf-8")
profiles = []
for component in session["components"]:
    data = component["data"]
    if data["moduleKind"] != "rtc" or data.get("origin") != "generated":
        continue
    name = data["name"]
    folder = ROOT / "build/generated" / name
    folder.mkdir(parents=True, exist_ok=True)
    ports = []
    for p in data["ports"]:
        item = dict(name=p["name"], portType="DataInPort" if p["direction"]=="in" else "DataOutPort",
                    type=p["dataType"], position="LEFT" if p["direction"]=="in" else "RIGHT")
        if p["dataType"].startswith("DroneTeleop::"):
            item["idlFile"] = str(idl)
        ports.append(item)
    profile = dict(profileVersion="0.3", basicInfo=dict(name=name,
        description="Approved simulated drone teleoperation component", version="1.0.0", vendor="Local",
        category="Simulation", componentType="STATIC", activityType="PERIODIC", componentKind="DataFlowComponent",
        maxInstances=1, executionType="PeriodicExecutionContext", executionRate=20.0 if name=="DroneJoystickGUIRTC" else 50.0),
        actions=dict(OnInitialize=True, OnActivated=True, OnDeactivated=True, OnExecute=True),
        configuration=[], dataPorts=ports, servicePorts=[], language=dict(kind="Python"))
    profile_path = folder / (name+".json")
    profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    subprocess.run([sys.executable, str(ROOT/"json_to_rtc_xml.py"), str(profile_path), str(folder/"RTC.xml")], check=True)
    profiles.append(dict(name=name, path=str(profile_path.relative_to(ROOT))))
(SYSTEM / "preparation.json").write_text(json.dumps(dict(
    designSha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    idlSha256=hashlib.sha256(idl.read_bytes()).hexdigest(), profiles=profiles,
    validation="version 2 endpoints and mixed contracts checked; no asset RTC profiles generated"),indent=2)+"\n")
print("Prepared", [p["name"] for p in profiles])

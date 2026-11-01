"""WSL-only offline deployment generator for the approved mixed teleop system."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
from teleop_connection_settings import write_settings

ROOT=Path(__file__).resolve().parents[1]
SYSTEM=ROOT/'build/system'
RUNTIME=SYSTEM/'teleop'
SCRIPTS=SYSTEM/'scripts'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--foundation',type=Path,default=Path('/home/nobu/hakoniwa-wsl-run/work-wsl/foundation'))
parser.add_argument('--drone-root',type=Path,default=Path('/home/nobu/hakoniwa-wsl-run/drone-core'))
parser.add_argument('--viewer-root',type=Path,default=Path('/home/nobu/hakoniwa-wsl-run/threejs-drone'))
parser.add_argument('--template',type=Path,default=Path('/home/nobu/hakoniwa-wsl-run/work-wsl/recipes/drone-position-pdu-live'))
args=parser.parse_args()
for p in (args.foundation/'install/python/bin/python',args.drone_root/'lnx/linux-main_hako_drone_service',args.viewer_root/'index.html',args.template/'config'):
    if not p.exists(): raise FileNotFoundError(p)
SCRIPTS.mkdir(parents=True,exist_ok=True)
RUNTIME.mkdir(parents=True,exist_ok=True)
for folder in ('mmap','owners','naming'):
    (RUNTIME/folder).mkdir(exist_ok=True)
for part in ('drone','pdudef','assets','controller'):
    shutil.copytree(args.template/'config'/part,RUNTIME/'config'/part,dirs_exist_ok=True)
for p in (RUNTIME/'config').rglob('*.json'):
    # Only upstream-native configuration files: not runtime process manifests.
    text=p.read_text()
    p.write_text(text.replace(str(args.template),str(RUNTIME)))
(RUNTIME/'config/cpp_core_config.json').write_text(json.dumps(dict(shm_type='mmap',core_mmap_path=str(RUNTIME/'mmap')),indent=2)+'\n')
BP=ROOT.parent/'hakoniwa-business-pack'
common=ROOT/'build/generated/common'
environment=f'''# Generated from approved design; native upstream JSON is limited to its required API config.
source {shlex.quote(str(args.foundation/'activate'))} >/dev/null
export ROOT={shlex.quote(str(ROOT))}
export RUNTIME={shlex.quote(str(RUNTIME))}
export BP_ROOT={shlex.quote(str(BP))}
export DRONE_ROOT={shlex.quote(str(args.drone_root))}
export VIEWER_ROOT={shlex.quote(str(args.viewer_root))}
export PY={shlex.quote(str(args.foundation/'install/python/bin/python'))}
export HAKO_CONFIG_PATH={shlex.quote(str(RUNTIME/'config/cpp_core_config.json'))}
export HAKO_PROFILE_SERVICE_CLIENT=0
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH={shlex.quote(str(common))}:/usr/lib/python3/dist-packages:/usr/lib/python3/dist-packages/OpenRTM_aist:/usr/lib/python3/dist-packages/OpenRTM_aist/RTM_IDL:/usr/lib/python3/dist-packages/OpenRTM_aist/utils:/usr/lib/python3/dist-packages/omniORB/COS
export LD_LIBRARY_PATH={shlex.quote(str(args.foundation/'install/lib'))}:{shlex.quote(str(args.drone_root/'lnx'))}:${{LD_LIBRARY_PATH-}}
export OMNIORB_CONFIG={shlex.quote(str(RUNTIME/'omniORB.cfg'))}
export RTCSERVER=localhost:2809
export OWNER_DIR={shlex.quote(str(RUNTIME/'owners'))}
source {shlex.quote(str(SCRIPTS/'processes.sh'))}
source {shlex.quote(str(SCRIPTS/'nameserver.sh'))}
if [[ -f $RUNTIME/current-run.txt ]]; then export RUN_DIR=$(cat $RUNTIME/current-run.txt); fi
'''
(RUNTIME/'runtime.env').write_text(environment)
(RUNTIME/'omniORB.cfg').write_text('clientCallTimeOutPeriod = 5000\n')
for name,instance,rate in (('DroneJoystickGUIRTC','gui-joystick-1',20),('DroneTeleopControllerRTC','teleop-controller-1',50)):
    conf=f'''corba.nameservers: localhost:2809
naming.formats: %n.rtc
manager.shutdown_auto: NO
manager.shutdown_on_nortcs: NO
manager.corba_servant: NO
exec_cxt.periodic.rate: {rate}
logger.enable: YES
logger.log_level: WARN
logger.file_name: STDOUT
buffer.length: 1
'''
    if instance == 'teleop-controller-1':
        conf += write_settings(ROOT)
    (RUNTIME/(instance+'.conf')).write_text(conf)

helpers=r'''# Process-only helpers plus bounded observations. RTC operations stay in lifecycle scripts.
begin_run() {
  if [[ -f $RUNTIME/current-run.txt ]]; then
    RUN_DIR=$(cat "$RUNTIME/current-run.txt")
    if [[ -d $RUN_DIR ]]; then export RUN_DIR; return; fi
  fi
  RUN_DIR=$ROOT/build/system/logs/teleop-$(date -u +%Y%m%dT%H%M%S)-$$
  mkdir -p "$RUN_DIR"; export RUN_DIR
  printf '%s\n' "$RUN_DIR" > "$RUNTIME/current-run.txt"
}
owned_alive() {
  local file=$OWNER_DIR/$1.pid
  [[ -f $file ]] || return 1
  local pid ticks digest now
  read -r pid ticks digest < "$file"
  [[ -r /proc/$pid/stat && -r /proc/$pid/cmdline ]] || return 1
  now=$(awk '{print $22}' /proc/$pid/stat 2>/dev/null) || return 1
  [[ $now == "$ticks" ]] || { echo "OWNERSHIP MISMATCH $1" >&2; return 2; }
  local state actual
  state=$(awk '{print $3}' /proc/$pid/stat 2>/dev/null) || return 1
  [[ $state != Z ]] || return 1
  actual=$(sha256sum /proc/$pid/cmdline 2>/dev/null | cut -d' ' -f1)
  [[ -r /proc/$pid/stat ]] || return 1
  [[ $actual == "$digest" ]] || { echo "COMMAND MISMATCH $1" >&2; return 2; }
}
start_owned() {
  local name=$1; shift
  if owned_alive "$name"; then echo "REUSE OWNED $name"; return; else
    local status=$?; [[ $status != 2 ]] || return 2
  fi
  begin_run
  for suffix in out err; do
    if [[ -f $RUN_DIR/$name.$suffix ]]; then cp "$RUN_DIR/$name.$suffix" "$RUN_DIR/$name.$suffix.$(date -u +%Y%m%dT%H%M%S%N)"; fi
  done
  printf 'START %s: ' "$name"; printf '%q ' "$@"; printf '\n'
  nohup "$@" > "$RUN_DIR/$name.out" 2> "$RUN_DIR/$name.err" </dev/null &
  local pid=$!
  sleep .4
  [[ -r /proc/$pid/stat ]] || { echo "START FAILED $name" >&2; return 1; }
  printf '%s %s %s\n' "$pid" "$(awk '{print $22}' /proc/$pid/stat)" "$(sha256sum /proc/$pid/cmdline | cut -d' ' -f1)" > "$OWNER_DIR/$name.pid"
  owned_alive "$name" || { echo "PROCESS EXITED $name" >&2; return 1; }
  echo "STARTED $name PID=$pid"
}
stop_owned() {
  local name=$1
  if owned_alive "$name"; then
    local pid ticks digest; read -r pid ticks digest < "$OWNER_DIR/$name.pid"
    kill -TERM "$pid"
    for i in $(seq 1 50); do owned_alive "$name" || break; sleep .1; done
    if owned_alive "$name"; then kill -KILL "$pid"; echo "FORCED TERMINATION $name" >&2; fi
    owned_alive "$name" && return 1
    echo "STOPPED $name"
  else
    local status=$?; [[ $status != 2 ]] || return 2
    echo "NOT RUNNING $name"
  fi
}
wait_registration() {
  local target=$1
  for i in $(seq 1 50); do
    if timeout 7 rtcat "/$RTCSERVER/$target.rtc" > "$RUN_DIR/registration-$target.txt" 2>&1 && grep -Eq "Instance name[[:space:]]+$target$" "$RUN_DIR/registration-$target.txt" && ! grep -qi zombie "$RUN_DIR/registration-$target.txt"; then return; fi
    sleep .2
  done
  echo "REGISTRATION TIMEOUT $target" >&2; return 1
}
assert_state() {
  local target=$1 expected=$2
  for i in $(seq 1 30); do
    timeout 7 rtcat "/$RTCSERVER/$target.rtc" > "$RUN_DIR/state-$target.txt" 2>&1 || return 1
    grep -Eqi "(^|[^[:alpha:]])$expected([^[:alpha:]]|$)" "$RUN_DIR/state-$target.txt" && return
    sleep .2
  done
  echo "STATE TIMEOUT $target $expected" >&2; return 1
}
wait_core() {
  local state=$1
  for i in $(seq 1 120); do
    if timeout 5 hako-cmd status > "$RUN_DIR/core-status.txt" 2>&1 && grep -q "status=$state" "$RUN_DIR/core-status.txt"; then return; fi
    cp "$RUN_DIR/core-status.txt" "$RUN_DIR/core-status-attempt-$state-$i.txt"
    sleep .5
  done
  cat "$RUN_DIR/core-status.txt" >&2; return 1
}
'''
(SCRIPTS/'processes.sh').write_text(helpers)
shutil.copy2(ROOT/'scripts/teleop_nameserver.sh',SCRIPTS/'nameserver.sh')
operations={
'start_simulation':r'''begin_run
cd "$RUNTIME"
if owned_alive drone; then
  if timeout 5 hako-cmd status > "$RUN_DIR/start-existing-core.txt" 2>&1 && grep -q 'status=running' "$RUN_DIR/start-existing-core.txt"; then
    for name in publisher webbridge viewer-http; do owned_alive "$name" || { echo "Missing owned $name; stop/restart the composition" >&2; exit 1; }; done
    echo 'REUSE RUNNING OWNED SIMULATION'
    exit 0
  fi
fi
if ! owned_alive drone; then
  if ss -lnt | grep -Eq ':(8000|8765) '; then echo 'Required viewer ports are occupied by an unowned process' >&2; exit 1; fi
  # This composition owns a dedicated mmap domain. Preserve stopped-domain files;
  # the native master PID and locks must not be reused by the next conductor.
  for name in controller gui publisher webbridge viewer-http; do
    if owned_alive "$name"; then echo "Stop owned $name before a cold simulation start" >&2; exit 1; else
      status=$?; [[ $status != 2 ]] || exit 2
    fi
  done
  mmap_dir=$(readlink -f "$RUNTIME/mmap")
  [[ $mmap_dir == "$ROOT/build/system/teleop/mmap" && ! -L $RUNTIME/mmap ]] || { echo 'Unexpected mmap directory' >&2; exit 1; }
  if grep -lF "$mmap_dir/" /proc/[0-9]*/maps 2>/dev/null > "$RUN_DIR/mmap-users-before-start.txt"; then
    echo 'Dedicated mmap files still mapped by a process; refusing rotation' >&2; exit 1
  fi
  if [[ -d $mmap_dir ]]; then
    mv -- "$mmap_dir" "$RUN_DIR/mmap-before-start-$(date -u +%Y%m%dT%H%M%S%N)"
  fi
  mkdir -p "$mmap_dir"
fi
start_owned drone "$DRONE_ROOT/lnx/linux-main_hako_drone_service" config/drone/fleets/api-1.json config/pdudef/drone-pdudef-1.json --real-sleep-msec 1
wait_core stopped
start_owned publisher "$PY" "$BP_ROOT/tools/recipe/drone_gui_visual_state.py" "$RUNTIME/config/pdudef/gui-visual.json"
start_owned webbridge "$HAKONIWA_HOME/bin/hakoniwa-pdu-web-bridge" --config-root "$RUNTIME/config/assets/web_bridge_fleets" --node-name web_bridge_fleets_node1 --delta-time-step-usec 20000 --enable-ondemand
start_owned viewer-http "$PY" -m http.server 8000 --bind 127.0.0.1 --directory "$VIEWER_ROOT"
sleep 2
timeout 5 hako-cmd ls > "$RUN_DIR/registered-assets.txt"
timeout 5 hako-cmd start
wait_core running
echo 'VIEWER http://127.0.0.1:8000/index.html?viewerConfigPath=/config/viewer-config-fleets.json&wsUri=ws://127.0.0.1:8765&wireVersion=v2'
''',
'start_rtcs':r'''begin_run
prepare_nameserver
"$PY" "$ROOT/scripts/configure_wsl_rtc_endpoint.py"
for i in $(seq 1 30); do nameserver_list > "$RUN_DIR/naming.txt" 2>&1 && break; sleep .2; done
nameserver_list
start_owned controller "$PY" "$ROOT/build/generated/DroneTeleopControllerRTC/DroneTeleopControllerRTC.py" -f "$RUNTIME/teleop-controller-1.conf" --instance_name=teleop-controller-1
start_owned gui "$PY" "$ROOT/build/generated/DroneJoystickGUIRTC/DroneJoystickGUIRTC.py" -f "$RUNTIME/gui-joystick-1.conf" --instance_name=gui-joystick-1
wait_registration teleop-controller-1
wait_registration gui-joystick-1
timeout 7 rtcat "/$RTCSERVER/teleop-controller-1.rtc"
timeout 7 rtcat "/$RTCSERVER/gui-joystick-1.rtc"
''',
'connect_ports':r'''wait_registration teleop-controller-1
wait_registration gui-joystick-1
timeout 10 rtcon -d -i pilot-input -n pilot-input -p dataport.dataflow_type=push -p dataport.subscription_type=flush -p dataport.buffer.length=1 "/$RTCSERVER/gui-joystick-1.rtc:pilot" "/$RTCSERVER/teleop-controller-1.rtc:pilot"
timeout 10 rtcon -d -i teleop-status -n teleop-status -p dataport.dataflow_type=push -p dataport.subscription_type=flush -p dataport.buffer.length=1 "/$RTCSERVER/teleop-controller-1.rtc:status" "/$RTCSERVER/gui-joystick-1.rtc:status"
scoped_rtcat "/$RTCSERVER/teleop-controller-1.rtc" > "$RUN_DIR/connections.txt"
grep -q pilot-input "$RUN_DIR/connections.txt"
grep -q teleop-status "$RUN_DIR/connections.txt"
wait_core running
"$PY" "$ROOT/scripts/single_port_connections.py" --rtc "/$RTCSERVER/teleop-controller-1.rtc" --config "$RUNTIME/native-connections.ini" --action connect
echo 'Seven native bindings connected from INI; plugins loaded through rtc.conf.' 
''',
'activate_rtcs':r'''wait_core running
scoped_rtcat "/$RTCSERVER/teleop-controller-1.rtc" > "$RUN_DIR/preactivation.txt"
grep -q pilot-input "$RUN_DIR/preactivation.txt"
grep -q teleop-status "$RUN_DIR/preactivation.txt"
"$PY" "$ROOT/scripts/single_port_connections.py" --rtc "/$RTCSERVER/teleop-controller-1.rtc" --config "$RUNTIME/native-connections.ini" --action check
timeout 7 rtcat "/$RTCSERVER/teleop-controller-1.rtc" > "$RUN_DIR/activation-controller.txt"
if ! grep -Eq '(^|[^[:alpha:]])Active([^[:alpha:]]|$)' "$RUN_DIR/activation-controller.txt"; then timeout 10 rtact "/$RTCSERVER/teleop-controller-1.rtc"; fi
assert_state teleop-controller-1 Active
timeout 7 rtcat "/$RTCSERVER/gui-joystick-1.rtc" > "$RUN_DIR/activation-gui.txt"
if ! grep -Eq '(^|[^[:alpha:]])Active([^[:alpha:]]|$)' "$RUN_DIR/activation-gui.txt"; then timeout 10 rtact "/$RTCSERVER/gui-joystick-1.rtc"; fi
assert_state gui-joystick-1 Active
scoped_rtcat "/$RTCSERVER/teleop-controller-1.rtc" > "$RUN_DIR/native-bindings.txt"
echo 'ACTIVE: GUI input and command processing enabled. Flight requires explicit GUI Take off.'
''',
'deactivate_rtcs':r'''result=0
timeout 7 rtcat "/$RTCSERVER/gui-joystick-1.rtc" > "$RUN_DIR/deactivation-gui.txt" || result=1
if ! grep -qi Inactive "$RUN_DIR/deactivation-gui.txt"; then timeout 10 rtdeact "/$RTCSERVER/gui-joystick-1.rtc" || result=1; fi
assert_state gui-joystick-1 Inactive || result=1
timeout 7 rtcat "/$RTCSERVER/teleop-controller-1.rtc" > "$RUN_DIR/deactivation-controller.txt" || result=1
if ! grep -qi Inactive "$RUN_DIR/deactivation-controller.txt"; then timeout 10 rtdeact "/$RTCSERVER/teleop-controller-1.rtc" || result=1; fi
assert_state teleop-controller-1 Inactive || result=1
exit $result
''',
'stop_rtcs':r'''result=0
nameserver_list > "$RUN_DIR/naming-before-stop.txt" || exit 1
for entry in gui-joystick-1:gui teleop-controller-1:controller; do
  target=${entry%:*}; process=${entry#*:}
  if grep -q "$target.rtc" "$RUN_DIR/naming-before-stop.txt"; then
    timeout 7 rtcat "/$RTCSERVER/$target.rtc" > "$RUN_DIR/stop-initial-$target.txt" 2>&1 || { result=1; continue; }
    if grep -qi 'Active' "$RUN_DIR/stop-initial-$target.txt" && ! grep -qi 'Inactive' "$RUN_DIR/stop-initial-$target.txt"; then
      timeout 10 rtdeact "/$RTCSERVER/$target.rtc" || result=1
    fi
    timeout 10 rtexit "/$RTCSERVER/$target.rtc" || result=1
    for i in $(seq 1 30); do
      nameserver_list > "$RUN_DIR/naming-after-$target.txt" 2>&1 || { result=1; break; }
      grep -q "$target.rtc" "$RUN_DIR/naming-after-$target.txt" || break
      sleep .2
    done
    if grep -q "$target.rtc" "$RUN_DIR/naming-after-$target.txt"; then echo "STILL REGISTERED $target"; result=1; continue; fi
  fi
  stop_owned "$process" || result=1
  echo "SHUTDOWN_SUMMARY $target registration=absent owned_process=checked"
done
nameserver_list > "$RUN_DIR/naming-final.txt" || result=1
echo 'Shared NameService localhost:2809 retained'
exit $result
''',
'stop_simulation':r'''result=0
if owned_alive drone; then timeout 5 hako-cmd stop || result=1; wait_core stopped || result=1; fi
for name in webbridge publisher viewer-http drone; do stop_owned "$name" || result=1; done
exit $result
'''
}
for name,body in operations.items():
    path=SCRIPTS/(name+'.sh')
    path.write_text('#!/usr/bin/env bash\nset -eu\nsource '+shlex.quote(str(RUNTIME/'runtime.env'))+'\n'+
        "if [[ ${1-} == --plan ]]; then cat <<'PLAN'\n"+body+'PLAN\nexit 0\nfi\n'+
        'begin_run\nexec > >(tee -a "$RUN_DIR/'+name+'.log") 2>&1\n'+body)
    path.chmod(0o755)
    # Inline actual shell/rtshell commands in the Windows entry point, no Python lifecycle wrapper.
    inline='set -eu; source '+shlex.quote(str(RUNTIME/'runtime.env'))+'; begin_run; '+body.replace('\n','; ')
    inline=inline.replace(';;',';').replace('then;','then').replace('do;','do').replace('else;','else')
    cmd='wsl.exe -d Ubuntu -- bash --noprofile --norc -c "'+inline.replace('"','\\"').replace('%','%%')+'"'
    bat='@echo off\r\nif "%~1"=="--plan" (\r\n  echo '+cmd.replace('&','^&')+'\r\n  exit /b 0\r\n)\r\n'+cmd+'\r\nexit /b %ERRORLEVEL%\r\n'
    (SCRIPTS/(name+'.bat')).write_text(bat,newline='')
(SCRIPTS/'run_demo.sh').write_text('#!/usr/bin/env bash\nset -eu\n'+''.join('bash '+shlex.quote(str(SCRIPTS/(name+'.sh')))+'\n' for name in ('start_simulation','start_rtcs','connect_ports','activate_rtcs')))
(SCRIPTS/'README-runtime.txt').write_text('''Approved GUI joystick Drone system (WSL2 Ubuntu).
Run bash build/system/scripts/run_demo.sh inside WSL2, or the corresponding .bat entries on Windows.
Windows: double-click build/system/scripts/run_demo.bat to start; use stop_demo.bat to stop.
Keep this workspace at its configured location. Ubuntu WSL2, WSLg, the configured Foundation and existing Drone distribution are required.
Order: start_simulation -> start_rtcs -> connect_ports -> activate_rtcs.
In the GUI: Take off 1m, hold/drag a stick, release to stop future steps, Land.
The left stick uses world X/Y; the right stick uses Z/yaw. Input loss does NOT cancel a pending position step.
Left: right = +X, up = +Y. Right: up = +Z, right = positive yaw.
Wait for READY before takeoff; wait for ACTIVE before moving. Land and wait for READY before shutdown.
Steps: up to 0.2m / 5 degrees, one command at a time; bounds X/Y +/-3m, commanded flight altitude 0.3-3m.
Disable input and focus loss stop future steps. Closing the GUI alone does not stop the simulator; use stop_demo.bat.
Viewer: http://127.0.0.1:8000/index.html?viewerConfigPath=/config/viewer-config-fleets.json&wsUri=ws://127.0.0.1:8765&wireVersion=v2
Shutdown: Land in GUI and wait READY, deactivate_rtcs -> stop_rtcs -> stop_simulation.
Each lifecycle script accepts --plan. No physical devices are used.
All Python participants use the selected Foundation interpreter. OpenRTM standard IDL paths are exposed locally.
This deployment uses the existing public Drone distribution under its existing license; no new commercial rights.
Native upstream configuration remains JSON as required by those applications; RTC/process settings are conf/env/PID text.
Unique logs: build/system/logs/teleop-*. current run path: build/system/teleop/current-run.txt.
Owned PID/start tick/command digest records prevent cleanup of unrelated processes.
Plugins load via manager.modules.load_path/preload in teleop-controller-1.conf before RTC creation.
Native PDU bindings are specified in native-connections.ini and created by single_port_connections.py in connect_ports.
The installed rtcon/rtctree rejects single-ended DataPorts; only this native-binding exception uses the public PortService API.
RTC-to-RTC edges and all RTC lifecycle operations still use rtshell. Native connections persist through deactivate/reactivate.
Run connect_ports after the native simulation/PDU domain is ready. Runtime settings are not hardcoded in RTC source.
Bounded operations: CORBA call 5s, native command 5s, lifecycle request 10s, state/registration bounded retries.
Native readiness: up to 120 polls at 0.5s intervals plus each command duration (5s timeout per call).
Cold starts archive this composition's stopped mmap directory in the current log directory, then create a fresh dedicated domain.
Rotation requires the configured exact path, no live owned participants, and no observed process mapping those files.
GUI requires WSLg DISPLAY; browser uses localhost port8000 and WebSocket8765. Shared NameService uses port2809; healthy instances are reused and retained on RTC shutdown.
Validation: build/system/implementation-verification.json; motion GUI E2E and live viewer stream results are in its runtimeLogDirectory.
Verification covers WSLg Tk widget events, not Windows desktop mouse automation or browser GPU rendering.
If FAULT is shown, stop_demo.bat then run_demo.bat resets the dedicated simulation; no real hardware is connected.
''')
(SYSTEM/'deployment.json').write_text(json.dumps(dict(
    purpose='offline deployment metadata, not a runtime process manifest',
    designSha256=hashlib.sha256((SYSTEM/'final-session.json').read_bytes()).hexdigest(),
    foundation=str(args.foundation), runtime=str(RUNTIME), sourceTemplate=str(args.template),
    rootReferences={'FOUNDATION_ROOT':str(args.foundation),'DRONE_ROOT':str(args.drone_root),'BUSINESS_PACK_ROOT':str(BP),'RECIPE_ROOT':str(RUNTIME)},
    lifecycleScripts=list(operations),note='rtc.conf preloads plugins; native-connections.ini and the single-port tool own native bindings; rtshell owns ordinary connections/lifecycle.'),indent=2)+'\n')
print('Configured',RUNTIME)
subprocess.run([sys.executable,str(ROOT/'scripts/generate_teleop_batches.py')],check=True)

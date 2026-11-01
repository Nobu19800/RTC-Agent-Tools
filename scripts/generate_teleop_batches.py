"""Generate Windows entry points with direct WSL/rtshell calls, avoiding nested quoting."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/'build/system/scripts'
RUNTIME=ROOT/'build/system/teleop'
env=str(RUNTIME/'runtime.env')
ns='/localhost:2809/'


def shell(command,op):
    if '"' in command:
        raise ValueError('Use single-quoted arguments; nested Windows/bash double quotes are forbidden')
    body="set -eu; source '"+env+"'; begin_run; "+command
    return 'wsl.exe -d Ubuntu --exec bash --noprofile --norc -c "'+body+'"'


def state(id,active):
    return 'assert_state '+id+(' Active' if active else ' Inactive')


def connect(name,source,source_port,target,target_port):
    src=ns+source+'.rtc'; dst=ns+target+'.rtc'
    snapshot="scoped_rtcat '"+src+"' > $RUN_DIR/"+name+"-source.txt; scoped_rtcat '"+dst+"' > $RUN_DIR/"+name+"-target.txt; "
    check="$PY $ROOT/scripts/check_rtc_connection.py $RUN_DIR/"+name+"-source.txt $RUN_DIR/"+name+"-target.txt "+source_port+' '+target_port+" '"+src+':'+source_port+"' '"+dst+':'+target_port+"'"
    create="timeout 10 rtcon -d -i "+name+' -n '+name+" -p dataport.dataflow_type=push -p dataport.subscription_type=flush -p dataport.buffer.length=1 '"+src+':'+source_port+"' '"+dst+':'+target_port+"'"
    return snapshot+'if '+check+"; then echo 'Existing connection verified'; else connection_result=$?; if [ $connection_result -eq 2 ]; then "+create+"; else exit 1; fi; fi; "+snapshot+check


plans={
'start_rtcs':[
    "prepare_nameserver; $PY $ROOT/scripts/configure_wsl_rtc_endpoint.py",
    "start_owned controller $PY $ROOT/build/generated/DroneTeleopControllerRTC/DroneTeleopControllerRTC.py -f $RUNTIME/teleop-controller-1.conf --instance_name=teleop-controller-1; wait_registration teleop-controller-1",
    "start_owned gui $PY $ROOT/build/generated/DroneJoystickGUIRTC/DroneJoystickGUIRTC.py -f $RUNTIME/gui-joystick-1.conf --instance_name=gui-joystick-1; wait_registration gui-joystick-1",
],
'connect_ports':[
    "wait_registration gui-joystick-1; wait_registration teleop-controller-1",
    connect('pilot-input','gui-joystick-1','pilot','teleop-controller-1','pilot'),
    connect('teleop-status','teleop-controller-1','status','gui-joystick-1','status'),
    "wait_core running; $PY $ROOT/scripts/single_port_connections.py --rtc /localhost:2809/teleop-controller-1.rtc --config $RUNTIME/native-connections.ini --action connect",
    "scoped_rtcat '"+ns+"teleop-controller-1.rtc' > $RUN_DIR/windows-connections.txt; grep -q pilot-input $RUN_DIR/windows-connections.txt; grep -q teleop-status $RUN_DIR/windows-connections.txt",
],
'activate_rtcs':[
    "$PY $ROOT/scripts/single_port_connections.py --rtc /localhost:2809/teleop-controller-1.rtc --config $RUNTIME/native-connections.ini --action check",
    "wait_core running; scoped_rtcat '"+ns+"teleop-controller-1.rtc' > $RUN_DIR/windows-preactivation.txt; grep -q pilot-input $RUN_DIR/windows-preactivation.txt; grep -q teleop-status $RUN_DIR/windows-preactivation.txt",
    "if ! rtc_active teleop-controller-1; then timeout 10 rtact '"+ns+"teleop-controller-1.rtc'; fi; "+state('teleop-controller-1',True),
    "if ! rtc_active gui-joystick-1; then timeout 10 rtact '"+ns+"gui-joystick-1.rtc'; fi; "+state('gui-joystick-1',True),
],
'deactivate_rtcs':[
    "ensure_naming; if rtc_registered gui-joystick-1; then wait_registration gui-joystick-1; if rtc_active gui-joystick-1; then timeout 10 rtdeact '"+ns+"gui-joystick-1.rtc'; fi; "+state('gui-joystick-1',False)+"; else echo 'GUI already absent'; fi",
    "ensure_naming; if rtc_registered teleop-controller-1; then wait_registration teleop-controller-1; if rtc_active teleop-controller-1; then timeout 10 rtdeact '"+ns+"teleop-controller-1.rtc'; fi; "+state('teleop-controller-1',False)+"; else echo 'Controller already absent'; fi",
],
'stop_rtcs':[],
}
for id,process in (('gui-joystick-1','gui'),('teleop-controller-1','controller')):
    plans['stop_rtcs'].append(
        "ensure_naming; if rtc_registered "+id+"; then if owned_alive "+process+"; then wait_registration "+id+
        "; if rtc_active "+id+"; then timeout 10 rtdeact '"+ns+id+".rtc'; fi; timeout 10 rtexit '"+ns+id+
        ".rtc'; else timeout 7 rtdel -z '"+ns+id+".rtc'; fi; wait_absence "+id+"; fi; stop_owned "+process+
        "; echo 'SHUTDOWN_SUMMARY "+id+" registration=absent process=checked'")
plans['stop_rtcs'].append("echo 'Shared NameService localhost:2809 retained'")

for operation,commands in plans.items():
    lines=[shell(c,operation) for c in commands]
    aggregate=operation in ('deactivate_rtcs','stop_rtcs')
    output=['@echo off','setlocal','set RESULT=0','if "%~1"=="--plan" goto plan']
    for line in lines:
        output += [line,'if errorlevel 1 '+('set RESULT=1' if aggregate else 'exit /b %ERRORLEVEL%')]
    output += ['exit /b %RESULT%',':plan']
    for line in lines:
        # Escape cmd metacharacters only in echo/plan, not in the real native command.
        escaped=line.replace('^','^^')
        for char in '&|<>()': escaped=escaped.replace(char,'^'+char)
        output.append('echo '+escaped)
    output.append('exit /b 0')
    (SCRIPTS/(operation+'.bat')).write_text('\r\n'.join(output)+'\r\n',newline='')

helpers=r'''
ensure_naming() {
  nameserver_list > "$RUN_DIR/windows-naming.txt" 2>&1
}
rtc_registered() {
  grep -Fq "$1.rtc" "$RUN_DIR/windows-naming.txt"
}
rtc_active() {
  timeout 7 rtcat "/$RTCSERVER/$1.rtc" > "$RUN_DIR/windows-state-$1.txt" 2>&1 || return 1
  grep -Eq '(^|[^[:alpha:]])Active([^[:alpha:]]|$)' "$RUN_DIR/windows-state-$1.txt"
}
wait_absence() {
  for i in $(seq 1 30); do
    ensure_naming || return 1
    rtc_registered "$1" || return 0
    sleep .2
  done
  echo "STILL REGISTERED $1" >&2; return 1
}
'''
process=SCRIPTS/'processes.sh'
text=process.read_text()
if '\nensure_naming()' in text: text=text.split('\nensure_naming()')[0]
process.write_text(text+helpers)
for operation in ('start_simulation','stop_simulation'):
    command='wsl.exe -d Ubuntu --exec bash "'+str(SCRIPTS/(operation+'.sh'))+'"'
    (SCRIPTS/(operation+'.bat')).write_text('@echo off\r\n'+command+' %*\r\nexit /b %ERRORLEVEL%\r\n',newline='')
for demo,sequence in [('run_demo',('start_simulation','start_rtcs','connect_ports','activate_rtcs')),
                      ('stop_demo',('deactivate_rtcs','stop_rtcs','stop_simulation'))]:
    lines=['@echo off','setlocal','set RESULT=0']
    for op in sequence:
        lines += ['call "%~dp0'+op+'.bat" %*','if errorlevel 1 '+('set RESULT=1' if demo=='stop_demo' else 'exit /b %ERRORLEVEL%')]
    lines.append('exit /b %RESULT%')
    (SCRIPTS/(demo+'.bat')).write_text('\r\n'.join(lines)+'\r\n',newline='')
print('Generated five direct-command Windows lifecycle batches and demo entry points')

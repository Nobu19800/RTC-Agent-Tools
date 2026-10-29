"""Render native lifecycle batches. Generation only; no runtime command is run."""
from pathlib import Path
import shutil
import subprocess


COMMON = r'''@echo off
if "%~1"=="owned" goto owned
if "%~1"=="state" goto state
if "%~1"=="wait_state" goto wait_state
if "%~1"=="wait_absent" goto wait_absent
if "%~1"=="connected" goto connected
if "%~1"=="data" goto data
if "%~1"=="service" goto service
if "%~1"=="wait_ns" goto wait_ns
if "%~1"=="check_design" goto check_design
exit /b 2

:check_design
certutil -hashfile "%RTC_FINAL_SESSION%" SHA256 >"%RTC_QUERY%" 2>&1
if errorlevel 1 exit /b 1
findstr /I /L /C:"%RTC_DESIGN_SHA256%" "%RTC_QUERY%" >nul
exit /b %errorlevel%

:wait_ns
set /a RTC_TRY=0
:wait_ns_loop
"%RTLS%" "%RTC_NS_ROOT%/" >"%RTC_QUERY%" 2>&1
if not errorlevel 1 exit /b 0
set /a RTC_TRY+=1
if %RTC_TRY% GEQ %RTC_WAIT_ATTEMPTS% exit /b 1
ping -n 2 127.0.0.1 >nul
goto wait_ns_loop

:owned
"%RTCAT%" -ll "%~2" >"%RTC_QUERY%" 2>&1
if errorlevel 1 exit /b 1
findstr /R /C:"^  Instance name  *%~4$" "%RTC_QUERY%" >nul || exit /b 1
findstr /R /C:"^  Type name  *%~3$" "%RTC_QUERY%" >nul || exit /b 1
findstr /R /C:"^ *runtime_owner  *%RTC_SESSION%_%~5$" "%RTC_QUERY%" >nul || exit /b 1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-OwnedRtc.ps1" -Mode Check -Node "%~5" >>"%RTC_LOG%" 2>&1
exit /b %errorlevel%

:state
set "RTC_STATE="
"%RTLS%" -l "%~2" >"%RTC_QUERY%" 2>&1
if errorlevel 1 exit /b 1
for /f "usebackq tokens=1" %%S in ("%RTC_QUERY%") do set "RTC_STATE=%%S"
if not defined RTC_STATE exit /b 1
exit /b 0

:wait_state
set /a RTC_TRY=0
:wait_state_loop
call "%~f0" state "%~2"
if "%RTC_STATE%"=="%~3" exit /b 0
if "%RTC_STATE%"=="Error" exit /b 1
set /a RTC_TRY+=1
if %RTC_TRY% GEQ %RTC_WAIT_ATTEMPTS% exit /b 1
ping -n 2 127.0.0.1 >nul
goto wait_state_loop

:wait_absent
set /a RTC_TRY=0
:wait_absent_loop
"%RTLS%" "%RTC_NS_ROOT%/" >"%RTC_QUERY%" 2>&1
if errorlevel 1 exit /b 1
"%RTLS%" -l "%~2" >"%RTC_QUERY%" 2>&1
if errorlevel 1 exit /b 0
set /a RTC_TRY+=1
if %RTC_TRY% GEQ %RTC_WAIT_ATTEMPTS% exit /b 1
ping -n 2 127.0.0.1 >nul
goto wait_absent_loop

:connected
"%RTCAT%" -ll "%~2" >"%RTC_QUERY%" 2>&1
if errorlevel 1 exit /b 1
set "RTC_CONNECTED="
for /f "tokens=1,2,*" %%A in ('findstr /L /C:"Connected to  " "%RTC_QUERY%"') do if "%%C"=="%~3" set "RTC_CONNECTED=YES"
if defined RTC_CONNECTED exit /b 0
exit /b 1

:data
"%RTCAT%" -l "%~2" >"%RTC_QUERY%" 2>&1
if errorlevel 1 exit /b 1
findstr /L /C:"%~4:" "%RTC_QUERY%" >nul || exit /b 1
set "RTC_TYPE_OK="
for /f "usebackq tokens=1,*" %%A in ("%RTC_QUERY%") do if "%%A"=="dataport.data_type" if "%%B"=="%~3" set "RTC_TYPE_OK=YES"
for /f "usebackq tokens=1,*" %%A in ("%RTC_QUERY%") do if "%%A"=="dataport.data_type" if "%%B"=="%~5" set "RTC_TYPE_OK=YES"
if defined RTC_TYPE_OK exit /b 0
exit /b 1

:service
"%RTCAT%" -l "%~2" >"%RTC_QUERY%" 2>&1
if errorlevel 1 exit /b 1
findstr /L /C:"CorbaPort:" "%RTC_QUERY%" >nul || exit /b 1
findstr /R /C:"^ *Instance name  *%~3$" "%RTC_QUERY%" >nul || exit /b 1
findstr /R /C:"^ *Type name  *%~4$" "%RTC_QUERY%" >nul || exit /b 1
findstr /R /C:"^ *Polarity  *%~5$" "%RTC_QUERY%" >nul || exit /b 1
exit /b 0
'''

COMMON = COMMON.replace('"%RTLS%" ', 'call "%RTLS%" ').replace('"%RTCAT%" ', 'call "%RTCAT%" ')


def write_direct_batches(root, folder, manifest):
    def write(name, lines):
        text = lines if isinstance(lines, str) else '\n'.join(lines)+'\n'
        (folder/name).write_bytes(text.replace('\r\n','\n').replace('\n','\r\n').encode('utf-8'))
    def quote(value):
        if any(c in value for c in '\r\n%!"'):
            raise ValueError('Unsupported batch metacharacters in generated value: ' + value)
        return '"' + value + '"'
    for node in manifest['nodes']:
        node['argumentLine'] = subprocess.list2cmdline(node['command'][1:])
        node['path'] = '/' + manifest['nameserver'] + '/' + manifest['context'] + '/' + node['instance'] + '.rtc'
        config = Path(node['componentConf'])
        text = config.read_text(encoding='utf-8')
        text += 'runtime_owner: ' + manifest['sessionId'] + '_' + node['id'] + '\n'
        config.write_text(text, encoding='utf-8')
    by_id = {n['id']: n for n in manifest['nodes']}
    ns_directory = str(Path(manifest['namingDataDirectory']))
    ns_command = [manifest['omniNames'], '-start', '2809', '-always', '-datadir', ns_directory]
    manifest['infrastructure'] = [dict(id='nameserver', command=ns_command,
        argumentLine=subprocess.list2cmdline(ns_command[1:]), workingDirectory=ns_directory, environment={})]
    common = 'call "%~dp0runtime_common.bat" '
    process = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-OwnedRtc.ps1" '
    fail = 'if errorlevel 1 goto failed'
    env = ['@echo off', 'set "RTC_SESSION='+manifest['sessionId']+'"',
           'set "PYTHONIOENCODING=utf-8"',
           'set "PYTHONUTF8=1"',
           r'set "RTC_FINAL_SESSION=%~dp0..\final-session.json"',
           'set "RTC_DESIGN_SHA256='+manifest['finalSessionSha256']+'"',
           'set "RTC_NS_ROOT=/'+manifest['nameserver']+'"',
           'set "RTCTREE_NAMESERVERS='+manifest['nameserver']+'"',
           'set "RTCTREE_ORB_ARGS=-ORBclientCallTimeOutPeriod;3000"',
           'if not defined RTC_WAIT_ATTEMPTS set "RTC_WAIT_ATTEMPTS=15"',
           r'set "RTC_LOG_DIR=%~dp0..\logs"', r'set "RTC_STATE_DIR=%~dp0..\runtime-state"',
           'set "PATH='+';'.join(manifest['dllDirectories'])+';%PATH%"']
    for name, executable in manifest['rtshell'].items():
        env += ['if not defined '+name.upper()+' set "'+name.upper()+'='+executable+'"']
    env += ['exit /b 0']
    write('runtime_env.bat', env)
    write('runtime_common.bat', COMMON)
    shutil.copy2(root/'scripts/Start-OwnedRtc.ps1', folder/'Start-OwnedRtc.ps1')

    def header(operation, plan):
        lines = ['@echo off', 'setlocal DisableDelayedExpansion', 'call "%~dp0runtime_env.bat"',
                 'if errorlevel 1 exit /b %errorlevel%', 'if /I "%~1"=="--plan" goto plan',
                 'if not exist "%RTC_LOG_DIR%" mkdir "%RTC_LOG_DIR%"',
                 'if not exist "%RTC_STATE_DIR%" mkdir "%RTC_STATE_DIR%"',
                 'set "RTC_LOG=%RTC_LOG_DIR%\\'+operation+'-%RANDOM%.log"',
                 'set "RTC_QUERY=%RTC_LOG_DIR%\\'+operation+'-%RANDOM%.txt"',
                 'echo [%DATE% %TIME%] '+operation+' >>"%RTC_LOG%"',
                 common+'check_design',fail]
        for name in manifest['rtshell']:
            lines += ['if not exist "%'+name.upper()+'%" goto failed']
        lines += ['"%RTLS%" "%RTC_NS_ROOT%/" >>"%RTC_LOG%" 2>&1', fail]
        return lines
    def footer(plan):
        return ['echo Completed. Logs: "%RTC_LOG%"', 'exit /b 0', ':failed',
                'echo ERROR: operation failed. Check "%RTC_LOG%" and "%RTC_QUERY%". 1>&2',
                'exit /b 1', ':plan', *['echo '+line for line in plan], 'exit /b 0']
    def owned(node):
        return common+'owned '+ ' '.join(quote(v) for v in [node['path'],node['name'],node['instance'],node['id']])
    def check_all(lines):
        for node in manifest['nodes']:
            lines += [owned(node), fail]
    def endpoints(edge):
        return by_id[edge['source']]['path']+':'+edge['sourcePort'], by_id[edge['target']]['path']+':'+edge['targetPort']

    # The actual rtcon commands remain visible in connect_ports.bat.
    plan=[]
    lines=header('connect', plan)
    check_all(lines)
    for index,edge in enumerate(manifest['edges']):
        a,b=endpoints(edge)
        if edge['kind']=='data':
            repository='IDL:'+edge['dataType'].replace('::','/')+':1.0'
            for port,direction in [(a,'DataOutPort'),(b,'DataInPort')]:
                lines += [common+'data '+' '.join(quote(v) for v in [port,edge['dataType'],direction,repository]),fail]
        else:
            for interface in edge['interfaces']:
                for port,polarity in [(a,'Required'),(b,'Provided')]:
                    lines += [common+'service '+' '.join(quote(v) for v in [port,interface['name'],interface['interfaceType'],polarity]),fail]
        command='"%RTCON%" -d -i '+quote(edge['id'])+' -n '+quote(edge['id'])+' '+quote(a)+' '+quote(b)
        lines += [common+'connected '+quote(a)+' '+quote(b),
                  'if not errorlevel 1 goto connected_'+str(index),command+' >>"%RTC_LOG%" 2>&1',fail,
                  common+'connected '+quote(a)+' '+quote(b),fail,':connected_'+str(index)]
        plan.append(command)
    write('connect_ports.bat',lines+footer(plan))

    for operation,filename,order,desired,tool in [
        ('activate','activate_rtcs.bat',manifest['activationOrder'],'Active','RTACT'),
        ('deactivate','deactivate_rtcs.bat',manifest['deactivationOrder'],'Inactive','RTDEACT'),
        ('stop','stop_rtcs.bat',manifest['deactivationOrder'],'Inactive','RTDEACT')]:
        plan=[]
        lines=header(operation, plan)
        if operation=='activate':
            check_all(lines)
            for edge in manifest['edges']:
                a,b=endpoints(edge)
                lines += [common+'connected '+quote(a)+' '+quote(b),fail]
        for index,key in enumerate(order):
            node=by_id[key]
            path=quote(node['path'])
            if operation!='activate':
                lines += [common+'state '+path,
                          'if errorlevel 1 goto absent_'+str(index),owned(node),fail]
            lines += [common+'state '+path,fail,
                      'if "%RTC_STATE%"=="'+desired+'" goto state_done_'+str(index),
                      'if not "%RTC_STATE%"=="'+('Inactive' if desired=='Active' else 'Active')+'" goto failed']
            command='"%'+tool+'%" -e '+str(node['ecIndex'])+' '+path
            lines += [command+' >>"%RTC_LOG%" 2>&1',fail,
                      common+'wait_state '+path+' '+desired,fail,':state_done_'+str(index)]
            plan.append(command)
            if operation=='stop':
                command='"%RTEXIT%" '+path
                lines += [command+' >>"%RTC_LOG%" 2>&1',fail,
                          common+'wait_absent '+path,fail]
                plan.append(command)
            if operation=='deactivate':
                lines += ['goto node_done_'+str(index), ':absent_'+str(index),
                          common+'wait_absent '+path,fail,':node_done_'+str(index)]
            else:
                lines += [':absent_'+str(index)]
            if operation=='stop':
                # Check server availability before treating a missing registration as exited.
                lines += [common+'wait_absent '+path,fail,
                          process+'-Mode Cleanup -Node '+quote(key)+' >>"%RTC_LOG%" 2>&1',fail]
        write(filename,lines+footer(plan))

    # Startup uses a process-only PS utility; the .bat owns sequencing and readiness.
    plan=[]
    lines=header('start',plan)
    # Override the nameserver check in this file with an explicit, hidden local launch.
    lines=lines[:-2]+['"%RTLS%" "%RTC_NS_ROOT%/" >>"%RTC_LOG%" 2>&1',
        'if not errorlevel 1 goto nameserver_ready',
        process+'-Mode Start -Node "nameserver"',fail,
        common+'wait_ns',fail, ':nameserver_ready']
    for index,node in enumerate(manifest['nodes']):
        path=quote(node['path'])
        lines += [common+'state '+path,'if errorlevel 1 goto launch_'+str(index),
                  owned(node),fail,'goto started_'+str(index),':launch_'+str(index),
                  process+'-Mode Start -Node '+quote(node['id']),fail,
                  common+'wait_state '+path+' Inactive',fail,owned(node),fail,':started_'+str(index)]
        plan.append('START '+subprocess.list2cmdline(node['command']))
    write('start_rtcs.bat',lines+footer(plan))
    readme='''Native RTC lifecycle batch files

Execute in order: start_rtcs.bat, connect_ports.bat, activate_rtcs.bat,
deactivate_rtcs.bat, stop_rtcs.bat. Each accepts --plan to print commands only.
The rtcon/rtact/rtdeact/rtexit command lines are written directly in the four
control batches. No Python lifecycle controller is invoked. rtshell itself
requires Python; the myCobot RTC is also a Python application.

runtime_env.bat contains shared rtshell locations, DLL paths and wait attempts.
runtime_common.bat uses rtcat/rtls for profile, type, connection and state checks.
Start-OwnedRtc.ps1 ONLY launches hidden processes, verifies PID/executable/start
time and cleans up owned managers after successful rtexit and unregistration.
runtime-settings.json is used by that process utility, not for RTC orchestration.
Per-RTC configurations are in ../runtime-config/; logs are in ../logs/.
Ownership markers are set in component configuration and checked with rtcat -ll.
Do not delete ../runtime-state/*-pid.json while owned RTCs/managers are running.

Prerequisites: reachable localhost:2809 nameserver, rtshell rtls/rtcat/rtcon/rtact/
rtdeact/rtexit, Windows PowerShell, existing RTC executables and their dependencies.
The startup batch reuses a reachable server or starts the configured local
omniNames process with an ownership record. Nameservers are never terminated.
COM3 remains the reviewed placeholder. myCobot connects to the serial device
during initialization/startup, before activation. Review hardware settings first.

Activation order is arm, executor, planner, projector, detector, camera. This
starts service providers and downstream consumers before the image producer.
Deactivation stops the planner and producer first, then executor before the arm.
The feedback loop is handled by activating the executor before the planner.
RTC_WAIT_ATTEMPTS defaults to 15, with 1-second polling and a 3-second CORBA call
timeout. A full operation can take longer than 15 seconds. Failed commands or
checks return exit code 1 and retain diagnostic query output in the log folder.
Equivalent connections and already completed state transitions are skipped.
Owned single-RTC manager processes left alive by manager.shutdown_auto=NO are
cleaned up by recorded PID, executable path and start time; no name-based kill.
Do not run multiple lifecycle batches concurrently.

Regenerate after changing final-session.json:
  python scripts/generate_runtime_batches.py
Python is used only for this generation step, not as a runtime controller.
Inspect the generated files before running. Verification performed during
generation is offline only. See ../startup-verification.json for any subsequent
real startup checks; generation itself does not operate RTCs. Generated RTCs
use typed Manipulation IDL data; dry_run=true and enabled=false are preserved.
'''
    write('README-runtime.txt',readme)

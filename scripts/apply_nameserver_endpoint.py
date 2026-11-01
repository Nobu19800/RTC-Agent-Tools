"""Root-only one-time service configuration; repeated healthy startup does not restart."""
import configparser
from datetime import datetime,timezone
import hashlib
import ipaddress
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]

def main():
    if os.geteuid()!=0: raise PermissionError('Run through the verified WSL root service helper')
    address=str(ipaddress.IPv4Address(sys.argv[1]))
    if ipaddress.ip_address(address).is_loopback: raise ValueError('Select Windows-reachable WSL IPv4')
    service='omniorb-nameserver.service'
    command=subprocess.check_output(['systemctl','show',service,'-p','ExecStart','--value'],text=True)
    if '/usr/bin/omniNames' not in command: raise ValueError('Unrecognized service; refusing reconfiguration')
    desired=(ROOT/'scripts/omniorb-nameserver-2809.conf').read_text().replace('@WSL_ENDPOINT_IP@',address)
    digest=hashlib.sha256(desired.encode()).hexdigest()
    target=Path('/etc/systemd/system/omniorb-nameserver.service.d/2809-local.conf')
    marker=Path('/var/lib/omniorb/rtc-agent-endpoint.ini')
    previous=configparser.ConfigParser(); previous.read(marker)
    first=previous.get('application','config_sha256',fallback='')!=digest
    if first and previous.has_section('application') and '--apply-changed-endpoint' not in sys.argv[2:]:
        raise ValueError('Endpoint configuration changed after initial application; review it and explicitly apply with --apply-changed-endpoint')
    actual=target.read_text() if target.exists() else ''
    if not first and actual!=desired:
        raise ValueError('Service settings changed after initial application; review before restart')
    if first:
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists(): shutil.copy2(target,target.with_name(target.name+'.before-'+stamp))
        target.write_text(desired)
        subprocess.run(['systemctl','daemon-reload'],check=True)
        subprocess.run(['systemctl','restart',service],check=True)
        print('INITIAL ENDPOINT APPLICATION: restarted NameService -> '+address+':2809',flush=True)
    # No automatic restart loop on later startup. Unhealthy service is reported.
    probe=['/usr/bin/python3',str(ROOT/'scripts/nameserver_probe.py'),'127.0.0.1:2809']
    for _ in range(10 if first else 1):
        result=subprocess.run(probe,capture_output=True,text=True,timeout=8)
        if result.returncode==0: break
        time.sleep(.3)
    else: raise RuntimeError('NameService unhealthy; no repeated restart: '+result.stderr)
    pid=subprocess.check_output(['systemctl','show',service,'-p','MainPID','--value'],text=True).strip()
    if first:
        record=configparser.ConfigParser()
        record['application']={'address':address,'port':'2809','config_sha256':digest,
            'applied_at_utc':datetime.now(timezone.utc).isoformat(),'initial_pid':pid}
        with marker.open('w') as stream: record.write(stream)
    print(('APPLIED' if first else 'REUSE WITHOUT RESTART')+' NameService PID='+pid,flush=True)

if __name__=='__main__': main()

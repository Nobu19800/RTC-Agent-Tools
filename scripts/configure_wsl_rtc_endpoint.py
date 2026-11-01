"""Resolve unspecified WSL RTC endpoint defaults; explicit endpoints are preserved."""
import configparser
import ipaddress
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
RUNTIME=ROOT/'build/system/teleop'

def resolve_address():
    routes=json.loads(subprocess.check_output(['ip','-j','-4','route','show','default'],text=True))
    interfaces={r['dev'] for r in routes if 'dev' in r and r['dev']!='lo'}
    addresses=json.loads(subprocess.check_output(['ip','-j','-4','addr','show','scope','global'],text=True))
    candidates=[info['local'] for link in addresses if link['ifname'] in interfaces
                for info in link.get('addr_info',[]) if info.get('family')=='inet' and not ipaddress.ip_address(info['local']).is_loopback]
    if len(candidates)!=1:
        raise ValueError('Cannot choose a unique default-route IPv4 address: '+repr(candidates))
    return candidates[0]

def main():
    address=resolve_address()
    marker=RUNTIME/'endpoint-defaults.ini'
    previous=configparser.ConfigParser(); previous.read(marker)
    current=configparser.ConfigParser()
    for instance in ('gui-joystick-1','teleop-controller-1'):
        path=RUNTIME/(instance+'.conf'); text=path.read_text()
        endpoints=re.search(r'^corba\.endpoints\s*:\s*(.*?)\s*$',text,re.M)
        corba_args=re.search(r'^corba\.args\s*:\s*(.*)$',text,re.M)
        old=previous.get(instance,'endpoint',fallback=None)
        value=endpoints[1] if endpoints else ''
        if corba_args and any(k in corba_args[1] for k in ('endPoint','ORBendPoint')):
            print('PRESERVE explicit corba.args endpoint:',instance); continue
        if value not in ('','all',old):
            print('PRESERVE explicit corba.endpoints:',instance,value); continue
        setting=address+':'
        if endpoints: text=text[:endpoints.start()]+ 'corba.endpoints: '+setting+text[endpoints.end():]
        else: text='corba.endpoints: '+setting+'\n'+text
        if path.read_text()!=text: path.write_text(text)
        current[instance]={'endpoint':setting,'selection':'default-route-interface','windows_verification':'separate required check'}
        print('WSL RTC ENDPOINT DEFAULT:',instance,setting)
    with marker.open('w') as stream: current.write(stream)
    print('Windows-side RTC calls must verify the selected address; selection alone is not verification.')

if __name__=='__main__': main()

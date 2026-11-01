"""Offline repair of stale local NamingContext addresses; preserve all RTC bindings."""
import argparse
from datetime import datetime,timezone
from pathlib import Path
import re
import shutil
import struct

class CDR:
    def __init__(self,data): self.data=data; self.pos=0; self.endian='<' if data[0] else '>'; self.pos=4
    def align(self,n): self.pos=(self.pos+n-1)//n*n
    def u32(self):
        self.align(4); v=struct.unpack_from(self.endian+'I',self.data,self.pos)[0]; self.pos+=4; return v
    def octets(self):
        n=self.u32(); v=self.data[self.pos:self.pos+n]; assert len(v)==n; self.pos+=n; return v
    def string(self): return self.octets().rstrip(b'\0').decode()

def pad(data,n): return data+b'\0'*((-len(data))%n)
def seq(data,value,endian): return pad(data,4)+struct.pack(endian+'I',len(value))+value

def repair_ior(value):
    data=bytes.fromhex(value[4:]); r=CDR(data)
    repository=r.string()
    if not repository.startswith('IDL:omg.org/CosNaming/NamingContext'): return value
    count=r.u32(); out=seq(data[:4],repository.encode()+b'\0',r.endian)
    out=pad(out,4)+struct.pack(r.endian+'I',count)
    changed=False
    for _ in range(count):
        tag=r.u32(); profile=r.octets()
        if tag==0:
            p=CDR(profile); host=p.string()
            if host=='10.255.255.254':
                p.align(2); port=struct.unpack_from(p.endian+'H',profile,p.pos)[0]; p.pos+=2
                assert port==2809
                key=p.octets(); p.align(4)
                rebuilt=seq(profile[:4],b'127.0.0.1\0',p.endian)
                rebuilt=pad(rebuilt,2)+struct.pack(p.endian+'H',port)
                rebuilt=seq(rebuilt,key,p.endian)
                if p.pos<len(profile): rebuilt=pad(rebuilt,4)+profile[p.pos:]
                profile=rebuilt; changed=True
        out=pad(out,4)+struct.pack(r.endian+'I',tag)
        out=seq(out,profile,r.endian)
    return 'IOR:'+out.hex() if changed else value

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file',type=Path); args=parser.parse_args()
    path=args.file.resolve(); assert path.parent==Path('/var/lib/omniorb') and path.suffix=='.dat'
    original=path.read_text()
    revised=re.sub(r'IOR:[0-9A-Fa-f]+',lambda m:repair_ior(m.group()),original)
    if revised!=original:
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        shutil.copy2(path,path.with_name(path.name+'.before-context-repair-'+stamp))
        path.write_text(revised)
        print('Repaired local NamingContext IOR addresses; RTC object references and names retained')
    else: print('No stale local NamingContext addresses')

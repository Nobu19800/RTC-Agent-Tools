"""Read-only check of two rtcat -ll snapshots. Exit 0=reuse, 2=absent, 1=conflict."""
import argparse
from pathlib import Path
import re

def port_snapshot(text,port):
    sections=re.split(r'^\s*[+-]Data(?:In|Out)Port:\s*',text,flags=re.M)
    for section in sections[1:]:
        if section.splitlines()[0].strip()!=port: continue
        if re.search(r'\(\d+ other connections?\)',section):
            raise ValueError('Opaque connection cannot be verified on '+port)
        dtype=re.search(r'^\s*data_type\s+(\S+)',section,re.M)
        blocks=re.split(r'^\s*[+-]Connected to\s+',section,flags=re.M)[1:]
        connections=[]
        for block in blocks:
            lines=block.splitlines()
            props={}
            for line in lines[1:]:
                match=re.match(r'\s*(\S+)\s{2,}(.*?)\s*$',line)
                if match: props[match[1]]=match[2]
            connections.append((lines[0].strip(),props))
        return (dtype[1] if dtype else None),connections
    raise ValueError('Port missing: '+port)

def check(source,target,source_port,target_port,source_endpoint,target_endpoint):
    st,sc=port_snapshot(source,source_port); tt,tc=port_snapshot(target,target_port)
    if not st or st!=tt: return 1
    if not sc and not tc: return 2
    if len(sc)!=1 or len(tc)!=1: return 1
    sp,sprops=sc[0]; tp,tprops=tc[0]
    if sp!=target_endpoint or tp!=source_endpoint: return 1
    if not sprops.get('ID') or sprops.get('ID')!=tprops.get('ID'): return 1
    required={'dataport.dataflow_type':'push','dataport.subscription_type':'flush',
              'dataport.buffer.length':'1','dataport.interface_type':'corba_cdr','dataport.data_type':st}
    return 0 if all(sprops.get(k)==v and tprops.get(k)==v for k,v in required.items()) else 1

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source_file','target_file','source_port','target_port','source_endpoint','target_endpoint'): p.add_argument(name)
    a=p.parse_args()
    try:
        result=check(Path(a.source_file).read_text(),Path(a.target_file).read_text(),a.source_port,a.target_port,a.source_endpoint,a.target_endpoint)
    except (ValueError,OSError) as e:
        p.exit(1,str(e)+'\n')
    print({0:'REUSE equivalent existing connection',2:'No existing connection',1:'Conflicting or partial connection; unchanged'}[result])
    raise SystemExit(result)

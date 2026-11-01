"""Read-only prerequisite inspection; does not start RTCs, native assets or installers."""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import zipfile

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--java',type=Path); p.add_argument('--builder-lib',type=Path)
    p.add_argument('--teleop',action='store_true',help='Check imports in this selected Foundation interpreter')
    p.add_argument('--viewer-root',type=Path); p.add_argument('--output',type=Path)
    a=p.parse_args(); checks=[]
    def check(name,operation):
        try: checks.append(dict(name=name,passed=True,detail=operation()))
        except Exception as e: checks.append(dict(name=name,passed=False,detail=str(e)))
    if a.java:
        def java():
            r=subprocess.run([str(a.java),'-version'],capture_output=True,text=True,timeout=10,check=True)
            return r.stdout+r.stderr
        check('Java executable',java)
    if a.builder_lib:
        def jars():
            paths=list(a.builder_lib.glob('*.jar'))
            if not paths: raise ValueError('No JARs in '+str(a.builder_lib))
            if not any('jp/go/aist/rtm/cuirtcbuilder/CuiRtcBuilder.class' in zipfile.ZipFile(x).namelist() for x in paths):
                raise ValueError('CuiRtcBuilder main class missing')
            return {str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in paths}
        check('Builder libraries',jars)
    if a.teleop:
        for name in ('CORBA','OpenRTM_aist','rtshell','hakopy','hakoniwa_pdu','DroneTeleop'):
            check(name,lambda n=name:str(getattr(importlib.import_module(n),'__file__',None)))
    if a.viewer_root:
        for name in ('index.html','src/public/drone_viewer.js','thirdparty/hakoniwa-pdu-javascript/src/PduManager.js',
                     'thirdparty/hakoniwa-pdu-javascript/src/pdu_msgs/std_msgs/pdu_conv_UInt32.js','assets/models/base-drone-frame.glb','assets/models/base-floor.glb'):
            def asset(n=name):
                f=a.viewer_root/n
                if not f.is_file(): raise FileNotFoundError(f)
                return hashlib.sha256(f.read_bytes()).hexdigest()
            check(name,asset)
    report=dict(interpreter=sys.executable,python=platform.python_version(),abi=sys.implementation.cache_tag,
                passed=bool(checks) and all(c['passed'] for c in checks),checks=checks)
    raw=json.dumps(report,indent=2)+'\n'
    if a.output: a.output.write_text(raw)
    print(raw); return 0 if report['passed'] else 1

if __name__=='__main__': raise SystemExit(main())

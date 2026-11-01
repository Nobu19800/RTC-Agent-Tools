"""Complete the local viewer deployment using existing checked-out dependencies."""
import json
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
from datetime import datetime, timezone

root=Path(__file__).resolve().parents[1]
viewer=Path(os.environ['VIEWER_ROOT']).resolve()
run=Path(os.environ['RUN_DIR'])
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--dependency-source',type=Path,required=True,help='Explicit clean hakoniwa-pdu-javascript checkout')
parser.add_argument('--dependency-revision',required=True,help='Expected full source commit hash')
args=parser.parse_args()
source=args.dependency_source.resolve()
revision=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
if revision!=args.dependency_revision: raise ValueError('Dependency revision mismatch')
if subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True).strip():
    raise ValueError('Dependency source is dirty; supply a clean recorded revision')
target=viewer/'thirdparty/hakoniwa-pdu-javascript'
assert (source/'src/PduManager.js').is_file()
shutil.copytree(source,target,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.git','node_modules'))
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
for name in ('viewer-config-fleets.json','drone_config-compact-1.json'):
    p=viewer/'config'/name
    shutil.copy2(p,run/(name+'.before-'+stamp))
    data=json.loads(p.read_text())
    if name.startswith('viewer-config'):
        data['pdu']['autoConnect']=True
    else:
        data['main_camera'].update(fov=60,followDistance=4.0,position=[-3,-4,2.5])
    p.write_text(json.dumps(data,indent=2)+'\n')
revision=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
report=dict(deployedAtUTC=stamp,viewerRoot=str(viewer),dependencySource=str(source),dependencyRevision=revision,
            changes=['restored missing JavaScript submodule','automatic WebSocket connection','fixed camera outside drone body'])
report['dependencyFiles']={p.relative_to(target).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
    for p in (target/'src').rglob('*') if p.is_file()}
(root/'build/system/viewer-deployment.json').write_text(json.dumps(report,indent=2)+'\n')
print('Viewer dependency, automatic connection and camera configured:',revision)

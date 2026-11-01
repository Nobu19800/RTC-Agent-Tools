"""Fingerprints and strict evidence checks; never infer a test result."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def fingerprint(root=ROOT):
    files={}
    for folder in ('scripts','build/generated','build/system/teleop/config','build/system/scripts'):
        for p in (root/folder).rglob('*'):
            if p.is_file() and p.suffix in ('.py','.cjs','.js','.sh','.bat','.conf','.env','.idl','.xml','.json'):
                files[p.relative_to(root).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    for name in ('build/system/final-session.json','build/system/teleop/runtime.env','build/system/teleop/teleop-controller-1.conf','build/system/teleop/gui-joystick-1.conf','build/system/teleop/native-connections.ini','build/system/deployment.json','build/system/viewer-deployment.json'):
        p=root/name
        if p.exists(): files[name]=hashlib.sha256(p.read_bytes()).hexdigest()
    return {'sha256':hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest(),'files':files}

def require_current(record,current):
    if record.get('implementationFingerprint')!=current['sha256']:
        raise ValueError('Missing/stale implementation fingerprint; rerun the affected check')
    if not record.get('startedAtUTC') or not record.get('finishedAtUTC'):
        raise ValueError('Missing execution timestamps')
    if record.get('passed') is not True: raise ValueError('Execution did not pass')

if __name__=='__main__': print(json.dumps(fingerprint()))

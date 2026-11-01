"""Run real tests and retain command/exit/count/fingerprint evidence without activation."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import re
import subprocess
import sys
from verification_evidence import ROOT,fingerprint

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    before=fingerprint(); started=datetime.now(timezone.utc).isoformat(); results=[]
    for name,script in [('behaviorAndSerializers','scripts/test_gui_drone.py'),('genericTransport','examples/hakoniwa_transport/test_hakoniwa.py'),('externalConnections','scripts/test_single_port_connections.py')]:
        command=[sys.executable,str(ROOT/script),'-v']
        proc=subprocess.run(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=120)
        output=a.output/(name+'-'+stamp+'.log'); output.write_text(proc.stdout)
        count=re.search(r'Ran (\d+) tests? in ',proc.stdout)
        skipped=re.search(r'skipped=(\d+)',proc.stdout)
        results.append(dict(name=name,command=command,exitCode=proc.returncode,tests=int(count[1]) if count else None,
            skipped=int(skipped[1]) if skipped else 0,log=str(output),passed=proc.returncode==0 and count is not None and 'OK' in proc.stdout))
    passed=all(r['passed'] and r['skipped']==0 for r in results) and before==fingerprint()
    report=dict(startedAtUTC=started,finishedAtUTC=datetime.now(timezone.utc).isoformat(),implementationFingerprint=before['sha256'],
                passed=passed,results=results)
    (a.output/('unit-tests-'+stamp+'.json')).write_text(json.dumps(report,indent=2)+'\n')
    (a.output/'unit-test-result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2)); return 0 if passed else 1

if __name__=='__main__': raise SystemExit(main())

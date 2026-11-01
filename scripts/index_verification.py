"""Index evidence freshness without rewriting historical test claims."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
from verification_evidence import ROOT,fingerprint,require_current

def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--unit-report',type=Path)
    args=parser.parse_args(); current=fingerprint(); records=[]
    paths=[ROOT/'build/system'/name for name in ('implementation-verification.json','latest-runtime-verification.json','profiles-nameserver-verification.json','windows-endpoint-verification.json')]
    if args.unit_report: paths.append(args.unit_report)
    for path in paths:
        if not path.exists(): continue
        record=json.loads(path.read_text())
        try:
            require_current(record,current); status='current'
        except ValueError as e:
            status='historical/unverified for current files: '+str(e)
        records.append(dict(path=str(path),status=status))
    output=dict(recordedAtUTC=datetime.now(timezone.utc).isoformat(),implementationFingerprint=current['sha256'],records=records)
    target=ROOT/'build/system/verification-index.json'
    target.write_text(json.dumps(output,indent=2)+'\n'); print(target)

if __name__=='__main__': main()

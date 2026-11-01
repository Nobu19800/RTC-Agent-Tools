"""Publish a report from fresh measured evidence; never promote contracts implicitly.

Does not rewrite the approved session or deployment. Server metadata changes use
the normal retrieve/reconcile/roundtrip workflow independently of test results.
"""
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
from verification_evidence import ROOT,fingerprint,require_current

def main():
    system=ROOT/'build/system'
    run=Path((system/'teleop/current-run.txt').read_text().strip())
    current=fingerprint()
    units=json.loads((run/'unit-test-result.json').read_text())
    motion=json.loads((run/'gui-smoke-result.json').read_text())
    for record in (units,motion): require_current(record,current)
    if not units.get('results') or any(r['exitCode']!=0 or r['skipped'] or not r['tests'] for r in units['results']):
        raise ValueError('Missing, failed or skipped unit test execution')
    contracts=json.loads((system/'connection-contracts.json').read_text())
    covered=set(motion.get('validatedEdgeIds',[]))
    missing=set(contracts['edges'])-covered
    if missing: raise ValueError('Mixed edges lack measured coverage: '+', '.join(sorted(missing)))
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    report=dict(recordedAtUTC=datetime.now(timezone.utc).isoformat(),runtimeLogDirectory=str(run),
        implementationFingerprint=current['sha256'],testedFiles=current['files'],
        unitTests=units,motionE2E=motion,validatedEdgeIds=sorted(covered),
        passed=units['passed'] and motion['passed'],
        scope='Measured WSLg widget-event native simulation and unit tests. No physical hardware claim.',
        contractPolicy='Coverage is reported per edge; this tool does not change executable/status flags or erase unresolved issues.')
    render=run/'viewer-render-result.json'
    if render.exists():
        browser=json.loads(render.read_text())
        report['browser']=browser
        try:
            require_current(browser,current)
            report['browserEvidenceStatus']='current; screenshot scene review must be recorded separately'
        except ValueError:
            report['browserEvidenceStatus']='historical or failed; not current verification'
    else: report['browserEvidenceStatus']='not executed'
    target=system/'implementation-verification.json'
    if target.exists():
        history=system/'history'; history.mkdir(exist_ok=True)
        shutil.copy2(target,history/('implementation-verification-before-'+stamp+'.json'))
    raw=json.dumps(report,indent=2)+'\n'
    (run/('implementation-verification-'+stamp+'.json')).write_text(raw)
    target.write_text(raw)
    print('Published measured evidence; no session/contract promotion performed')

if __name__=='__main__': main()

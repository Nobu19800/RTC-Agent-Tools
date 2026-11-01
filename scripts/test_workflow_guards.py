"""Offline regression checks for conflicts and stale/failed verification evidence."""
import tempfile
from pathlib import Path
import unittest
from check_rtc_connection import check
from verification_evidence import fingerprint,require_current

SRC='/localhost:2809/gui.rtc:pilot'; DST='/localhost:2809/controller.rtc:pilot'
def snapshot(peer=None,**overrides):
    s=' -DataOutPort: pilot\n    data_type   IDL:DroneTeleop/TimedPilotInput:1.0\n'
    if peer:
        values={'ID':'pilot-input','dataport.data_type':'IDL:DroneTeleop/TimedPilotInput:1.0',
            'dataport.interface_type':'corba_cdr','dataport.dataflow_type':'push',
            'dataport.subscription_type':'flush','dataport.buffer.length':'1'}
        values.update(overrides)
        s+='   -Connected to  '+peer+'\n'+''.join('      '+k+'  '+v+'\n' for k,v in values.items())
    return s

class ConnectionTests(unittest.TestCase):
    def check_pair(self,a,b): return check(a,b,'pilot','pilot',SRC,DST)
    def test_absent_pair(self): self.assertEqual(self.check_pair(snapshot(),snapshot()),2)
    def test_equivalent_is_reusable(self): self.assertEqual(self.check_pair(snapshot(DST),snapshot(SRC)),0)
    def test_wrong_peer_is_conflict(self): self.assertEqual(self.check_pair(snapshot(DST+'wrong'),snapshot(SRC)),1)
    def test_property_conflict(self): self.assertEqual(self.check_pair(snapshot(DST,**{'dataport.buffer.length':'8'}),snapshot(SRC)),1)
    def test_partial_connection(self): self.assertEqual(self.check_pair(snapshot(DST),snapshot()),1)
    def test_different_type(self): self.assertEqual(self.check_pair(snapshot().replace('TimedPilotInput','TimedStatus'),snapshot()),1)

class EvidenceTests(unittest.TestCase):
    def test_missing_or_failed_or_stale_cannot_pass(self):
        current={'sha256':'now'}
        base={'implementationFingerprint':'now','startedAtUTC':'start','finishedAtUTC':'end','passed':True}
        require_current(base,current)
        for change in ({'passed':False},{'implementationFingerprint':'old'},{'finishedAtUTC':None}):
            with self.assertRaises(ValueError): require_current(dict(base,**change),current)
    def test_code_change_invalidates_but_logs_do_not(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'scripts').mkdir(); (root/'build/system/logs').mkdir(parents=True)
            p=root/'scripts/code.py'; p.write_text('v1'); first=fingerprint(root)
            (root/'build/system/logs/a.log').write_text('new output')
            self.assertEqual(first,fingerprint(root))
            p.write_text('v2'); self.assertNotEqual(first,fingerprint(root))

if __name__=='__main__': unittest.main()

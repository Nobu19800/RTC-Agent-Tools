"""Offline direct-batch checks. Only --plan or fake rtshell tools run."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'build/system/scripts'


class DirectBatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='direct batch test ')
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.settings = json.loads((FOLDER/'runtime-settings.json').read_text(encoding='utf-8'))

    def run_common(self, operation, output, *args):
        fake = self.directory/'fake rtshell.cmd'
        fake.write_bytes(('@echo off\r\n'+''.join('echo '+line+'\r\n' for line in output.splitlines())+'exit /b 0\r\n').encode())
        wrapper = self.directory/'invoke.cmd'
        quoted = ' '.join('"'+arg+'"' for arg in args)
        wrapper.write_bytes(('@echo off\r\ncall "'+str(FOLDER/'runtime_common.bat')+'" '+operation+' '+quoted+
            '\r\nexit /b %errorlevel%\r\n').encode())
        env = os.environ.copy()
        env.update(RTC_QUERY=str(self.directory/'query.txt'), RTC_LOG=str(self.directory/'log.txt'),
                   RTLS=str(fake), RTCAT=str(fake), RTC_WAIT_ATTEMPTS='1')
        return subprocess.run([str(wrapper)], shell=True, env=env, capture_output=True, text=True, timeout=15)

    def test_direct_rtshell_command_counts(self):
        for filename, command, expected in [('connect_ports.bat','RTCON',7), ('activate_rtcs.bat','RTACT',6),
                ('deactivate_rtcs.bat','RTDEACT',6), ('stop_rtcs.bat','RTEXIT',6)]:
            text=(FOLDER/filename).read_text()
            self.assertEqual(sum(line.startswith('"%'+command+'%"') for line in text.splitlines()),expected)
            self.assertNotIn('runtime_control.py',text)
            self.assertNotIn('RTC_PYTHON',text)

    def test_all_connections_match_manifest(self):
        text=(FOLDER/'connect_ports.bat').read_text()
        nodes={n['id']:n for n in self.settings['nodes']}
        for e in self.settings['edges']:
            self.assertIn('"'+nodes[e['source']]['path']+':'+e['sourcePort']+'"',text)
            self.assertIn('"'+nodes[e['target']]['path']+':'+e['targetPort']+'"',text)
            self.assertIn('-i "'+e['id']+'"',text)

    def test_activation_follows_reviewed_order(self):
        lines=[line for line in (FOLDER/'activate_rtcs.bat').read_text().splitlines() if line.startswith('"%RTACT%"')]
        nodes={n['id']:n for n in self.settings['nodes']}
        for line,key in zip(lines,self.settings['activationOrder']):
            self.assertIn('"'+nodes[key]['path']+'"',line)

    def test_state_parser_and_noop_wait(self):
        self.assertEqual(self.run_common('wait_state','Inactive  2  1/1  1/1  - X0.rtc','/fake','Inactive').returncode,0)
        self.assertNotEqual(self.run_common('wait_state','Error  2  1/1  1/1  - X0.rtc','/fake','Active').returncode,0)

    def test_equivalent_connection_detection(self):
        self.assertEqual(self.run_common('connected','-CorbaPort: middle\n  -Connected to  /target.rtc:middle','/source.rtc:middle','/target.rtc:middle').returncode,0)
        self.assertNotEqual(self.run_common('connected','-CorbaPort: middle\n  -Connected to  /other.rtc:middle','/source.rtc:middle','/target.rtc:middle').returncode,0)

    def test_data_port_type_and_direction(self):
        output='-DataOutPort: out\n  dataport.data_type  RTC::TimedString'
        self.assertEqual(self.run_common('data',output,'/x:out','RTC::TimedString','DataOutPort','IDL:RTC/TimedString:1.0').returncode,0)
        self.assertNotEqual(self.run_common('data',output,'/x:out','RTC::TimedLong','DataOutPort','IDL:RTC/TimedLong:1.0').returncode,0)

    def test_service_interface_matching(self):
        output='-CorbaPort: middle\n  Interface:\n    Instance name  svc\n    Type name  JARA_ARM::Middle\n    Polarity  Required'
        self.assertEqual(self.run_common('service',output,'/x:middle','svc','JARA_ARM::Middle','Required').returncode,0)
        self.assertNotEqual(self.run_common('service',output,'/x:middle','wrong','JARA_ARM::Middle','Required').returncode,0)

    def test_all_plans_run_from_paths_with_spaces_without_runtime_calls(self):
        destination=self.directory/'scripts with spaces'
        shutil.copytree(FOLDER,destination)
        for name,token in [('start_rtcs','START '),('connect_ports','rtcon'),('activate_rtcs','rtact'),
                           ('deactivate_rtcs','rtdeact'),('stop_rtcs','rtexit')]:
            p=subprocess.run([str(destination/(name+'.bat')),'--plan'],shell=True,cwd=self.directory,
                             capture_output=True,text=True,timeout=15)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertIn(token.lower(),p.stdout.lower())
        self.assertFalse((self.directory/'logs').exists())
        self.assertFalse((self.directory/'runtime-state').exists())

    def test_environment_has_only_crlf_line_endings(self):
        for file in FOLDER.glob('*.bat'):
            contents=file.read_bytes()
            self.assertEqual(contents.count(b'\r'),contents.count(b'\r\n'),file.name)
            self.assertEqual(contents.count(b'\n'),contents.count(b'\r\n'),file.name)

    def test_configs_preserve_final_values(self):
        session=json.loads((ROOT/'build/system/final-session.json').read_text(encoding='utf-8'))
        for n in self.settings['nodes']:
            d=next(x['data'] for x in session['nodes'] if x['id']==n['id'])
            text=Path(n['componentConf']).read_text(encoding='utf-8')
            for c in d['configuration']:
                self.assertIn('conf.default.'+c['name']+': '+c['value']+'\n',text)
            rtc_config=Path(n['rtcConf']).read_text(encoding='utf-8')
            self.assertIn('corba.nameservers: '+d['rtcConf']['corbaNameServers']+'\n',rtc_config)


if __name__=='__main__':
    unittest.main()

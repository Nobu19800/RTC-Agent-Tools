"""Regression checks for the JAXB/RTC Builder compatibility fixes."""
import copy
import json
from pathlib import Path
import sys
import unittest
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from json_to_rtc_xml import generate, tag


class ProfileConversionTests(unittest.TestCase):
    def setUp(self):
        self.profile = {
            'profileVersion': '0.3',
            'basicInfo': dict(name='ArmActionExecutor', description='Japanese: 設定', version='1.0.0',
                              vendor='User', category='Manipulation'),
            'actions': dict(OnInitialize=True, OnExecute=True),
            'configuration': [dict(name='workspace_limits_json', type='string', defaultValue='', widget='text')],
            'dataPorts': [dict(name='command', portType='DataInPort', type='RTC::TimedString')],
            'servicePorts': [dict(name='middle', interfaces=[dict(name='middle', direction='Required',
                             type='JARA_ARM::ManipulatorCommonInterface_Middle',
                             instanceName='middle', idlFile='ManipulatorCommonInterface_Middle.idl')])],
            'language': dict(kind='C++'),
        }

    def test_roundtrip_preserves_qualified_profile_and_empty_default(self):
        xml = ET.fromstring(ET.tostring(generate(self.profile).getroot()))
        basic = xml.find(tag('rtc', 'BasicInfo'))
        self.assertEqual(basic.get(tag('rtc', 'name')), 'ArmActionExecutor')
        self.assertTrue(basic.get(tag('rtc', 'creationDate')))
        self.assertEqual(basic.get(tag('rtcExt', 'saveProject')), 'ArmActionExecutor')
        self.assertTrue(basic.get(tag('xsi', 'type')).endswith(':basic_info_ext'))
        configs = xml.find(tag('rtc', 'ConfigurationSet'))
        empty = next(c for c in configs if c.get(tag('rtc', 'name')) == 'workspace_limits_json')
        self.assertEqual(empty.get(tag('rtc', 'defaultValue')), '')
        widget = empty.find(tag('rtcExt', 'Properties'))
        self.assertEqual(widget.get(tag('rtcExt', 'name')), '__widget__')
        iface = xml.find('.//' + tag('rtc', 'ServiceInterface'))
        self.assertEqual(iface.get(tag('rtc', 'direction')), 'Required')
        self.assertEqual(iface.get(tag('rtc', 'type')), 'JARA_ARM::ManipulatorCommonInterface_Middle')
        action = xml.find('.//' + tag('rtc', 'OnExecute'))
        self.assertTrue(action.get(tag('xsi', 'type')).endswith(':action_status_doc'))

    def test_explicit_timestamps_are_preserved(self):
        profile = copy.deepcopy(self.profile)
        profile['basicInfo'].update(creationDate='2026-10-01T00:00:00Z', updateDate='2026-10-02T00:00:00Z')
        basic = generate(profile).getroot().find(tag('rtc', 'BasicInfo'))
        self.assertEqual(basic.get(tag('rtc', 'creationDate')), '2026-10-01T00:00:00Z')
        self.assertEqual(basic.get(tag('rtc', 'updateDate')), '2026-10-02T00:00:00Z')

    def test_invalid_service_direction_is_rejected(self):
        self.profile['servicePorts'][0]['interfaces'][0]['direction'] = 'Consumer'
        with self.assertRaises(ValueError):
            generate(self.profile)


if __name__ == '__main__':
    unittest.main()

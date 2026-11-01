"""Failure/ownership tests for the native-only external connector."""
from pathlib import Path
import sys
import tempfile
import unittest

import OpenRTM_aist as R
import RTC
from single_port_connections import operate, read_settings


def nv(values):
    prop = R.Properties()
    for key, value in values.items():
        prop.setProperty(key, value)
    result = []
    R.NVUtil.copyFromProperties(result, prop)
    return result


VALUES = {'dataport.interface_type': 'hakoniwa', 'dataport.marshaling_type': 'example-codec',
          'dataport.hakoniwa.channel': '7', 'dataport.hakoniwa.pdu_size': '104'}


class Port:
    def __init__(self, name, fail=False):
        self.name, self.fail = name, fail
        self.profiles = []
        self.calls = 0

    def get_port_profile(self):
        return type('Profile', (), {'name': 'test.' + self.name, 'properties': nv({
            'port.port_type': 'DataOutPort', 'dataport.interface_type': 'hakoniwa',
            'dataport.marshaling_types': 'example-codec,cdr'})})()

    def get_connector_profiles(self):
        return self.profiles

    def _is_equivalent(self, other):
        return self is other

    def connect(self, profile):
        self.calls += 1
        if self.fail:
            return RTC.RTC_ERROR, profile
        self.profiles.append(profile)
        return RTC.RTC_OK, profile

    def disconnect(self, identifier):
        self.profiles = [p for p in self.profiles if p.connector_id != identifier]
        return RTC.RTC_OK


class ConnectorTests(unittest.TestCase):
    def component(self, *ports):
        return type('Component', (), {'get_ports': lambda self: list(ports)})()

    def settings(self, *names):
        return [(n, n, 'out', dict(VALUES)) for n in names]

    def test_reuse_and_disconnect_only_matching_owned_profiles(self):
        port = Port('a'); comp = self.component(port); settings = self.settings('a')
        operate(comp, settings, 'connect'); operate(comp, settings, 'connect')
        self.assertEqual(port.calls, 1)
        operate(comp, settings, 'disconnect'); operate(comp, settings, 'disconnect')
        self.assertEqual(port.profiles, [])

    def test_changed_properties_are_conflict_and_do_not_mutate(self):
        a, b = Port('a'), Port('b'); comp = self.component(a, b)
        operate(comp, self.settings('b'), 'connect')
        changed = self.settings('a', 'b'); changed[1][3]['dataport.hakoniwa.channel'] = '8'
        with self.assertRaises(ValueError): operate(comp, changed, 'connect')
        self.assertEqual(a.calls, 0)
        self.assertEqual(len(b.profiles), 1)

    def test_partial_failure_rolls_back_new_but_retains_preexisting(self):
        a, b, c = Port('a'), Port('b'), Port('c', fail=True)
        comp = self.component(a, b, c)
        operate(comp, self.settings('a'), 'connect')
        with self.assertRaises(RuntimeError): operate(comp, self.settings('a', 'b', 'c'), 'connect')
        self.assertEqual(len(a.profiles), 1)
        self.assertEqual(b.profiles, [])

    def test_missing_connection_fails_check_without_creation(self):
        port = Port('a')
        with self.assertRaises(ValueError): operate(self.component(port), self.settings('a'), 'check')
        self.assertEqual(port.calls, 0)

    def test_settings_reject_duplicate_ports(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'connections.ini'
            path.write_text('''[DEFAULT]
dataport.interface_type=hakoniwa
dataport.marshaling_type=test
dataport.hakoniwa.robot=Drone
dataport.hakoniwa.channel=7
dataport.hakoniwa.pdu_size=104
[a]
port=move_request
direction=out
[b]
port=move_request
direction=out
''')
            with self.assertRaises(ValueError): read_settings(path)


if __name__ == '__main__':
    unittest.main()

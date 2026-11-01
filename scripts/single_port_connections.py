"""Connect native single-ended DataPorts from INI; no RTC lifecycle operations.

The installed rtctree.DataPort.connect rejects an empty destination list. Use
the public CORBA PortService API for only this explicitly configured exception.
"""
import argparse
import configparser
import sys


def read_settings(filename):
    config = configparser.ConfigParser(interpolation=None)
    if not config.read(filename, encoding='utf-8'):
        raise ValueError('Connection INI not found: ' + str(filename))
    result = []
    seen = set()
    for name in config.sections():
        values = dict(config[name])
        port = values.pop('port')
        direction = values.pop('direction')
        if port in seen or direction not in ('in', 'out'):
            raise ValueError('Duplicate port or invalid direction: ' + port)
        seen.add(port)
        if not values or any(not key.startswith('dataport.') for key in values):
            raise ValueError('Only dataport properties are accepted')
        if values.get('dataport.interface_type') != 'hakoniwa':
            raise ValueError('This deployment supports only native hakoniwa bindings')
        for key in ('dataport.marshaling_type', 'dataport.hakoniwa.robot'):
            if not values.get(key):
                raise ValueError('Missing ' + key)
        if int(values['dataport.hakoniwa.channel']) < 0 or int(values['dataport.hakoniwa.pdu_size']) <= 0:
            raise ValueError('Invalid channel/capacity')
        result.append((name, port, direction, values))
    if not result:
        raise ValueError('No connections configured')
    return result


def operate(component, settings, action):
    import OpenRTM_aist as R
    import RTC
    from omniORB import any as corba_any

    def properties(profile):
        return {p.name: str(corba_any.from_any(p.value)) for p in profile.properties}

    ports = {p.get_port_profile().name.rsplit('.', 1)[-1]: p for p in component.get_ports()}
    planned = []
    # Validate every endpoint/conflict before creating any connector.
    for name, port_name, direction, values in settings:
        if port_name not in ports:
            raise ValueError('Port not found: ' + port_name)
        port = ports[port_name]
        advertised = properties(port.get_port_profile())
        if advertised.get('port.port_type') != ('DataInPort' if direction == 'in' else 'DataOutPort'):
            raise ValueError('Direction mismatch: ' + port_name)
        for key in ('dataport.interface_type', 'dataport.marshaling_type'):
            advertised_key = 'dataport.marshaling_types' if key == 'dataport.marshaling_type' else key
            supported = [v.strip() for v in advertised.get(advertised_key, '').split(',')]
            if values[key] not in supported and 'any' not in supported:
                raise ValueError('Plugin not loaded / unsupported ' + key + ': ' + port_name)
        existing = port.get_connector_profiles()
        same = [p for p in existing if p.connector_id == name]
        if len(same) > 1 or any(p.connector_id != name for p in existing):
            raise ValueError('Unexpected existing connection on ' + port_name)
        if same:
            current = same[0]
            actual = properties(current)
            if (current.name != name or len(current.ports) != 1 or
                    not current.ports[0]._is_equivalent(port) or
                    any(actual.get(k) != v for k, v in values.items())):
                raise ValueError('Existing connection conflicts with INI: ' + name)
        if action == 'check' and not same:
            raise ValueError('Missing connection: ' + name)
        planned.append((name, port, values, bool(same)))
    created = []
    try:
        for name, port, values, exists in planned:
            if action == 'connect' and not exists:
                prop = R.Properties()
                for key, value in values.items():
                    prop.setProperty(key, value)
                nv = []
                R.NVUtil.copyFromProperties(nv, prop)
                status, profile = port.connect(RTC.ConnectorProfile(name, name, [port], nv))
                if status != RTC.RTC_OK:
                    # A failed connect may still leave a partial profile.
                    for pending in port.get_connector_profiles():
                        if pending.connector_id == name:
                            port.disconnect(name)
                    raise RuntimeError('Connection rejected: ' + name + ' ' + str(status))
                created.append((port, profile.connector_id))
            elif action == 'disconnect' and exists:
                if port.disconnect(name) != RTC.RTC_OK:
                    raise RuntimeError('Disconnect rejected: ' + name)
            print(action.upper(), name, 'reused' if exists else 'new/absent', flush=True)
        if action == 'connect':
            operate(component, settings, 'check')
        if action == 'disconnect':
            for name, port, _, _ in planned:
                if any(p.connector_id == name for p in port.get_connector_profiles()):
                    raise RuntimeError('Still connected: ' + name)
    except Exception:
        for port, identifier in reversed(created):
            if port.disconnect(identifier) != RTC.RTC_OK:
                print('ROLLBACK FAILED', identifier, file=sys.stderr)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rtc', required=True, help='Absolute rtshell RTC path')
    parser.add_argument('--config', required=True)
    parser.add_argument('--action', choices=['connect', 'check', 'preflight', 'disconnect'], required=True)
    args = parser.parse_args()
    settings = read_settings(args.config)
    import rtctree.path
    import rtctree.tree
    path, port = rtctree.path.parse_path(args.rtc)
    if port or not args.rtc.startswith('/'):
        raise ValueError('Expected an absolute component path without port')
    tree = rtctree.tree.RTCTree(paths=[path], filter=[path])
    try:
        node = tree.get_node(path)
        if node is None or node.is_zombie or not node.is_component:
            raise ValueError('Target RTC not reachable: ' + args.rtc)
        operate(node.object, settings, args.action)
    finally:
        # RTCTree owns its ORB; its destructor shuts down/destroys it.
        # Do not destroy it first and trigger OBJECT_NOT_EXIST during cleanup.
        del tree
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

"""Generate deployment settings; runtime connection tools read INI, not JSON."""
from pathlib import Path
import configparser


def write_settings(root):
    root = Path(root)
    runtime = root / 'build/system/teleop'
    common = root / 'build/generated/common'
    config = configparser.ConfigParser(interpolation=None)
    config['DEFAULT'] = {
        'dataport.interface_type': 'hakoniwa',
        'dataport.dataflow_type': 'push',
        'dataport.subscription_type': 'flush',
        'dataport.hakoniwa.robot': 'Drone',
        'dataport.hakoniwa.init_for_external': 'YES',
        'dataport.hakoniwa.poll_interval': '0.02',
        'dataport.hakoniwa.skip_zero_packet': 'YES',
        'dataport.buffer.length': '1',
        'dataport.buffer.write.full_policy': 'overwrite',
        'dataport.sync_readwrite': 'NO',
    }
    for kind, channel, size in [('move', 7, 104), ('takeoff', 6, 88), ('land', 8, 88)]:
        for role in ('request', 'response'):
            config[kind + '-' + role] = {
                'port': kind + '_' + role,
                'direction': 'out' if role == 'request' else 'in',
                'dataport.marshaling_type': 'hakoniwa:hako_msgs/HakoDroneCmd' + kind.title() + ':foundation-padded',
                'dataport.hakoniwa.channel': str(channel),
                'dataport.hakoniwa.pdu_size': str(size),
            }
    config['pose-feedback'] = {
        'port': 'pose', 'direction': 'in',
        'dataport.marshaling_type': 'hakoniwa:geometry_msgs/Twist:pose-metadata72',
        'dataport.hakoniwa.channel': '1', 'dataport.hakoniwa.pdu_size': '72',
    }
    with (runtime / 'native-connections.ini').open('w', encoding='utf-8') as stream:
        config.write(stream)
    return ('\n# Plugins are loaded before component creation; no RTC-specific loader calls.\n'
            f'manager.modules.load_path: {common.as_posix()}\n'
            'manager.modules.preload: HakoniwaTransport.py, DroneSerializers.py\n')


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    extra = write_settings(root)
    # This generator is run from WSL; keep target paths in the deployment namespace.
    target = root / 'build/system/teleop/teleop-controller-1.conf'
    text = target.read_text(encoding='utf-8')
    marker = '\n# Plugins are loaded before component creation; no RTC-specific loader calls.\n'
    target.write_text(text.split(marker)[0].rstrip() + '\n' + extra, encoding='utf-8')

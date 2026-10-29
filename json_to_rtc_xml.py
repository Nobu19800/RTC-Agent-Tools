#!/usr/bin/env python3
"""Generate an OpenRTM RtcProfile XML file from a semantic JSON definition.

This converter supports the documented subset in rtc_sample.json. It is not a
lossless general-purpose XML/JSON converter and does not validate against XSD.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {
    'rtc': 'http://www.openrtp.org/namespaces/rtc',
    'rtcExt': 'http://www.openrtp.org/namespaces/rtc_ext',
    'rtcDoc': 'http://www.openrtp.org/namespaces/rtc_doc',
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
}
for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)

ACTIONS = (
    'OnInitialize', 'OnFinalize', 'OnStartup', 'OnShutdown',
    'OnActivated', 'OnDeactivated', 'OnAborting', 'OnError',
    'OnReset', 'OnExecute', 'OnStateUpdate', 'OnRateChanged',
    'OnAction', 'OnModeChanged',
)
BASIC_FIELDS = (
    'name', 'description', 'version', 'vendor', 'category',
    'componentType', 'activityType', 'componentKind', 'maxInstances',
    'executionType', 'executionRate', 'creationDate', 'updateDate', 'abstract',
)
DATA_FIELDS = ('name', 'portType', 'type', 'idlFile', 'interfaceType',
               'dataflowType', 'subscriptionType', 'unit')
SERVICE_FIELDS = ('name', 'direction', 'type', 'instanceName', 'idlFile', 'path')


def tag(prefix, local):
    return f'{{{NS[prefix]}}}{local}'


def obj(value, label):
    if not isinstance(value, dict):
        raise ValueError(f'{label} must be a JSON object')
    return value


def arr(value, label):
    if not isinstance(value, list):
        raise ValueError(f'{label} must be a JSON array')
    return value


def string(value):
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if value is None or isinstance(value, (dict, list)):
        raise ValueError('XML attribute values must be strings, numbers or booleans')
    return str(value)


def attributes(element, data, fields):
    for key in fields:
        if key in data and data[key] is not None:
            element.set(tag('rtc', key), string(data[key]))


def extension(element, data):
    extension_types = {
        'BasicInfo': 'basic_info_ext',
        'Configuration': 'configuration_ext',
        'DataPorts': 'dataport_ext',
        'ServicePorts': 'serviceport_ext',
        'ServiceInterface': 'serviceinterface_ext',
        'Language': 'language_ext',
    }
    local = element.tag.rsplit('}', 1)[-1]
    if local in extension_types:
        element.set(tag('xsi', 'type'), ET.QName(NS['rtcExt'], extension_types[local]))
    for source, attr in (('position', 'position'), ('variableName', 'variableName')):
        if source in data and data[source] is not None:
            element.set(tag('rtcExt', attr), string(data[source]))


def docs(parent, data):
    if 'doc' in data:
        doc = obj(data['doc'], 'doc')
        element = ET.SubElement(parent, tag('rtcDoc', 'Doc'))
        for key, value in doc.items():
            if not isinstance(key, str):
                raise ValueError('doc attribute names must be strings')
            element.set(tag('rtcDoc', key), string(value))


def generate(profile):
    profile = obj(profile, 'root')
    basic = obj(profile.get('basicInfo', {}), 'basicInfo')
    if not basic.get('name'):
        raise ValueError('basicInfo.name is required')
    version = string(profile.get('profileVersion', '0.3'))
    if version not in ('0.2', '0.3'):
        raise ValueError('profileVersion must be 0.2 or 0.3')

    root = ET.Element(tag('rtc', 'RtcProfile'))
    root.set(tag('rtc', 'version'), version)
    root.set(tag('rtc', 'id'), string(profile.get('id',
        f"RTC:{basic.get('vendor', '')}:{basic.get('category', '')}:{basic['name']}:{basic.get('version', '1.0.0')}")))

    info = ET.SubElement(root, tag('rtc', 'BasicInfo'))
    attributes(info, basic, BASIC_FIELDS)
    # RTC Builder dereferences both timestamps even when the JSON omits them.
    created = basic.get('creationDate') or datetime.now(timezone.utc).isoformat(timespec='seconds')
    info.set(tag('rtc', 'creationDate'), string(created))
    info.set(tag('rtc', 'updateDate'), string(basic.get('updateDate') or created))
    extension(info, basic)
    info.set(tag('rtcExt', 'saveProject'), string(basic.get('saveProject') or basic['name']))
    docs(info, basic)

    action_data = obj(profile.get('actions', {}), 'actions')
    unknown = set(action_data) - set(ACTIONS)
    if unknown:
        raise ValueError(f'Unknown action names: {", ".join(sorted(unknown))}')
    actions = ET.SubElement(root, tag('rtc', 'Actions'))
    for action in ACTIONS:
        if action in action_data:
            value = action_data[action]
            if not isinstance(value, bool):
                raise ValueError(f'actions.{action} must be boolean')
            ET.SubElement(actions, tag('rtc', action), {
                tag('rtc', 'implemented'): string(value),
                tag('xsi', 'type'): ET.QName(NS['rtcDoc'], 'action_status_doc'),
            })

    configs = arr(profile.get('configuration', []), 'configuration')
    if configs:
        config_set = ET.SubElement(root, tag('rtc', 'ConfigurationSet'))
        for i, raw in enumerate(configs):
            conf = obj(raw, f'configuration[{i}]')
            if not conf.get('name') or not conf.get('type'):
                raise ValueError(f'configuration[{i}] requires name and type')
            node = ET.SubElement(config_set, tag('rtc', 'Configuration'))
            attributes(node, conf, ('name', 'type', 'defaultValue', 'unit'))
            extension(node, conf)
            if 'constraint' in conf:
                raise ValueError('constraint conversion is not supported yet; refusing to silently drop it')
            docs(node, conf)
            if 'widget' in conf:
                props = ET.SubElement(node, tag('rtcExt', 'Properties'))
                props.set(tag('rtcExt', 'name'), '__widget__')
                props.set(tag('rtcExt', 'value'), string(conf['widget']))

    for i, raw in enumerate(arr(profile.get('dataPorts', []), 'dataPorts')):
        port = obj(raw, f'dataPorts[{i}]')
        if not port.get('name') or not port.get('portType') or not port.get('type'):
            raise ValueError(f'dataPorts[{i}] requires name, portType, type')
        if port['portType'] not in ('DataInPort', 'DataOutPort'):
            raise ValueError(f'dataPorts[{i}].portType must be DataInPort or DataOutPort')
        node = ET.SubElement(root, tag('rtc', 'DataPorts'))
        attributes(node, port, DATA_FIELDS)
        extension(node, port)
        docs(node, port)

    for i, raw in enumerate(arr(profile.get('servicePorts', []), 'servicePorts')):
        port = obj(raw, f'servicePorts[{i}]')
        if not port.get('name'):
            raise ValueError(f'servicePorts[{i}].name is required')
        node = ET.SubElement(root, tag('rtc', 'ServicePorts'))
        attributes(node, port, ('name',))
        extension(node, port)
        docs(node, port)
        for j, raw_iface in enumerate(arr(port.get('interfaces', []), f'servicePorts[{i}].interfaces')):
            iface = obj(raw_iface, f'servicePorts[{i}].interfaces[{j}]')
            if not iface.get('name') or not iface.get('direction') or not iface.get('type'):
                raise ValueError(f'servicePorts[{i}].interfaces[{j}] requires name, direction, type')
            if iface['direction'] not in ('Provided', 'Required'):
                raise ValueError('ServiceInterface direction must be Provided or Required')
            child = ET.SubElement(node, tag('rtc', 'ServiceInterface'))
            attributes(child, iface, SERVICE_FIELDS)
            extension(child, iface)
            docs(child, iface)

    language = obj(profile.get('language', {'kind': 'C++'}), 'language')
    if not language.get('kind'):
        raise ValueError('language.kind is required')
    language_node = ET.SubElement(root, tag('rtc', 'Language'), {tag('rtc', 'kind'): string(language['kind'])})
    extension(language_node, language)
    ET.indent(root, space='  ')
    return ET.ElementTree(root)


def main():
    parser = argparse.ArgumentParser(description='Convert RTC JSON definition to RTC.xml')
    parser.add_argument('input', type=Path, help='Input JSON file')
    parser.add_argument('output', type=Path, nargs='?', default=Path('RTC.xml'), help='Output XML file')
    args = parser.parse_args()
    try:
        with args.input.open(encoding='utf-8') as f:
            profile = json.load(f)
        tree = generate(profile)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        tree.write(args.output, encoding='utf-8', xml_declaration=True)
        print(f'Generated: {args.output}')
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

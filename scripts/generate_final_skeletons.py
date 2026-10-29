"""Generate approved RTC skeletons, with recorded local builder workarounds.

Never overwrite an implemented component. Canonical profiles and final session
remain unchanged. Only pristine skeleton configuration lines are normalized.
"""
import copy
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from json_to_rtc_xml import NS, generate, tag


def verify_xml(profile, path):
    root = ET.parse(path).getroot()
    assert root.find(tag('rtc', 'BasicInfo')).get(tag('rtc', 'name')) == profile['basicInfo']['name']
    assert root.find(tag('rtc', 'Language')).get(tag('rtc', 'kind')) == profile['language']['kind']
    for element_name, key, fields in (
        ('DataPorts', 'dataPorts', ('name', 'portType', 'type')),
        ('ConfigurationSet/' + tag('rtc', 'Configuration'), 'configuration', ('name', 'type', 'defaultValue')),
        ('ServicePorts', 'servicePorts', ('name',)),
    ):
        elements = root.findall(tag('rtc', element_name))
        assert len(elements) == len(profile[key]), (path, key)
        for element, value in zip(elements, profile[key]):
            assert all(element.get(tag('rtc', f)) == str(value[f]) for f in fields)
            if key == 'servicePorts':
                interfaces = element.findall(tag('rtc', 'ServiceInterface'))
                assert len(interfaces) == len(value['interfaces'])
                for a, b in zip(interfaces, value['interfaces']):
                    assert all(a.get(tag('rtc', f)) == b[f] for f in
                               ('name', 'direction', 'type', 'instanceName', 'idlFile'))


def normalize_auxiliary(profile, folder):
    # The builder emits the same configuration declarations in its test scaffold.
    for file in (folder / 'test/src').glob('*Test.cpp'):
        text = file.read_text(encoding='utf-8')
        for c in profile['configuration']:
            literal = json.dumps(c['defaultValue'], ensure_ascii=False)
            key = re.escape(c['name'])
            text = re.sub(r'(?m)^(\s*)"conf\.default\.' + key + r'",.*$',
                          lambda m: m[1] + '"conf.default.' + c['name'] + '", ' + literal + ',', text)
            text = re.sub(r'(?m)^(\s*)bindParameter\("' + key + r'",\s*([^,]+),.*$',
                          lambda m: m[1] + 'bindParameter("' + c['name'] + '", ' + m[2] + ', ' + literal + ');', text)
        file.write_text(text, encoding='utf-8')
    for file in (folder / 'idl/CMakeLists.txt', folder / 'test/idl/CMakeLists.txt'):
        if file.exists():
            text = file.read_text(encoding='utf-8')
            if 'list(REMOVE_DUPLICATES idls)' not in text:
                text = text.replace('OPENRTM_COMPILE_IDL_FILES(${idls})',
                                    'list(REMOVE_DUPLICATES idls)\nOPENRTM_COMPILE_IDL_FILES(${idls})')
                file.write_text(text, encoding='utf-8')


def main():
    s = json.loads((ROOT / 'build/system/final-session.json').read_text(encoding='utf-8'))
    report = []
    for node in s['nodes']:
        n = node['data']
        if n['origin'] != 'generated':
            continue
        name = n['name']
        assert re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', name)
        folder = ROOT / 'build/generated' / name
        profile_path = folder / (name + '.json')
        profile = json.loads(profile_path.read_text(encoding='utf-8'))
        canonical_xml = folder / 'RTC.xml'
        verify_xml(profile, canonical_xml)
        cpp = folder / 'src' / (name + '.cpp')
        state_path = folder / 'skeleton-generation.json'
        if state_path.exists():
            state = json.loads(state_path.read_text(encoding='utf-8'))
            for file, digest in state['fileHashes'].items():
                assert hashlib.sha256((folder / file).read_bytes()).hexdigest() == digest, 'Edited skeleton: ' + file
            normalize_auxiliary(profile, folder)
            report.append(state)
            continue
        adaptations = []
        args = [str(ROOT / 'cuirtcbuilder.bat'), '-d', str(folder), '-f', str(canonical_xml)]
        if not cpp.exists():
            staged = copy.deepcopy(profile)
            empty = [c['name'] for c in staged['configuration'] if c['type'] == 'string' and c['defaultValue'] == '']
            has_services = bool(profile['servicePorts'])
            if empty or has_services:
                stage_dir = ROOT / 'work/builder-inputs' / name
                stage_dir.mkdir(parents=True, exist_ok=True)
                for c in staged['configuration']:
                    if c['name'] in empty:
                        c['defaultValue'] = '__RTC_BUILDER_UNSET__'
                for p in staged['servicePorts']:
                    for i in p['interfaces']:
                        stage_idl_dir = stage_dir / 'idl'
                        stage_idl_dir.mkdir(exist_ok=True)
                        for source_idl in (folder / 'idl').glob('*.idl'):
                            shutil.copy2(source_idl, stage_idl_dir / source_idl.name)
                        upstream = stage_idl_dir / Path(i['idlFile']).name
                        assert upstream.is_file()
                        i['idlFile'] = upstream.as_posix()
                        i['path'] = upstream.parent.as_posix()
                staged_json = stage_dir / (name + '.json')
                staged_json.write_text(json.dumps(staged, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
                staged_xml = stage_dir / 'RTC.xml'
                subprocess.run([sys.executable, str(ROOT / 'json_to_rtc_xml.py'), str(staged_json), str(staged_xml)], check=True)
                args[-1] = str(staged_xml)
                if empty:
                    adaptations.append('Temporary nonempty builder defaults for: ' + ', '.join(empty) +
                                       '; original empty values restored in generated C++ and component conf.')
                if has_services:
                    adaptations.append('Builder reads upstream IDLs outside its output folder to avoid copying a file onto itself.')
            idls = sorted({i['idlFile'] for p in staged['servicePorts'] for i in p['interfaces']})
            if idls:
                args += ['-i'] + idls
            result = subprocess.run(args, cwd=ROOT, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            log = ROOT / 'work' / ('builder-' + name + '.log')
            log.write_bytes(result.stdout)
            assert result.returncode == 0 and b'Error:' not in result.stdout and b'Exception' not in result.stdout, str(log)
        text = cpp.read_text(encoding='utf-8')
        assert re.search(rf'{name}::onExecute\([^)]*\)\s*\{{\s*return RTC::RTC_OK;\s*\}}', text), 'Not a pristine skeleton'
        # The installed C++ template embeds JSON configuration without escaping.
        # Rebuild exactly the two configuration lines from authoritative values.
        for c in profile['configuration']:
            key, value = c['name'], c['defaultValue']
            literal = json.dumps(value, ensure_ascii=False)
            pattern = r'(?m)^(\s*)"conf\.default\.' + re.escape(key) + r'",.*$'
            text, count = re.subn(pattern, lambda m: m[1] + '"conf.default.' + key + '", ' + literal + ',', text)
            assert count == 1, (name, key, 'spec')
            pattern = r'(?m)^(\s*)bindParameter\("' + re.escape(key) + r'",\s*([^,]+),.*$'
            text, count = re.subn(pattern, lambda m: m[1] + 'bindParameter("' + key + '", ' + m[2] + ', ' + literal + ');', text)
            assert count == 1, (name, key, 'binding')
        cpp.write_text(text, encoding='utf-8')
        adaptations.append('C++ configuration literals escaped; all defaults restored from canonical RTC JSON.')
        component_conf = folder / (name + '.conf')
        conf_text = component_conf.read_text(encoding='utf-8')
        for c in profile['configuration']:
            conf_text = re.sub(r'(?m)^(#?\s*conf\.default\.' + re.escape(c['name']) + r':).*$',
                               lambda m: m[1] + ' ' + c['defaultValue'], conf_text)
        component_conf.write_text(conf_text, encoding='utf-8')
        normalize_auxiliary(profile, folder)
        required = [f'src/{name}.cpp', f'src/{name}Comp.cpp', f'include/{name}/{name}.h', 'CMakeLists.txt']
        for f in required:
            assert (folder / f).is_file(), f
        header = (folder / required[2]).read_text(encoding='utf-8')
        for p in profile['dataPorts']:
            direction = 'In' if p['portType'] == 'DataInPort' else 'Out'
            assert f'RTC::{direction}Port<{p["type"]}>' in header
            assert f'add{direction}Port("{p["name"]}"' in text
        for p in profile['servicePorts']:
            for i in p['interfaces']:
                assert i['type'] in header
                assert f'registerConsumer("{i["instanceName"]}", "{i["type"]}"' in text
        assert '__RTC_BUILDER_UNSET__' not in text
        hashes = {f: hashlib.sha256((folder / f).read_bytes()).hexdigest() for f in required}
        state = dict(name=name, status='skeleton-generated', behaviorImplemented=False,
                     adaptations=adaptations, command=args, fileHashes=hashes)
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        report.append(state)
        print(name + ': skeleton verified')
    (ROOT / 'build/system/skeleton-validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()

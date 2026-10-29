"""Validate an approved downloaded session and export semantic RTC profiles.

Does not fetch a session, change the approved design, or run the skeleton builder.
"""
import copy
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYSTEM = ROOT / 'build/system'
SOURCE = ROOT / 'work/final-session.json'


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def validate(s):
    assert isinstance(s, dict)
    assert all(isinstance(s[k], str) for k in ('name', 'description'))
    assert all(isinstance(s[k], list) for k in ('rtcTemplates', 'nodes', 'edges'))
    nodes = {n['id']: n['data'] for n in s['nodes']}
    assert len(nodes) == len(s['nodes']), 'Duplicate node ID'
    assert len({e['id'] for e in s['edges']}) == len(s['edges']), 'Duplicate edge ID'
    templates = {t['name']: t for t in s['rtcTemplates']}
    for n in nodes.values():
        assert len({p['id'] for p in n['ports']}) == len(n['ports'])
        for k in ('summary', 'requirements', 'constraints', 'notes'):
            assert isinstance(n['implementation'][k], str)
        if n['origin'] == 'catalog':
            assert n.get('repositoryUrl'), 'Existing RTC has no repository URL'
            t = templates[n['name']]
            for k in ('catalogId', 'repositoryUrl', 'directoryUrl', 'rtcXmlUrl', 'rawRtcXmlUrl'):
                if t.get(k):
                    assert n.get(k) == t[k], f'Provenance conflict: {n["name"]}.{k}'
        else:
            assert n['origin'] == 'generated'
            assert not any(n.get(k) for k in ('repositoryUrl', 'directoryUrl', 'rtcXmlUrl'))
    for e in s['edges']:
        a = next(p for p in nodes[e['source']]['ports'] if p['id'] == e['sourceHandle'])
        b = next(p for p in nodes[e['target']]['ports'] if p['id'] == e['targetHandle'])
        assert a['portType'] == b['portType'] == e['data']['connectionType']
        if a['portType'] == 'data':
            assert a['direction'] == 'out' and b['direction'] == 'in'
            assert a['dataType'] == b['dataType']
        else:
            assert any(i['name'] == j['name'] and i['interfaceType'] == j['interfaceType']
                       and {i['polarity'], j['polarity']} == {'consumer', 'provider'}
                       for i in a['interfaces'] for j in b['interfaces'])
    return nodes


def export_profile(n):
    name = n['name']
    assert re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', name), 'Unsafe or invalid RTC name'
    folder = ROOT / 'build/generated' / name
    folder.mkdir(parents=True, exist_ok=True)
    meta = copy.deepcopy(n['profileMetadata'])
    profile = dict(profileVersion=meta.pop('profileVersion'),
                   language=dict(kind=meta.pop('language')), actions=meta.pop('actions'))
    profile['basicInfo'] = dict(name=name, description=n['description'], **meta)
    profile['configuration'] = [dict(name=c['name'], type=c['type'],
                                    defaultValue=c['value'], widget=c.get('widget', 'text'))
                                for c in n['configuration']]
    profile['dataPorts'] = []
    profile['servicePorts'] = []
    for p in n['ports']:
        if p['portType'] == 'data':
            profile['dataPorts'].append(dict(name=p['name'],
                portType='DataInPort' if p['direction'] == 'in' else 'DataOutPort',
                type=p['dataType'], position='LEFT' if p['direction'] == 'in' else 'RIGHT',
                variableName=p['name']))
        else:
            interfaces = []
            idl_dir = folder / 'idl'
            idl_dir.mkdir(exist_ok=True)
            for i in p['interfaces']:
                # Resolve the real upstream IDL; never synthesize a replacement interface.
                filename = i['interfaceType'].split('::')[-1] + '.idl'
                source_dir = Path(n.get('idlSourceDirectory', ROOT / 'build/existing/URRobotControllerRTC/idl'))
                upstream = source_dir / filename
                assert upstream.is_file(), f'Missing upstream IDL: {filename}'
                interfaces.append(dict(name=i['name'], direction='Required' if i['polarity'] == 'consumer' else 'Provided',
                    type=i['interfaceType'], instanceName=i.get('instanceName', i['name']),
                    idlFile=str((idl_dir / filename).resolve()).replace('\\', '/'),
                    path=str(idl_dir.resolve()).replace('\\', '/'), sourceIdlFile=upstream.resolve().as_posix()))
                # Copy the actual include closure from declared source directories.
                search_dirs = [source_dir] + [Path(d) for d in n.get('idlIncludeDirectories', [])]
                pending = [upstream]
                copied = set()
                while pending:
                    src = pending.pop()
                    if src.name in copied:
                        continue
                    copied.add(src.name)
                    shutil.copy2(src, idl_dir / src.name)
                    for include in re.findall(r'^\s*#include\s+"([^"]+)"', src.read_text(encoding='utf-8'), re.MULTILINE):
                        found = next((d / include for d in [src.parent] + search_dirs if (d / include).is_file()), None)
                        assert found is not None, f'Missing IDL include: {include}'
                        pending.append(found)
            profile['servicePorts'].append(dict(name=p['name'], interfaces=interfaces, position='LEFT'))
    # Refuse to overwrite edited inputs on a later invocation.
    destination = folder / (name + '.json')
    if destination.exists():
        assert json.loads(destination.read_text(encoding='utf-8')) == profile, f'Existing profile differs: {destination}'
    else:
        save(destination, profile)
    save(folder / 'implementation-spec.json', n['implementation'])
    save(folder / 'deployment.json', dict(deployment=n['deployment'], rtcConf=n['rtcConf'],
                                         instanceName=n['instanceName'], configuration=n['configuration']))
    return str(destination.relative_to(ROOT))


def main():
    s = json.loads(SOURCE.read_text(encoding='utf-8'))
    nodes = validate(s)
    SYSTEM.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE, SYSTEM / 'final-session.json')
    proposal = json.loads((ROOT / 'work/session-proposal.json').read_text(encoding='utf-8'))
    before = {n['id']: n['data'] for n in proposal['nodes']}
    changes = dict(added=list(nodes.keys() - before.keys()), removed=list(before.keys() - nodes.keys()),
                   nodeFields={nid: [k for k in nodes[nid].keys() | before[nid].keys()
                                     if nodes[nid].get(k) != before[nid].get(k)]
                               for nid in nodes.keys() & before.keys()},
                   edgesChanged=proposal['edges'] != s['edges'])
    save(SYSTEM / 'design-diff.json', changes)
    sources = []
    profiles = []
    seen = {}
    for n in nodes.values():
        if n['origin'] == 'generated':
            if n['name'] in seen:
                assert seen[n['name']]['ports'] == n['ports'], 'Conflicting instances need distinct definitions'
                assert seen[n['name']]['configuration'] == n['configuration']
                continue
            profiles.append(export_profile(n))
            seen[n['name']] = n
        elif n['repositoryUrl'] not in {r['repositoryUrl'] for r in sources}:
            folder = ROOT / 'build/existing' / n['repositoryUrl'].rstrip('/').split('/')[-1]
            commit = subprocess.check_output(['git', '-c', 'safe.directory=' + folder.as_posix(),
                                              '-C', str(folder), 'rev-parse', 'HEAD'], text=True).strip()
            match = re.search(r'/blob/([0-9a-f]{40})/', n.get('rtcXmlUrl', ''))
            assert not match or match.group(1) == commit, 'Source commit differs from approved RTC.xml'
            sources.append(dict(repositoryUrl=n['repositoryUrl'], commit=commit,
                                directory=str(folder.relative_to(ROOT)), rtcXmlUrl=n.get('rtcXmlUrl', '')))
    save(SYSTEM / 'sources.json', sources)
    result = dict(valid=True, sessionId=(ROOT / 'work/current_session_id.txt').read_text(encoding='utf-8-sig').strip(),
                  sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(), nodes=len(nodes), edges=len(s['edges']),
                  profiles=profiles, sources=sources, changes=changes)
    save(SYSTEM / 'preparation-validation.json', result)
    print(json.dumps(dict(valid=True, nodes=len(nodes), edges=len(s['edges']), profiles=len(profiles))))


if __name__ == '__main__':
    main()

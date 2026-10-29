"""Generate the approved local system's lifecycle batches, without running RTCs."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_final_session import validate


def main():
    system = ROOT / 'build/system'
    final = system / 'final-session.json'
    session = json.loads(final.read_text(encoding='utf-8'))
    validate(session)
    scripts = system / 'scripts'
    config = system / 'runtime-config'
    scripts.mkdir(exist_ok=True)
    config.mkdir(exist_ok=True)
    session_id = (ROOT / 'work/current_session_id.txt').read_text(encoding='utf-8-sig').strip()
    context = 'codex_' + session_id + '.cxt'
    tools = {name: shutil.which(name) for name in ('rtls', 'rtcat', 'rtcon', 'rtact', 'rtdeact', 'rtexit')}
    if not all(tools.values()):
        raise RuntimeError('rtshell commands missing: ' + ', '.join(k for k, v in tools.items() if not v))
    ns_exe = shutil.which('omniNames')
    if not ns_exe:
        raise RuntimeError('omniNames is unavailable.')
    rtm = Path(os.environ['RTM_ROOT'])
    dll_dirs = [rtm / 'bin/vc16', Path(ns_exe).parent]
    cv = Path(os.environ.get('OpenCV_DIR', rtm / 'OpenCV4.13.0')) / 'x64/vc16/bin'
    if cv.is_dir():
        dll_dirs.append(cv)
    nodes = []
    endpoints = set()
    for entry in session['nodes']:
        d = entry['data']
        if d['deployment']['host'].lower() not in ('localhost', '127.0.0.1'):
            raise RuntimeError('Remote launch must be configured explicitly: ' + d['name'])
        if d['instanceName'] != d['name'] + '0':
            raise RuntimeError('Custom instance creation must be verified for: ' + d['instanceName'])
        endpoint = d['rtcConf']['corbaNameServers']
        if endpoint == 'localhost':
            endpoint = 'localhost:2809'
        if endpoint != 'localhost:2809':
            raise RuntimeError('Verify nameserver deployment before generating: ' + endpoint)
        endpoints.add(endpoint)
        wd = Path(d['deployment']['workingDirectory'])
        if not wd.is_absolute():
            wd = ROOT / wd
        executable = d['deployment']['executable']
        if not executable:
            binary = system / 'checks' / d['name'] / 'src/Release' / (d['name'] + 'Comp.exe')
            if not binary.is_file():
                raise RuntimeError('Deployment executable unresolved: ' + str(binary))
            executable = str(binary)
        elif not Path(executable).is_file():
            raise RuntimeError('Deployment interpreter/executable unavailable: ' + executable)
        arguments = [a.strip('"') for a in shlex.split(d['deployment']['arguments'], posix=False)]
        if '-f' in arguments:
            raise RuntimeError('Existing -f argument needs explicit merge with generated rtc.conf: ' + d['name'])
        environment = {}
        for line in d['deployment']['environment'].splitlines():
            if line.strip():
                key, separator, value = line.partition('=')
                if not separator or not key.strip():
                    raise RuntimeError('Use KEY=VALUE lines for environment: ' + d['name'])
                environment[key.strip()] = value
        node_dir = config / entry['id']
        node_dir.mkdir(exist_ok=True)
        component_config = node_dir / (d['name'] + '.conf')
        lines = ['# Generated from final-session.json. Preserve reviewed configuration values.']
        for c in d['configuration']:
            if '\n' in c['value'] or '\r' in c['value']:
                raise RuntimeError('Multiline component value needs a verified encoding: ' + c['name'])
            lines.append('conf.default.' + c['name'] + ': ' + c['value'])
        component_config.write_text('\n'.join(lines)+'\n', encoding='utf-8')
        category = d.get('category') or d.get('profileMetadata', {}).get('category')
        if not category:
            raise RuntimeError('Component category unresolved for config_file: ' + d['name'])
        rtc_config = node_dir / 'rtc.conf'
        lines = ['corba.nameservers: ' + d['rtcConf']['corbaNameServers'],
                 'manager.shutdown_auto: ' + d['rtcConf']['managerShutdownAuto'],
                 'manager.shutdown_on_nortcs: NO',
                 'naming.formats: ' + context + '/%n.rtc',
                 'logger.file_name: ' + (system / 'logs' / (entry['id']+'-%p.log')).as_posix(),
                 category + '.' + d['instanceName'] + '.config_file: ' + component_config.as_posix()]
        if 'profileMetadata' in d:
            lines.append('exec_cxt.periodic.rate: ' + str(d['profileMetadata']['executionRate']))
        rtc_config.write_text('\n'.join(lines)+'\n', encoding='utf-8')
        nodes.append(dict(id=entry['id'], name=d['name'], instance=d['instanceName'],
            command=[executable, *arguments, '-f', str(rtc_config)], workingDirectory=str(wd.resolve()),
            environment=environment, rtcConf=str(rtc_config), componentConf=str(component_config), ecIndex=0))
    by_id = {n['id']: n['data'] for n in session['nodes']}
    edges = []
    for edge in session['edges']:
        a = next(p for p in by_id[edge['source']]['ports'] if p['id'] == edge['sourceHandle'])
        b = next(p for p in by_id[edge['target']]['ports'] if p['id'] == edge['targetHandle'])
        item = dict(id=session_id + '-' + edge['id'], source=edge['source'], target=edge['target'],
                    sourcePort=a['name'], targetPort=b['name'], kind=edge['data']['connectionType'])
        if item['kind'] == 'data':
            item['dataType'] = a['dataType']
        else:
            item['interfaces'] = [{k: i[k] for k in ('name', 'interfaceType')} for i in a['interfaces']]
        edges.append(item)
    activation = ['arm-1', 'executor-1', 'planner-1', 'projector-1', 'detector-1', 'camera-1']
    deactivation = ['planner-1', 'camera-1', 'detector-1', 'projector-1', 'executor-1', 'arm-1']
    if set(activation) != set(by_id):
        raise RuntimeError('Determine an activation order for the modified system before generating.')
    manifest = dict(finalSession=str(final), finalSessionSha256=hashlib.sha256(final.read_bytes()).hexdigest(),
        python=sys.executable, nameserver=next(iter(endpoints)), context=context,
        omniNames=ns_exe, rtshell=tools, dllDirectories=[str(p) for p in dll_dirs],
        nodes=nodes, edges=edges, activationOrder=activation, deactivationOrder=deactivation,
        commandTimeoutSeconds=15, waitTimeoutSeconds=45, logDirectory=str(system / 'logs'),
        stateFile=str(system / 'runtime-state/processes.json'), namingDataDirectory=str(system / 'runtime-state/nameserver'))
    from scripts.direct_runtime_batches import write_direct_batches
    manifest['sessionId'] = session_id
    manifest['runtimeMode'] = 'direct-batch-rtshell'
    manifest['processDirectory'] = str(system / 'runtime-state')
    for obsolete in ('stateFile', 'commandTimeoutSeconds', 'waitTimeoutSeconds'):
        manifest.pop(obsolete, None)
    write_direct_batches(ROOT, scripts, manifest)
    (scripts / 'runtime-settings.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('Generated 5 native batches with direct rtshell commands; no Python runtime controller.')


if __name__ == '__main__':
    main()

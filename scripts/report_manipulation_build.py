"""Record successful implementation build evidence without changing the design."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
NAMES = ['ColorObjectDetector', 'PlaneTargetProjector', 'ColorActionPlanner', 'ArmActionExecutor']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path):
    return path.relative_to(ROOT).as_posix()


def read_log(path):
    data = path.read_bytes()
    return data.decode('utf-16' if data.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8', errors='replace')


def main():
    final = ROOT / 'build/system/final-session.json'
    assert final.read_bytes() == (ROOT / 'work/final-session.json').read_bytes(), 'Final snapshots differ'
    test_log = (ROOT / 'build/system/checks/ManipulationCoreTests/Testing/Temporary/LastTest.log').read_text(encoding='utf-8', errors='replace')
    match = re.search(r'(\d+) passed, (\d+) failed', test_log)
    assert match and int(match[1]) > 0 and int(match[2]) == 0 and 'Test Passed.' in test_log, 'Core tests not successful'
    records = []
    for name in NAMES:
        sources = sorted((ROOT / f'build/generated/{name}/src').glob('*.cpp'))
        sources += sorted((ROOT / f'build/generated/{name}/include/{name}').glob('*.h'))
        for path in sources:
            if path.name.endswith(('Core.cpp', 'Core.h')):
                text = path.read_text(encoding='utf-8')
                assert not re.search(r'\b(?:RTC|CORBA|Manipulation)::|\bJson\b|nlohmann|\b(?:isNew|read|write)\(', text), f'Core contains transport integration: {path}'
        cmakes = sorted((ROOT / f'build/generated/{name}').rglob('CMakeLists.txt'))
        files = sources + cmakes
        products = [ROOT / f'build/system/checks/{name}/src/Release/{name}{suffix}' for suffix in ['.dll', 'Comp.exe']]
        for path in products:
            assert path.is_file(), f'Missing build product: {path}'
            assert path.stat().st_mtime >= max(p.stat().st_mtime for p in files), f'Stale product: {path}'
        log_path = ROOT / f'work/build-implemented-{name}.log'
        log = read_log(log_path)
        assert not re.search(r'\b(?:error|warning) (?:C\d+|LNK\d+)', log, re.I), f'Build diagnostics remain: {name}'
        records.append({'name': name, 'releaseBuild': 'passed',
                        'products': {relative(p): digest(p) for p in products},
                        'implementationSources': {relative(p): digest(p) for p in files},
                        'buildLog': relative(log_path)})
    upstream = []
    for name in ['ImageProcessing', 'myCobotRTC']:
        repo = ROOT / f'build/existing/{name}'
        command = ['git', '-c', f'safe.directory={repo.as_posix()}', '-C', str(repo)]
        status = subprocess.check_output(command + ['status', '--porcelain'], text=True)
        assert not status.strip(), f'Upstream source modified: {name}'
        upstream.append({'name': name, 'unchanged': True,
                         'commit': subprocess.check_output(command + ['rev-parse', 'HEAD'], text=True).strip()})
    report = {
        'recordedAt': datetime.now(timezone.utc).isoformat(),
        'sessionId': '9c083a702c30', 'finalSessionSha256': digest(final),
        'scope': 'Four plain C++ cores, typed IDL ports, OpenRTM conversion/read/write in skeletons, and dry-run; physical executor unavailable',
        'rtcs': records, 'existingSources': upstream,
        'sharedSources': {relative(p): digest(p) for p in sorted((ROOT / 'build/generated/common').rglob('*')) if p.is_file()},
        'tests': {'framework': 'CTest with pure C++/OpenCV core tests', 'passed': int(match[1]), 'failed': 0,
                  'log': 'build/system/checks/ManipulationCoreTests/Testing/Temporary/LastTest.log',
                  'sources': {relative(p): digest(p) for p in sorted((ROOT / 'build/generated/tests').glob('*')) if p.is_file()},
                  'hardwareUsed': False},
        'runtimeStartedOrActivated': False,
        'limitations': [
            'myCobot physical service execution is intentionally unavailable, including with hardware_verified=true: absolute-speed conversion and reliable completion/stop feedback remain unverified.',
            'Real YAML calibration_file, tool_rpy_rad and CSV workspace_limits remain unset; no fabricated deployment values were installed.',
            'Selected OpenCVCamera does not assign image timestamps in its source. Zero/stale timestamps are retained and rejected downstream; a design-approved timestamp source/adapter is needed.',
            'workspace_limits uses xmin,ymin,zmin,xmax,ymax,zmax in metres; bounds checks are not collision/reachability/force validation.',
            'Synthetic tests validate core behavior. Connected RTC dataflow and physical hardware behavior were not tested in this implementation run.'
        ],
        'rebuild': 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/Check-ManipulationBuild.ps1',
        'details': 'build/generated/IMPLEMENTATION.md'
    }
    target = ROOT / 'build/system/implementation-build-report.json'
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{len(records)} RTC builds, {match[1]} core tests passed; report: {relative(target)}')


if __name__ == '__main__':
    main()

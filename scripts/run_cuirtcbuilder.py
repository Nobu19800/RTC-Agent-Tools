"""Expose -i IDL file paths while adapting to the bundled Java directory API."""
import argparse
import os
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree as ET


def main():
    parser = argparse.ArgumentParser(description='Generate RTC skeletons from RTC.xml')
    parser.add_argument('-d', required=True, help='Output directory')
    parser.add_argument('-f', required=True, help='RTC.xml path')
    parser.add_argument('-i', nargs='+', default=[], help='IDL file path(s); include directories also accepted')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    search_paths = []
    for value in args.i:
        path = Path(value).resolve()
        if not path.exists():
            parser.error('IDL path does not exist: ' + str(path))
        directory = path.parent if path.is_file() else path
        if str(directory) not in search_paths:
            search_paths.append(str(directory))
    if not os.environ.get('RTM_JAVA_ROOT'):
        parser.error('RTM_JAVA_ROOT must identify the installed OpenRTM Java/OpenRTP folder')
    plugins = Path(os.environ['RTM_JAVA_ROOT']) / 'utils/OpenRTP/plugins'
    if not plugins.is_dir():
        parser.error('OpenRTP plugin directory not found: ' + str(plugins))
    classpath = os.pathsep.join([str(root / 'tool/cuirtcbuilder/lib/*'), str(plugins / '*')])
    command = ['java', '-cp', classpath, 'jp.go.aist.rtm.cuirtcbuilder.CuiRtcBuilder',
               '-d', str(Path(args.d).resolve()), '-f', str(Path(args.f).resolve())]
    if search_paths:
        command += ['-i'] + search_paths
    profile = ET.parse(args.f).getroot()
    if profile.findall('.//{http://www.openrtp.org/namespaces/rtc}ServiceInterface'):
        command = ['java', '-cp', classpath, str(root / 'tool/cuirtcbuilder/CuiRtcBuilderServiceBridge.java'),
                   str(Path(args.d).resolve()), str(Path(args.f).resolve())] + search_paths
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    sys.stdout.buffer.write(result.stdout)
    # The Java main catches failures and sometimes exits with status zero.
    return result.returncode or (1 if any(x in result.stdout for x in
                                          (b'Error:', b'Exception', b'usage: CuiRTCBuilder')) else 0)


if __name__ == '__main__':
    sys.exit(main())

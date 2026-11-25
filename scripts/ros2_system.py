"""Search ROS 2 nodes, place them in a v2 design, and launch its local ROS 2 processes."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import time
from dataclasses import dataclass, field
from ros2_transport import Binding, render_config, serializer


CATALOG = Path(__file__).resolve().parents[1] / "catalog/ros2_catalog.json"
TOKEN = r"[A-Za-z_][A-Za-z0-9_]*"
PATH = rf"{TOKEN}(?:/{TOKEN})*"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def session(path):
    design = json.loads(path.read_text(encoding="utf-8-sig"))
    require(design.get("version") == 2, "Expected a version 2 design")
    require(isinstance(design.get("components"), list) and isinstance(design.get("edges"), list),
            "Expected components and edges arrays")
    return design


def make_component(entry, name, namespace, x, y):
    require(re.fullmatch(TOKEN, name) is not None, f"Invalid ROS node name: {name}")
    require(valid_namespace(namespace), f"Invalid ROS namespace: {namespace}")
    topics = [
        {"id": f"topic-{i}", "name": item["name"], "portType": "data",
         "direction": "in" if item["direction"] == "input" else "out",
         "dataType": item.get("dataType", "")}
        for i, item in enumerate(entry["topics"], 1)
    ]
    services = [
        {"id": f"{item['kind']}-{i}", "name": item["name"], "portType": "service",
         "rosInterfaceKind": item["kind"], "interfaces": [
             {"name": item["name"], "interfaceType": item.get("dataType", ""), "polarity": "provider"}
         ]}
        for i, item in enumerate(entry["servicesAndActions"], 1)
    ]
    return {
        "id": name, "type": "rtc", "position": {"x": x, "y": y},
        "data": {
            "moduleKind": "ros2", "catalogId": entry["catalogId"], "name": entry["executable"],
            "instanceName": name, "state": "INACTIVE", "ports": topics + services,
            "ros2": {"package": entry["package"], "executable": entry["executable"],
                     "namespace": namespace, "catalogLaunchAvailable": entry["launch"] is not None},
            "deployment": {"host": "localhost", "executable": "", "workingDirectory": "",
                           "arguments": "", "environment": ""},
            "rtcConf": {"corbaNameServers": "", "managerShutdownAuto": ""},
            "configuration": [],
            "implementation": {"summary": entry["description"], "requirements": "",
                               "constraints": "", "notes": entry["interfaceSummary"]},
        },
    }


def valid_namespace(namespace):
    return namespace == "/" or re.fullmatch(rf"/{PATH}", namespace) is not None


def port_name(name, namespace, instance):
    require(re.fullmatch(rf"(?:/|~/)?{PATH}", name) is not None, f"Invalid ROS interface name: {name}")
    if name.startswith("/"):
        return name
    if name.startswith("~/"):
        return f"{namespace.rstrip('/')}/{instance}/{name[2:]}"
    return f"{namespace.rstrip('/')}/{name}"


@dataclass
class Process:
    component_id: str
    package: str
    executable: str
    name: str
    namespace: str
    arguments: list[str]
    parameters: list[str]
    parameters_file: str | None
    cwd: str | None
    environment: dict[str, str]
    ports: dict
    remaps: dict = field(default_factory=dict)

    def command(self, ros2):
        command = [ros2, "run", self.package, self.executable, *self.arguments,
                   "--ros-args", "-r", f"__node:={self.name}", "-r", f"__ns:={self.namespace}"]
        if self.parameters_file:
            command.extend(["--params-file", self.parameters_file])
        for parameter in self.parameters:
            command.extend(["-p", parameter])
        for (kind, original), target in sorted(self.remaps.items()):
            if original != target:
                scheme = {"topic": "rostopic", "service": "rosservice"}[kind]
                command.extend(["-r", f"{scheme}://{original}:={target}"])
        return command


def process_for(component, root):
    component_id, data = component["id"], component["data"]
    settings = data.get("ros2", {})
    package, executable = settings.get("package", ""), settings.get("executable", "")
    name, namespace = data.get("instanceName", ""), settings.get("namespace", "/")
    require(re.fullmatch(r"[a-z][a-z0-9_]*", package), f"{component_id}: invalid ROS package")
    require(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", executable), f"{component_id}: invalid ROS executable")
    require(settings.get("catalogLaunchAvailable") is not False
            or data.get("catalogId") != f"ros2:{package}/{executable}",
            f"{component_id}: set a verified executable; the catalog has no launch entry")
    require(re.fullmatch(TOKEN, name), f"{component_id}: invalid ROS node name")
    require(valid_namespace(namespace), f"{component_id}: invalid ROS namespace")
    deployment = data.get("deployment", {})
    require(deployment.get("host", "") in ("", "localhost", "127.0.0.1", "::1"),
            f"{component_id}: start this design on its intended host; remote launch is unsupported")
    require(not deployment.get("executable"), f"{component_id}: set the executable in ROS 2 settings")
    cwd = deployment.get("workingDirectory", "")
    if cwd:
        resolved = root / cwd
        require(resolved.is_dir(), f"{component_id}: working directory does not exist: {resolved}")
        cwd = str(resolved)
    args = shlex.split(deployment.get("arguments", ""))
    require(not any(arg in {"--ros-args", "--"} for arg in args),
            f"{component_id}: use Configuration for ROS parameters")
    env = os.environ.copy()
    for line in deployment.get("environment", "").splitlines():
        if not line.strip():
            continue
        key, separator, value = line.partition("=")
        require(separator and re.fullmatch(TOKEN, key), f"{component_id}: expected NAME=value in Environment")
        env[key] = value
    parameters = []
    for parameter in data.get("configuration", []):
        key, value = parameter["name"], parameter["value"]
        require(re.fullmatch(rf"{TOKEN}(?:\.{TOKEN})*", key), f"{component_id}: invalid parameter name: {key}")
        parameters.append(f"{key}:={value}")
    parameters_file = settings.get("parametersFile")
    if parameters_file:
        resolved_file = (root / parameters_file).resolve()
        require(resolved_file.is_file(), f"{component_id}: ROS parameter file does not exist: {resolved_file}")
        parameters_file = str(resolved_file)
    port_list = data.get("ports", [])
    ports = {port["id"]: port for port in port_list}
    require(len(ports) == len(port_list), f"{component_id}: duplicate port ID")
    return Process(component_id, package, executable, name, namespace, args, parameters,
                   parameters_file, cwd or None, env, ports)


def edge_remap(edge, producer, consumer):
    edge_id = edge.get("id", "<edge>")
    source = producer.ports.get(edge.get("sourceHandle"))
    target = consumer.ports.get(edge.get("targetHandle"))
    require(source and target, f"{edge_id}: missing ROS 2 port")
    require(producer.environment.get("ROS_DOMAIN_ID", "0") == consumer.environment.get("ROS_DOMAIN_ID", "0"),
            f"{edge_id}: endpoints use different ROS domains")
    source_name = port_name(source["name"], producer.namespace, producer.name)
    target_name = port_name(target["name"], consumer.namespace, consumer.name)
    if source["portType"] == target["portType"] == "data":
        data_type = source.get("dataType", "")
        require(source["direction"] == "out" and target["direction"] == "in"
                and re.fullmatch(rf"{TOKEN}/msg/{TOKEN}", data_type)
                and data_type == target.get("dataType"), f"{edge_id}: incompatible ROS topic ports")
        process, kind, original, canonical = consumer, "topic", target_name, source_name
    else:
        kind = source.get("rosInterfaceKind")
        require(source["portType"] == target["portType"] == "service"
                and kind in ("service", "action") and kind == target.get("rosInterfaceKind"),
                f"{edge_id}: incompatible ROS interface kinds")
        family = "srv" if kind == "service" else "action"
        types = [
            {item["interfaceType"] for item in port.get("interfaces", [])
             if item.get("polarity") == polarity and re.fullmatch(rf"{TOKEN}/{family}/{TOKEN}", item["interfaceType"])}
            for port, polarity in ((source, "consumer"), (target, "provider"))
        ]
        require(bool(types[0] & types[1]), f"{edge_id}: incompatible ROS client and server")
        if kind == "action":
            require(source_name == target_name, f"{edge_id}: ROS action endpoints must resolve to the same name")
            return
        process, original, canonical = producer, source_name, target_name
    previous = process.remaps.setdefault((kind, original), canonical)
    require(previous == canonical, f"{edge_id}: conflicting remaps for {process.component_id}/{original}")


def build_plan(design, root, bindings=None):
    components = {component["id"]: component for component in design["components"]}
    require(len(components) == len(design["components"]), "Duplicate component ID")
    processes = {
        key: process_for(component, root) for key, component in components.items()
        if component["data"].get("moduleKind") == "ros2"
    }
    require(processes, "No ROS 2 node in the design")
    names = {(p.environment.get("ROS_DOMAIN_ID", "0"), p.namespace, p.name) for p in processes.values()}
    require(len(names) == len(processes), "Duplicate ROS 2 node name within a namespace and domain")
    mixed = []
    for edge in design["edges"]:
        source, target = processes.get(edge["source"]), processes.get(edge["target"])
        if source and target:
            edge_remap(edge, source, target)
        elif source or target:
            mixed.append((edge, source or target, bool(source)))
    # A ROS remap applies to the original name, so an endpoint used on both
    # sides of a graph cannot silently change the provider side of another edge.
    for edge in design["edges"]:
        if edge["source"] in processes and edge["target"] in processes:
            source, target = processes[edge["source"]], processes[edge["target"]]
            a, b = source.ports[edge["sourceHandle"]], target.ports[edge["targetHandle"]]
            kind = "topic" if a["portType"] == "data" else a["rosInterfaceKind"]
            left = port_name(a["name"], source.namespace, source.name)
            right = port_name(b["name"], target.namespace, target.name)
            require(source.remaps.get((kind, left), left) == target.remaps.get((kind, right), right),
                    f"{edge.get('id', '<edge>')}: resulting ROS interface names do not match")
    native = []
    for edge, ros, ros_publishes in mixed:
        side, other = ("target", "source") if ros_publishes else ("source", "target")
        rtc = components.get(edge[side])
        label = edge.get("id", "<edge>")
        require((edge.get("data") or {}).get("transport") in (None, "ros2"),
                f"{label}: RTC/ROS 2 edges require ROS2Transport")
        require(rtc and rtc["data"].get("moduleKind", "rtc") == "rtc",
                f"{label}: ROS2Transport requires an RTC DataPort")
        data = rtc["data"]
        rtc_port = next((p for p in data.get("ports", []) if p["id"] == edge.get(side + "Handle")), None)
        ros_port = ros.ports.get(edge.get(other + "Handle"))
        require(rtc_port and ros_port and rtc_port["portType"] == ros_port["portType"] == "data"
                and rtc_port["direction"] == ("in" if ros_publishes else "out")
                and ros_port["direction"] == ("out" if ros_publishes else "in"),
                f"{label}: ROS2Transport requires an output-to-input topic connection")
        codec = serializer(rtc_port.get("dataType", ""), ros_port.get("dataType", ""))
        require(codec, f"{label}: no supported ROS2Transport mapping for "
                f"{rtc_port.get('dataType', '')} and {ros_port.get('dataType', '')}")
        instance, port = data.get("instanceName", ""), rtc_port["name"]
        port = port.removeprefix(instance + ".")
        require(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", instance)
                and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", port),
                f"{label}: invalid RTC instance or DataPort name for rtc.conf preconnect")
        rtc_domain = os.environ.get("ROS_DOMAIN_ID", "0")
        for line in data.get("deployment", {}).get("environment", "").splitlines():
            if line.startswith("ROS_DOMAIN_ID="):
                rtc_domain = line.partition("=")[2]
        require(rtc_domain == ros.environment.get("ROS_DOMAIN_ID", "0"),
                f"{label}: endpoints use different ROS domains")
        name = port_name(ros_port["name"], ros.namespace, ros.name)
        topic = ros.remaps.get(("topic", name), name)
        native.append(Binding(rtc["id"], f"{instance}.{port}", topic, codec, rtc_domain,
                              not ros_publishes))
    if bindings is not None:
        bindings.extend(dict.fromkeys(native))
    return list(processes.values())


def run(processes):
    require(os.name == "posix", "Run from a sourced ROS 2 Linux/WSL environment")
    ros2 = shutil.which("ros2")
    require(ros2, "ros2 was not found. Source the ROS distribution and workspace first")
    for process in processes:
        command = [ros2, "pkg", "executables", process.package]
        result = subprocess.run(command, env=process.environment, cwd=process.cwd,
                                capture_output=True, text=True, timeout=30)
        expected = [process.package, process.executable]
        require(result.returncode == 0 and any(line.split() == expected for line in result.stdout.splitlines()),
                f"{process.component_id}: {process.package}/{process.executable} is not installed")
    children = []
    try:
        for process in processes:
            command = process.command(ros2)
            print(shlex.join(command), flush=True)
            child = subprocess.Popen(command, env=process.environment, cwd=process.cwd, start_new_session=True)
            children.append((process.component_id, child))
        while True:
            for name, child in children:
                status = child.poll()
                if status is not None and status != 0:
                    raise ValueError(f"{name}: ROS process exited with status {status}")
            if all(child.poll() is not None for _, child in children):
                return
            time.sleep(0.2)
    except KeyboardInterrupt:
        return
    finally:
        for sig, wait_seconds in ((signal.SIGINT, 2), (signal.SIGTERM, 1), (signal.SIGKILL, 0)):
            any_group = False
            for _, child in children:
                try:
                    os.killpg(child.pid, sig)
                    any_group = True
                except ProcessLookupError:
                    pass
            if not any_group:
                break
            time.sleep(wait_seconds)
        for _, child in children:
            child.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    search = commands.add_parser("search")
    search.add_argument("query", nargs="?", default="")
    add = commands.add_parser("add")
    add.add_argument("catalog_id")
    add.add_argument("design", type=Path, help="Existing or new v2 design JSON")
    add.add_argument("--instance", required=True)
    add.add_argument("--namespace", default="/")
    add.add_argument("--x", type=float, default=80)
    add.add_argument("--y", type=float, default=80)
    for name in ("plan", "run"):
        child = commands.add_parser(name)
        child.add_argument("design", type=Path)
    configure = commands.add_parser("transport", help="Generate an rtc.conf with ROS2Transport preconnections")
    configure.add_argument("design", type=Path)
    configure.add_argument("--rtc-id", required=True)
    configure.add_argument("--base-conf", required=True, type=Path)
    configure.add_argument("--module", required=True, type=Path)
    configure.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command in {"search", "add"}:
            entries = json.loads(CATALOG.read_bytes())["nodes"]
            if args.command == "search":
                matches = [item for item in entries if all(
                    term in json.dumps(item, ensure_ascii=False).casefold()
                    for term in args.query.casefold().split())]
                print(json.dumps(matches, ensure_ascii=True, indent=2))
                return
            entry = next((item for item in entries if item["catalogId"] == args.catalog_id), None)
            require(entry, f"Unknown catalog ID: {args.catalog_id}")
            design = session(args.design) if args.design.exists() else {
                "version": 2, "id": args.design.stem, "name": args.design.stem, "description": "",
                "components": [], "edges": [],
            }
            require(not any(c["id"] == args.instance for c in design["components"]),
                    f"Duplicate component ID: {args.instance}")
            design["components"].append(make_component(entry, args.instance, args.namespace, args.x, args.y))
            args.design.write_bytes((json.dumps(design, ensure_ascii=False, indent=2) + "\n").encode())
            return
        bindings = []
        processes = build_plan(session(args.design), args.design.resolve().parent, bindings)
        if args.command == "transport":
            selected = [binding for binding in bindings if binding.rtc_id == args.rtc_id]
            require(selected, f"No ROS2Transport connection for RTC {args.rtc_id}")
            module = args.module.resolve(strict=True)
            require(module.is_file(), f"ROS2Transport module is not a file: {module}")
            text = render_config(args.base_conf.read_text(encoding="utf-8-sig"), selected, module)
            require(args.output.resolve() != args.base_conf.resolve(),
                    "Use a separate output path to preserve the base rtc.conf")
            args.output.write_text(text, encoding="utf-8", newline="\n")
            print(f"{args.output}: {len(selected)} ROS2Transport preconnection(s)")
        elif args.command == "plan":
            for process in processes:
                print(f"{process.component_id}: {shlex.join(process.command('ros2'))}")
            for binding in bindings:
                print(f"{binding.rtc_id}: {binding.preconnect()}")
        else:
            print(f"Design SHA-256: {hashlib.sha256(args.design.read_bytes()).hexdigest()}", flush=True)
            run(processes)
    except (KeyError, TypeError, AttributeError, ValueError, OSError, subprocess.SubprocessError) as error:
        parser.exit(1, f"ROS 2: {error}\n")


if __name__ == "__main__":
    main()

"""Import the supplied 100-node report and build a ROS 2 catalog from XML."""

import argparse
import hashlib
import json
import re
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROFILE_DIR = ROOT / "profiles/iso22166-202/ros2"
CATALOG = ROOT / "catalog/ros2_catalog.json"
ENGLISH_METADATA = PROFILE_DIR / "english-metadata.txt"
STANDARD = "ISO 22166-202:2025"
NAMESPACE = "urn:rtc-agent-tools:iso22166-202:ros2-mapping:0.1"
ET.register_namespace("ros", NAMESPACE)
ROW = re.compile(r"\*\*(\d+)\. `([a-zA-Z0-9_]+)`\*\*")
TOKEN = r"`((?:/|~/)?[a-zA-Z_][a-zA-Z_0-9/]*)`"
NAMED_ENDPOINT = re.compile(
    rf"^({TOKEN}(?:\s*,\s*{TOKEN})*)"
    r"(?:\s*:\s*`([a-zA-Z_0-9]+/(?:msg|srv|action)/[a-zA-Z_0-9]+)`(.*))?"
)


def tag(name):
    return f"{{{NAMESPACE}}}{name}"


def add(parent, element, text=None, **attributes):
    child = ET.SubElement(parent, tag(element), attributes)
    child.text = text
    return child


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_report(path):
    data = path.read_bytes()
    digest = sha256(data)
    entries = []
    previous_urls = []
    for line in data.decode("utf-8-sig").splitlines():
        if not line.startswith("|"):
            continue
        match = ROW.search(line)
        if not match:
            continue
        fields = [field.strip() for field in line.strip("|").split("|")]
        category, _, package, description, io, distro, references = fields
        package = package.strip("`")
        if not re.fullmatch(r"[a-zA-Z_][a-zA-Z_0-9]*", package):
            raise ValueError(f"Invalid ROS package: {package}")
        urls = re.findall(r"https?://[^\s<>\x60\ue000-\uf8ff]+", references)
        if urls:
            previous_urls = list(dict.fromkeys(urls))
        elif not references.startswith("同上") or not previous_urls:
            raise ValueError(f"Missing source URLs at report row {match[1]}")
        entries.append((int(match[1]), package, match[2], category, description, io, distro, previous_urls))
    if [entry[0] for entry in entries] != list(range(1, 101)):
        raise ValueError("Expected the numbered report rows 1 through 100 in order")
    if len({entry[1:3] for entry in entries}) != len(entries):
        raise ValueError("Duplicate package/executable pair in the report")
    return entries, digest


def named_interfaces(summary):
    """Extract explicitly named endpoints while retaining loose I/O in the summary."""
    roles = {"Sub": "subscribe", "Pub": "publish", "Srv": "service",
             "Service": "service", "Services": "service", "Action": "action", "Actions": "action"}
    expected_types = {"subscribe": "msg", "publish": "msg", "service": "srv", "action": "action"}
    for clause in summary.split(";"):
        role, _, text = clause.strip().partition(" ")
        if role not in roles:
            continue
        kind = roles[role]
        while match := NAMED_ENDPOINT.match(text):
            names = re.findall(TOKEN, match[1])
            data_type, remainder = match[4], match[5] or text[match.end():]
            # A continuation can be a second named endpoint or ambiguous free text.
            continuation = remainder.removeprefix(",").strip()
            next_endpoint = remainder.startswith(",") and NAMED_ENDPOINT.match(continuation)
            unambiguous = not remainder or next_endpoint or remainder.strip() == ", TF"
            if data_type and (data_type.split("/")[1] != expected_types[kind] or not unambiguous):
                data_type = None
            for name in names:
                if "/" + expected_types[kind] + "/" not in name and (
                    name.startswith(("/", "~/")) or name[0].islower()
                ):
                    yield kind, name, data_type
            if not next_endpoint:
                break
            text = continuation


def read_english_metadata():
    categories = {
        "座標変換": "Coordinate transforms", "状態配信": "State publishing",
        "状態推定": "State estimation", "制御": "Control", "画像処理": "Image processing",
        "深度画像": "Depth imaging", "深度点群": "Depth point clouds",
        "可視化": "Visualization", "画像保存": "Image capture", "録画": "Video recording",
        "Scan変換": "Scan conversion", "点群": "Point-cloud processing",
        "点群I/O": "Point-cloud I/O", "通信": "Communication",
        "Web通信": "Web communication", "可視化通信": "Visualization bridge",
        "録再": "Recording and playback", "Simulation通信": "Simulation bridge",
        "診断": "Diagnostics", "入力": "Input devices", "操作": "Teleoperation",
        "Camera校正": "Camera calibration", "画像入力": "Image publishing",
    }
    translations = {}
    for line in ENGLISH_METADATA.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            number, *content = (field.strip() for field in line.split("|"))
            translations[int(number)] = content
    return categories, translations


def profile_document(entry, report_name, digest, categories, translations, review):
    index, package, executable, category, _, summary, _, urls = entry
    description, english_summary, *notes = translations[index]
    category = categories.get(category, category)
    distro = notes[0] if notes else "The report lists this entry for ROS 2 Jazzy."
    checked = review.get(str(index), {})
    package = checked.get("package", package)
    executable = checked.get("executable", executable)
    distro = checked.get("distributionNote", distro)
    identity = f"ros2:{package}/{executable}"
    module = ET.Element(tag("Module"), targetStandard=STANDARD, profileVersion="0.1",
                        conformanceStatus="not-assessed")
    general = add(module, "GenInfo")
    add(general, "ModuleName", executable)
    add(general, "Description", description)
    identity_group = add(module, "IDnType")
    add(identity_group, "ID", uuid.uuid5(uuid.NAMESPACE_URL, identity).urn)
    add(identity_group, "InformationModelVersion", "local-mapping-0.1")
    properties = add(module, "ModuleProp")
    for name, value in (("rosPackage", package), ("category", category)):
        add(properties, "Property", value, name=name)
    variables = add(module, "IOVariables")
    add(variables, "Description", english_summary)
    services = add(module, "Services")
    interfaces = checked.get("interfaces")
    if interfaces is None:
        interfaces = named_interfaces(summary)
    for role, name, data_type in dict.fromkeys(map(tuple, interfaces)):
        fields = {"name": name}
        if data_type:
            fields["dataType"] = data_type
        if role in {"subscribe", "publish"}:
            direction = {"subscribe": "input", "publish": "output"}[role]
            add(variables, "Variable", direction=direction, transport="ROS 2 topic", **fields)
        else:
            if role == "service-client":
                add(services, "Service", kind="service", role="client", **fields)
            else:
                add(services, "Service", kind=role, **fields)
    parameters = checked.get("parameters", [])
    if parameters:
        parameter_group = add(module, "Parameters")
        for item in parameters:
            parameter = add(parameter_group, "Parameter", name=item["name"], dataType=item["type"])
            if "default" in item:
                add(parameter, "Default", json.dumps(item["default"], ensure_ascii=False))
    infrastructure = add(module, "Infra")
    add(infrastructure, "Requirement", distro, kind="report-distribution-note")
    if checked.get("status") != "not-registered":
        launch = add(module, "ExecutableForm")
        add(launch, "Command", "ros2")
        for argument in ("run", package, executable):
            add(launch, "Argument", argument)
    evidence = add(module, "Evidence")
    add(evidence, "Report", report_name, sha256=digest, row=str(index))
    for url in urls:
        add(evidence, "Source", url)
    if "url" in checked:
        add(evidence, "UpstreamSource", checked["url"], status=checked["status"])
    if "implementationUrl" in checked:
        add(evidence, "ImplementationSource", checked["implementationUrl"])
    for url in checked.get("additionalImplementationUrls", []):
        add(evidence, "AdditionalImplementationSource", url)
    if "note" in checked:
        add(evidence, "SourceReviewNote", checked["note"])
    add(evidence, "Verification", "Runtime behavior and Annex B conformance have not been verified.")
    ET.indent(module)
    return identity.removeprefix("ros2:").replace("/", "__") + ".xml", ET.tostring(
        module, encoding="utf-8", xml_declaration=True
    ) + b"\n"


def read_profile(path):
    data = path.read_bytes()
    module = ET.fromstring(data)
    if module.tag != tag("Module") or module.get("targetStandard") != STANDARD:
        raise ValueError(f"Unexpected profile format: {path.name}")

    def required(group, field):
        element = module.find(f"{tag(group)}/{tag(field)}")
        if element is None or not element.text:
            raise ValueError(f"{path.name}: missing {group}/{field}")
        return element

    properties = {item.attrib["name"]: item.text for item in module.findall(
        f"{tag('ModuleProp')}/{tag('Property')}"
    )}
    executable = required("GenInfo", "ModuleName").text
    package = properties["rosPackage"]
    report = module.find(f"{tag('Evidence')}/{tag('Report')}")
    upstream = module.find(f"{tag('Evidence')}/{tag('UpstreamSource')}")
    implementation_url = module.findtext(f"{tag('Evidence')}/{tag('ImplementationSource')}")
    if report is None and (upstream is None or not implementation_url):
        raise ValueError(f"{path.name}: standalone profiles require upstream and implementation sources")
    review_note = module.findtext(f"{tag('Evidence')}/{tag('SourceReviewNote')}")
    launch = module.find(tag("ExecutableForm"))
    parameters = []
    for item in module.findall(f"{tag('Parameters')}/{tag('Parameter')}"):
        parameter = {"name": item.attrib["name"], "type": item.attrib["dataType"]}
        default = item.findtext(tag("Default"))
        if default is not None:
            parameter["default"] = json.loads(default)
        parameters.append(parameter)
    return {
        "catalogId": f"ros2:{package}/{executable}",
        "moduleId": required("IDnType", "ID").text,
        "moduleKind": "ros2",
        "package": package,
        "executable": executable,
        "category": properties["category"],
        "description": required("GenInfo", "Description").text,
        "interfaceSummary": required("IOVariables", "Description").text,
        "topics": [item.attrib for item in module.findall(f"{tag('IOVariables')}/{tag('Variable')}")],
        "servicesAndActions": [item.attrib for item in module.findall(f"{tag('Services')}/{tag('Service')}")],
        "parameters": parameters,
        "distributionNote": required("Infra", "Requirement").text,
        "launch": None if launch is None else {
            "command": required("ExecutableForm", "Command").text,
            "arguments": [item.text for item in module.findall(f"{tag('ExecutableForm')}/{tag('Argument')}")],
        },
        "source": {
            "profilePath": path.relative_to(ROOT).as_posix(),
            "profileSha256": sha256(data),
            **({"report": report.text, "reportSha256": report.attrib["sha256"],
                "reportRow": int(report.attrib["row"])} if report is not None else {}),
            "urls": [item.text for item in module.findall(f"{tag('Evidence')}/{tag('Source')}")],
            **({"upstreamSource": {"url": upstream.text, "status": upstream.attrib["status"]}}
               if upstream is not None else {}),
            **({"implementationUrl": implementation_url} if implementation_url else {}),
            **({"additionalImplementationUrls": sources} if (sources := [
                item.text for item in module.findall(
                    f"{tag('Evidence')}/{tag('AdditionalImplementationSource')}")
            ]) else {}),
            **({"reviewNote": review_note} if review_note else {}),
        },
        "profile": {
            "targetStandard": STANDARD,
            "namespace": NAMESPACE,
            "version": module.attrib["profileVersion"],
            "conformanceStatus": module.attrib["conformanceStatus"],
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--report", type=Path, help="Import the original Markdown report before rebuilding")
    mode.add_argument("--check", action="store_true", help="Verify the catalog matches the XML profiles")
    args = parser.parse_args()
    if args.report:
        entries, digest = read_report(args.report)
        if digest != "a8ac313c49c6b958a86bc11474c8a694c69f7968c10bd8d71edd93c87c2f93b6":
            parser.error("The English metadata is specific to the original report revision")
        categories, translations = read_english_metadata()
        review = json.loads((PROFILE_DIR / "upstream-review.json").read_bytes())
        profiles = dict(profile_document(entry, args.report.name, digest, categories, translations, review)
                        for entry in entries)
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        for name, content in profiles.items():
            (PROFILE_DIR / name).write_bytes(content)
    profiles = [read_profile(path) for path in PROFILE_DIR.glob("*.xml")]
    report_nodes = sorted((node for node in profiles if "reportRow" in node["source"]),
                          key=lambda node: node["source"]["reportRow"])
    standalone_nodes = sorted((node for node in profiles if "reportRow" not in node["source"]),
                              key=lambda node: node["catalogId"])
    nodes = report_nodes + standalone_nodes
    if [node["source"]["reportRow"] for node in report_nodes] != list(range(1, 101)):
        parser.error("Expected a complete set of report rows 1 through 100")
    for key in ("catalogId", "moduleId"):
        if len({node[key] for node in nodes}) != len(nodes):
            parser.error(f"Duplicate {key} in XML profiles")
    if len({node["source"]["reportSha256"] for node in report_nodes}) != 1:
        parser.error("XML profiles refer to different report revisions")
    catalog = {"schemaVersion": "1.0", "catalogKind": "ros2-nodes", "nodes": nodes}
    content = (json.dumps(catalog, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if args.check:
        if not CATALOG.is_file() or CATALOG.read_bytes().replace(b"\r\n", b"\n") != content:
            parser.error("ROS 2 catalog does not match the XML profiles")
    else:
        CATALOG.write_bytes(content)
    print(f"ROS 2 catalog: {len(nodes)} profiles ({'checked' if args.check else 'generated'})")


if __name__ == "__main__":
    main()

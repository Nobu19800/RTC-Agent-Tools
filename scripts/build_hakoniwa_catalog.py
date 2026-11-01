#!/usr/bin/env python3
"""Generate a local Hakoniwa asset catalog from the explicitly local XML mapping."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = "urn:hakoniwa:iso22166-202:mapping:0.1"
NS = {"h": NAMESPACE}
PROFILE_DIR = Path("profiles/iso22166-202/drone-three-point")


def text(node, path):
    return node.findtext(path, default="", namespaces=NS).strip()


def records(node, path):
    return [dict(element.attrib, description=(element.text or "").strip())
            for element in node.findall(path, NS)]


def texts(node, path):
    return [(element.text or "").strip() for element in node.findall(path, NS)]


def named_values(node, path):
    result = {}
    for element in node.findall(path, NS):
        key = element.attrib["name"]
        if key in result:
            raise ValueError("duplicate named value: " + key)
        result[key] = (element.text or "").strip()
    return result


def asset_from_xml(path, source_root):
    raw = path.read_bytes()
    module = ET.fromstring(raw)
    if module.tag != "{%s}Module" % NAMESPACE:
        raise ValueError("unsupported XML mapping: " + str(path))
    asset_id = path.stem
    module_id = text(module, "h:IDnType/h:ID")
    name = text(module, "h:GenInfo/h:ModuleName")
    if not module_id or not name:
        raise ValueError("module ID and name required: " + str(path))
    variables, ports = [], []
    seen = set()
    for element in module.findall("h:IOVariables/h:Variable", NS):
        variable = dict(element.attrib)
        var_id = variable["id"]
        if var_id in seen:
            raise ValueError("duplicate variable: " + var_id)
        seen.add(var_id)
        variable["description"] = text(element, "h:Description")
        variable["fields"] = records(element, "h:Field")
        if "channel" in variable:
            variable["channelId"] = int(variable.pop("channel"))
            if variable["channelId"] < 0:
                raise ValueError("negative channel: " + var_id)
        if "capacityBytes" in variable:
            variable["capacityBytes"] = int(variable["capacityBytes"])
            if variable["capacityBytes"] <= 0:
                raise ValueError("nonpositive capacity: " + var_id)
        directions = {"input": ["in"], "output": ["out"], "inout": ["in", "out"]}
        if variable["direction"] not in directions:
            raise ValueError("invalid direction: " + var_id)
        variables.append(variable)
        for direction in directions[variable["direction"]]:
            port = {key: value for key, value in variable.items() if key not in ("id", "direction")}
            port_id = var_id + "-" + direction if variable["direction"] == "inout" else var_id
            port.update(id=port_id, name=port_id, portType="data", direction=direction,
                        sourceVariableId=var_id, sourceDirection=variable["direction"])
            ports.append(port)
    executable = module.find("h:ExecutableForm", NS)
    if executable is None:
        raise ValueError("ExecutableForm missing: " + str(path))
    return {
        "catalogId": "hakoniwa.drone-three-point." + asset_id,
        "id": asset_id,
        "moduleId": module_id,
        "moduleKind": "hakoniwa",
        "componentName": name,
        "description": text(module, "h:GenInfo/h:Description"),
        "manufacturer": text(module, "h:GenInfo/h:Manufacturer"),
        "examples": text(module, "h:GenInfo/h:Examples"),
        "profile": dict(module.attrib, namespace=NAMESPACE,
                        informationModelVersion=text(module, "h:IDnType/h:InformationModelVersion"),
                        identifierPolicy=text(module, "h:IDnType/h:IdentifierPolicy")),
        "source": {"repository": "RTC-Agent-Tools",
                   "path": path.relative_to(source_root).as_posix(),
                   "sha256": hashlib.sha256(raw).hexdigest()},
        "catalogReferences": records(module, "h:CatalogReferences/h:CatalogReference"),
        "properties": named_values(module, "h:ModuleProp/h:Property"),
        "ioVariables": variables,
        "ports": ports,
        "status": {"description": text(module, "h:Status/h:Description"),
                   "states": texts(module, "h:Status/h:State")},
        "services": records(module, "h:Services/h:Service"),
        "requirements": texts(module, "h:Infra/h:Requirement"),
        "constraints": texts(module, "h:SafeSecure/h:Constraint"),
        "modelling": text(module, "h:Modelling/h:Description"),
        "executable": {"command": text(executable, "h:Command"),
                       "arguments": texts(executable, "h:Argument"),
                       "workingDirectory": text(executable, "h:WorkingDirectory"),
                       "environment": named_values(executable, "h:Environment"),
                       "pathReferences": named_values(executable, "h:PathReference"),
                       "dependencies": texts(executable, "h:Dependency")},
        "evidence": {"sources": records(module, "h:Evidence/h:Source"),
                     "verification": texts(module, "h:Evidence/h:Verification"),
                     "conformance": texts(module, "h:Evidence/h:Conformance")},
    }


def build(source_root):
    paths = sorted((source_root / PROFILE_DIR).glob("*.xml"))
    if not paths:
        raise ValueError("no XML profiles found under " + str(source_root / PROFILE_DIR))
    assets = [asset_from_xml(path, source_root) for path in paths]
    if len({asset["moduleId"] for asset in assets}) != len(assets):
        raise ValueError("duplicate module ID")
    return {
        "schemaVersion": "1.0",
        "catalogKind": "hakoniwa-assets",
        "description": "XML-derived integration profiles for the three-point simulated Drone composition.",
        "sourceRootReference": "${RTC_AGENT_TOOLS_ROOT}",
        "knowledgeRootReference": "${BUSINESS_PACK_ROOT}",
        "sourceDirectory": PROFILE_DIR.as_posix(),
        "scope": "Four local implementation profiles; not a complete product catalog or ISO certification.",
        "assets": assets,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=ROOT / "catalog/hakoniwa_catalog.json")
    parser.add_argument("--check", action="store_true", help="fail if the saved catalog differs from current XML")
    args = parser.parse_args()
    content = json.dumps(build(args.source_root.resolve()), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != content:
            parser.exit(1, "Catalog is missing or differs from source XML; regenerate it.\n")
        print("PASS: catalog matches source XML")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
        print("Created:", args.output)


if __name__ == "__main__":
    main()

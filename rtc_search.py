#!/usr/bin/env python3
"""
rtc_search.py

Search an RTC catalog and show:
- Component name
- Description
- Data ports
- Service ports
- RTC.xml URL

Supported catalog fields (flexible):
- rtcXmlContent
- rtcXmlUrl
- rawRtcXmlUrl
- repositoryUrl
- directoryUrl
- path
- name / componentName / rtcName
- description

Usage:
    python rtc_search.py rtc_catalog.json camera
    python rtc_search.py rtc_catalog.json "mobile robot"
    python rtc_search.py rtc_catalog.json --all
    python rtc_search.py rtc_catalog.json camera --json
"""

import argparse
import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional


def local_name(tag: str) -> str:
    """Return an XML tag name without namespace."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    if ":" in tag:
        return tag.split(":", 1)[1]
    return tag


def get_attr(elem: ET.Element, *names: str) -> Optional[str]:
    """Get an attribute by local name, ignoring XML namespaces/prefixes."""
    wanted = {n.lower() for n in names}
    for key, value in elem.attrib.items():
        key_local = local_name(key).lower()
        if key_local in wanted:
            return value
    return None


def fetch_text(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "rtc-search/1.0"}
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        data = response.read()
    return data.decode("utf-8", errors="replace")


def get_xml_text(entry: Dict[str, Any]) -> Optional[str]:
    content = entry.get("rtcXmlContent")
    if isinstance(content, str) and content.strip():
        return content

    for key in ("rawRtcXmlUrl", "rtcXmlUrl"):
        url = entry.get(key)
        if isinstance(url, str) and url.startswith(("http://", "https://")):
            try:
                # Convert normal GitHub blob URL to raw URL if needed.
                if "github.com/" in url and "/blob/" in url:
                    url = url.replace("https://github.com/", "https://raw.githubusercontent.com/")
                    url = url.replace("/blob/", "/")
                return fetch_text(url)
            except Exception:
                continue

    return None


def first_text(root: ET.Element, names: List[str]) -> Optional[str]:
    wanted = {n.lower() for n in names}
    for elem in root.iter():
        if local_name(elem.tag).lower() in wanted:
            text = (elem.text or "").strip()
            if text:
                return text
    return None


def first_attr(root: ET.Element, names: List[str]) -> Optional[str]:
    for elem in root.iter():
        value = get_attr(elem, *names)
        if value:
            return value.strip()
    return None


def parse_component_name(root: ET.Element, entry: Dict[str, Any]) -> str:
    for key in ("componentName", "rtcName", "name"):
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    value = first_attr(root, ["name", "componentName", "implementation_id"])
    if value:
        return value

    value = first_text(root, ["Name", "ComponentName", "ImplementationId"])
    if value:
        return value

    path = entry.get("path")
    if isinstance(path, str) and path:
        p = Path(path)
        if p.parent.name:
            return p.parent.name

    return "(unknown)"


def parse_description(root: ET.Element, entry: Dict[str, Any]) -> str:
    value = entry.get("description")
    if isinstance(value, str) and value.strip():
        return value.strip()

    value = first_attr(root, ["description"])
    if value:
        return value

    value = first_text(root, ["Description", "description"])
    if value:
        return value

    return ""


def parse_data_ports(root: ET.Element) -> List[Dict[str, str]]:
    ports: List[Dict[str, str]] = []
    seen = set()

    for elem in root.iter():
        tag = local_name(elem.tag).lower()

        # Common RTC Builder / RTC Profile tag names.
        if tag not in {
            "dataports", "dataport", "inport", "outport",
            "data_inport", "data_outport"
        }:
            continue

        name = (
            get_attr(elem, "name", "port_name")
            or first_text(elem, ["Name"])
            or ""
        )
        port_type = (
            get_attr(elem, "portType", "direction", "type")
            or ""
        )
        data_type = (
            get_attr(elem, "dataType", "datatype")
            or ""
        )

        # Some RTC profiles store type information in child elements.
        for child in elem.iter():
            ctag = local_name(child.tag).lower()
            text = (child.text or "").strip()
            if not text:
                continue
            if ctag in {"porttype", "direction"} and not port_type:
                port_type = text
            elif ctag in {"datatype", "data_type"} and not data_type:
                data_type = text
            elif ctag == "name" and not name:
                name = text

        direction = ""
        ptl = port_type.lower()
        tl = tag.lower()
        if "inport" in ptl or "inport" in tl or ptl in {"in", "input", "datainport"}:
            direction = "InPort"
        elif "outport" in ptl or "outport" in tl or ptl in {"out", "output", "dataoutport"}:
            direction = "OutPort"
        else:
            direction = port_type or "DataPort"

        if name or data_type:
            key = (name, direction, data_type)
            if key not in seen:
                seen.add(key)
                ports.append({
                    "name": name,
                    "direction": direction,
                    "dataType": data_type
                })

    return ports


def parse_service_ports(root: ET.Element) -> List[Dict[str, Any]]:
    services: List[Dict[str, Any]] = []
    seen = set()

    for elem in root.iter():
        tag = local_name(elem.tag).lower()
        if tag not in {
            "serviceports", "serviceport", "corbaport", "service_port"
        }:
            continue

        port_name = (
            get_attr(elem, "name", "port_name")
            or first_text(elem, ["Name"])
            or ""
        )

        interfaces = []
        for child in elem.iter():
            ctag = local_name(child.tag).lower()
            if ctag not in {
                "serviceinterface", "serviceinterfaces",
                "interface", "corbainterface"
            }:
                continue

            name = (
                get_attr(child, "name", "instanceName", "instance_name")
                or first_text(child, ["Name", "InstanceName"])
                or ""
            )
            interface_type = (
                get_attr(child, "type", "interfaceType", "interface_type")
                or first_text(child, ["Type", "InterfaceType"])
                or ""
            )
            direction = (
                get_attr(child, "direction", "polarity")
                or first_text(child, ["Direction", "Polarity"])
                or ""
            )

            dl = direction.lower()
            if dl in {"provided", "provider", "provides"}:
                direction = "Provider"
            elif dl in {"required", "consumer", "requires"}:
                direction = "Consumer"

            if name or interface_type or direction:
                interfaces.append({
                    "name": name,
                    "type": interface_type,
                    "direction": direction
                })

        key = (
            port_name,
            tuple(
                (i["name"], i["type"], i["direction"])
                for i in interfaces
            )
        )
        if key not in seen:
            seen.add(key)
            services.append({
                "name": port_name,
                "interfaces": interfaces
            })

    return services


def parse_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    xml_text = get_xml_text(entry)
    root = None
    parse_error = None

    if xml_text:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            parse_error = str(e)

    if root is not None:
        name = parse_component_name(root, entry)
        description = parse_description(root, entry)
        data_ports = parse_data_ports(root)
        service_ports = parse_service_ports(root)
    else:
        name = (
            entry.get("componentName")
            or entry.get("rtcName")
            or entry.get("name")
            or "(unknown)"
        )
        description = entry.get("description", "")
        data_ports = entry.get("dataPorts", [])
        service_ports = entry.get("servicePorts", [])

    return {
        "componentName": name,
        "description": description,
        "dataPorts": data_ports,
        "servicePorts": service_ports,
        "rtcXmlUrl": entry.get("rtcXmlUrl") or entry.get("rawRtcXmlUrl") or "",
        "repositoryUrl": entry.get("repositoryUrl", ""),
        "directoryUrl": entry.get("directoryUrl", ""),
        "path": entry.get("path", ""),
        "parseError": parse_error,
    }


def searchable_text(item: Dict[str, Any]) -> str:
    parts = [
        str(item.get("componentName", "")),
        str(item.get("description", "")),
        str(item.get("rtcXmlUrl", "")),
        str(item.get("repositoryUrl", "")),
        str(item.get("path", "")),
    ]

    for port in item.get("dataPorts", []):
        if isinstance(port, dict):
            parts.extend([
                str(port.get("name", "")),
                str(port.get("direction", "")),
                str(port.get("dataType", "")),
            ])

    for service in item.get("servicePorts", []):
        if not isinstance(service, dict):
            continue
        parts.append(str(service.get("name", "")))
        for interface in service.get("interfaces", []):
            if isinstance(interface, dict):
                parts.extend([
                    str(interface.get("name", "")),
                    str(interface.get("type", "")),
                    str(interface.get("direction", "")),
                ])

    return " ".join(parts).lower()


def matches(item: Dict[str, Any], query: str) -> bool:
    words = [w.lower() for w in query.split() if w.strip()]
    haystack = searchable_text(item)
    return all(word in haystack for word in words)


def print_human(item: Dict[str, Any], index: int) -> None:
    print(f"[{index}] {item['componentName']}")
    print(f"Description : {item['description'] or '-'}")

    print("Data Ports  :")
    if item["dataPorts"]:
        for port in item["dataPorts"]:
            if isinstance(port, dict):
                print(
                    f"  - {port.get('direction') or 'DataPort'} "
                    f"{port.get('name') or '(unnamed)'}"
                    f" : {port.get('dataType') or '(type unknown)'}"
                )
            else:
                print(f"  - {port}")
    else:
        print("  - None")

    print("Service Ports:")
    if item["servicePorts"]:
        for service in item["servicePorts"]:
            if not isinstance(service, dict):
                print(f"  - {service}")
                continue

            print(f"  - {service.get('name') or '(unnamed)'}")
            interfaces = service.get("interfaces", [])
            if interfaces:
                for interface in interfaces:
                    if isinstance(interface, dict):
                        direction = interface.get("direction") or "Interface"
                        name = interface.get("name") or "(unnamed)"
                        itype = interface.get("type") or "(type unknown)"
                        print(f"      {direction}: {name} : {itype}")
    else:
        print("  - None")

    print(f"RTC.xml URL : {item['rtcXmlUrl'] or '-'}")
    if item.get("repositoryUrl"):
        print(f"Repository  : {item['repositoryUrl']}")
    if item.get("path"):
        print(f"Path        : {item['path']}")
    if item.get("parseError"):
        print(f"Warning     : XML parse error: {item['parseError']}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Search an RTC catalog and show RTC metadata."
    )
    parser.add_argument(
        "catalog",
        help="Path to rtc_catalog.json"
    )
    parser.add_argument(
        "query",
        nargs="?",
        default="",
        help="Search words (AND search)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Show all RTCs"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    args = parser.parse_args()

    catalog_path = Path(args.catalog)
    if not catalog_path.exists():
        print(f"Error: catalog not found: {catalog_path}", file=sys.stderr)
        return 1

    try:
        data = json.loads(catalog_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Error: failed to read catalog: {e}", file=sys.stderr)
        return 1

    if isinstance(data, dict):
        if isinstance(data.get("rtcs"), list):
            entries = data["rtcs"]
        else:
            entries = [data]
    elif isinstance(data, list):
        entries = data
    else:
        print("Error: catalog must be a JSON object or array.", file=sys.stderr)
        return 1

    parsed = []
    for entry in entries:
        if isinstance(entry, dict):
            parsed.append(parse_entry(entry))

    if args.all:
        results = parsed
    else:
        if not args.query.strip():
            parser.error("Specify a search query or use --all")
        results = [item for item in parsed if matches(item, args.query)]

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(f"Found {len(results)} RTC(s).\n")
        for index, item in enumerate(results, start=1):
            print_human(item, index)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

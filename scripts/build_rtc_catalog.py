#!/usr/bin/env python3

import argparse
import base64
import json
import os
import sys
import urllib.parse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path


GITHUB_API = "https://api.github.com"
OUTPUT_FILE = Path("catalog/rtc_catalog.json")

TOKEN = os.environ.get("GITHUB_TOKEN", "")

HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "rtc-catalog-builder",
    "X-GitHub-Api-Version": "2022-11-28",
}

if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"


def github_api(url):
    request = urllib.request.Request(
        url,
        headers=HEADERS,
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=30,
        ) as response:
            return json.load(response)

    except urllib.error.HTTPError as e:
        print(
            f"GitHub API error: {e.code} {e.reason}",
            file=sys.stderr,
        )

        try:
            body = e.read().decode("utf-8")
            print(body, file=sys.stderr)
        except Exception:
            pass

        raise


def local_name(name):
    if "}" in name:
        return name.split("}", 1)[1]

    if ":" in name:
        return name.split(":", 1)[1]

    return name


def get_attribute(element, name):
    target = name.lower()

    for key, value in element.attrib.items():
        key_name = local_name(key).lower()

        if key_name == target:
            return value

    return None


def search_rtc_xml():
    query = 'filename:RTC.xml'

    encoded_query = urllib.parse.quote(query)

    url = (
        f"{GITHUB_API}/search/code"
        f"?q={encoded_query}"
        f"&per_page=100"
        f"&page=1"
    )

    print("Searching GitHub for RTC.xml ...")

    data = github_api(url)

    print(
        "GitHub search result count:",
        data.get("total_count", 0),
    )

    return data.get("items", [])


def get_file_content(item):
    api_url = item["url"]

    data = github_api(api_url)

    encoding = data.get("encoding")
    content = data.get("content")

    if encoding == "base64" and content:

        decoded = base64.b64decode(content)

        return decoded.decode(
            "utf-8",
            errors="replace",
        )

    download_url = data.get("download_url")

    if download_url:

        request = urllib.request.Request(
            download_url,
            headers={
                "User-Agent": "rtc-catalog-builder",
            },
        )

        with urllib.request.urlopen(
            request,
            timeout=30,
        ) as response:

            return response.read().decode(
                "utf-8",
                errors="replace",
            )

    raise RuntimeError(
        "RTC.xml content could not be retrieved"
    )


def parse_basic_info(root):
    result = {
        "componentName": "",
        "description": "",
        "category": "",
        "vendor": "",
        "version": "",
    }

    for element in root.iter():

        if local_name(element.tag).lower() != "basicinfo":
            continue

        name = get_attribute(element, "name")

        if name:
            result["componentName"] = name

        description = get_attribute(
            element,
            "description",
        )

        if description:
            result["description"] = description

        category = get_attribute(
            element,
            "category",
        )

        if category:
            result["category"] = category

        vendor = get_attribute(
            element,
            "vendor",
        )

        if vendor:
            result["vendor"] = vendor

        version = get_attribute(
            element,
            "version",
        )

        if version:
            result["version"] = version

        break

    return result


def normalize_data_type(value):
    if not value:
        return ""

    return value.strip()


def detect_port_direction(element):
    tag = local_name(
        element.tag
    ).lower()

    if "inport" in tag:
        return "InPort"

    if "outport" in tag:
        return "OutPort"

    port_type = (
        get_attribute(
            element,
            "portType",
        )
        or get_attribute(
            element,
            "direction",
        )
        or ""
    )

    lower = port_type.lower()

    if "inport" in lower:
        return "InPort"

    if "outport" in lower:
        return "OutPort"

    if lower in (
        "in",
        "input",
    ):
        return "InPort"

    if lower in (
        "out",
        "output",
    ):
        return "OutPort"

    return "DataPort"


def parse_data_ports(root):
    ports = []
    seen = set()

    valid_tags = {
        "dataports",
        "dataport",
        "inport",
        "outport",
        "data_inport",
        "data_outport",
    }

    for element in root.iter():

        tag = local_name(
            element.tag
        ).lower()

        if tag not in valid_tags:
            continue

        name = (
            get_attribute(
                element,
                "name",
            )
            or ""
        )

        data_type = (
            get_attribute(
                element,
                "dataType",
            )
            or get_attribute(
                element,
                "datatype",
            )
            or ""
        )

        direction = detect_port_direction(
            element
        )

        for child in element.iter():

            child_tag = local_name(
                child.tag
            ).lower()

            text = (
                child.text or ""
            ).strip()

            if child_tag == "name":

                if text and not name:
                    name = text

            elif child_tag in (
                "datatype",
                "data_type",
            ):

                if text and not data_type:
                    data_type = text

            elif child_tag in (
                "properties",
                "property",
            ):

                property_name = (
                    get_attribute(
                        child,
                        "name",
                    )
                    or ""
                )

                property_value = (
                    get_attribute(
                        child,
                        "value",
                    )
                    or ""
                )

                property_name_lower = (
                    property_name
                    .strip()
                    .lower()
                )

                if property_name_lower in (
                    "dataport.data_type",
                    "dataport.datatype",
                    "data_type",
                    "datatype",
                ):

                    if property_value:
                        data_type = property_value

                elif property_name_lower in (
                    "port.port_type",
                    "dataport.port_type",
                    "port_type",
                ):

                    direction_value = (
                        property_value
                        .strip()
                        .lower()
                    )

                    if "inport" in direction_value:
                        direction = "InPort"

                    elif "outport" in direction_value:
                        direction = "OutPort"

        data_type = normalize_data_type(
            data_type
        )

        if not name:
            continue

        key = (
            name,
            direction,
            data_type,
        )

        if key in seen:
            continue

        seen.add(key)

        ports.append(
            {
                "name": name,
                "direction": direction,
                "dataType": data_type,
            }
        )

    return ports


def normalize_service_direction(value):
    lower = value.lower()

    if lower in (
        "provided",
        "provider",
        "provides",
    ):
        return "Provider"

    if lower in (
        "required",
        "consumer",
        "requires",
    ):
        return "Consumer"

    return value


def parse_service_ports(root):
    service_ports = []

    valid_port_tags = {
        "serviceports",
        "serviceport",
        "corbaport",
        "service_port",
    }

    valid_interface_tags = {
        "serviceinterface",
        "serviceinterfaces",
        "interface",
        "corbainterface",
    }

    for element in root.iter():

        tag = local_name(
            element.tag
        ).lower()

        if tag not in valid_port_tags:
            continue

        port_name = (
            get_attribute(
                element,
                "name",
            )
            or ""
        )

        interfaces = []

        for child in element.iter():

            child_tag = local_name(
                child.tag
            ).lower()

            if child_tag not in valid_interface_tags:
                continue

            interface_name = (
                get_attribute(
                    child,
                    "name",
                )
                or get_attribute(
                    child,
                    "instanceName",
                )
                or get_attribute(
                    child,
                    "instance_name",
                )
                or ""
            )

            interface_type = (
                get_attribute(
                    child,
                    "type",
                )
                or get_attribute(
                    child,
                    "interfaceType",
                )
                or get_attribute(
                    child,
                    "interface_type",
                )
                or ""
            )

            direction = (
                get_attribute(
                    child,
                    "direction",
                )
                or get_attribute(
                    child,
                    "polarity",
                )
                or ""
            )

            direction = normalize_service_direction(
                direction
            )

            if (
                interface_name
                or interface_type
                or direction
            ):

                interfaces.append(
                    {
                        "name": interface_name,
                        "type": interface_type,
                        "direction": direction,
                    }
                )

        if not port_name and not interfaces:
            continue

        service_ports.append(
            {
                "name": port_name,
                "interfaces": interfaces,
            }
        )

    return service_ports


def parse_language(root):
    for element in root.iter():

        tag = local_name(
            element.tag
        ).lower()

        if tag != "language":
            continue

        value = (
            get_attribute(
                element,
                "kind",
            )
            or get_attribute(
                element,
                "name",
            )
            or (
                element.text or ""
            ).strip()
        )

        if value:
            return value

    return ""


def parse_rtc_xml(xml_text):
    root = ET.fromstring(
        xml_text
    )

    basic = parse_basic_info(
        root
    )

    rtc = {
        **basic,

        "language": parse_language(
            root
        ),

        "dataPorts": parse_data_ports(
            root
        ),

        "servicePorts": parse_service_ports(
            root
        ),
    }

    return rtc


def is_valid_rtc(rtc):
    name = rtc.get(
        "componentName",
        "",
    ).strip()

    if not name:
        return False

    return True


def build_directory_url(
    repository_url,
    path,
    default_branch,
):
    parent = str(
        Path(path).parent
    )

    if parent == ".":
        return repository_url

    return (
        f"{repository_url}/tree/"
        f"{default_branch}/"
        f"{parent}"
    )


def get_repository_info(item):
    repository = item["repository"]

    repository_url = repository[
        "html_url"
    ]

    repository_api_url = repository.get(
        "url"
    )

    default_branch = "main"

    if repository_api_url:

        try:

            repo_data = github_api(
                repository_api_url
            )

            default_branch = repo_data.get(
                "default_branch",
                "main",
            )

        except Exception:

            pass

    return (
        repository_url,
        default_branch,
    )


def create_catalog_entry(
    item,
    rtc,
):
    (
        repository_url,
        default_branch,
    ) = get_repository_info(
        item
    )

    path = item["path"]

    directory_url = build_directory_url(
        repository_url,
        path,
        default_branch,
    )

    entry = {
        "componentName": rtc.get(
            "componentName",
            "",
        ),

        "description": rtc.get(
            "description",
            "",
        ),

        "category": rtc.get(
            "category",
            "",
        ),

        "vendor": rtc.get(
            "vendor",
            "",
        ),

        "version": rtc.get(
            "version",
            "",
        ),

        "language": rtc.get(
            "language",
            "",
        ),

        "dataPorts": rtc.get(
            "dataPorts",
            [],
        ),

        "servicePorts": rtc.get(
            "servicePorts",
            [],
        ),

        "repositoryUrl": repository_url,

        "directoryUrl": directory_url,

        "path": path,

        "rtcXmlUrl": item.get(
            "html_url",
            "",
        ),
    }

    return entry


def save_catalog(catalog):
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    data = {
        "schemaVersion": "1.0",
        "rtcs": catalog,
    }

    OUTPUT_FILE.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print(
        f"Catalog written to: "
        f"{OUTPUT_FILE}"
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Search GitHub for RTC.xml and "
            "build an RT-Component catalog."
        )
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Stop after finding this number "
            "of valid RT-Components."
        ),
    )

    args = parser.parse_args()

    if args.limit is not None:
        if args.limit <= 0:
            parser.error(
                "--limit must be greater than 0"
            )

    if not TOKEN:

        print(
            "Warning: GITHUB_TOKEN is not set.",
            file=sys.stderr,
        )

        print(
            "Unauthenticated GitHub API "
            "requests have stricter limits.",
            file=sys.stderr,
        )

    items = search_rtc_xml()

    catalog = []

    processed = 0
    skipped = 0

    seen = set()

    for item in items:

        repository_url = (
            item["repository"]["html_url"]
        )

        path = item["path"]

        unique_key = (
            repository_url,
            path,
        )

        if unique_key in seen:
            continue

        seen.add(
            unique_key
        )

        processed += 1

        print()
        print(
            f"Checking: "
            f"{repository_url}/{path}"
        )

        try:

            xml_text = get_file_content(
                item
            )

            rtc = parse_rtc_xml(
                xml_text
            )

            if not is_valid_rtc(
                rtc
            ):

                skipped += 1

                print(
                    "  Skip: "
                    "not recognized as RTC Profile"
                )

                continue

            entry = create_catalog_entry(
                item,
                rtc,
            )

            catalog.append(
                entry
            )

            print(
                f"  [{len(catalog)}] "
                f"{entry['componentName']}"
            )

            print(
                f"      DataPorts:"
            )

            if entry["dataPorts"]:

                for port in entry[
                    "dataPorts"
                ]:

                    print(
                        "        "
                        f"{port['direction']} "
                        f"{port['name']} : "
                        f"{port['dataType']}"
                    )

            else:

                print(
                    "        None"
                )

            print(
                "      ServicePorts: "
                f"{len(entry['servicePorts'])}"
            )

            if (
                args.limit is not None
                and len(catalog) >= args.limit
            ):

                print()
                print(
                    "Test limit reached: "
                    f"{args.limit} RTCs"
                )

                break

        except ET.ParseError as e:

            skipped += 1

            print(
                f"  Skip: "
                f"XML parse error: {e}"
            )

        except Exception as e:

            skipped += 1

            print(
                f"  Skip: {e}"
            )

    save_catalog(
        catalog
    )

    print()

    print(
        "Summary"
    )

    print(
        "-------"
    )

    print(
        f"Processed files : "
        f"{processed}"
    )

    print(
        f"Valid RTCs      : "
        f"{len(catalog)}"
    )

    print(
        f"Skipped files   : "
        f"{skipped}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
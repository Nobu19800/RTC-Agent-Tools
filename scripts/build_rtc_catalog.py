#!/usr/bin/env python3

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


GITHUB_API = "https://api.github.com"
OUTPUT_FILE = Path("catalog/rtc_catalog.json")

RTC_NS = "http://www.openrtp.org/namespaces/rtc"
RTC_EXT_NS = "http://www.openrtp.org/namespaces/rtc_ext"

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


def get_attr(elem, name):
    """
    Get an attribute.

    If a namespace-qualified name is specified,
    ElementTree's elem.get() is used directly.

    Otherwise, attributes are searched by local name.
    """

    if name.startswith("{"):
        return elem.get(name)

    target = name.lower()

    for key, value in elem.attrib.items():
        if local_name(key).lower() == target:
            return value

    return elem.get(name)


def rtc_attr(elem, name):
    """
    Get an attribute specifically from the rtc namespace.
    """

    return elem.get(
        f"{{{RTC_NS}}}{name}"
    )


def search_rtc_xml():
    """
    Search GitHub for RTC.xml.

    This test version retrieves up to 100 files
    from the first search result page.
    """

    query = "filename:RTC.xml"

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
    """
    Download RTC.xml through GitHub Contents API.
    """

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
    """
    Parse RTC BasicInfo.
    """

    result = {
        "componentName": "",
        "description": "",
        "category": "",
        "vendor": "",
        "version": "",
    }

    for elem in root.iter():

        if local_name(elem.tag).lower() != "basicinfo":
            continue

        result["componentName"] = (
            rtc_attr(elem, "name")
            or get_attr(elem, "name")
            or ""
        )

        result["description"] = (
            rtc_attr(elem, "description")
            or get_attr(elem, "description")
            or ""
        )

        result["category"] = (
            rtc_attr(elem, "category")
            or get_attr(elem, "category")
            or ""
        )

        result["vendor"] = (
            rtc_attr(elem, "vendor")
            or get_attr(elem, "vendor")
            or ""
        )

        result["version"] = (
            rtc_attr(elem, "version")
            or get_attr(elem, "version")
            or ""
        )

        break

    return result


def get_port_type(elem):
    """
    Get rtc:portType exactly as written in RTC.xml.

    Examples:
        DataInPort
        DataOutPort
    """

    return (
        rtc_attr(elem, "portType")
        or ""
    ).strip()


def get_data_type(elem):
    """
    Get rtc:type exactly as written in RTC.xml.

    xsi:type is intentionally ignored.
    """

    return (
        rtc_attr(elem, "type")
        or ""
    ).strip()


def parse_data_ports(root):
    """
    Parse DataPorts.

    Output example:

        {
            "name": "target_velocity_in",
            "portType": "DataInPort",
            "dataType": "RTC::TimedVelocity2D"
        }
    """

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

    for elem in root.iter():

        if (
            local_name(elem.tag).lower()
            not in valid_tags
        ):
            continue

        name = (
            rtc_attr(elem, "name")
            or get_attr(elem, "name")
            or ""
        )

        port_type = get_port_type(elem)
        data_type = get_data_type(elem)

        if not name:
            continue

        key = (
            name,
            port_type,
            data_type,
        )

        if key in seen:
            continue

        seen.add(key)

        ports.append(
            {
                "name": name,
                "portType": port_type,
                "dataType": data_type,
            }
        )

    return ports


def normalize_service_direction(value):
    value = (value or "").strip()

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


def get_property_value(elem, property_names):
    """
    Search descendant Properties / Property elements.

    Example:
        <rtcExt:Properties
            rtcExt:name="interface_type"
            rtcExt:value="MyService"/>
    """

    property_names = {
        name.lower()
        for name in property_names
    }

    for child in elem.iter():

        tag = local_name(
            child.tag
        ).lower()

        if tag not in (
            "properties",
            "property",
        ):
            continue

        prop_name = (
            get_attr(
                child,
                "name",
            )
            or ""
        ).strip().lower()

        prop_value = (
            get_attr(
                child,
                "value",
            )
            or ""
        ).strip()

        if (
            prop_name in property_names
            and prop_value
        ):
            return prop_value

    return ""


def get_service_interface_name(elem):
    """
    Get service interface instance/name.
    """

    return (
        rtc_attr(elem, "instanceName")
        or rtc_attr(elem, "name")
        or get_attr(elem, "instanceName")
        or get_attr(elem, "instance_name")
        or get_attr(elem, "name")
        or get_property_value(
            elem,
            {
                "instance_name",
                "interface.instance_name",
                "service.instance_name",
            },
        )
        or ""
    ).strip()


def get_service_interface_type(elem):
    """
    Get the actual service interface type.

    Try explicit RTC attributes first and then
    extension Properties.

    Generic xsi:type is not used.
    """

    value = (
        rtc_attr(elem, "type")
        or rtc_attr(elem, "interfaceType")
        or get_property_value(
            elem,
            {
                "interface_type",
                "interfacetype",
                "service.interface_type",
                "service.interface.type",
                "interface.type",
            },
        )
        or ""
    )

    return value.strip()


def get_service_interface_direction(elem):
    """
    Get Provider / Consumer direction.
    """

    value = (
        rtc_attr(elem, "direction")
        or rtc_attr(elem, "polarity")
        or get_attr(elem, "direction")
        or get_attr(elem, "polarity")
        or get_property_value(
            elem,
            {
                "direction",
                "polarity",
                "interface.direction",
                "service.interface.direction",
            },
        )
        or ""
    )

    return normalize_service_direction(
        value
    )


def parse_service_ports(root):
    """
    Parse ServicePorts and their interfaces.

    Supports interface information stored as:

        rtc:name
        rtc:instanceName
        rtc:type
        rtc:interfaceType
        rtc:direction
        rtc:polarity

    and selected Properties representations.
    """

    service_ports = []
    seen_ports = set()

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

    for elem in root.iter():

        tag = local_name(
            elem.tag
        ).lower()

        if tag not in valid_port_tags:
            continue

        port_name = (
            rtc_attr(elem, "name")
            or get_attr(elem, "name")
            or ""
        ).strip()

        interfaces = []
        seen_interfaces = set()

        for child in elem.iter():

            if child is elem:
                continue

            child_tag = local_name(
                child.tag
            ).lower()

            if (
                child_tag
                not in valid_interface_tags
            ):
                continue

            interface_name = (
                get_service_interface_name(
                    child
                )
            )

            interface_type = (
                get_service_interface_type(
                    child
                )
            )

            interface_direction = (
                get_service_interface_direction(
                    child
                )
            )

            if not (
                interface_name
                or interface_type
                or interface_direction
            ):
                continue

            interface_key = (
                interface_name,
                interface_type,
                interface_direction,
            )

            if (
                interface_key
                in seen_interfaces
            ):
                continue

            seen_interfaces.add(
                interface_key
            )

            interfaces.append(
                {
                    "name": interface_name,
                    "type": interface_type,
                    "direction": interface_direction,
                }
            )

        if (
            not port_name
            and not interfaces
        ):
            continue

        port_key = (
            port_name,
            tuple(
                (
                    interface["name"],
                    interface["type"],
                    interface["direction"],
                )
                for interface in interfaces
            ),
        )

        if port_key in seen_ports:
            continue

        seen_ports.add(
            port_key
        )

        service_ports.append(
            {
                "name": port_name,
                "interfaces": interfaces,
            }
        )

    return service_ports


def parse_language(root):
    """
    Parse implementation language.
    """

    for elem in root.iter():

        if (
            local_name(elem.tag).lower()
            != "language"
        ):
            continue

        value = (
            rtc_attr(elem, "kind")
            or rtc_attr(elem, "name")
            or get_attr(elem, "kind")
            or get_attr(elem, "name")
            or (
                elem.text or ""
            ).strip()
        )

        if value:
            return value

    return ""


def parse_rtc_xml(xml_text):
    """
    Parse one RTC.xml.
    """

    root = ET.fromstring(
        xml_text
    )

    basic = parse_basic_info(
        root
    )

    return {
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


def is_valid_rtc(rtc):
    """
    Check whether parsed XML looks like an RTC Profile.
    """

    component_name = (
        rtc.get(
            "componentName",
            "",
        )
        .strip()
    )

    return bool(component_name)


def get_repository_info(item):
    """
    Get repository URL and default branch.
    """

    repository = item[
        "repository"
    ]

    repository_url = repository[
        "html_url"
    ]

    repository_api_url = repository.get(
        "url"
    )

    default_branch = repository.get(
        "default_branch"
    )

    if (
        not default_branch
        and repository_api_url
    ):

        try:

            repo_data = github_api(
                repository_api_url
            )

            default_branch = (
                repo_data.get(
                    "default_branch"
                )
            )

        except Exception as e:

            print(
                "  Warning: could not get "
                f"default branch: {e}"
            )

    if not default_branch:
        default_branch = "main"

    return (
        repository_url,
        default_branch,
    )


def build_directory_url(
    repository_url,
    path,
    default_branch,
):
    """
    Build GitHub URL of directory containing RTC.xml.
    """

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


def create_catalog_entry(
    item,
    rtc,
):
    """
    Add GitHub metadata to parsed RTC information.
    """

    (
        repository_url,
        default_branch,
    ) = get_repository_info(
        item
    )

    path = item["path"]

    directory_url = (
        build_directory_url(
            repository_url,
            path,
            default_branch,
        )
    )

    return {
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


def save_catalog(catalog):
    """
    Save RTC catalog.
    """

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


def print_rtc(entry, index):
    """
    Print parsed information to GitHub Actions log.
    """

    print(
        f"  [{index}] "
        f"{entry['componentName']}"
    )

    if entry["description"]:

        print(
            f"      Description: "
            f"{entry['description']}"
        )

    print(
        "      DataPorts:"
    )

    if entry["dataPorts"]:

        for port in entry[
            "dataPorts"
        ]:

            port_type = (
                port.get(
                    "portType"
                )
                or "(unknown)"
            )

            data_type = (
                port.get(
                    "dataType"
                )
                or "(unknown)"
            )

            print(
                "        "
                f"{port_type} "
                f"{port['name']} : "
                f"{data_type}"
            )

    else:

        print(
            "        None"
        )

    print(
        "      ServicePorts:"
    )

    if entry["servicePorts"]:

        for port in entry[
            "servicePorts"
        ]:

            print(
                f"        "
                f"{port['name']}"
            )

            for interface in port.get(
                "interfaces",
                [],
            ):

                interface_name = (
                    interface.get(
                        "name"
                    )
                    or "(unnamed)"
                )

                interface_type = (
                    interface.get(
                        "type"
                    )
                    or "(unknown)"
                )

                interface_direction = (
                    interface.get(
                        "direction"
                    )
                    or "(unknown)"
                )

                print(
                    "          "
                    f"{interface_direction} "
                    f"{interface_name} : "
                    f"{interface_type}"
                )

    else:

        print(
            "        None"
        )

    print(
        f"      RTC.xml: "
        f"{entry['rtcXmlUrl']}"
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

    if (
        args.limit is not None
        and args.limit <= 0
    ):
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
            item[
                "repository"
            ][
                "html_url"
            ]
        )

        path = item[
            "path"
        ]

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

            xml_text = (
                get_file_content(
                    item
                )
            )

            rtc = (
                parse_rtc_xml(
                    xml_text
                )
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

            entry = (
                create_catalog_entry(
                    item,
                    rtc,
                )
            )

            catalog.append(
                entry
            )

            print_rtc(
                entry,
                len(catalog),
            )

            if (
                args.limit is not None
                and len(catalog)
                >= args.limit
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
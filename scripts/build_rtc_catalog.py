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
    """
    Remove XML namespace or prefix.

    Examples:
        {namespace}DataPorts -> DataPorts
        rtc:DataPorts       -> DataPorts
    """

    if "}" in name:
        return name.split("}", 1)[1]

    if ":" in name:
        return name.split(":", 1)[1]

    return name


def get_attribute(element, name):
    """
    Get an XML attribute while ignoring namespaces.

    Example:
        rtc:name
        {namespace}name
        name

    are all treated as "name".
    """

    target = name.lower()

    for key, value in element.attrib.items():

        key_name = local_name(key).lower()

        if key_name == target:
            return value

    return None


def search_rtc_xml():
    """
    Search GitHub for files named RTC.xml.

    This test version retrieves the first 100 search results.
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
    Parse BasicInfo element.
    """

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

        name = get_attribute(
            element,
            "name",
        )

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
    """
    Normalize a DataPort data type.

    Do not automatically add RTC:: because RTC.xml may use
    user-defined IDL types or another namespace.
    """

    if not value:
        return ""

    return value.strip()


def detect_port_direction(element):
    """
    Detect InPort / OutPort from RTC Profile attributes.
    """

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

    value = port_type.strip().lower()

    if "datainport" in value:
        return "InPort"

    if "dataoutport" in value:
        return "OutPort"

    if "inport" in value:
        return "InPort"

    if "outport" in value:
        return "OutPort"

    if value in (
        "in",
        "input",
    ):
        return "InPort"

    if value in (
        "out",
        "output",
    ):
        return "OutPort"

    return "DataPort"


def parse_data_ports(root):
    """
    Parse RTC DataPorts.

    Supported examples include:

        <rtc:DataPorts
            rtc:name="target_angle"
            rtc:portType="DataInPort"
            rtc:type="RTC::TimedDoubleSeq">

    and:

        <rtcExt:Properties
            rtcExt:name="dataport.data_type"
            rtcExt:value="RTC::TimedDoubleSeq">
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

        #
        # RTC Profile commonly stores the data type
        # in the "type" attribute.
        #
        data_type = (
            get_attribute(
                element,
                "dataType",
            )
            or get_attribute(
                element,
                "datatype",
            )
            or get_attribute(
                element,
                "data_type",
            )
            or get_attribute(
                element,
                "type",
            )
            or ""
        )

        direction = detect_port_direction(
            element
        )

        #
        # Search child elements and extension properties.
        #
        for child in element.iter():

            if child is element:
                continue

            child_tag = local_name(
                child.tag
            ).lower()

            text = (
                child.text or ""
            ).strip()

            #
            # Child <Name>
            #
            if child_tag == "name":

                if text and not name:
                    name = text

            #
            # Child <DataType> / <Type>
            #
            elif child_tag in (
                "datatype",
                "data_type",
                "type",
            ):

                if text and not data_type:
                    data_type = text

            #
            # RTC Builder extension properties
            #
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
                    "type",
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

                    if (
                        "datainport"
                        in direction_value
                        or "inport"
                        in direction_value
                    ):
                        direction = "InPort"

                    elif (
                        "dataoutport"
                        in direction_value
                        or "outport"
                        in direction_value
                    ):
                        direction = "OutPort"

        #
        # Some profiles may store information in rtcDoc:Doc.
        #
        if not data_type:

            for child in element.iter():

                child_tag = local_name(
                    child.tag
                ).lower()

                if child_tag != "doc":
                    continue

                doc_type = (
                    get_attribute(
                        child,
                        "type",
                    )
                    or get_attribute(
                        child,
                        "dataType",
                    )
                    or ""
                )

                if doc_type:
                    data_type = doc_type
                    break

        data_type = normalize_data_type(
            data_type
        )

        #
        # A port without a name is not useful for the catalog.
        #
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
    """
    Normalize service interface direction.
    """

    value = value.strip()

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
    """
    Parse ServicePorts and service interfaces.
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
        seen_interfaces = set()

        for child in element.iter():

            if child is element:
                continue

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

            if not (
                interface_name
                or interface_type
                or direction
            ):
                continue

            interface_key = (
                interface_name,
                interface_type,
                direction,
            )

            if interface_key in seen_interfaces:
                continue

            seen_interfaces.add(
                interface_key
            )

            interfaces.append(
                {
                    "name": interface_name,
                    "type": interface_type,
                    "direction": direction,
                }
            )

        if not port_name and not interfaces:
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
    """
    Parse one RTC.xml.
    """

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
    """
    Determine whether the XML is likely an RTC Profile.
    """

    component_name = (
        rtc.get(
            "componentName",
            "",
        )
        .strip()
    )

    if not component_name:
        return False

    return True


def get_repository_info(item):
    """
    Get repository URL and default branch.

    Code search results do not always contain default_branch,
    so retrieve repository metadata when necessary.
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

    if not default_branch and repository_api_url:

        try:

            repo_data = github_api(
                repository_api_url
            )

            default_branch = repo_data.get(
                "default_branch"
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
    Build URL for the directory containing RTC.xml.
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
    Add GitHub metadata to parsed RTC data.
    """

    (
        repository_url,
        default_branch,
    ) = get_repository_info(
        item
    )

    path = item[
        "path"
    ]

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
    """
    Save rtc_catalog.json.
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
    Print parsed RTC information to Actions log.
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

            data_type = (
                port.get(
                    "dataType"
                )
                or "(unknown)"
            )

            print(
                "        "
                f"{port['direction']} "
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
                f"        {port['name']}"
            )

            for interface in port.get(
                "interfaces",
                [],
            ):

                print(
                    "          "
                    f"{interface['direction']} "
                    f"{interface['name']} : "
                    f"{interface['type']}"
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

            print_rtc(
                entry,
                len(catalog),
            )

            #
            # Stop after --limit valid RTCs.
            #
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
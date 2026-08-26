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
    "X-GitHub-Api-Version": "2026-03-10",
}

if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"


def github_api(url):
    """
    Call GitHub REST API and return decoded JSON.
    """

    request = urllib.request.Request(
        url,
        headers=HEADERS,
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
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
    Remove XML namespace.
    """

    if "}" in name:
        return name.split("}", 1)[1]

    if ":" in name:
        return name.split(":", 1)[1]

    return name


def get_attribute(element, name):
    """
    Get an XML attribute while ignoring namespaces.
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

    GitHub Search API returns at most 100 entries per page.
    For this test version, one page is sufficient because
    the caller normally stops after --limit entries.
    """

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

    #
    # Fallback to download_url
    #

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
    Parse BasicInfo.
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

        for field in result.keys():

            value = get_attribute(
                element,
                field,
            )

            if value:
                result[field] = value

        #
        # RTC Profile usually uses "name" instead of
        # componentName.
        #

        if not result["componentName"]:

            value = get_attribute(
                element,
                "name",
            )

            if value:
                result["componentName"] = value

        break

    return result


def detect_port_direction(element):
    """
    Determine whether a DataPort is an InPort or OutPort.
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
    """
    Parse DataPorts.
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

        #
        # Some RTC.xml files store these values
        # in child elements.
        #

        for child in element.iter():

            child_tag = local_name(
                child.tag
            ).lower()

            text = (
                child.text or ""
            ).strip()

            if not text:
                continue

            if child_tag == "name" and not name:
                name = text

            elif child_tag in (
                "datatype",
                "data_type",
            ) and not data_type:
                data_type = text

        #
        # Avoid adding container elements that have
        # no actual port information.
        #

        if not name and not data_type:
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
    Convert RTC Profile service direction names
    to Provider / Consumer.
    """

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
    Parse ServicePorts and their interfaces.
    """

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

        #
        # Ignore empty container nodes.
        #

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
    """
    Parse implementation language if available.
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
    Determine whether the XML looks like an RTC Profile.

    For the test catalog, componentName is required.
    """

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
    """
    Create a GitHub URL pointing to the directory
    containing RTC.xml.
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

    repository = item[
        "repository"
    ]

    repository_url = repository[
        "html_url"
    ]

    default_branch = repository.get(
        "default_branch",
        "main",
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
    Save catalog as JSON.
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

        seen.add(unique_key)

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

            if not is_valid_rtc(rtc):

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
                f"      DataPorts: "
                f"{len(entry['dataPorts'])}"
            )

            print(
                f"      ServicePorts: "
                f"{len(entry['servicePorts'])}"
            )

            #
            # Test mode limit
            #

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
                f"  Skip: XML parse error: {e}"
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
    print("Summary")
    print("-------")
    print(
        f"Processed files : {processed}"
    )
    print(
        f"Valid RTCs      : {len(catalog)}"
    )
    print(
        f"Skipped files   : {skipped}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
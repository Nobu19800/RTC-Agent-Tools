#!/usr/bin/env python3

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


GITHUB_API = "https://api.github.com"
OUTPUT_FILE = Path("catalog/rtc_catalog.json")

RTC_NS = "http://www.openrtp.org/namespaces/rtc"

TOKEN = os.environ.get("GITHUB_TOKEN", "")

HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "rtc-catalog-builder",
    "X-GitHub-Api-Version": "2022-11-28",
}

if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"


# ============================================================
# GitHub API
# ============================================================

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


# ============================================================
# XML utility
# ============================================================

def local_name(name):
    if "}" in name:
        return name.split("}", 1)[1]

    if ":" in name:
        return name.split(":", 1)[1]

    return name


def get_attr(elem, name):
    """
    Get an XML attribute.

    If namespace-qualified name is specified,
    use elem.get() directly.

    Otherwise search by local attribute name.
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
    Get an attribute specifically from the RTC namespace.
    """

    return elem.get(
        f"{{{RTC_NS}}}{name}"
    )


# ============================================================
# GitHub search
# ============================================================

def search_rtc_xml():
    """
    Search GitHub for RTC.xml.

    Multiple queries are used because GitHub Code Search
    limits the number of results obtainable for one query.

    Results are deduplicated by:
        repository + file path
    """

    queries = [
        "filename:RTC.xml",
        "filename:RTC.xml language:C++",
        "filename:RTC.xml language:Python",
        "filename:RTC.xml language:Java",
    ]

    all_items = []
    seen = set()

    for query in queries:

        print()
        print("=" * 70)
        print(f"Search query: {query}")
        print("=" * 70)

        encoded_query = urllib.parse.quote(
            query
        )

        # GitHub search results are limited to
        # 100 results/page and at most 10 pages.
        for page in range(1, 11):

            url = (
                f"{GITHUB_API}/search/code"
                f"?q={encoded_query}"
                f"&per_page=100"
                f"&page={page}"
            )

            print(
                f"Searching page {page} ..."
            )

            try:

                data = github_api(
                    url
                )

            except urllib.error.HTTPError as e:

                # GitHub may reject page > available
                # search window.
                if e.code == 422:

                    print(
                        "Search result limit reached."
                    )

                    break

                raise

            items = data.get(
                "items",
                [],
            )

            total_count = data.get(
                "total_count",
                0,
            )

            if page == 1:

                print(
                    f"GitHub reports "
                    f"{total_count} matches."
                )

            if not items:
                break

            added = 0

            for item in items:

                repository = item[
                    "repository"
                ]

                repository_name = (
                    repository.get(
                        "full_name",
                        repository.get(
                            "html_url",
                            "",
                        ),
                    )
                )

                path = item[
                    "path"
                ]

                key = (
                    repository_name,
                    path,
                )

                if key in seen:
                    continue

                seen.add(
                    key
                )

                all_items.append(
                    item
                )

                added += 1

            print(
                f"  received : {len(items)}"
            )

            print(
                f"  new      : {added}"
            )

            print(
                f"  unique   : {len(all_items)}"
            )

            if len(items) < 100:
                break

            # Small delay to avoid unnecessarily
            # hammering the Search API.
            time.sleep(1)

    print()
    print(
        "GitHub search completed."
    )

    print(
        f"Unique RTC.xml candidates: "
        f"{len(all_items)}"
    )

    return all_items


# ============================================================
# Download RTC.xml
# ============================================================

def get_file_content(item):
    """
    Download RTC.xml through GitHub Contents API.
    """

    api_url = item[
        "url"
    ]

    data = github_api(
        api_url
    )

    encoding = data.get(
        "encoding"
    )

    content = data.get(
        "content"
    )

    if (
        encoding == "base64"
        and content
    ):

        decoded = base64.b64decode(
            content
        )

        return decoded.decode(
            "utf-8",
            errors="replace",
        )

    download_url = data.get(
        "download_url"
    )

    if download_url:

        request = urllib.request.Request(
            download_url,
            headers={
                "User-Agent":
                    "rtc-catalog-builder",
            },
        )

        with urllib.request.urlopen(
            request,
            timeout=30,
        ) as response:

            return (
                response
                .read()
                .decode(
                    "utf-8",
                    errors="replace",
                )
            )

    raise RuntimeError(
        "RTC.xml content could not be retrieved"
    )


# ============================================================
# BasicInfo
# ============================================================

def parse_basic_info(root):

    result = {
        "componentName": "",
        "description": "",
        "category": "",
        "vendor": "",
        "version": "",
    }

    for elem in root.iter():

        if (
            local_name(elem.tag).lower()
            != "basicinfo"
        ):
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


# ============================================================
# DataPorts
# ============================================================

def get_port_type(elem):
    """
    Get rtc:portType exactly as stored in RTC.xml.

    Examples:
        DataInPort
        DataOutPort
    """

    return (
        rtc_attr(
            elem,
            "portType",
        )
        or ""
    ).strip()


def get_data_type(elem):
    """
    Get rtc:type.

    xsi:type is intentionally ignored.

    Example:

        xsi:type="rtcExt:dataport_ext"
        rtc:type="RTC::TimedVelocity2D"

    returns:

        RTC::TimedVelocity2D
    """

    return (
        rtc_attr(
            elem,
            "type",
        )
        or ""
    ).strip()


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

    for elem in root.iter():

        tag = local_name(
            elem.tag
        ).lower()

        if tag not in valid_tags:
            continue

        name = (
            rtc_attr(
                elem,
                "name",
            )
            or get_attr(
                elem,
                "name",
            )
            or ""
        )

        port_type = get_port_type(
            elem
        )

        data_type = get_data_type(
            elem
        )

        if not name:
            continue

        key = (
            name,
            port_type,
            data_type,
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        ports.append(
            {
                "name": name,
                "portType": port_type,
                "dataType": data_type,
            }
        )

    return ports


# ============================================================
# ServicePorts
# ============================================================

def normalize_service_direction(value):

    value = (
        value or ""
    ).strip()

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


def get_property_value(
    elem,
    property_names,
):

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

    return (
        rtc_attr(
            elem,
            "instanceName",
        )
        or rtc_attr(
            elem,
            "name",
        )
        or get_attr(
            elem,
            "instanceName",
        )
        or get_attr(
            elem,
            "instance_name",
        )
        or get_attr(
            elem,
            "name",
        )
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
    Get service interface type.

    xsi:type is intentionally ignored.
    """

    value = (
        rtc_attr(
            elem,
            "type",
        )
        or rtc_attr(
            elem,
            "interfaceType",
        )
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

    value = (
        rtc_attr(
            elem,
            "direction",
        )
        or rtc_attr(
            elem,
            "polarity",
        )
        or get_attr(
            elem,
            "direction",
        )
        or get_attr(
            elem,
            "polarity",
        )
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
            rtc_attr(
                elem,
                "name",
            )
            or get_attr(
                elem,
                "name",
            )
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
                    "name":
                        interface_name,

                    "type":
                        interface_type,

                    "direction":
                        interface_direction,
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
                for interface
                in interfaces
            ),
        )

        if port_key in seen_ports:
            continue

        seen_ports.add(
            port_key
        )

        service_ports.append(
            {
                "name":
                    port_name,

                "interfaces":
                    interfaces,
            }
        )

    return service_ports


# ============================================================
# Language
# ============================================================

def parse_language(root):

    for elem in root.iter():

        if (
            local_name(elem.tag).lower()
            != "language"
        ):
            continue

        value = (
            rtc_attr(
                elem,
                "kind",
            )
            or rtc_attr(
                elem,
                "name",
            )
            or get_attr(
                elem,
                "kind",
            )
            or get_attr(
                elem,
                "name",
            )
            or (
                elem.text or ""
            ).strip()
        )

        if value:
            return value

    return ""


# ============================================================
# RTC.xml parser
# ============================================================

def parse_rtc_xml(xml_text):

    root = ET.fromstring(
        xml_text
    )

    basic = parse_basic_info(
        root
    )

    return {
        **basic,

        "language":
            parse_language(
                root
            ),

        "dataPorts":
            parse_data_ports(
                root
            ),

        "servicePorts":
            parse_service_ports(
                root
            ),
    }


def is_valid_rtc(rtc):

    component_name = (
        rtc.get(
            "componentName",
            "",
        )
        .strip()
    )

    return bool(
        component_name
    )


# ============================================================
# GitHub metadata
# ============================================================

def get_repository_info(item):

    repository = item[
        "repository"
    ]

    repository_url = repository[
        "html_url"
    ]

    repository_api_url = (
        repository.get(
            "url"
        )
    )

    default_branch = (
        repository.get(
            "default_branch"
        )
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

    (
        repository_url,
        default_branch,
    ) = get_repository_info(
        item
    )

    path = item[
        "path"
    ]

    directory_url = (
        build_directory_url(
            repository_url,
            path,
            default_branch,
        )
    )

    return {
        "componentName":
            rtc.get(
                "componentName",
                "",
            ),

        "description":
            rtc.get(
                "description",
                "",
            ),

        "category":
            rtc.get(
                "category",
                "",
            ),

        "vendor":
            rtc.get(
                "vendor",
                "",
            ),

        "version":
            rtc.get(
                "version",
                "",
            ),

        "language":
            rtc.get(
                "language",
                "",
            ),

        "dataPorts":
            rtc.get(
                "dataPorts",
                [],
            ),

        "servicePorts":
            rtc.get(
                "servicePorts",
                [],
            ),

        "repositoryUrl":
            repository_url,

        "directoryUrl":
            directory_url,

        "path":
            path,

        "rtcXmlUrl":
            item.get(
                "html_url",
                "",
            ),
    }


# ============================================================
# Save catalog
# ============================================================

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


# ============================================================
# Console output
# ============================================================

def print_rtc(
    entry,
    index,
):

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


# ============================================================
# Main
# ============================================================

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
            "of valid RT-Components. "
            "If omitted, process all search results."
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

    # ----------------------------------------
    # Search GitHub
    # ----------------------------------------

    items = search_rtc_xml()

    catalog = []

    processed = 0
    skipped = 0

    seen = set()

    # ----------------------------------------
    # Parse each RTC.xml
    # ----------------------------------------

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

            # Test mode
            if (
                args.limit is not None
                and len(catalog)
                >= args.limit
            ):

                print()
                print(
                    "Limit reached: "
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

    # ----------------------------------------
    # Save result
    # ----------------------------------------

    save_catalog(
        catalog
    )

    # ----------------------------------------
    # Summary
    # ----------------------------------------

    print()

    print(
        "Summary"
    )

    print(
        "-------"
    )

    print(
        f"Search candidates : "
        f"{len(items)}"
    )

    print(
        f"Processed files   : "
        f"{processed}"
    )

    print(
        f"Valid RTCs        : "
        f"{len(catalog)}"
    )

    print(
        f"Skipped files     : "
        f"{skipped}"
    )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
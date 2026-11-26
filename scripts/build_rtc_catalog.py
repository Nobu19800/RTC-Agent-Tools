#!/usr/bin/env python3

import argparse
import base64
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from functools import lru_cache
from pathlib import Path, PurePosixPath


GITHUB_API = "https://api.github.com"
OUTPUT_FILE = Path("catalog/rtc_catalog.json")
SAMPLES_OUTPUT_FILE = Path("catalog/openrtm_samples_catalog.json")

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

class GitHubRateLimit(OSError):
    """A GitHub cooldown exceeded the retry budget."""


def github_api(url):
    """Wait for rate limits within a bounded retry budget."""
    remaining_wait = 60
    for attempt in range(3):
        request = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            headers = error.headers
            retry_after = headers.get("Retry-After")
            primary_limit = headers.get("X-RateLimit-Remaining") == "0"
            body = error.read().decode("utf-8", errors="replace")
            secondary_limit = "secondary rate limit" in body.casefold()
            if error.code != 429 and not (
                error.code == 403 and (retry_after or primary_limit or secondary_limit)
            ):
                raise

            waits = [1]
            if retry_after is not None:
                try:
                    waits.append(int(retry_after) + 1)
                except ValueError:
                    waits.append(60)
            if primary_limit:
                try:
                    waits.append(int(headers["X-RateLimit-Reset"]) - int(time.time()) + 2)
                except (KeyError, TypeError, ValueError):
                    waits.append(60)
            if not primary_limit and retry_after is None:
                waits.append(60)
            wait = max(waits)
            if attempt == 2 or wait > remaining_wait:
                raise GitHubRateLimit(
                    f"HTTP {error.code}: GitHub cooldown requires {wait}s; retry budget exhausted"
                ) from error
            print(f"GitHub HTTP {error.code}; retrying in {wait}s", file=sys.stderr)
            time.sleep(wait)
            remaining_wait -= wait


# ============================================================
# XML utility
# ============================================================

def local_name(name):

    if "}" in name:
        return name.split(
            "}",
            1,
        )[1]

    if ":" in name:
        return name.split(
            ":",
            1,
        )[1]

    return name


def get_attr(
    elem,
    name,
):

    if name.startswith(
        "{"
    ):
        return elem.get(
            name
        )

    target = name.lower()

    for key, value in (
        elem.attrib.items()
    ):

        if (
            local_name(
                key
            ).lower()
            == target
        ):

            return value

    return elem.get(
        name
    )


def rtc_attr(
    elem,
    name,
):

    return elem.get(
        f"{{{RTC_NS}}}{name}"
    )


# ============================================================
# GitHub Code Search
# ============================================================

def search_rtc_xml(query="filename:RTC.xml"):
    """
    Search GitHub for RTC.xml.

    Start with a single query:

        filename:RTC.xml

    GitHub Code Search returns at most 100 results/page
    and at most 10 pages (1000 accessible search results).

    A delay is inserted between search requests because
    Code Search has a stricter rate limit than normal REST API.
    """

    encoded_query = (
        urllib.parse.quote(
            query
        )
    )

    all_items = []
    seen = set()

    print()
    print(
        "=" * 70
    )

    print(
        f"Search query: "
        f"{query}"
    )

    print(
        "=" * 70
    )

    for page in range(
        1,
        11,
    ):

        url = (
            f"{GITHUB_API}"
            f"/search/code"
            f"?q={encoded_query}"
            f"&per_page=100"
            f"&page={page}"
        )

        print()
        print(
            f"Searching page "
            f"{page} ..."
        )

        try:

            data = github_api(
                url
            )

        except urllib.error.HTTPError as e:

            #
            # Search API may return 422
            # when the accessible search window
            # has been exceeded.
            #
            if e.code == 422 and page > 1:

                print(
                    "Search result window "
                    "limit reached."
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

            if total_count > 1000:

                print(
                    "Warning: GitHub reports "
                    "more than 1000 matches."
                )

                print(
                    "Only the first 1000 "
                    "search results are "
                    "accessible with this query."
                )

        if not items:

            print(
                "No more search results."
            )

            break

        added = 0

        for item in items:

            repository = (
                item[
                    "repository"
                ]
            )

            repository_name = (
                repository.get(
                    "full_name"
                )
                or repository.get(
                    "html_url",
                    "",
                )
            )

            path = item.get(
                "path",
                "",
            )

            # RTC.xml以外のファイルを除外
            if Path(path).name != "RTC.xml":
                continue

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
            f"  received : "
            f"{len(items)}"
        )

        print(
            f"  new      : "
            f"{added}"
        )

        print(
            f"  unique   : "
            f"{len(all_items)}"
        )

        #
        # Last partial page.
        #
        if len(items) < 100:

            print(
                "Last search page reached."
            )

            break

        #
        # Code Search has a strict rate limit.
        #
        print(
            "Waiting 7 seconds before "
            "next Code Search request..."
        )

        time.sleep(
            7
        )

    print()
    print(
        "GitHub search completed."
    )

    print(
        f"Unique RTC.xml candidates: "
        f"{len(all_items)}"
    )

    return all_items


def catalog_owners(entries):
    owners = {}
    for entry in entries:
        url = urllib.parse.urlsplit(entry.get("repositoryUrl") or "")
        parts = url.path.strip("/").split("/")
        if url.scheme == "https" and url.hostname == "github.com" and len(parts) == 2:
            login = parts[0]
            if re.fullmatch(r"[A-Za-z0-9-]+", login):
                owners.setdefault(login.casefold(), login)
    return list(owners.values())


def owner_repositories(login):
    # This public listing works for both individual accounts and organizations.
    page = 1
    while True:
        repositories = github_api(
            f"{GITHUB_API}/users/{login}/repos?type=owner&per_page=100&page={page}"
        )
        yield from repositories
        if len(repositories) < 100:
            break
        page += 1


def repository_rtc_files(repository):
    branch = repository["default_branch"]
    tree_url = f'{GITHUB_API}/repos/{repository["full_name"]}/git/trees'
    root_url = f"{tree_url}/{urllib.parse.quote(branch, safe='')}"

    def matching_files(nodes, prefix=""):
        for node in nodes:
            name = prefix + node["path"]
            if node["type"] == "blob" and Path(name).name == "RTC.xml":
                yield {
                    "repository": repository,
                    "path": name,
                    "url": node["url"],
                    "html_url": f'{repository["html_url"]}/blob/{urllib.parse.quote(branch)}/{urllib.parse.quote(name)}',
                }

    tree = github_api(f"{root_url}?recursive=1")
    if not tree.get("truncated"):
        yield from matching_files(tree["tree"])
        return

    pending = [(root_url, "")]
    while pending:
        url, prefix = pending.pop()
        subtree = github_api(url)
        if subtree.get("truncated"):
            raise ValueError(f"Truncated Git tree for {repository['full_name']}: {prefix}")
        yield from matching_files(subtree["tree"], prefix)
        pending.extend((node["url"], prefix + node["path"] + "/")
                       for node in subtree["tree"] if node["type"] == "tree")


def search_rtc_xml_by_owner(entries):
    owners = catalog_owners(entries)
    print(f"Searching default branches for {len(owners)} catalog owners.", flush=True)
    for login in owners:
        print(f"Searching repositories owned by {login}", flush=True)
        try:
            for repository in owner_repositories(login):
                if repository.get("private"):
                    continue
                try:
                    yield from repository_rtc_files(repository)
                except GitHubRateLimit:
                    raise
                except (OSError, ValueError) as error:
                    print(f"Warning: could not scan {repository['full_name']}: {error}", file=sys.stderr)
        except GitHubRateLimit:
            raise
        except OSError as error:
            print(f"Warning: could not list repositories for {login}: {error}", file=sys.stderr)


# ============================================================
# Download RTC.xml
# ============================================================

def get_file_content(
    item,
):

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

        decoded = (
            base64.b64decode(
                content
            )
        )

        return (
            decoded.decode(
                "utf-8",
                errors="replace",
            )
        )

    download_url = data.get(
        "download_url"
    )

    if download_url:

        request = (
            urllib.request.Request(
                download_url,
                headers={
                    "User-Agent":
                        "rtc-catalog-builder",
                },
            )
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
        "RTC.xml content "
        "could not be retrieved"
    )


# ============================================================
# BasicInfo
# ============================================================

def parse_basic_info(
    root,
):

    result = {
        "componentName": "",
        "description": "",
        "category": "",
        "vendor": "",
        "version": "",
    }

    for elem in root.iter():

        if (
            local_name(
                elem.tag
            ).lower()
            != "basicinfo"
        ):

            continue

        result[
            "componentName"
        ] = (
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

        result[
            "description"
        ] = (
            rtc_attr(
                elem,
                "description",
            )
            or get_attr(
                elem,
                "description",
            )
            or ""
        )

        result[
            "category"
        ] = (
            rtc_attr(
                elem,
                "category",
            )
            or get_attr(
                elem,
                "category",
            )
            or ""
        )

        result[
            "vendor"
        ] = (
            rtc_attr(
                elem,
                "vendor",
            )
            or get_attr(
                elem,
                "vendor",
            )
            or ""
        )

        result[
            "version"
        ] = (
            rtc_attr(
                elem,
                "version",
            )
            or get_attr(
                elem,
                "version",
            )
            or ""
        )

        break

    return result


# ============================================================
# DataPorts
# ============================================================

def get_port_type(
    elem,
):

    return (
        rtc_attr(
            elem,
            "portType",
        )
        or ""
    ).strip()


def get_data_type(
    elem,
):

    return (
        rtc_attr(
            elem,
            "type",
        )
        or ""
    ).strip()


def parse_data_ports(
    root,
):

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

        tag = (
            local_name(
                elem.tag
            )
            .lower()
        )

        if (
            tag
            not in valid_tags
        ):

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

        port_type = (
            get_port_type(
                elem
            )
        )

        data_type = (
            get_data_type(
                elem
            )
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
                "name":
                    name,

                "portType":
                    port_type,

                "dataType":
                    data_type,
            }
        )

    return ports


# ============================================================
# ServicePorts
# ============================================================

def normalize_service_direction(
    value,
):

    value = (
        value or ""
    ).strip()

    lower = (
        value.lower()
    )

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
        for name
        in property_names
    }

    for child in elem.iter():

        tag = (
            local_name(
                child.tag
            )
            .lower()
        )

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
            prop_name
            in property_names
            and prop_value
        ):

            return prop_value

    return ""


def get_service_interface_name(
    elem,
):

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


def get_service_interface_type(
    elem,
):

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

    return (
        value.strip()
    )


def get_service_interface_direction(
    elem,
):

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

    return (
        normalize_service_direction(
            value
        )
    )


def parse_service_ports(
    root,
):

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

        tag = (
            local_name(
                elem.tag
            )
            .lower()
        )

        if (
            tag
            not in valid_port_tags
        ):

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

            child_tag = (
                local_name(
                    child.tag
                )
                .lower()
            )

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
                    interface[
                        "name"
                    ],
                    interface[
                        "type"
                    ],
                    interface[
                        "direction"
                    ],
                )
                for interface
                in interfaces
            ),
        )

        if (
            port_key
            in seen_ports
        ):

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

def parse_language(
    root,
):

    for elem in root.iter():

        if (
            local_name(
                elem.tag
            ).lower()
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
                elem.text
                or ""
            ).strip()
        )

        if value:
            return value

    return ""


# ============================================================
# RTC parser
# ============================================================

def parse_rtc_xml(
    xml_text,
):

    root = (
        ET.fromstring(
            xml_text
        )
    )

    basic = (
        parse_basic_info(
            root
        )
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


def is_valid_rtc(
    rtc,
):

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
# Repository metadata
# ============================================================

@lru_cache(maxsize=None)
def repository_metadata(api_url):
    try:
        return github_api(api_url)
    except GitHubRateLimit:
        raise
    except OSError as error:
        print(f"Warning: could not fetch repository metadata: {error}", file=sys.stderr)
        return {} if isinstance(error, urllib.error.HTTPError) and error.code == 404 else None


def get_repository_info(item):
    repository = item["repository"]
    branch = repository.get("default_branch")
    if not branch and repository.get("url"):
        metadata = repository_metadata(repository["url"]) or {}
        branch = metadata.get("default_branch")
    return repository["html_url"], branch


@lru_cache(maxsize=None)
def folder_commit_timestamp(repository_api_url, branch, directory):
    params = {"sha": branch, "per_page": 1}
    if directory != ".":
        params["path"] = directory
    query = urllib.parse.urlencode(params)
    try:
        commits = github_api(f"{repository_api_url}/commits?{query}")
        if commits:
            stamp = datetime.fromisoformat(commits[0]["commit"]["committer"]["date"])
            if stamp.tzinfo is not None:
                return stamp
    except GitHubRateLimit:
        raise
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(f"Warning: could not fetch RTC folder history for {repository_api_url} ({directory}): {error}", file=sys.stderr)
    return None


def rtc_folder_timestamp(entry):
    url = urllib.parse.urlsplit(entry.get("repositoryUrl") or "")
    repo_path = url.path.strip("/").removesuffix(".git")
    if url.scheme != "https" or url.hostname != "github.com" or not re.fullmatch(r"[\w.-]+/[\w.-]+", repo_path):
        return None
    profile = entry.get("path")
    if not profile:
        return None
    api_url = f"{GITHUB_API}/repos/{repo_path}"
    branch = entry.get("repositoryDefaultBranch")
    if not branch:
        metadata = repository_metadata(api_url) or {}
        branch = metadata.get("default_branch")
    if not branch:
        return None
    return folder_commit_timestamp(api_url, branch, PurePosixPath(profile).parent.as_posix())


def prefer_rtc(candidate, current):
    if current is None:
        return True
    def source(entry):
        return entry.get("repositoryUrl", "").rstrip("/").casefold(), entry.get("path")

    if source(candidate) == source(current):
        # Refresh the same file without querying its history.
        return True

    new = rtc_folder_timestamp(candidate)
    old = rtc_folder_timestamp(current) if new is not None else None
    return new is not None and old is not None and new > old


def build_directory_url(
    repository_url,
    path,
    default_branch,
):

    parent = str(
        Path(
            path
        ).parent
    )

    if parent == ".":
        return repository_url

    return (
        f"{repository_url}"
        f"/tree/"
        f"{default_branch}"
        f"/{parent}"
    )


def create_catalog_entry(
    item,
    rtc,
):

    (
        repository_url,
        default_branch,
    ) = (
        get_repository_info(
            item
        )
    )

    path = (
        item[
            "path"
        ]
    )

    directory_url = (
        build_directory_url(
            repository_url,
            path,
            default_branch or "main",
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

        **({"repositoryDefaultBranch": default_branch} if default_branch else {}),

        "path":
            path,

        "rtcXmlUrl":
            item.get(
                "html_url",
                "",
            ),
    }


# ============================================================
# Save
# ============================================================

def rtc_identity(rtc):
    return rtc["componentName"].strip(), rtc.get("language", "").strip().casefold()


def existing_catalog(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}

    if not isinstance(data, dict) or not isinstance(data.get("rtcs"), list):
        raise ValueError(f"Invalid RTC catalog: {path}")
    entries = {}
    for entry in data["rtcs"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("componentName"), str) or not isinstance(entry.get("language", ""), str):
            raise ValueError(f"Invalid RTC entry in {path}")
        entries.setdefault(rtc_identity(entry), entry)
    return entries


def openrtm_samples():
    """Read pinned OpenRTM sample entries for the separate sample catalog."""
    root = Path(__file__).resolve().parents[1]
    manifest = root / "profiles/openrtm-samples/catalog-entries.json"
    samples = json.loads(manifest.read_text(encoding="utf-8"))
    entries = {}
    for sample in samples:
        profile_path = sample["source"]["profilePath"]
        if profile_path:
            profile = parse_rtc_xml((root / profile_path).read_text(encoding="utf-8"))
            if rtc_identity(profile) != rtc_identity(sample):
                raise ValueError(f"RTC profile identity does not match manifest: {profile_path}")
            sample = {**profile, **sample}
        entries[rtc_identity(sample)] = sample
    return list(entries.values())


def save_catalog(
    catalog,
    output_file=OUTPUT_FILE,
):

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    data = {
        "schemaVersion":
            "1.0",

        "rtcs":
            catalog,
    }

    payload = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    temporary = tempfile.NamedTemporaryFile(dir=output_file.parent, delete=False)
    temporary_path = Path(temporary.name)
    try:
        with temporary:
            temporary.write(payload)
        temporary_path.replace(output_file)
    finally:
        temporary_path.unlink(missing_ok=True)

    print()
    print(
        f"Catalog written to: "
        f"{output_file}"
    )


# ============================================================
# Console
# ============================================================

def print_rtc(
    entry,
    index,
):

    print(
        f"  [{index}] "
        f"{entry['componentName']}"
    )

    if (
        entry[
            "description"
        ]
    ):

        print(
            f"      Description: "
            f"{entry['description']}"
        )

    print(
        "      DataPorts:"
    )

    if (
        entry[
            "dataPorts"
        ]
    ):

        for port in (
            entry[
                "dataPorts"
            ]
        ):

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

    if (
        entry[
            "servicePorts"
        ]
    ):

        for port in (
            entry[
                "servicePorts"
            ]
        ):

            print(
                f"        "
                f"{port['name']}"
            )

            for interface in (
                port.get(
                    "interfaces",
                    [],
                )
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

def collect_catalog_entries(items, seen, previous, limit):
    catalog = {}
    processed = 0
    skipped = 0
    for item in items:

        repository_url = (
            item[
                "repository"
            ][
                "html_url"
            ]
        )

        path = (
            item[
                "path"
            ]
        )

        if (
            repository_url.rstrip("/").casefold() == "https://github.com/nobu19800/rtc-agent-tools"
            and path.startswith("profiles/openrtm-samples/")
        ):
            continue

        unique_key = (
            repository_url,
            path,
        )

        if (
            unique_key
            in seen
        ):

            continue

        seen.add(
            unique_key
        )

        processed += 1

        print()
        print(
            f"Checking: "
            f"{repository_url}/"
            f"{path}"
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

            if not (
                is_valid_rtc(
                    rtc
                )
            ):

                skipped += 1

                print(
                    "  Skip: "
                    "not recognized "
                    "as RTC Profile"
                )

                continue

            key = rtc_identity(rtc)
            entry = create_catalog_entry(item, rtc)
            if not prefer_rtc(entry, catalog.get(key, previous.get(key))):
                skipped += 1
                print(f"  Skip: keeping current RTC for {key[0]} ({key[1] or 'unknown'})")
                continue
            catalog[key] = entry

            print_rtc(
                entry,
                len(catalog),
            )

            if (
                limit
                is not None
                and len(
                    catalog
                )
                >= limit
            ):

                print()
                print(
                    "Limit reached: "
                    f"{limit} RTCs"
                )

                break

        except GitHubRateLimit as error:
            print(f"Warning: stopping profile retrieval; retaining saved catalog entries: {error}", file=sys.stderr)
            return catalog, processed, skipped
        except ET.ParseError as e:

            skipped += 1

            print(
                f"  Skip: "
                f"XML parse error: "
                f"{e}"
            )

        except Exception as e:

            skipped += 1

            print(
                f"  Skip: "
                f"{e}"
            )

    return catalog, processed, skipped


def main():

    parser = (
        argparse.ArgumentParser(
            description=(
                "Search GitHub for "
                "RTC.xml and build "
                "an RT-Component catalog."
            )
        )
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Stop after finding "
            "this number of valid "
            "RT-Components. "
            "If omitted, process all "
            "accessible search results."
        ),
    )
    parser.add_argument(
        "--openrtm-samples-only", action="store_true",
        help="Build the separate OpenRTM samples catalog without querying GitHub.",
    )

    args = (
        parser.parse_args()
    )
    if args.openrtm_samples_only:
        save_catalog(openrtm_samples(), SAMPLES_OUTPUT_FILE)
        return 0

    if (
        args.limit
        is not None
        and args.limit <= 0
    ):

        parser.error(
            "--limit must be "
            "greater than 0"
        )

    if not TOKEN:

        print(
            "Warning: GITHUB_TOKEN "
            "is not set.",
            file=sys.stderr,
        )

        print(
            "Unauthenticated "
            "GitHub API requests "
            "have stricter limits.",
            file=sys.stderr,
        )

    try:
        previous = existing_catalog(OUTPUT_FILE)
    except (OSError, ValueError) as error:
        print(f"Error: existing catalog could not be read: {error}", file=sys.stderr)
        return 1

    seen = set()
    try:
        items = search_rtc_xml()
    except GitHubRateLimit as error:
        print(f"Warning: global code search deferred: {error}", file=sys.stderr)
        items = []

    catalog, processed, skipped = collect_catalog_entries(
        items, seen, previous, args.limit
    )
    existing_keys = set(previous)
    previous.update(catalog)
    if catalog:
        save_catalog(list(previous.values()), OUTPUT_FILE)
    print(f"Global search collected {len(catalog)} RTCs.", flush=True)

    limit = None if args.limit is None else args.limit - len(catalog)
    if limit != 0:
        def owner_candidates():
            try:
                yield from search_rtc_xml_by_owner(previous.values())
            except GitHubRateLimit as error:
                print(f"Warning: stopping owner scan: {error}", file=sys.stderr)

        added, owner_processed, owner_skipped = collect_catalog_entries(
            owner_candidates(), seen, previous, limit
        )
        previous.update(added)
        if added:
            save_catalog(list(previous.values()), OUTPUT_FILE)
        catalog.update(added)
        processed += owner_processed
        skipped += owner_skipped
        print(f"Owner scan collected {len(added)} RTCs.", flush=True)

    if not catalog and not OUTPUT_FILE.is_file():
        print("Error: no RTCs collected and no existing catalog available.", file=sys.stderr)
        return 1
    retained = len(existing_keys - catalog.keys())
    print(f"Retained RTCs not found in this run: {retained}")
    print(f"Total RTCs in catalog: {len(previous)}")

    print()
    print(
        "Summary"
    )
    print(
        "-------"
    )

    print(
        f"Global candidates : "
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

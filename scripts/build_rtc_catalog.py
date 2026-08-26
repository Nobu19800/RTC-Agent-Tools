import base64
import json
import os
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


TOKEN = os.environ["GITHUB_TOKEN"]

HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {TOKEN}",
    "X-GitHub-Api-Version": "2026-03-10",
    "User-Agent": "rtc-catalog-builder",
}


def github_api(url):
    req = urllib.request.Request(url, headers=HEADERS)

    with urllib.request.urlopen(req) as response:
        return json.load(response)


def search_rtc_xml():
    query = urllib.parse.quote('filename:RTC.xml')

    url = (
        "https://api.github.com/search/code"
        f"?q={query}&per_page=100"
    )

    data = github_api(url)

    return data["items"]


def get_file_content(item):
    data = github_api(item["url"])

    content = base64.b64decode(data["content"])

    return content.decode("utf-8", errors="replace")
#!/usr/bin/env python3
"""Search the local XML-derived Hakoniwa asset catalog; retain full asset metadata."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalog", type=Path)
    parser.add_argument("query", nargs="?", default="")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if not args.all and not args.query.strip():
        parser.error("Specify search words or --all")
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    if catalog.get("catalogKind") != "hakoniwa-assets" or not isinstance(catalog.get("assets"), list):
        parser.error("Expected a hakoniwa-assets catalog with an assets array")
    words = args.query.casefold().split()
    assets = [asset for asset in catalog["assets"] if args.all or all(
        word in json.dumps(asset, ensure_ascii=False).casefold() for word in words)]
    if args.json:
        print(json.dumps(assets, ensure_ascii=False, indent=2))
    else:
        print("Found %d Hakoniwa asset(s)." % len(assets))
        for asset in assets:
            print("\n%s: %s" % (asset["catalogId"], asset["componentName"]))
            print(asset["description"])
            for port in asset["ports"]:
                channel = " channel=%s" % port["channelId"] if "channelId" in port else ""
                print("  %s %s: %s [%s]%s" % (
                    port["direction"], port["name"], port["dataType"], port.get("transport", ""), channel))


if __name__ == "__main__":
    main()

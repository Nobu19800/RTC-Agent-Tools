"""Create or retrieve a session on the local Designer integration server."""

import argparse
import json
from pathlib import Path
from urllib.parse import quote
from urllib.request import ProxyHandler, Request, build_opener


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=5173)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create")
    create.add_argument("proposal", type=Path)
    download = commands.add_parser("get")
    download.add_argument("session_id")
    download.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")

    url = f"http://127.0.0.1:{args.port}/api/sessions"
    try:
        if args.command == "create":
            proposal = json.loads(args.proposal.read_text(encoding="utf-8-sig"))
            request = Request(
                url,
                data=json.dumps(proposal).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
        else:
            request = Request(f"{url}/{quote(args.session_id, safe='')}")
        opener = build_opener(ProxyHandler({}))
        with opener.open(request, timeout=10) as response:
            result = json.load(response)
        content = json.dumps(result, indent=2, ensure_ascii=False)
        if args.command == "get" and args.output:
            args.output.write_text(content + "\n", encoding="utf-8")
        else:
            print(content)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Local Designer session request failed: {error}\n")


if __name__ == "__main__":
    main()

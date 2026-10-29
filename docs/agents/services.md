# Repository tools and services

Part of the mandatory repository instructions linked from [AGENTS.md](../../AGENTS.md).
Read before catalog searches, session-server access, or RTSystemDesigner link creation.
All command examples and workspace paths are relative to the repository root unless explicitly stated otherwise.

## Repository tools and external services

### RTC search tool

Use the repository's `rtc_search.py` to search RTC metadata.

Typical usage:

```bash
python rtc_search.py catalog/rtc_catalog.json camera --json
python rtc_search.py catalog/rtc_catalog.json "object detection" --json
python rtc_search.py catalog/rtc_catalog.json robot --json
python rtc_search.py catalog/rtc_catalog.json --all --json
```

`rtc_search.py` supports searching component metadata, descriptions, DataPorts, ServicePorts, RTC.xml URLs, repository URLs, and related fields.

Do not replace catalog searches with guesses when a potentially reusable RTC may exist.

### RTC catalog

Do not assume that `catalog/rtc_catalog.json` in the repository is current.

Before starting a new system-design task, download the latest catalog from:

```text
https://raw.githubusercontent.com/Nobu19800/RTC-Agent-Tools/refs/heads/main/catalog/rtc_catalog.json
```

Save it as:

```text
catalog/rtc_catalog.json
```

Create the `catalog` directory if it does not exist.

Prefer a normal HTTP download tool available in the environment. For example:

```bash
curl -L "https://raw.githubusercontent.com/Nobu19800/RTC-Agent-Tools/refs/heads/main/catalog/rtc_catalog.json" -o catalog/rtc_catalog.json
```

If `curl` is unavailable, use Python or another standard download mechanism.

After download, confirm that the file is valid JSON and contains an `rtcs` array before using it.

### Temporary session server

Base URL:

```text
https://rt-session-server.rtsystem-designer-web.workers.dev
```

Create a session:

```text
POST /api/sessions
```

Get a session:

```text
GET /api/sessions/:id
```

Update is performed by RTSystemDesigner:

```text
PUT /api/sessions/:id
```

### RTSystemDesigner

Designer URL:

```text
https://nobu19800.github.io/RTSystemDesigner/
```

A designed session is opened with:

```text
https://nobu19800.github.io/RTSystemDesigner/?session=<SESSION_ID>
```

The session server may also return `designerUrl`. If it does, show that exact URL to the user instead of rebuilding it manually.

---

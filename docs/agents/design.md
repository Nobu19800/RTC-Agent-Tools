# System design workflow

Part of the mandatory repository instructions linked from [AGENTS.md](../../AGENTS.md).
Read with [services.md](services.md) and [session-format.md](session-format.md) before starting a new system design. Phase 4 is defined in session-format.md; follow phases in numeric order.
All command examples and workspace paths are relative to the repository root unless explicitly stated otherwise.

## Required workflow

### Phase 1: Understand the user's requested system

When the user gives a natural-language description of a system:

1. Identify the system's major functions.
2. Break the system into candidate RTC responsibilities.
3. Identify required input/output data and control flows.
4. Identify external hardware, sensors, actuators, and software dependencies.
5. Do not assume that one RTC is required for every conceptual function. Reuse existing RTC boundaries when their interfaces and responsibilities are suitable.
6. Do not start coding RTC implementations yet.

Create a short internal list such as:

```text
Required capabilities
- acquire camera/depth data
- detect target object
- determine manipulation action
- control robot arm
```

Use this list only as a search and design aid.

---

## Phase 2: Refresh and search the RTC catalog

Always refresh `catalog/rtc_catalog.json` from the canonical URL before catalog-based design.

For each required capability, search with `rtc_search.py`.

Use multiple focused searches when useful. For example:

```bash
python rtc_search.py catalog/rtc_catalog.json camera --json
python rtc_search.py catalog/rtc_catalog.json "point cloud" --json
python rtc_search.py catalog/rtc_catalog.json "object detection" --json
python rtc_search.py catalog/rtc_catalog.json arm --json
python rtc_search.py catalog/rtc_catalog.json controller --json
```

Do not select an RTC only because its name looks relevant.

For each candidate, inspect at least:

- `componentName`
- `description`
- `dataPorts`
- `servicePorts`
- `repositoryUrl`
- `directoryUrl`
- `rtcXmlUrl`
- `rawRtcXmlUrl` when present

Check connection compatibility.

For DataPorts, the source and destination data types must match unless a newly designed adapter/converter RTC is explicitly inserted.

For ServicePorts, check service interface name, interface type, and Consumer/Provider direction.

If no existing RTC satisfies a required responsibility or interface, define a new RTC in the session JSON.

Never invent an existing repository or claim that a generated RTC already exists.

---

## Phase 3: Select existing RTCs and define new RTCs

Classify every RTC as either:

```text
existing
```

or:

```text
generated
```

For existing RTCs, preserve catalog provenance whenever available, including:

- catalog ID
- repository URL
- directory URL
- RTC.xml URL
- component name
- port definitions

For newly required RTCs, create enough metadata for RTSystemDesigner and later Codex implementation.

Each generated RTC must define:

- name
- description
- ports
- configuration parameters when needed
- deployment placeholders
- rtc.conf placeholders
- AI implementation specification

The AI implementation specification must have four fields:

```json
{
  "summary": "",
  "requirements": "",
  "constraints": "",
  "notes": ""
}
```

Use these fields as follows:

- `summary`: concise responsibility of the RTC.
- `requirements`: behavior that must be implemented.
- `constraints`: interface, compatibility, library, generated-code, hardware, or architectural constraints.
- `notes`: unresolved details, assumptions to verify, or useful implementation guidance.

Do not fabricate undocumented semantics for an existing RTC's payload.

For example, if the catalog only states that a port is `RTC::TimedDoubleSeq`, do not assume the meaning or order of each array element. Record that the implementation or documentation must be checked.

---

## Phase 5: Validate the generated JSON

Before uploading:

1. Parse the JSON locally.
2. Confirm the root is an object.
3. Confirm `name` is a string.
4. Confirm `description` is a string.
5. Confirm `rtcTemplates` is an array.
6. Confirm `nodes` and `edges` are arrays.
7. Confirm every edge references existing node IDs.
8. Confirm every edge handle refers to a port on the corresponding node.
9. Confirm DataPort types match across each direct DataPort connection.
10. Confirm every generated RTC has all four `implementation` fields.
11. Confirm existing RTC provenance is preserved when available.

If validation fails, fix the JSON before uploading.

---

## Phase 6: Upload the proposal to the temporary session server

Upload the generated session JSON to:

```text
https://rt-session-server.rtsystem-designer-web.workers.dev/api/sessions
```

Example:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  --data-binary "@work/session-proposal.json" \
  "https://rt-session-server.rtsystem-designer-web.workers.dev/api/sessions"
```

If the server requires an authentication header in the current deployment, obtain it only from the environment or user-provided secure configuration. Never hard-code secrets in `AGENTS.md`, source files, generated JSON, logs, or chat output.

Parse the response and retain:

- `sessionId`
- `designerUrl`, if returned
- session API URL, if returned

Save the current session ID locally for the follow-up step. A suitable file is:

```text
work/current_session_id.txt
```

The file should contain only the current session ID.

Do not commit temporary session files or secrets unless the user explicitly requests it.

---

## Phase 7: Show the design link and stop implementation

After successful upload, tell the user that the proposed system design is ready for review and show the RTSystemDesigner link.

Prefer:

```text
<designerUrl returned by the server>
```

Otherwise construct:

```text
https://nobu19800.github.io/RTSystemDesigner/?session=<SESSION_ID>
```

At this point, stop.

Do not download RTC repositories.
Do not implement generated RTCs.
Do not build the final system.

Ask the user to review and edit:

- selected RTCs
- RTC connections
- Deployment settings
- Configuration settings
- Implementation instructions

Wait for explicit design completion.

The expected transition phrase is a message such as:

```text
設計完了しました
```

Do not infer design completion merely because the user asks a question about the diagram.

---

## Expected user interaction example

User:

```text
カメラ画像から物体を検出し、色によってロボットアームの動作を変更するシステムを作りたい
```

Agent:

1. Download the current RTC catalog.
2. Search it using `rtc_search.py`.
3. Select suitable reusable RTCs.
4. Define missing RTCs.
5. Generate `work/session-proposal.json`.
6. Upload it to the temporary session server.
7. Return the RTSystemDesigner link.
8. Stop and wait.

User edits the design in RTSystemDesigner.

User:

```text
設計完了しました
```

Agent:

1. GET the final session JSON.
2. Save it as `work/final-session.json`.
3. Copy it to `build/system/final-session.json`.
4. Determine RTCs actually instantiated in the final design.
5. Clone existing RTC repositories into `build/existing/`.
6. Create generated RTC workspaces under `build/generated/`.
7. Export each used generated RTC's definition JSON in the `rtc_sample.json` format, convert it to `RTC.xml` with `json_to_rtc_xml.py`, and generate skeleton code with `cuirtcbuilder.bat`.
8. Use final Implementation fields and connections to continue implementation and build preparation.
9. Generate the five lifecycle batch files and runtime usage instructions from the final design, and report their verification status.

---

## Completion criteria for the design phase

The design phase is complete only when all of the following are true:

- the latest catalog was downloaded,
- relevant existing RTCs were searched,
- missing RTCs were explicitly marked as generated,
- proposed ports and connections were represented in JSON,
- the JSON was validated,
- the session was uploaded successfully,
- the user received the RTSystemDesigner link,
- the agent is waiting for explicit design completion.

# System design workflow

Part of the mandatory repository instructions linked from [AGENTS.md](../../AGENTS.md).
Read with [services.md](services.md) and [session-format.md](session-format.md) before starting a new system design. Phase 4 is defined in session-format.md; follow phases in numeric order.
All command examples and workspace paths are relative to the repository root unless explicitly stated otherwise.

## Required workflow

### Phase 1: Understand the user's requested system

When the user gives a natural-language description of a system:

1. Identify the system's major functions.
2. Break the system into candidate module responsibilities, considering both RTCs and Hakoniwa assets.
3. Identify required input/output data and control flows.
4. Identify external hardware, sensors, actuators, and software dependencies.
5. Reuse suitable module boundaries; a function may belong to an existing RTC or Hakoniwa asset. Do not require one new RTC per function or replace a suitable simulation asset with a generated RTC by default.
6. Do not start coding RTCs, assets or transport plugins yet.

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

## Phase 2: Refresh/check and search both catalogs

Always refresh `catalog/rtc_catalog.json` from the canonical URL before catalog-based design.

Also check `catalog/hakoniwa_catalog.json` against its source XML using `python scripts/build_hakoniwa_catalog.py --check`. If the source is available and changed, regenerate it and repeat the check. If the source is unavailable, retain the recorded source/hash, report freshness as unverified and continue provisional design from the saved catalog; do not claim a fresh source verification or invent a remote catalog URL.

For each required capability, search both catalogs with focused terms using `rtc_search.py` and `hakoniwa_search.py`. If a focused asset search returns nothing, inspect `--all` before concluding that the small asset catalog has no suitable candidate. Search results inform one shared composition; do not create separate RTC and Hakoniwa systems by default.

Use multiple focused searches when useful. For example:

```bash
python rtc_search.py catalog/rtc_catalog.json camera --json
python rtc_search.py catalog/rtc_catalog.json "point cloud" --json
python rtc_search.py catalog/rtc_catalog.json "object detection" --json
python rtc_search.py catalog/rtc_catalog.json arm --json
python rtc_search.py catalog/rtc_catalog.json controller --json
python hakoniwa_search.py catalog/hakoniwa_catalog.json controller --json
python hakoniwa_search.py catalog/hakoniwa_catalog.json Drone --json
python hakoniwa_search.py catalog/hakoniwa_catalog.json --all --json
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

For each Hakoniwa candidate, inspect `catalogId`, `moduleId`, `moduleKind`, `source`, `ports`, `ioVariables`, `properties`, `executable`, `requirements`, `constraints`, `catalogReferences`, `profile` and `evidence`. Carry its actual ports and source identity into the design. Its referenced Business Pack component ID is not the asset profile's own catalog ID. Preserve original XML directions, shared request/response channels and the WebSocket/PDU distinction.

Check connection compatibility by endpoint kinds.

For RTC-to-RTC DataPorts, require matching types unless an explicit adapter/converter is inserted. For asset-to-asset PDUs, check exact message type, robot, channel, capacity, layout and semantics. For RTC-to-asset or asset-to-RTC DataPorts, require the OpenRTM-aist custom Hakoniwa interface and a serializer mapping the typed RTC value to/from the asset PDU. The RTC and PDU type names can differ only with that explicit mapping; follow [hakoniwa-serializer.md](hakoniwa-serializer.md). Do not select a serializer solely because it mentions the same message name.

For ServicePorts, check service interface name, interface type, and Consumer/Provider direction.

Only after searching both catalogs, define missing RTCs where suitable. Record missing asset capabilities or serializers explicitly as planned/unresolved work. A missing serializer is not a reason to replace the asset with a fictitious existing RTC.

Never invent an existing repository or claim that a generated RTC already exists.

---

## Phase 3: Select modules and define missing implementations

First distinguish RTCs from Hakoniwa assets using `components[].data.moduleKind` as specified in [session-format.md](session-format.md). Classify every RTC's source as either:

```text
existing
```

or:

```text
generated
```

Select Hakoniwa instances from the `assets` catalog separately, with `moduleKind:hakoniwa`. Preserve `catalogId`, `moduleId`, XML path/hash, actual PDU port metadata and deployment requirements in the session or a companion provenance record if extensions do not survive the Designer round trip. Do not use RTC skeleton/build procedures for these modules. Use a single `components` array and `edges` array for the complete selected system.

For each mixed edge, prepare a connection contract as specified in the transport guide. Record the custom interface, serializer, binary format, endpoint types, robot/channel/capacity, mapping semantics, runtime ownership and validation status. Reuse a supported plugin/serializer; when new implementation is needed, describe it in the RTC's `implementation` fields and connection contract, to be implemented after design approval. Do not invent Designer transport fields or silently label planned bindings as executable.

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
5. Confirm `version` is numeric `2`, `id` is a nonempty string, and `components` and `edges` are arrays. Do not require legacy `rtcTemplates` or `nodes`.
6. Confirm component and edge IDs are unique; each component has `type: "rtc"`, numeric position coordinates, and `data.moduleKind` equal to `rtc` or `hakoniwa`. Check the common metadata fields in the session-format guide.
7. Confirm every edge references existing component IDs.
8. Confirm port IDs are unique within each component and every edge handle refers to a port on the corresponding component.
9. Confirm each DataPort connection is output-to-input with `connectionType: "data"`. For RTC-only edges require matching types or an explicit converter; for mixed edges require the custom interface/serializer contract, including an explicit conversion if endpoint type names differ. Preserve integer PDU `channelId` values and asset robot/capacity metadata without inventing them for WebSocket ports. Flag unresolved mappings separately from structural validity and block their runtime execution.
10. Confirm every component has all four `implementation` string fields.
11. Confirm both RTC and Hakoniwa provenance is preserved when available, including asset catalog IDs and XML hashes. Missing source classification is unresolved, not evidence that a module is generated. Confirm every mixed edge has a connection contract with `dataport.interface_type:hakoniwa` and an implemented or explicitly planned serializer. Keep format validation separate from implementation and runtime readiness.

12. Apply the portable-path checks in [session-format.md](session-format.md): use named references or explicitly based relative paths instead of machine-specific local absolute paths, including paths embedded in arguments, environment and implementation notes. Document reference meanings and hosts; keep actual bindings in separate deployment settings. Record the reason for any permitted concrete-path exception. Unresolved deployment bindings do not by themselves invalidate a reviewable design, but must block affected execution.

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

Do not download module repositories.
Do not implement generated RTCs, assets or transport/serializer plugins.
Do not build the final system.

Ask the user to review and edit:

- selected RTCs and Hakoniwa assets
- module connections and mixed-edge serializer mappings
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
2. Check the XML-derived Hakoniwa catalog and search both catalogs with `rtc_search.py` / `hakoniwa_search.py`.
3. Select suitable reusable RTCs and/or Hakoniwa assets.
4. Define missing RTCs and planned custom-interface/serializer mappings for mixed connections.
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
4. Determine modules actually instantiated in the final design by `moduleKind`, preserving their provenance and mixed-connection contracts.
5. Clone existing RTC repositories into `build/existing/`.
6. Create generated RTC workspaces under `build/generated/`.
7. Export each used generated RTC's definition JSON in the `rtc_sample.json` format, convert it to `RTC.xml` with `json_to_rtc_xml.py`, and generate skeleton code with `cuirtcbuilder.bat`.
8. Use final Implementation fields and connections to continue implementation and build preparation. Prepare selected Hakoniwa assets through their own documented deployment, and implement/load the custom interface and required serializers for mixed edges; do not generate RTC skeletons for assets.
9. Generate the five lifecycle batch files and runtime usage instructions from the final design, and report their verification status.

---

## Completion criteria for the design phase

The design phase is complete only when all of the following are true:

- the current RTC catalog was downloaded and the XML-derived asset catalog was checked (or its unverified freshness was reported),
- both catalogs were searched and suitable RTC/asset selections were made,
- missing RTCs were explicitly marked as generated,
- proposed ports and connections were represented in JSON,
- every mixed edge specifies the custom Hakoniwa interface and serializer contract, with unresolved implementation clearly identified,
- the JSON was validated,
- the session was uploaded successfully,
- the user received the RTSystemDesigner link,
- the agent is waiting for explicit design completion.

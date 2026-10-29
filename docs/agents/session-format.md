# RTSystemDesigner session format

Part of the mandatory repository instructions linked from [AGENTS.md](../../AGENTS.md).
Read before creating or revising a session. Apply [design.md](design.md) for validation, upload, and the design-completion gate.
All command examples and workspace paths are relative to the repository root unless explicitly stated otherwise.

## Phase 4: Generate the RTSystemDesigner session JSON

Generate one JSON file representing the proposed system.

Use a filename such as:

```text
work/session-proposal.json
```

Create `work/` if needed.

The root object must contain at least:

```json
{
  "name": "...",
  "description": "...",
  "rtcTemplates": [],
  "nodes": [],
  "edges": []
}
```

### rtcTemplates

`rtcTemplates` contains all reusable and generated RTC definitions that the user may add in RTSystemDesigner.

Each RTC template should use the structure expected by RTSystemDesigner, including:

```json
{
  "name": "ExampleRTC",
  "description": "...",
  "origin": "catalog",
  "catalogId": "...",
  "repositoryUrl": "...",
  "directoryUrl": "...",
  "rtcXmlUrl": "...",
  "ports": [],
  "deployment": {
    "host": "localhost",
    "executable": "",
    "workingDirectory": "",
    "arguments": "",
    "environment": ""
  },
  "rtcConf": {
    "corbaNameServers": "localhost",
    "managerShutdownAuto": "NO"
  },
  "configuration": [],
  "implementation": {
    "summary": "",
    "requirements": "",
    "constraints": "",
    "notes": ""
  }
}
```

For a newly generated RTC, use:

```json
"origin": "generated"
```

and do not invent `repositoryUrl`, `directoryUrl`, or `rtcXmlUrl`.

### nodes

Populate `nodes` with the proposed initial system layout.

Each node must have a stable unique ID, for example:

```text
camera-1
detector-1
controller-1
```

Each node must contain the RTC data required by RTSystemDesigner, including `name`, `instanceName`, `state`, `ports`, deployment information, configuration, and implementation instructions.

Use:

```json
"state": "INACTIVE"
```

for design-time nodes unless a different state is explicitly required by the schema.

Choose sensible positions so the initial diagram is readable. Prefer a left-to-right data/control flow.

### edges

Create connections only when port/interface compatibility is supported by the available metadata.

For a DataPort edge:

```json
{
  "id": "edge-source-port-target-port",
  "source": "source-node-id",
  "sourceHandle": "source-port-id",
  "target": "target-node-id",
  "targetHandle": "target-port-id",
  "data": {
    "connectionType": "data"
  }
}
```

Do not connect incompatible DataPort types.

Do not invent a connection merely because two RTCs are conceptually related.

If an adapter is needed, define a generated adapter RTC and route the connection through it.

---

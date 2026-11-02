# RTSystemDesigner session format

Part of the mandatory repository instructions linked from [AGENTS.md](../../AGENTS.md).
Read before creating or revising a session. Apply [design.md](design.md) for validation, upload, and the design-completion gate.
All command examples and workspace paths are relative to the repository root unless explicitly stated otherwise.

## Phase 4: Generate the RTSystemDesigner session JSON

Generate one proposed system JSON, such as `work/session-proposal.json`. Create `work/` if needed.

Use the version 2 structure supplied in `mixed_rtc_hakoniwa_system.json`. It replaces the legacy root `nodes` / `rtcTemplates` arrays with `components`. The sample establishes the fields below, not a complete schema for every port kind or runtime deployment.

```json
{
  "version": 2,
  "name": "Example system",
  "description": "Example RTC module",
  "id": "example-system",
  "components": [
    {
      "id": "source-rtc-1",
      "type": "rtc",
      "position": { "x": 80, "y": 180 },
      "data": {
        "moduleKind": "rtc",
        "name": "SourceRTC",
        "instanceName": "SourceRTC0",
        "state": "INACTIVE",
        "ports": [
          { "id": "out", "name": "out", "portType": "data", "direction": "out", "dataType": "RTC::TimedVelocity2D" }
        ],
        "deployment": { "host": "localhost", "executable": "", "workingDirectory": "", "arguments": "", "environment": "" },
        "rtcConf": { "corbaNameServers": "localhost", "managerShutdownAuto": "NO" },
        "configuration": [],
        "implementation": { "summary": "Produce velocity commands", "requirements": "Output typed velocity data", "constraints": "", "notes": "" }
      }
    }
  ],
  "edges": []
}
```

### System and component identity

- `version` is numeric `2`. Preserve the supplied root `id` during edits; do not assume it equals the server's returned `sessionId`.
- `components` contains actual instances. Each has a stable unique `id`, diagram `type: "rtc"`, numeric `position.x` / `position.y`, and `data`. Prefer a readable left-to-right layout.
- Dispatch by `data.moduleKind`: `rtc` for RT-Components, `hakoniwa` for Hakoniwa assets. Both use diagram `type: "rtc"`. Do not infer execution technology from diagram type, names, or executable fields.
- Keep `data.name`, `instanceName`, `state`, `ports`, `deployment`, `rtcConf`, `configuration`, and all four `implementation` strings. Use `INACTIVE` at design time. A Hakoniwa asset's displayed state or `rtcConf` does not establish an OpenRTM lifecycle or CORBA registration.
- Empty deployment fields are placeholders, not runnable launch instructions. Do not process Hakoniwa assets through RTC.xml, RTC Builder, or ordinary RTC lifecycle batches.

### Provenance and implementation metadata

`moduleKind` describes execution technology, not existing/generated origin. The supplied version 2 sample has no `origin` or catalog URLs; missing provenance must not be interpreted as `generated`.

Build the module selections from both catalogs: RTC results populate RTC instances; `hakoniwa_catalog.json` entries populate Hakoniwa instances. Copy the selected asset's `componentName` into `data.name` and its `ports` into `data.ports`, assign a unique instance ID/name and diagram position, and preserve its descriptions, requirements and constraints in the implementation fields. `catalogId` identifies the selected asset profile; preserve its distinct `moduleId` and XML source path/hash as provenance. Do not copy an entire catalog entry as a session component or replace the asset ID with its referenced Business Pack component ID.

Preserve asset port `robot`, `pduName`, `channelId`, `capacityBytes`, `transport`, field semantics and `sourceVariableId/sourceDirection` where supported. Keep original `inout` split ports on the same PDU channel. WebSocket ports have no inferred PDU channel. Asset properties and deployment metadata describe the selected profile: retain values and unresolved path references, but do not convert its static status list into a live RTC state or its `services` into CORBA ServicePorts. Keep arguments/environment structured in a companion record if the Designer accepts only deployment strings.

Preserve available `origin`, `catalogId`, `repositoryUrl`, `directoryUrl`, `rtcXmlUrl`, and `rawRtcXmlUrl` in component `data` when supported by the Designer. Verify extension fields survive the server/Designer round trip before relying on them. If needed provenance cannot be retained, save a companion source record keyed by component ID and report the limitation. Never invent repository URLs or catalog identity. Unresolved source classification blocks source-dependent implementation, not structural validation of the sample.

Use `implementation.summary` for responsibility, `requirements` for intended behavior, `constraints` for interface/runtime restrictions, and `notes` for unresolved assumptions.

### Portable path references

Use logical references for local paths in design JSON and companion design records. This includes `deployment.executable`, `workingDirectory`, paths inside `arguments` / `environment`, IDL and plugin locations, asset XML source locations, connection contracts and the four `implementation` strings. Do not copy the current checkout, user home, Windows drive, UNC share or WSL mount path into a reusable design simply because it was discovered during inspection.

Use the following conventions where appropriate; add references when needed and document their meaning. These names are a design convention, not additional required fields in the Designer schema.

| Reference | Meaning |
| --- | --- |
| `${WORKSPACE_ROOT}` | Root of the RTC-Agent-Tools workspace on the component's deployment host |
| `${FOUNDATION_ROOT}` | Selected compatible Hakoniwa Foundation installation root |
| `${DRONE_ROOT}` / `${VIEWER_ROOT}` | Selected Drone distribution / viewer checkout root |
| `${BUSINESS_PACK_ROOT}` | Referenced Business Pack checkout root |
| `${RECIPE_ROOT}` | This composition's prepared deployment/configuration directory |
| `${PYTHON_EXECUTABLE}` | Selected Python executable on the target host |

For example, a Python RTC's deployment metadata can express its paths as follows:

```json
{
  "host": "WSL2-Ubuntu",
  "executable": "${PYTHON_EXECUTABLE}",
  "workingDirectory": "${WORKSPACE_ROOT}",
  "arguments": "\"${WORKSPACE_ROOT}/build/generated/ExampleRTC/ExampleRTC.py\" -f \"${RECIPE_ROOT}/ExampleRTC.conf\"",
  "environment": "HAKO_CONFIG_PATH=${RECIPE_ROOT}/config/cpp_core_config.json"
}
```

This is design metadata, not a ready-to-run shell command. Do not assume that the Designer/server, rtc.conf loader, command interpreter or environment field performs variable expansion. Resolve path references through the deployment preparation procedure in [workspace.md](workspace.md), preserving arguments as data and applying the target tool's quoting rules.

Record reference definitions and required target hosts with the design, using a companion record keyed by component ID when the Designer cannot retain them. Keep concrete bindings in local deployment settings such as an env/INI file, outside the portable session and source/connection companions. A reference may have different Windows and WSL bindings; never reuse one host's path on the other without a verified translation. Relative paths must identify their base (for example, an XML path relative to a named source repository at a recorded revision). Preserve source URLs, revisions, hashes and catalog identity independently of local checkout locations.

Before upload or after design revision, inspect path-valued fields and embedded strings for machine-specific absolute paths, including drive-letter, UNC, `/home/`, `/Users/` and `/mnt/<drive>/` forms. Do not treat that short pattern list as exhaustive or blindly replace matching text: distinguish public URLs, semantic identifiers and evidence quotations from filesystem locations. Confirm all variable references have a documented meaning; missing local bindings may remain unresolved during design review but must block the affected execution. Retain a concrete design path only for an explicit user requirement or a verified external-format constraint, recording the reason, target host and limitation.

Do not apply this portability rule retroactively to original logs, resolved deployment snapshots or historical evidence. Those records must preserve the actual paths and revision tested. Keep resolved runtime artifacts separate from the portable authoritative design, with provenance linking them to its revision/hash.

### Ports and connections

Port IDs are unique within a component. DataPorts have `portType: "data"`, `direction: "in"` or `"out"`, and `dataType` with the exact qualified type name. Hakoniwa ports in the supplied sample also have integer `channelId` values:

```json
{ "id": "velocity_in", "name": "velocity_in", "portType": "data", "direction": "in", "dataType": "RTC::TimedVelocity2D", "channelId": 12 }
```

Preserve supplied channel IDs. Sample values 10, 11 and 12 are not global defaults or evidence of allocated runtime channels. Regular RTC ports need not carry `channelId`.

Edges reference component IDs and endpoint port IDs:

```json
{
  "id": "edge-source-asset",
  "source": "source-rtc-1",
  "sourceHandle": "out",
  "target": "asset-1",
  "targetHandle": "velocity_in",
  "data": { "connectionType": "data" },
  "markerEnd": { "type": "arrowclosed" }
}
```

This edge fragment requires an `asset-1` component with `data.moduleKind: "hakoniwa"` and the illustrated port; it is not part of the standalone root example above.

- Preserve edge IDs and display metadata such as `markerEnd`.
- Require an output source, input target and `connectionType: "data"`. RTC-only direct edges require matching `dataType` or an explicit converter. For mixed edges, endpoint types may differ only when an explicit typed RTC-to-PDU serializer mapping is recorded under the contract below. Asset-only PDU edges require matching message semantics and PDU mapping. Do not change an asset's cataloged type to an RTC type just to make names match.
- For asset-to-asset edges, check the intended PDU channel mapping, including agreement of channel IDs when both endpoints refer to the same channel. For mixed edges, resolve the Hakoniwa endpoint channel and RTC transport/serializer mapping.
- Type-name equality and channel IDs do not establish compatible PDU layout, robot identity, message semantics, writer ownership, or bridge implementation. For every mixed DataPort edge, use the OpenRTM-aist custom interface `dataport.interface_type:hakoniwa` and a suitable `dataport.marshaling_type`, with the contract in [hakoniwa-serializer.md](hakoniwa-serializer.md). Do not automatically translate mixed or asset-only edges into ordinary CORBA `rtcon` commands.
- The supplied sample contains only DataPorts. Confirm the Designer contract and interface compatibility for ServicePorts or other extensions; do not invent a version 2 ServicePort schema from this sample.

### Mixed-edge connection contracts

Keep a contract keyed by stable edge ID for every RTC/Hakoniwa DataPort edge. Record it in `work/connection-contracts.json` as local tool metadata when the Designer cannot preserve transport extensions, and summarize the mapping in the RTC's `implementation` fields. This companion is not a Designer API/schema feature or a runtime process configuration. It must contain the source/target instance and port IDs, endpoint kinds and types, custom interface and serializer identifiers, PDU mapping, ownership and readiness/evidence described in the transport guide. Do not invent fields in `edges[].data` and assume they are consumed by the Designer or runtime.

After retrieving an approved final session, reconcile every contract against the final instances, endpoints, types and PDU metadata. Removed edges lose their active contracts; changed edges require updated mappings. A stale companion cannot override the approved final design. Planned serializers can appear in a reviewable design, but their edges remain non-executable until implementation and verification. No unsupported serializer name is an existing factory merely because it is written in the contract.

### Legacy input and helper limitations

Detect legacy `nodes` / `rtcTemplates` input explicitly. Preserve the original and report its format. Migration must preserve IDs, ports, connections, implementation instructions and provenance, and resolve module kinds from evidence. Do not silently label every legacy node as an RTC or emit legacy fields as the new output contract.

`scripts/prepare_final_session.py` and `scripts/generate_runtime_batches.py` currently consume legacy sessions and contain assumptions specific to the earlier RTC example. Successful use on old inputs is not version 2 validation. Inspect and adapt them before use on version 2 or mixed systems; do not run legacy exporters or lifecycle generators against Hakoniwa assets as RTCs.

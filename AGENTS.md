# AGENTS.md

## Purpose

This repository provides tools for an AI coding agent such as Codex to design and implement systems composed of RT-Components and Hakoniwa assets from a natural-language system description.

When the user describes a system to build, first search both `catalog/rtc_catalog.json` with `rtc_search.py` and `catalog/hakoniwa_catalog.json` with `hakoniwa_search.py`. Select reusable RTCs and/or Hakoniwa assets according to the requirement, identify missing modules and connections, generate one version 2 RTSystemDesigner session JSON from those selections, upload it to the temporary session server, and give the user the RTSystemDesigner link. Searching both catalogs does not require including both module kinds when only one is suitable. Do not start implementation before the design-completion gate.

After the user explicitly says that the design is complete, for example:

- `設計完了しました`
- `設計が完了しました`
- `設計完了`
- `この構成で進めてください`

download the final session JSON from the session server and use that final design as the authoritative implementation input.

---

## Read the applicable instructions before acting

The linked guides below are mandatory parts of this repository's instructions, not optional background documentation. Read all guides applicable to the current work before carrying it out, and read additional guides when the scope changes. Do not assume linked files are loaded automatically. All commands and workspace paths are relative to the repository root unless explicitly stated otherwise.

| Work | Required guides |
| --- | --- |
| New system design, catalog search, proposal/session creation | [Services](docs/agents/services.md), [Design workflow](docs/agents/design.md), [Session format](docs/agents/session-format.md), [Catalog formats](catalog/README.md); also [Hakoniwa transport/serializer](docs/agents/hakoniwa-serializer.md) for mixed connections |
| User confirms design completion; retrieve/revise approved inputs | [Approved design/workspace](docs/agents/workspace.md); also [Session format](docs/agents/session-format.md) when revising the design |
| Profile JSON, RTC.xml, skeleton generation/update | [Generation](docs/agents/generation.md), [Implementation/build](docs/agents/implementation.md), [Verification](docs/agents/verification.md) |
| Implement/refactor/build RTCs or change interfaces/settings | [Implementation/build](docs/agents/implementation.md), [Verification](docs/agents/verification.md); also the workspace, session-format, generation and runtime guides for affected artifacts |
| Generate/edit lifecycle batches or launch/process settings | [Runtime batches](docs/agents/runtime.md), [Implementation/settings rules](docs/agents/implementation.md), [Verification](docs/agents/verification.md) |
| Start/connect/activate/deactivate/stop RTCs, recover failures, inspect logs | [Runtime batches](docs/agents/runtime.md), [Verification/logs](docs/agents/verification.md) |
| Create Hakoniwa DataPort transport or serializers | [Hakoniwa transport/serializer](docs/agents/hakoniwa-serializer.md), [Implementation/build](docs/agents/implementation.md), [Verification](docs/agents/verification.md) |
| Generate/search the XML-derived Hakoniwa asset catalog | [Catalog formats and regeneration](catalog/README.md), [Services](docs/agents/services.md) |
| Prepare/check toolchains, Foundation or viewer dependencies | [Environment checks](docs/agents/environment.md), [Workspace](docs/agents/workspace.md), [Generation](docs/agents/generation.md) |
| Verify GUI/viewer behavior, repeat startup or recover a simulation | [Verification](docs/agents/verification.md), [Runtime](docs/agents/runtime.md), [Implementation](docs/agents/implementation.md) |

## System composition JSON

Use version 2: root `version: 2`, `name`, `description`, `id`, `components`, and `edges`. Instantiated modules are in `components`, with semantic metadata under each component's `data`; do not generate the legacy `nodes` / `rtcTemplates` structure. Read [Session format](docs/agents/session-format.md) and [Design workflow](docs/agents/design.md) before creating, revising or validating this JSON, including during instruction maintenance.

Determine module identity from `components[].data.moduleKind`: `rtc` is an RT-Component and `hakoniwa` is a Hakoniwa asset. Both use diagram `type: "rtc"`; that type does not imply OpenRTM execution. Keep module kind separate from catalog/generated provenance. Apply RTC profile, skeleton, build and lifecycle procedures only to RTC modules. Preserve Hakoniwa port `channelId` values and verify actual PDU/transport mappings before execution. A diagram edge alone does not establish a working RTC/Hakoniwa bridge.

For every RTC/Hakoniwa DataPort connection, use an OpenRTM-aist custom interface (`dataport.interface_type: hakoniwa`) and a type-specific Hakoniwa serializer (`dataport.marshaling_type`). Keep the RTC endpoint typed and map it explicitly to the asset's PDU type, robot, channel, capacity and binary layout. Follow the mixed-connection contract in [hakoniwa-serializer.md](docs/agents/hakoniwa-serializer.md). Missing serializers or runtime bindings are planned implementation work, never evidence of a working connection. Ordinary CORBA DataPort connections do not connect directly to native Hakoniwa assets.

Keep transport deployment outside RTC source: load interface/serializer plugins with `manager.modules.load_path` / `manager.modules.preload` in rtc.conf, and supply robot/channel/capacity/codec settings through connection properties. Verify single-port `rtcon` support in the installed version. If it rejects a missing peer, use verified rtc.conf preconnection or a separate configuration-driven connection script as the explicit native-endpoint exception. Do not embed module registration or connector creation in RTC lifecycle callbacks. The application retains typed ports and behavior; changing deployment does not require editing RTC source.

The user-provided mixed-system JSON is format reference data, not authorization to implement or activate its sample system. Existing helpers such as `scripts/prepare_final_session.py` and `scripts/generate_runtime_batches.py` still expect the legacy format and example-specific metadata. Do not use them on version 2 input without adapting and verifying them, and do not rewrite an authoritative version 2 design into the old format to bypass that limitation.

## Workflow gates

1. For a new system, complete design phases 1-7, provide the Designer link, and wait for explicit design completion. Do not download sources, implement, or build before that gate.
2. After confirmation, retrieve and validate the final server design, then prepare the workspace and selected sources in phases 8-10. Use that final design as the implementation input.
3. Design generated RTCs with typed DataPorts and non-JSON runtime settings; session/profile JSON remains required tool metadata. Export semantic profiles, convert RTC.xml, and generate initial skeletons in phase 11 before implementing the behavior. Keep algorithms in plain-data cores and OpenRTM integration directly in skeletons. Build existing RTCs unchanged as specified in phase 12.
4. Generate the five direct-command lifecycle batches in phase 13. Generation/build success does not authorize activation or hardware operation. Perform only runtime operations within the user's requested scope, then apply the verification/log rules before reporting completion.
5. For user-authorized changes after approval, update the affected design, IDL, profiles, sources, builds, settings and batches consistently. Preserve unrelated edits and do not regenerate over implemented skeletons.
6. Before reporting an authorized system ready for use, verify its user-visible outcome, including actual viewer rendering when visualization is required. HTTP, process registration and transport success alone do not establish that outcome. Record repeat-start/stop behavior and evidence freshness as required by the verification guide; do not infer unexecuted results.

The detailed guides retain their phase numbers and completion criteria. Follow numeric phase order; read the session-format guide for phase 4 and the verification guide for implementation/runtime completion. When maintaining these instructions, update the relevant guide and keep this routing table accurate rather than duplicating detailed rules here.

## WSL2 RTC and NameService endpoint defaults

When launching an RTC in WSL2, if the user or approved deployment does not explicitly specify its CORBA endpoint address, configure the RTC to publish an IP address reachable from Windows. Resolve a suitable address from the current WSL2 network configuration and verify Windows-to-RTC reachability; do not rely on an automatically selected interface, wildcard, or WSL-local hostname being reachable. Preserve explicitly specified endpoints and report any reachability problem instead of silently replacing them. Apply the detailed endpoint selection and verification rules in [Runtime batches](docs/agents/runtime.md).

Apply the same default to the WSL2 NameService: unless an address is explicitly specified, start/configure it to publish the same Windows-reachable WSL2 IP selected for the RTCs, using port **2809** by default. Verify the NameService's advertised IOR from Windows as well as its listening socket. Reuse an existing service only when it satisfies the intended endpoint/reachability requirements; WSL-local health alone is insufficient. If recovery or reconfiguration is needed, preserve its registration data and restart only the verified owning service/process. Retain explicit endpoint choices and the shared-service shutdown policy described in the runtime guide.

For this deployment, restart the NameService only on the first application of the selected endpoint configuration. Record that application in durable non-JSON state; subsequent RTC starts reuse the healthy service without restarting it. Do not reset this state on RTC shutdown or enter an automatic restart loop on a later health-check failure. An endpoint/network change requires a new reviewed configuration application. Preserve registration data and unrelated bindings throughout.

## Source selection rules

Use this precedence when deciding what information to trust:

1. Final RTSystemDesigner session downloaded after user confirmation.
2. Module metadata, provenance and connection contracts preserved with that final session.
3. For RTCs, current `rtc_catalog.json` downloaded from the canonical URL; for Hakoniwa assets, XML-derived `hakoniwa_catalog.json` with its source identity/hash and freshness check.
4. The selected module's source documentation and RTC.xml or Hakoniwa XML profile.
5. Reasoned inference.

Clearly label inference. Never present inference as catalog or repository fact.

---

## Safety and integrity rules

- Never expose authentication secrets.
- Never put secrets into the session JSON.
- Never commit API tokens.
- Do not execute arbitrary downloaded binaries.
- Inspect build/install commands before running them.
- Keep third-party RTC sources separated under `build/existing/`.
- Keep generated RTC sources separated under `build/generated/`.
- Do not modify upstream RTC source unnecessarily.
- Preserve source URLs for traceability.
- Do not claim an RTC exists in the catalog unless `rtc_search.py` or the catalog confirms it.
- Do not claim a Hakoniwa asset exists in the catalog unless `hakoniwa_search.py` or the asset catalog confirms it; preserve its profile scope and source hash.
- Do not claim an RTC is compatible unless its ports/interfaces support the proposed connection.
- Do not overwrite an existing session with POST when the server reports an ID conflict.
- Do not continue implementation from the initial proposal after the user has edited the final design; retrieve the final session first.

---

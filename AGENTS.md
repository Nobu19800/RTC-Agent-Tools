# AGENTS.md

## Agent guide language

1. Use the agent-guide language explicitly requested by the user when it is Japanese or English. This choice is independent of the language requested for the response.
2. Otherwise, use the language of the current task request. If it is unclear or neither Japanese nor English, use English.
3. Open the matching index, [日本語](docs/agents/ja/README.md) or [English](docs/agents/en/README.md). For any applicable link below of the form `docs/agents/<guide>.md`, read `docs/agents/ja/<guide>.md` or `docs/agents/en/<guide>.md` according to that choice. The unqualified links are compatibility entry points.

The shared rules in this file apply in both languages. Use the selected guide as the working entry point. When it links to a detailed original for a command, data format, or exceptional case, consult the relevant section as needed and keep user-facing output in the requested response language. Update both localized guides when changing a procedure.

## Purpose

This repository provides tools for an AI coding agent such as Codex to design and implement systems composed of RT-Components and Hakoniwa assets from a natural-language system description.

When the user describes a system to build, search the RTC, Hakoniwa, and ROS 2 catalogs with `rtc_search.py`, `hakoniwa_search.py`, and `python scripts/ros2_system.py search`. Select reusable modules according to the requirement, identify missing modules and connections, generate one version 2 RTSystemDesigner session JSON, upload it to the configured session server, and provide the design link. Do not start implementation before the design-completion gate.

After the user explicitly says that the design is complete, for example:

- `設計完了しました`
- `設計が完了しました`
- `設計完了`
- `この構成で進めてください`

load the final design as described in [Approved design/workspace](docs/agents/workspace.md#phase-8-on-design-complete-load-the-final-design) and use it as the authoritative implementation input.

## Designer-first mode

When the user wants to design the system from scratch in RTSystemDesigner, let the user author the design on the Designer canvas. Use this mode when the user explicitly chooses it or asks to load a design they authored in Designer. Skip the agent-generated proposal and its upload.

- For a fresh canvas, the user builds the design with the Designer's module and connection tools, then exports the version 2 JSON using **JSON出力** and provides the file or its path.
- For a design already backed by a session, the user saves it in Designer and provides its URL or session ID. Retrieve it from the matching session server. Use [the local session client](docs/local-designer.md) for local integration and [the services guide](docs/agents/services.md) for the configured public service.
- A request to load a design authorizes read-only review. Check the version 2 structure, module kinds, ports, connections, and applicable transport mappings. Summarize the loaded composition and identify missing settings. Preserve the supplied design and report material changes for user review before applying them.
- Once the user confirms design completion, use the confirmed export or retrieve the latest saved session. Continue from phase 8 in [Approved design/workspace](docs/agents/workspace.md#phase-8-on-design-complete-load-the-final-design).

---

## Read the applicable instructions before acting

The linked guides below are mandatory parts of this repository's instructions, not optional background documentation. Read all guides applicable to the current work before carrying it out, and read additional guides when the scope changes. Do not assume linked files are loaded automatically. All commands and workspace paths are relative to the repository root unless explicitly stated otherwise.

| Work | Required guides |
| --- | --- |
| New system design, catalog search, proposal/session creation | [Services](docs/agents/services.md), [Design workflow](docs/agents/design.md), [Session format](docs/agents/session-format.md), [Catalog formats](catalog/README.md); also [Hakoniwa transport/serializer](docs/agents/hakoniwa-serializer.md) for mixed connections |
| Design or deploy RTCs that create DataPorts from peer ports, such as ExcelControlpy or OOo Calc | [Dynamic RTC ports](docs/agents/dynamic-rtc-ports.md), [Session format](docs/agents/session-format.md), [Runtime batches](docs/agents/runtime.md) when deploying |
| Select or launch an OpenRTM sample RTC | [OpenRTM sample workflow](docs/agents/openrtm-samples.md), [Runtime batches](docs/agents/runtime.md) when deploying |
| Load a user-authored Designer export or saved session | [Session format](docs/agents/session-format.md), [Approved design/workspace](docs/agents/workspace.md); [Services](docs/agents/services.md) when accessing a session server |
| User confirms design completion; retrieve/revise approved inputs | [Approved design/workspace](docs/agents/workspace.md); also [Session format](docs/agents/session-format.md) when revising the design |
| Profile JSON, RTC.xml, skeleton generation/update | [Generation](docs/agents/generation.md), [Implementation/build](docs/agents/implementation.md), [Verification](docs/agents/verification.md) |
| Implement/refactor/build RTCs or change interfaces/settings | [Implementation/build](docs/agents/implementation.md), [Verification](docs/agents/verification.md); also the workspace, session-format, generation and runtime guides for affected artifacts |
| User requests static analysis or unit tests for newly implemented C++, Python, or Lua modules | [On-request module checks](docs/agents/module-checks.md) |
| Generate/edit lifecycle batches or launch/process settings | [Runtime batches](docs/agents/runtime.md), [Implementation/settings rules](docs/agents/implementation.md), [Verification](docs/agents/verification.md) |
| Start/connect/activate/deactivate/stop RTCs, recover failures, inspect logs | [Runtime batches](docs/agents/runtime.md), [Verification/logs](docs/agents/verification.md) |
| Create Hakoniwa DataPort transport or serializers | [Hakoniwa transport/serializer](docs/agents/hakoniwa-serializer.md), [Implementation/build](docs/agents/implementation.md), [Verification](docs/agents/verification.md) |
| Generate/search the XML-derived Hakoniwa asset catalog | [Catalog formats and regeneration](catalog/README.md), [Services](docs/agents/services.md) |
| Search, place, or launch ROS 2 nodes | [ROS 2 workflow](docs/agents/ros2.md), [Catalog formats](catalog/README.md) |
| Connect RTC DataPorts to ROS 2 topics | [ROS2Transport settings](docs/agents/ros2-transport.md) |
| Connect Hakoniwa PDU channels to ROS 2 topics or add a viewer to that system | [Hakoniwa–ROS 2 integration](docs/agents/hakoniwa-ros2.md), [ROS 2 workflow](docs/agents/ros2.md) |
| Install OpenRTM-aist on Windows, Ubuntu or WSL2, or install ROS 2 or Hakoniwa on Ubuntu or WSL2 | [Runtime installation](docs/agents/install-runtime.md), [Environment checks](docs/agents/environment.md) |
| Prepare/check toolchains, Foundation or viewer dependencies | [Environment checks](docs/agents/environment.md), [Workspace](docs/agents/workspace.md), [Generation](docs/agents/generation.md) |
| Verify GUI/viewer behavior, repeat startup or recover a simulation | [Verification](docs/agents/verification.md), [Runtime](docs/agents/runtime.md), [Implementation](docs/agents/implementation.md) |

## System composition JSON

If existing RTCs meet the functional requirements and their DataPorts differ only in representation, prefer reusing both RTCs through a custom serializer and deserializer over generating a replacement RTC. Preserve the original port types and component source. Record the semantic mapping, wire format, shared `dataport.marshaling_type`, plugin loading, and runtime checks in the design. Verify that the selected OpenRTM-aist implementations can negotiate the typed connection, and verify data transfer after design approval. Mark unsupported negotiation or unresolved semantics as a design blocker.

Register each codec for its endpoint's original IDL type and preload it before the RTC creates its DataPorts. Verify the shared serializer identifier in both live port profiles. If `rtcon` rejects the distinct IDL types in its client-side check, the connection batch may invoke a dedicated `PortService.connect` helper for that approved edge. Require the helper to verify both port profiles and the codec before connecting. Follow [Design workflow](docs/agents/design.md) for the wire contract and runtime verification.

When an existing RTC creates DataPorts from a selected peer, derive the planned ports during design generation and place them in `components[].data.ports`. Connect them with ordinary v2 `edges` so they are visible in RTSystemDesigner. Follow [Dynamic RTC ports](docs/agents/dynamic-rtc-ports.md) for direction, supported types, naming and runtime reconciliation.

For ExcelControlpy and LibreOffice Calc RTCs based on CalcControl, record each spreadsheet port's sheet, starting cell or range, and whether the cell advances after each sample in RTSystemDesigner's **Implementation → Requirements** (`components[].data.implementation.requirements`). For advancing ports, state the direction and what triggers advancement. Read these settings from the confirmed design when configuring the RTC. Follow the startup and verification procedure in [Dynamic RTC ports](docs/agents/dynamic-rtc-ports.md).

Use version 2: root `version: 2`, `name`, `description`, `id`, `components`, and `edges`. Instantiated modules are in `components`, with semantic metadata under each component's `data`; do not generate the legacy `nodes` / `rtcTemplates` structure. Read [Session format](docs/agents/session-format.md) and [Design workflow](docs/agents/design.md) before creating, revising or validating this JSON, including during instruction maintenance.

Determine module identity from `components[].data.moduleKind`: `rtc` is an RT-Component, `hakoniwa` is a Hakoniwa asset, and `ros2` is a ROS 2 node. They share diagram `type: "rtc"`. Apply RTC generation, build and lifecycle procedures to RTC modules. Preserve Hakoniwa port `channelId` values and verify PDU/transport mappings. For ROS 2 deployment settings, topic/service/action handling and runtime commands, follow [the ROS 2 workflow](docs/agents/ros2.md).

For every RTC/Hakoniwa DataPort connection, use an OpenRTM-aist custom interface (`dataport.interface_type: hakoniwa`) and a type-specific Hakoniwa serializer (`dataport.marshaling_type`). Keep the RTC endpoint typed and map it explicitly to the asset's PDU type, robot, channel, capacity and binary layout. Follow the mixed-connection contract in [hakoniwa-serializer.md](docs/agents/hakoniwa-serializer.md). Missing serializers or runtime bindings are planned implementation work, never evidence of a working connection. Ordinary CORBA DataPort connections do not connect directly to native Hakoniwa assets.

Run the approved modules as separate components wherever the design specifies them. For an RTC, verify its instance and live ports through the intended NameService. A test harness that calls a component's callbacks or writes PDUs directly may verify an individual layer. Record that scope and separately verify the approved runtime before reporting it operational. For simulator systems with a viewer, follow the [runtime guide](docs/agents/runtime.md) for registration order, restart, and shutdown.

Keep transport deployment outside RTC source: load interface/serializer plugins with `manager.modules.load_path` / `manager.modules.preload` in rtc.conf, and supply robot/channel/capacity/codec settings through connection properties. Verify single-port `rtcon` support in the installed version. If it rejects a missing peer, use verified rtc.conf preconnection or a separate configuration-driven connection script as the explicit native-endpoint exception. Do not embed module registration or connector creation in RTC lifecycle callbacks. The application retains typed ports and behavior; changing deployment does not require editing RTC source.

The user-provided mixed-system JSON is format reference data, not authorization to implement or activate its sample system. Existing helpers such as `scripts/prepare_final_session.py` and `scripts/generate_runtime_batches.py` still expect the legacy format and example-specific metadata. Do not use them on version 2 input without adapting and verifying them, and do not rewrite an authoritative version 2 design into the old format to bypass that limitation.

## Portable paths in design information

Keep design information independent of a particular machine. By default, do not put local absolute paths (Windows drive/UNC paths, user home directories, WSL mount paths, or installation directories) into proposed/final session JSON, connection contracts, provenance companions or implementation instructions. Use named references such as `${WORKSPACE_ROOT}`, `${FOUNDATION_ROOT}`, `${DRONE_ROOT}`, `${VIEWER_ROOT}`, `${BUSINESS_PACK_ROOT}`, `${RECIPE_ROOT}` or `${PYTHON_EXECUTABLE}`. Repository-relative paths are also suitable when their base repository/root is explicitly identified. Apply this rule to paths embedded in arguments, environment strings, lists and notes as well as dedicated path fields.

Define each reference's meaning and target host; keep its actual local value in environment-specific deployment settings outside the portable design. Resolve and validate references when preparing deployment, then generate correctly quoted host-specific settings/commands without replacing references in the authoritative design. `${NAME}` is design notation, not a claim that RTSystemDesigner, the session server, rtc.conf or every shell expands it automatically. Missing bindings remain explicit and block the affected execution, not design review. Never invent local values or use shell evaluation to resolve design strings.

Preserve public source URLs, component IDs and revisions as identities rather than replacing them with path variables. Actual paths in original logs and verification evidence remain valid historical facts; do not rewrite that evidence to make it portable. Include a concrete local path in reusable design information only when the user explicitly requires it or a verified external format makes it unavoidable; document the reason, host and portability limitation. Follow the detailed examples and validation rules in [Session format](docs/agents/session-format.md) and the deployment resolution procedure in [Approved design/workspace](docs/agents/workspace.md).

## Workflow gates

Run static analysis and unit tests for newly implemented modules only when the user explicitly requests the respective check. A request to build, deploy, or run the system does not trigger these checks. Keep them out of automatic workflows and default build targets. For C++ use Clang and GoogleTest, for Python use Bandit, flake8, and pytest, and for Lua use Luacheck and LuaUnit. Display a coverage report whenever running the requested unit tests, following [On-request module checks](docs/agents/module-checks.md).

Run the requested checks independently so that static-analysis findings do not prevent unit tests or coverage from running. Use fresh coverage data and report the exact files and line or branch counts measured. When tests use doubles for middleware or measure only a logic or codec module, report build, analysis, unit tests, and live integration as separate results. Keep findings visible when the request is to measure the current implementation. See the worked examples for [Python](docs/drone-adapter-checks.md), [C++](docs/drone-adapter-cpp-checks.md), and [Lua](docs/lua-rtc-checks.md).

Whenever presenting system design information to the user, including a proposal, a revised design, or a design loaded from RTSystemDesigner, show a component table alongside the design link or file. List every instantiated component in the presented design with its instance name, module name, module kind, and implementation status (`既存` for reuse or `新規` for an implementation to create). If the design and its provenance do not establish the status, show `未確認`. A new instance of an existing implementation is `既存`. Follow [the design presentation format](docs/agents/design.md#phase-7-show-the-design-link-and-stop-implementation).

1. For an agent-designed system, complete design phases 1-7 and provide the Designer link. For Designer-first mode, load and review the user-authored design. Wait for explicit design completion before downloading component sources, implementing, or building.
2. After confirmation, load and validate the final session or confirmed JSON export, then prepare the workspace and selected sources in phases 8-10. Use that final design as the implementation input.
3. Design generated RTCs with typed DataPorts and non-JSON runtime settings; session/profile JSON remains required tool metadata. Export semantic profiles, convert RTC.xml, and generate initial skeletons in phase 11 before implementing the behavior. Keep algorithms in plain-data cores and OpenRTM integration directly in skeletons. Build existing RTCs unchanged as specified in phase 12.
4. Generate the five direct-command lifecycle batches in phase 13. Generation/build success does not authorize activation or hardware operation. Perform only runtime operations within the user's requested scope, then apply the verification/log rules before reporting completion.
5. For user-authorized changes after approval, update the affected design, IDL, profiles, sources, builds, settings and batches consistently. Preserve unrelated edits and do not regenerate over implemented skeletons.
6. Before reporting an authorized system ready for use, verify its user-visible outcome within the authorized scope. During pre-run verification, request permission for GUI operation and perform the check only if the user explicitly requests it. General build, run, and verification requests do not authorize that check. If the user did not request GUI operation, complete available non-GUI checks first. When execution is authorized and those checks reveal no blocker, start the system without waiting for GUI verification. Tell the user which window or URL to open, what to do, what result to expect, and which GUI behavior remains unverified. HTTP, process registration, and transport checks alone do not verify rendering. Record repeat-start/stop behavior and evidence freshness.

The detailed guides retain their phase numbers and completion criteria. Follow numeric phase order; read the session-format guide for phase 4 and the verification guide for implementation/runtime completion. When maintaining these instructions, update the relevant guide and keep this routing table accurate rather than duplicating detailed rules here.

## ROS 2 integration

Use [the ROS 2 workflow](docs/agents/ros2.md) for catalog selection, node deployment, and ROS interfaces. Register the v2 session in RTSystemDesigner, then retrieve the approved version before preparing runtime settings.

- For RTC DataPort ↔ ROS 2 topic connections, use [ROS2Transport](docs/agents/ros2-transport.md). Match the RTC serializer, ROS message type, topic, direction, DDS domain, and QoS. Use the named C++ module when the RTC must appear in the ROS 2 graph.
- For Hakoniwa asset ↔ ROS 2 topic connections, use a [PDU-to-ROS bridge](docs/agents/hakoniwa-ros2.md). Show the bridge as an independent module and identify the PDU and ROS 2 legs on the diagram. Preserve the asset's PDU identity and layout. Include the viewer path when visualization is part of the design.
- Verify actual data transfer in addition to node and topic discovery. Use the selected design's configuration and retain evidence for each implemented connection.

## Git installation

Before cloning RTC-Agent-Tools or component repositories, run `git --version` in the shell that will run `git clone`. If it succeeds, reuse the installed Git. Otherwise, install Git in that environment:

| Environment | Installation |
| --- | --- |
| Windows (PowerShell) | Run `winget install --id Git.Git --exact --source winget`. If WinGet is unavailable, use the standalone installer for the host architecture from [Git for Windows](https://git-scm.com/install/win). Open a new PowerShell session to pick up PATH changes. |
| Ubuntu | Run `sudo apt update`, then `sudo apt install git` using the Ubuntu package repositories. [Git for Linux](https://git-scm.com/install/linux.html) |
| WSL2 (Ubuntu) | Open the Ubuntu distribution that will perform the clone, then run `sudo apt update` and `sudo apt install git` inside its shell. Check and use the Linux `git` in that distribution. |

Run `git --version` again in the target shell before cloning. For the first clone of RTC-Agent-Tools, this check takes place before the local copy of this guide is available.

## Runtime installation

### OpenRTM Lua (RTM-Lua)

Reuse a compatible Lua 5.1 and LuaRocks installation when available. Choose the interpreter that will run the RTC and install rocks for that same Lua version and architecture.

- **Windows:** Follow the [official Windows instructions](https://nobu19800.github.io/RTM-Lua/docs/Windows.html). Install Lua for Windows, then run `luarocks install openrtm 0.4-12` from an elevated terminal for a system-wide installation. The upstream source-install alternative is to extract RTM-Lua and run its `install.bat` from an elevated terminal. Use a shell that can resolve the selected Lua and LuaRocks.
- **Ubuntu / WSL2:** Inside the target Ubuntu environment, run `sudo apt-get install lua5.1 luarocks`, then `sudo luarocks --lua-version=5.1 install openrtm`. If loading RTM-Lua fails because OiL was omitted, follow the upstream fallback `sudo luarocks --lua-version=5.1 install oil` and recheck the load. [Official Ubuntu instructions](https://nobu19800.github.io/RTM-Lua/docs/Ubuntu.html)

- **Explicit CORBA endpoint on Windows and WSL2:** Inspect the installed `openrtm/Manager.lua`. If it still contains `local uriport = uriobj.getPort()`, back up that file and replace the line with `local uriport = tonumber(uriobj:getPort())`. The colon supplies the receiver, and OiL requires a numeric port. Verify RTC creation and registration with the explicit endpoint after applying the fix.
- **UUID on WSL2 with RTM-Lua 0.5-3:** Pin `uuid` to `0.2-1` in the same Lua 5.1 rock tree as `openrtm`. For a user tree at `$HOME/.local/rtm-lua`, run `luarocks --lua-version=5.1 --tree="$HOME/.local/rtm-lua" install uuid 0.2-1` and verify the selected version with `luarocks --lua-version=5.1 --tree="$HOME/.local/rtm-lua" list uuid`. UUID 1.0.0-1 requires RNG configuration that this RTM-Lua version does not perform. If the OpenRTM source rock fails to unpack, use the official checkout and build its rockspec with `luarocks --lua-version=5.1 --tree="$HOME/.local/rtm-lua" make spec/openrtm-0.5-3.rockspec`.

In the target shell verify `lua -v` (or `lua5.1 -v`) and `lua5.1 -e 'assert(require("openrtm"))'` using the selected executable name. If connecting to other OpenRTM implementations, check that the chosen RTM-Lua distribution supports the required standard DataPort transport, such as `corba_cdr`. Apply the shared NameService and advertised endpoint rules below. Do not assume that RTM-Lua exposes custom serializer configuration. Prefer an RTC with matching port types for Lua examples, or document the conversion on a runtime that supports it. [Upstream transport variants](https://nobu19800.github.io/RTM-Lua/docs/#ダウンロード)

For RTM-Lua interoperation, inspect the live port profiles if rtshell rejects a connection that appears compatible. When the profiles confirm matching types, directions, and transport, a scoped `PortService.connect` call can establish the approved connection. Check its return code and verify the receiver's actual values. With console samples, activate the receivers before the sender. If logs are redirected, use unbuffered output when checking for the final received sample. See the [Windows and WSL2 example](docs/lua-rtc-checks.md#windows-と-wsl2-での-rtc-間通信).

Follow [Runtime installation](docs/agents/install-runtime.md) for OpenRTM-aist, ROS 2, and Hakoniwa. On Windows, use the newest compatible OpenRTM-aist MSI and reuse installed Visual Studio, Python, and CMake when compatible. On Ubuntu and WSL2, use the official OpenRTM-aist installation procedure and select ROS 2 for the actual Ubuntu release. For Hakoniwa on either Ubuntu host, start with the [Hakoniwa Business Pack AGENTS.md](https://github.com/hakoniwalab/hakoniwa-business-pack/blob/main/AGENTS.md) and follow the selected Recipe's Workspace and Foundation procedures.

## C++ OpenRTM-aist in WSL2

After setting up the official APT source, check the candidate for `openrtm2` with `apt-cache policy openrtm2`. If the candidate is `2.1.0-0`, build and use the C++ runtime from the OpenRTM-aist source repository. If APT offers a newer version, use the APT package. See [Runtime installation](docs/agents/install-runtime.md).

## One NameService per machine

Run or reuse one CORBA NameService on each participating machine that runs RTCs. Register each RTC with the NameService on its own machine. For cross-machine connections, resolve each RTC using its own machine's NameService and verify that its advertised RTC IOR is reachable. Configure management tools to query each machine as needed. Use port **2809** by default on each machine.

### Windows and WSL2 on the same machine

Use one shared CORBA NameService instance across Windows and all participating WSL2 distributions. Before starting RTCs or a NameService, inspect listeners and service ownership on Windows and in the participating distributions. Reuse the existing instance if both environments can query its root naming context through its advertised IOR. If none is running, start one instance on either Windows or WSL2, using port **2809** by default. Configure all participating RTCs and clients, including rtshell and RTSystemEditor, to use the same shared endpoint. Verify CORBA access from both environments and from any additional host in the approved deployment.

If multiple instances already exist, or the sole instance is reachable only from one environment, identify the owners and affected users and report the conflict. Resolve it through an authorized consolidation or reconfiguration that preserves required registrations and unrelated workloads. A failed reachability check must never trigger a second instance. Keep shared infrastructure running when stopping individual systems.

For Docker deployments using bridge networking, run one dedicated CORBA NameService in each container that runs OpenRTM RTCs. Configure the RTCs in each container to register with their container's instance. Port **2809** can be reused inside each isolated container. If clients connect from outside a container, configure distinct host ports when publishing ports on the same host address, and verify that each NameService and RTC advertises an IOR reachable by the intended clients. The shared Windows/WSL2 rule still applies to native processes and containers using host networking.

When launching an RTC in WSL2, if the user or approved deployment does not explicitly specify its CORBA endpoint address, configure the RTC to publish an IP address reachable from Windows. Resolve a suitable address from the current WSL2 network configuration and verify Windows-to-RTC reachability; do not rely on an automatically selected interface, wildcard, or WSL-local hostname being reachable. Preserve explicitly specified endpoints and report any reachability problem instead of silently replacing them. Apply the detailed endpoint selection and verification rules in [Runtime batches](docs/agents/runtime.md).

If the shared NameService runs in WSL2 and its address is unspecified, publish a WSL2 IP reachable from Windows. If it runs in Windows, publish a Windows address reachable from WSL2. Verify the listening socket and published IOR separately. Preserve explicit endpoint choices and report any reachability conflict. Restart only the verified owning service or process when applying an authorized endpoint change, and preserve its registration data.

For this deployment, restart the NameService only on the first application of the selected endpoint configuration. Record that application in durable non-JSON state; subsequent RTC starts reuse the healthy service without restarting it. Do not reset this state on RTC shutdown or enter an automatic restart loop on a later health-check failure. An endpoint/network change requires a new reviewed configuration application. Preserve registration data and unrelated bindings throughout.

## Source selection rules

For ROS2Transport, verify the connector on the actual RTC port before activation. A standard sample may create its RTC after Manager startup preconnect has already run. In that case, load the transport and serializer through runtime configuration and create the missing single-port connector after registration, following [ROS2Transport settings](docs/agents/ros2-transport.md). Confirm delivery with a ROS 2 subscriber and the receiving application. Graph discovery alone can omit an endpoint that is delivering data.

When a connection requires data conversion, prefer a type-specific serializer or deserializer at the transport boundary. Keep existing modules, port types, and interfaces intact. Implement only the directions the connection uses. Record the field mapping, units, limits, serializer registration, and compatibility with the selected transport in the design, then verify the conversion on the actual data path. Use a separate adapter when the transport cannot support the mapping or when the behavior needs state, sequencing, or coordination outside serialization.

Use this precedence when deciding what information to trust:

1. Final saved RTSystemDesigner session retrieved after user confirmation, or the RTSystemDesigner JSON export confirmed by the user.
2. Module metadata, provenance and connection contracts preserved with that final session.
3. For RTCs, current `rtc_catalog.json` downloaded from the canonical URL and the separately maintained `catalog/openrtm_samples_catalog.json` for installed examples. For Hakoniwa assets, use XML-derived `hakoniwa_catalog.json` with its source identity/hash and freshness check.
4. The selected module's source documentation and RTC.xml or Hakoniwa XML profile.
5. Reasoned inference.

Clearly label inference. Never present inference as catalog or repository fact.

Search [the OpenRTM sample catalog](catalog/openrtm_samples_catalog.json) alongside the general RTC catalog. Identify the sample by component name and implementation language. When the approved sample has `launch.kind: installed`, use the installed deployment for the target host and verify its files before starting. Follow [OpenRTM sample workflow](docs/agents/openrtm-samples.md).

---

## Safety and integrity rules

- Never expose authentication secrets.
- Never put secrets into the session JSON.
- Never commit API tokens.
- Do not execute arbitrary downloaded binaries.
- Inspect build/install commands before running them.
- Keep third-party RTC sources separated under `build/existing/`.
- Keep generated RTC sources separated under `build/generated/`.
- Preserve existing components' source and behavior. Obtain the user's explicit approval before making any change to an existing component other than a bug fix. This includes changes to its UI, controls, behavior, ports, and interfaces, whether implemented in the source, a wrapper, or a local copy. Show the proposed change and its effect before asking. Approval of a system design or a request to start or verify a system does not by itself approve an undisclosed component change. Prefer an independent adapter that leaves the existing component intact, when the approved design calls for adaptation.
- Preserve source URLs for traceability.
- Do not claim an RTC exists in the catalog unless `rtc_search.py` or the catalog confirms it.
- Do not claim a Hakoniwa asset exists in the catalog unless `hakoniwa_search.py` or the asset catalog confirms it; preserve its profile scope and source hash.
- Do not claim an RTC is compatible unless its ports/interfaces support the proposed connection.
- Do not overwrite an existing session with POST when the server reports an ID conflict.
- Do not continue implementation from the initial proposal after the user has edited the final design; retrieve the final session first.

---

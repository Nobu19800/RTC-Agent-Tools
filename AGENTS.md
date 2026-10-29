# AGENTS.md

## Purpose

This repository provides tools for an AI coding agent such as Codex to design and implement RT-Middleware systems from a natural-language system description.

When the user describes a system to build, do not immediately start implementing RT-Components. First perform system design by searching the RTC catalog, selecting reusable RTCs, defining any missing RTCs, generating a RTSystemDesigner session JSON, uploading it to the temporary session server, and giving the user the RTSystemDesigner link.

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
| New system design, catalog search, proposal/session creation | [Services](docs/agents/services.md), [Design workflow](docs/agents/design.md), [Session format](docs/agents/session-format.md) |
| User confirms design completion; retrieve/revise approved inputs | [Approved design/workspace](docs/agents/workspace.md); also [Session format](docs/agents/session-format.md) when revising the design |
| Profile JSON, RTC.xml, skeleton generation/update | [Generation](docs/agents/generation.md), [Implementation/build](docs/agents/implementation.md), [Verification](docs/agents/verification.md) |
| Implement/refactor/build RTCs or change interfaces/settings | [Implementation/build](docs/agents/implementation.md), [Verification](docs/agents/verification.md); also the workspace, session-format, generation and runtime guides for affected artifacts |
| Generate/edit lifecycle batches or launch/process settings | [Runtime batches](docs/agents/runtime.md), [Implementation/settings rules](docs/agents/implementation.md), [Verification](docs/agents/verification.md) |
| Start/connect/activate/deactivate/stop RTCs, recover failures, inspect logs | [Runtime batches](docs/agents/runtime.md), [Verification/logs](docs/agents/verification.md) |

## Workflow gates

1. For a new system, complete design phases 1-7, provide the Designer link, and wait for explicit design completion. Do not download sources, implement, or build before that gate.
2. After confirmation, retrieve and validate the final server design, then prepare the workspace and selected sources in phases 8-10. Use that final design as the implementation input.
3. Design generated RTCs with typed DataPorts and non-JSON runtime settings; session/profile JSON remains required tool metadata. Export semantic profiles, convert RTC.xml, and generate initial skeletons in phase 11 before implementing the behavior. Keep algorithms in plain-data cores and OpenRTM integration directly in skeletons. Build existing RTCs unchanged as specified in phase 12.
4. Generate the five direct-command lifecycle batches in phase 13. Generation/build success does not authorize activation or hardware operation. Perform only runtime operations within the user's requested scope, then apply the verification/log rules before reporting completion.
5. For user-authorized changes after approval, update the affected design, IDL, profiles, sources, builds, settings and batches consistently. Preserve unrelated edits and do not regenerate over implemented skeletons.

The detailed guides retain their phase numbers and completion criteria. Follow numeric phase order; read the session-format guide for phase 4 and the verification guide for implementation/runtime completion. When maintaining these instructions, update the relevant guide and keep this routing table accurate rather than duplicating detailed rules here.

## Source selection rules

Use this precedence when deciding what information to trust:

1. Final RTSystemDesigner session downloaded after user confirmation.
2. RTC metadata and provenance explicitly stored in that final session.
3. Current `rtc_catalog.json` downloaded from the canonical URL.
4. RTC repository documentation and RTC.xml.
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
- Do not claim an RTC is compatible unless its ports/interfaces support the proposed connection.
- Do not overwrite an existing session with POST when the server reports an ID conflict.
- Do not continue implementation from the initial proposal after the user has edited the final design; retrieve the final session first.

---

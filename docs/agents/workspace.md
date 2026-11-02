# Approved design and build workspace

Part of the mandatory repository instructions linked from [AGENTS.md](../../AGENTS.md).
Read when the user confirms design completion or an approved design must be retrieved/revised. Continue with [generation.md](generation.md) and [implementation.md](implementation.md) as applicable. Batch preparation is specified in [runtime.md](runtime.md).
All command examples and workspace paths are relative to the repository root unless explicitly stated otherwise.

## Phase 8: On "design complete", retrieve the final session

When the user explicitly confirms that the design is complete:

1. Read the session ID from the current conversation context or `work/current_session_id.txt`.
2. If no session ID can be determined, ask the user for the RTSystemDesigner URL or session ID.
3. Download the final JSON from:

```text
https://rt-session-server.rtsystem-designer-web.workers.dev/api/sessions/<SESSION_ID>
```

Example:

```bash
curl -L \
  "https://rt-session-server.rtsystem-designer-web.workers.dev/api/sessions/<SESSION_ID>" \
  -o work/final-session.json
```

4. Parse and validate `work/final-session.json`.
5. Treat the downloaded final session as authoritative. Do not continue using stale assumptions from the initial proposal if the user modified the design.
6. Summarize material differences when they affect implementation.

For mixed designs, reconcile `work/connection-contracts.json` and any companion provenance record with the downloaded final session as required by [session-format.md](session-format.md). Preserve a matching copy with the final session under `build/system/`. Verify selected asset catalog IDs/XML hashes and update every mixed-edge custom-interface/serializer mapping to the final endpoints. A removed or changed edge cannot retain an active stale binding; unresolved mappings remain blocked for execution. Implement the required OpenRTM-aist custom interface and serializers only from the approved final design.

---

## Phase 9: Prepare the build workspace

Apply [environment and dependency checks](environment.md). Record the selected source/submodule revisions, native ABI/build configuration, executable paths and required non-code assets. Rebuilding from these records must not depend on another Recipe's incidental deployment directory. XML asset profiles are owned by this repository under `profiles/`; Business Pack evidence and executable implementations retain their separate provenance and roots.

Keep the downloaded authoritative session portable according to [session-format.md](session-format.md). Define local values for its named path references in separate environment-specific deployment settings (env/INI or the target tool's supported configuration format). Record the target host and the design revision/hash used to generate resolved artifacts. Actual executable/source paths belong in these deployment or verification records, not back in the portable session or reusable design companions.

Resolve only documented path references and path-bearing arguments, without shell `eval` or interpreting design text as code. Validate required bindings, host-specific syntax, executable/file availability and access on the intended host before generating rtc.conf or launch/connect commands. Fail the affected deployment clearly on undefined references; do not guess values from another machine or silently substitute the current working directory. Quote resolved arguments for the target tool/shell, including paths containing spaces. Keep source URLs, component identities and historical evidence unchanged. A resolved deployment snapshot may contain absolute paths but must remain a separate local artifact rather than overwrite `final-session.json`.

Use:

```text
build/
```

as the workspace for downloaded or newly implemented RTCs.

Do not put external RTC source trees directly in the repository root.

Recommended structure:

```text
build/
  existing/
    <RTC-name-or-repository-name>/
  generated/
    <GeneratedRTCName>/
  system/
    final-session.json
```

Create these directories if needed.

Copy the downloaded final session to:

```text
build/system/final-session.json
```

---

## Phase 10: Download existing RTCs selected in the final design

Determine which RTCs are actually instantiated in the final `components` list, selecting only entries with `data.moduleKind == "rtc"`. Read metadata from `component.data`; version 2 does not require `rtcTemplates` or `nodes`.

Handle `data.moduleKind == "hakoniwa"` as Hakoniwa assets with their own verified source/deployment requirements. Do not put them through RTC.xml, RTC Builder or RTC lifecycle procedures merely because their diagram `type` is `rtc`. Missing provenance is unresolved and must not be treated as generated source.

For each used RTC whose origin is `catalog` or which has a catalog repository URL:

1. Identify its `repositoryUrl`.
2. Clone or download the repository into:

```text
build/existing/<repository-or-rtc-name>/
```

3. If several selected RTCs refer to the same repository, download it only once.
4. Preserve the upstream repository unchanged initially.
5. Record the source URL and selected commit when possible.
6. Never silently replace a catalog RTC with a different project.

Typical clone:

```bash
git clone "<repositoryUrl>" "build/existing/<name>"
```

If the repository cannot be cloned:

- report the failure,
- preserve the final design,
- continue with other RTCs when possible,
- do not invent replacement source code without telling the user.

If `repositoryUrl` is unavailable but `rtcXmlUrl` exists, do not pretend the whole RTC source repository has been obtained. Report that only the profile URL is known.

---

## Completion criteria after user approval

After the user confirms design completion, the preparation phase is complete when:

- the final session was downloaded from the server,
- the final design was validated,
- selected existing RTC repositories were placed under `build/existing/`,
- generated RTC directories were created under `build/generated/`,
- each used generated RTC has a validated definition JSON in the `rtc_sample.json` format and a verified `RTC.xml` produced by `json_to_rtc_xml.py`,
- skeleton code for each used generated RTC was produced by `cuirtcbuilder.bat` and verified, or generation blockers were explicitly reported as incomplete work,
- the final session was saved under `build/system/`,
- the five RTC lifecycle batch files and their usage instructions were generated under `build/system/scripts/`, or generation blockers were explicitly reported as incomplete work,
- the batch files' prerequisites and verification status were reported, distinguishing generation from actual RTC or hardware execution,
- unresolved dependencies or underspecified interfaces were reported clearly.

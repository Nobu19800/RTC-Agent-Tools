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

---

## Phase 9: Prepare the build workspace

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

Determine which RTCs are actually used by `nodes` in the final design.

Do not download every RTC in `rtcTemplates` if it is not instantiated in the final `nodes` list.

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

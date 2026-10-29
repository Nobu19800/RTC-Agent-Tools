# RTC lifecycle batch generation and operation

Part of the mandatory repository instructions linked from [AGENTS.md](../../AGENTS.md).
Read before generating, editing, or running lifecycle batches. Also read the runtime-setting format rules in [implementation.md](implementation.md) and log/completion rules in [verification.md](verification.md).
All command examples and workspace paths are relative to the repository root unless explicitly stated otherwise.

## Phase 13: Generate RTC lifecycle batch files

After retrieving the final design and preparing the build workspace, generate Windows batch files for operating the RTCs actually instantiated in `build/system/final-session.json`. Include both existing and generated RTCs. Do not include unused templates.

Place the batch files under:

```text
build/system/scripts/
  start_rtcs.bat
  connect_ports.bat
  activate_rtcs.bat
  deactivate_rtcs.bat
  stop_rtcs.bat
```

Shared settings and native batch subroutines may be added in the same directory when needed. Keep the five operations independently callable. Write the actual runtime commands directly in the `.bat` files; do not make them wrappers around a Python lifecycle controller such as `runtime_control.py`. Python may be used to generate the files, and to run a Python RTC itself.

### Resolve runtime commands and settings

- Derive executables or interpreters, working directories, arguments, environment variables, hosts, instance names, nameservers, configuration values, and connections from the final design and verified build outputs.
- Generate runtime `rtc.conf` and component configuration files under `build/system/` as needed. Preserve the final design's values and refer to these files from the startup commands rather than modifying existing RTC sources.
- Use the non-JSON runtime-setting formats required by the common implementation rules, including for process-launch/ownership metadata. Generation tools may read the final session JSON, but runtime batches and their process-only helpers must not depend on parsing that JSON or a separate JSON process manifest. Retain a design hash for drift detection.
- Resolve nameserver settings for each tool independently. Do not assume an rtshell path such as `/localhost:2809/...` can be copied unchanged into every OpenRTM runtime setting; verify the installed C++/Python runtime's accepted nameserver syntax.
- Inspect the installed OpenRTM runtime and rtshell utilities, including their help and documented options, before choosing commands. Do not invent command names, flags, CORBA naming paths, or service connector properties. Use native batch commands and rtshell for runtime control, state checks, waiting, and logging. A small PowerShell utility may handle only hidden process launch, PID ownership records, and cleanup of owned processes where native batch commands are insufficient. Do not move lifecycle or connection orchestration into Python, PowerShell, or direct OpenRTM/CORBA API calls.
- Record required tools and dependencies. If an executable, interpreter, naming path, or deployment setting cannot be resolved, identify the missing setting and make the affected operation fail clearly rather than silently skipping the RTC or claiming the batch file is ready.
- For remote hosts, use an established remote execution mechanism or document the per-host launch procedure. Do not treat a remote deployment as a local process.

### Required use of rtshell

Use rtshell for the RTC operations in all four of these batch files:

| Batch file | Operation that must use rtshell |
| --- | --- |
| `connect_ports.bat` | Execute `rtcon` directly to connect RTC DataPorts and ServicePorts. |
| `activate_rtcs.bat` | Execute `rtact` directly to activate RTCs. |
| `deactivate_rtcs.bat` | Execute `rtdeact` directly to deactivate RTCs. |
| `stop_rtcs.bat` | Execute `rtdeact` as needed and `rtexit` directly to request graceful RTC exit. |

Check that rtshell and the required commands are installed and callable in the batch execution environment. Verify their syntax against the installed version's help. If rtshell is unavailable, report it as an unresolved prerequisite and fail the affected operation clearly; do not silently substitute a custom lifecycle/connection implementation. Document rtshell setup and command requirements in `README-runtime.txt`.

The command lines for `rtcon`, `rtact`, `rtdeact`, and `rtexit` must appear in their corresponding batch files. Shared `.bat` subroutines may perform repeated readiness/profile checks and polling, but must not conceal these four operations behind another-language controller. rtshell's own Python implementation is compatible with this rule; the restriction is on adding a separate orchestration layer.

### Required behavior of each batch file

1. `start_rtcs.bat`: launch the selected RTCs with their deployment and configuration settings. Reuse a reachable nameserver when available; if a local nameserver must be started, verify its startup command and record ownership. Launch processes without opening extra console windows unless requested. Wait with a bounded timeout until the intended RTC instances are registered and reachable. Record the launched process IDs or equivalent ownership information. Do not connect ports or activate RTCs as part of this operation.
2. `connect_ports.bat`: resolve the actual registered RTCs and connect every edge in the final design. Check DataPort names, directions, and matching data types. For ServicePorts, verify interface names, interface types, and Consumer/Provider polarity, and use the actual IDLs and supported connector properties. Detect equivalent existing connections and avoid duplicates. Verify each requested connection after creation and report failures.
3. `activate_rtcs.bat`: verify the required RTCs and connections are ready, then activate the RTCs in their intended execution contexts. Determine and document an activation order appropriate to the system's data/control dependencies, including feedback loops. Treat an already active RTC as an explicit no-op. Wait for and verify the resulting states; report ERROR states and timeouts.
4. `deactivate_rtcs.bat`: deactivate the selected RTCs in an order appropriate for stopping producers, controllers, and actuators. Treat an already inactive RTC as an explicit no-op. Verify that deactivation completed and report failures.
5. `stop_rtcs.bat`: deactivate active target RTCs as needed, then request graceful RTC exit and wait for completion with a bounded timeout. Verify registration removal and the disposition of the owned process separately. An RTC may unregister while its manager remains alive because automatic shutdown is disabled. Clean up only a verified, dedicated owned manager after graceful exit/RTC removal has been established; compare PID, executable path and start time before fallback termination. Do not terminate unrelated RTCs, shared managers, or nameservers, and do not kill by a broad executable-name match. Leave shared infrastructure running and stop owned infrastructure only when no longer needed. If naming service or process information is unavailable, report the unknown verification result rather than claiming complete shutdown.

### Bounded waits, partial failure, and recovery

- Configure CORBA call timeouts, registration/transition/exit wait limits, polling intervals, and retry limits in shared settings. Use bounded waits and document effective values. A three-second client timeout proved insufficient during this example's shutdown; ten seconds is a tested recovery value, not a guarantee for every deployment. Distinguish a per-call timeout from the overall operation deadline.
- Treat confirmed naming-service `NotFound`, a live RTC, a stale/zombie reference, `CORBA.TIMEOUT`, and a nameserver/network failure as different results. A failed query is not proof that an RTC has exited. Confirm the naming service is reachable and the intended registration is absent; independently check the recorded process. Do not interpret every nonzero rtshell exit as "already stopped" or "not connected".
- After a timed-out operation, query the actual state before repeating it: the original request may already have completed. Retry only appropriate transient failures, with bounded attempts/backoff. Never blindly repeat activation, connection creation, or exit requests, and do not retry identity/ownership mismatches as though they were communication errors.
- In `stop_rtcs.bat`, a failure for one RTC must not abandon all remaining targets. Continue safe shutdown attempts for independent verified targets in the documented dependency order, respecting actuator/control safety dependencies. Skip unsafe or unverified targets, continue what can safely be completed, and report every unresolved target. Use native batch subroutines/status aggregation rather than a global immediate `goto failed` for each per-RTC error.
- Produce a per-RTC shutdown summary: initial state, deactivation result, exit-request result, registration result, process/manager cleanup result, retries, and remaining/unknown resources. Return nonzero if any required shutdown or verification remains incomplete. If recovery completes all required work, report success together with the recovered failures; do not erase their diagnostic history.

### Batch file quality and verification

- Use paths based on `%~dp0` and quoted absolute paths so the batch files work when invoked from another working directory or a path containing spaces. Keep shared settings in one place rather than duplicating machine-specific paths across the five files.
- Provide `--plan` for each batch to print its intended commands without launching processes or changing registrations, connections or states. Inspect the plan against the final design. Offline generation/plan tests do not establish runtime success.
- Propagate helper failures and return nonzero exit codes for failed operations. Save useful per-operation logs under `build/system/logs/` without exposing secrets.
- Capture each native command's exit code immediately before another command can overwrite it. Check both that exit code and the requested postcondition. For Windows PowerShell process-only helpers, handle redirected native stderr without treating every warning as a fatal exception; decide native-command failure by the exit code and verification result, while retaining stderr diagnostics.
- Make repeated execution predictable: detect already running instances, existing connections, and completed state transitions. Verify instance identity before reusing a registration; do not start a duplicate or operate on an unrelated RTC with a similar name.
- Provide usage instructions, prerequisites, timeout settings, log locations, and the sequence `start_rtcs.bat` -> `connect_ports.bat` -> `activate_rtcs.bat` -> `deactivate_rtcs.bat` -> `stop_rtcs.bat` in `build/system/scripts/README-runtime.txt`.
- Inspect the generated batch files and helpers against the final design. Generating these files does not itself authorize executing the system or operating hardware. Run lifecycle checks when system execution is within the user's requested scope, and distinguish file generation, build verification, RTC lifecycle verification, and application/hardware behavior verification in the report.
- If an RTC is still a skeleton, state that lifecycle success does not demonstrate its intended processing behavior. Report unexecuted checks and unresolved runtime prerequisites explicitly.

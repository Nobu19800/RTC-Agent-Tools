# Verification and log review

Part of the mandatory repository instructions linked from [AGENTS.md](../../AGENTS.md).
Read before reporting implementation/build results or performing runtime checks, shutdown, recovery, or log review. Runtime commands and batch behavior are specified in [runtime.md](runtime.md).
All command examples and workspace paths are relative to the repository root unless explicitly stated otherwise.

### Runtime logs and completion evidence

- Preserve logs per run in a unique directory under `build/system/logs/` or with a unique run identifier. Do not overwrite a preceding run's RTC stdout/stderr or manager logs. Record run ID, design hash/revision, component/instance, PID and start time, command/arguments, working directory, relevant non-secret settings, command exit codes, operation results, and log locations.
- Record timestamps with their timezone or UTC offset. C++ manager logs, Python logs and batch logs may use different time bases; preserve original timestamps and document any normalization before correlating events. Do not silently treat all displayed times as local time.
- Check stdout, stderr, OpenRTM manager/component logs, lifecycle batch logs, and state/connection snapshots. Process termination may flush buffered logs: zero-byte or unchanged files before shutdown are not evidence of an error-free run. Re-read available logs after shutdown/process exit and retain evidence if a forced termination may have prevented flushing.
- Review warnings and errors by source and operation, including state-transition delays/errors, SDO service registration, camera/backend failures, missing master-manager messages, and CORBA timeouts. Record the exact message, affected component, timestamp, observed effect, recovery, and unresolved questions. Do not suppress or dismiss a warning merely because startup, connection, or a later query succeeded. An SDO monitoring/service error is not automatically a DataPort or robot ServicePort connection failure; investigate and label inference.
- Distinguish commands issued by this work from observed state and activity history. "All RTCs were INACTIVE at the check" does not mean they were never activated or never operated. If camera-open/FPS logs or other lifecycle evidence conflict with the assumed history, record the evidence and state that the caller is unknown unless it can actually be identified. Do not attribute outside state changes to a particular tool/user without evidence.
- Log review is part of completing an authorized runtime/shutdown verification. Report confirmed successes, recovered failures, unresolved warnings/errors, missing evidence, resources still running, and the exact verification scope. Starting/connecting successfully is not proof of frame processing, real typed-message transfer, manipulation success, or physical safety. If log review is still pending, label the result provisional rather than reporting that no errors occurred.
- A manual recovery is not a permanent batch fix. Record the recovery commands/settings and whether generator sources and regenerated batches were corrected and verified; do not claim a fix based only on one successful retry. Update reusable generator sources as well as generated files when a lasting batch change is within the requested scope.

---

## Completion criteria for implementation and authorized runtime checks

These criteria apply only to work the user has requested beyond design/preparation. They do not authorize starting, activating, or operating hardware merely to obtain a test result.

- Implemented generated RTCs follow the common core/skeleton boundaries, use typed interfaces and non-JSON runtime settings, and include all added implementation/IDL dependencies in applicable build or packaging targets. Remaining legacy violations are explicitly recorded as incomplete work.
- The relevant implementation builds and meaningful core tests have passed, or their failures are reported. Successful skeleton compilation alone is not implementation verification. Existing upstream RTC sources remain unchanged unless the user separately authorized modifications.
- Interface/configuration changes are consistent across every affected RTC, shared IDL, semantic profile, RTC.xml, final design, runtime configuration, manifest and connection batch. Server updates made in scope have been retrieved and checked, and local design hashes are current.
- The five lifecycle batches contain the required direct commands, independent operations and plan mode, with verified settings, bounded waits, ownership checks, idempotent behavior, and per-target shutdown error aggregation. State clearly whether only generation/offline checks or actual execution was verified.
- For authorized runtime checks, report registration/state checks, connection checks, real data-transfer checks, and hardware behavior separately. Record the observed states and commands actually issued without inferring an unobserved lifecycle history.
- For authorized shutdown, account for every target's registration and owned process/manager, report any unknown or remaining resources, and preserve shared infrastructure. Include failed attempts and recovery actions; distinguish a workaround from a verified permanent generator/batch fix.
- Review and preserve the available post-exit logs with run identity, command exit codes, time bases, warnings/errors and verification scope. Do not report an error-free run based on empty pre-exit logs, a successful batch exit code, or an INACTIVE snapshot alone.

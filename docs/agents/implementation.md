# Core implementation and builds

Part of the mandatory repository instructions linked from [AGENTS.md](../../AGENTS.md).
Read before implementing, changing interfaces/configuration, or building RTCs. Apply [verification.md](verification.md) for verification scope and completion criteria. Existing RTCs follow the as-is build rules below.
All command examples and workspace paths are relative to the repository root unless explicitly stated otherwise.

### Common implementation boundaries and data contracts

- Put algorithms, image processing, coordinate transformations, planning, and domain validation in separate core files. Core APIs use ordinary language data structures: C++ structures/enums/containers/optional results and const references, Python classes/dataclasses/enums, or Lua tables/module objects. Avoid unnecessary copies of large inputs.
- Keep all OpenRTM-aist integration directly in the builder-generated component files: port registration, `isNew`/`read`/`write`, configuration binding, service calls, lifecycle handling, return codes, and conversion between plain domain objects and RTC/IDL data. Do not place this integration in a Core, Integration, Codec, or other external implementation file. Integration code may be substantial when conversions require it; the minimal-skeleton rule limits algorithms in skeletons, not necessary OpenRTM integration.
- Core files must not depend on OpenRTM/CORBA classes, RTC/IDL message types, registered ports, or component instances. Convert inputs in the skeleton before calling the core, then convert results and write output ports in the skeleton. Pure utility libraries such as OpenCV may be used by the core when required by its algorithm.
- Do not use JSON for core inputs/results, DataPort payloads, component configuration values, calibration files, or runtime launch/process settings. Use typed structures and suitable non-JSON configuration formats such as `rtc.conf`, INI, YAML, or documented numeric lists. Never replace JSON payloads with another serialized string when a suitable typed DataPort can represent the data.
- RTSystemDesigner session JSON and semantic RTC profile JSON remain required tool metadata formats. JSON verification reports and historical evidence are also permitted; these exceptions do not permit runtime JSON parsing or serialization. Runtime process manifests such as the existing `runtime-settings.json` and active ownership records such as `*-pid.json` are not exceptions: migrate them and their consumers to a non-JSON format when generating/updating runtime tooling. Until migration is verified, report the remaining JSON dependency explicitly rather than claiming runtime JSON removal is complete. Do not alter an existing upstream RTC solely to impose these generated-RTC rules.
- Prefer suitable standard RTC data types. When they cannot express the required data with clear semantics, define a shared IDL and use the exact same definition on all connected generated RTCs. Define field names, enum values, sequence/array meanings, units, coordinate frames, timestamps, identifiers, validity, and error/status semantics before implementation. Preserve original acquisition time through downstream transformations; assign current time to newly emitted status updates. Do not fabricate missing sensor timestamps, calibration, hardware limits, or completion feedback.
- Store shared IDL in a traceable location such as `build/generated/common/idl/`, record its dependencies and hash, and make each affected build depend on it. Respect IDL's case-insensitive identifier rules; for example, use `ColorCode color` rather than a conflicting type/member pair. Compile custom IDL as needed, but reuse SDK-provided standard type libraries instead of recompiling their imported symbols. Deduplicating file lists alone does not resolve SDK symbol duplication.
- When the user authorizes an interface/configuration change after design approval, archive the preceding design/profile revision, update all affected RTCs, shared IDL, semantic profiles, RTC.xml, final session, configuration files, deployment metadata, runtime manifests and connection batches together. Check the current server revision before updating the existing session, preserve unrelated user edits, and validate the downloaded round trip. Refresh local design hashes from the resulting authoritative snapshot. Do not require another design approval for changes the user has already authorized.
- Recreate connections that used old types and check both endpoints against the revised design. Do not silently keep old profiles, optional generated test scaffolds, or runtime configuration examples with obsolete types or defaults. Verify the source/header/build definitions and build products match the current revision.
- Do not regenerate over implemented skeletons. Inspect diffs and generator ownership/hash records first. Apply required interface changes to edited files carefully, or generate into a separate review directory and merge the necessary changes. Preserve original skeleton-generation evidence and record subsequent implementation verification separately.

### Implement generated C++ RTCs

When the generated source code is C++, follow these rules:

1. Keep core algorithms out of cuirtcbuilder-generated component files such as `src/<RTCName>.cpp` and `include/<RTCName>/<RTCName>.h`. Write the required OpenRTM integration and type conversions directly in these files, following the common implementation boundaries above.
2. Add separate implementation files under `src/` and corresponding headers under `include/<RTCName>/`. Implement the core processing in functions or classes in those files. For example, use `src/<RTCName>Core.cpp` and `include/<RTCName>/<RTCName>Core.h`.
3. Have `src/<RTCName>.cpp` call those functions or classes from its lifecycle callbacks. Keep algorithms, image processing, coordinate transformations, planning, and other core logic in the added files. Do not implement core processing directly in the generated component `.cpp` or `.h` files, including as inline methods in the generated header.
4. Update `CMakeLists.txt`, `src/CMakeLists.txt`, and related source/header lists or build definitions as needed to compile the added sources and include/link their required dependencies. Ensure both the component library and standalone executable include the core implementation when both targets are generated.
5. Configure and build the C++ RTC after implementation. Fix relevant compilation and link errors, then rebuild. If dependencies or platform requirements prevent a successful build, report the failure and the unresolved requirements explicitly; do not claim the RTC is built or operational.
6. Keep OpenRTM-aist integration directly in the builder-generated component `.cpp` and `.h`: port registration, `isNew`/`read`/`write`, configuration binding, service calls, lifecycle handling, and conversion between RTC/IDL data and plain C++ structures. Do not move these operations into `Core`, `Integration`, `Codec`, or other external implementation files. This integration code is permitted in the skeleton; algorithms remain in separate core files.
7. Follow the common typed-data and non-JSON rules above. Inspect effective compile/link settings, including UTF-8 and exception handling on MSVC, and include required custom IDL sources exactly once per target. Do not suppress SDK symbol/linkage warnings instead of resolving duplicate standard-IDL compilation.

### Implement generated Python RTCs

When the generated source code is Python, follow these rules:

1. Keep algorithms out of the cuirtcbuilder-generated `<RTCName>.py`. Write imports, object ownership, port/configuration integration, RTC/domain conversions, and calls to the core directly in this skeleton file.
2. Add separate Python files in the generated RTC's workspace, for example `<RTCName>Core.py`. Implement the core processing in functions or classes in those files.
3. Have `<RTCName>.py` use those functions or classes from its lifecycle callbacks. Keep algorithms, image processing, coordinate transformations, planning, and other core logic in the added files. Do not implement core processing directly in the generated component file.
4. Update module packaging or installation file lists as needed so the added modules are available when the RTC runs.
5. Apply the common implementation boundaries and non-JSON rules. Core modules use ordinary Python data objects and must not import OpenRTM/CORBA or operate on RTC instances/ports. Generate/import the actual IDL bindings at the skeleton boundary when custom types are required.

### Implement generated Lua RTCs

When the generated source code is Lua, follow these rules:

1. Keep algorithms out of the cuirtcbuilder-generated `<RTCName>.lua`. Write module loading, object ownership, port/configuration integration, RTC/domain conversions, and calls to the core directly in this skeleton file.
2. Add separate Lua files in the generated RTC's workspace, for example `<RTCName>Core.lua`. Implement the core processing in functions or module-provided objects in those files.
3. Have `<RTCName>.lua` load the added modules with `require` and use their functions or objects from its lifecycle callbacks. Keep algorithms, image processing, coordinate transformations, planning, and other core logic in the added files. Do not implement core processing directly in the generated component file.
4. Update module search paths, packaging, or installation file lists as needed so the added modules are available when the RTC runs.
5. Apply the common implementation boundaries and non-JSON rules. Core modules use ordinary Lua data objects and must not operate on OpenRTM/CORBA objects or RTC ports; perform those operations in the generated skeleton.

---

## Phase 12: Build preparation

After sources are present in `build/`:

1. Inspect each repository's README, build files, and local `AGENTS.md` if present.
2. Follow the RTC's own documented build procedure.
3. Do not assume all RTCs use the same language or build system.
4. Do not assume all repositories are safe to build without inspection.
5. Do not execute downloaded binaries or arbitrary install scripts merely because they exist.
6. Prefer source builds using documented build systems.
7. Record unresolved dependencies and platform requirements.
8. For generated C++ RTCs, include the separate core implementation files in the build and perform the configure/build verification described in Phase 11. Skeleton build results alone do not verify the subsequently implemented code.
9. Use meaningful core tests with synthetic data where appropriate, covering the specified behavior and rejection of invalid inputs without operating hardware. Separately validate session/profile/XML/type/configuration consistency. Compilation, core tests, runtime registration, port connection, real data transfer, and hardware behavior are different verification levels; never substitute one for another or run an unauthorized activation/hardware test to fill a verification gap.

### Build existing RTCs as-is

For existing RTCs selected in the final design, build the sources under `build/existing/` as obtained from upstream, using each RTC's documented build procedure after inspecting its build commands.

- Preserve the existing source layout, implementation files, interfaces, and build definitions. Do not apply the generated-RTC core separation rules, regenerate skeletons, or refactor existing RTCs.
- Use documented build options and environment settings to select dependencies and the target platform. Prefer a separate build output directory when supported by the upstream build system.
- Perform the documented configure/build steps rather than stopping after source download or configuration alone. For interpreted RTCs without a compilation step, follow their documented dependency and module/IDL preparation steps.
- If the unchanged sources cannot be built, record the failed command, error, and missing dependencies or platform requirements. Report the build as incomplete; do not silently patch upstream source or build files to make it pass.

The goal of this phase is to prepare a reproducible workspace, not to conceal build failures.

---

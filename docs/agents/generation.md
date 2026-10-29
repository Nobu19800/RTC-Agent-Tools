# Generated RTC profiles and skeletons

Part of the mandatory repository instructions linked from [AGENTS.md](../../AGENTS.md).
Read before exporting profiles, converting RTC.xml, or generating/updating skeletons. Read [implementation.md](implementation.md) before editing implementation files; preserve existing implementation changes.
All command examples and workspace paths are relative to the repository root unless explicitly stated otherwise.

## Phase 11: Handle generated RTCs

For each RTC used by the final `nodes` whose origin is `generated`:

1. Create:

```text
build/generated/<RTCName>/
```

2. Use the final node/template metadata as the source of truth.
3. Read:
   - ports
   - service interfaces
   - configuration
   - deployment
   - implementation.summary
   - implementation.requirements
   - implementation.constraints
   - implementation.notes
4. Generate the RTC definition JSON, RTC.xml, and skeleton code using the procedure below before implementing the RTC. Do this only after the final design has been retrieved and validated.
5. Maintain exact compatibility with connected port types and service interfaces.
6. Do not alter existing RTC interfaces merely to make generated code easier.
7. If an interface is underspecified, stop and report the missing information rather than silently inventing incompatible semantics.

### Generate the RTC definition JSON

For each distinct generated RTC definition instantiated in the final design, write:

```text
build/generated/<RTCName>/<RTCName>.json
```

Use the semantic RTC profile format of the user-provided `rtc_sample.json`, not the RTSystemDesigner session/node format. The following shows its structure; replace the example values, ports, interfaces, and configuration with the final design. Use empty arrays when no configuration, DataPorts, or ServicePorts are needed.

```json
{
  "profileVersion": "0.3",
  "basicInfo": {
    "name": "SampleRTC",
    "description": "Example RT component",
    "version": "1.0.0",
    "vendor": "AIST",
    "category": "example",
    "componentType": "STATIC",
    "activityType": "PERIODIC",
    "componentKind": "DataFlowComponent",
    "maxInstances": 1,
    "executionType": "PeriodicExecutionContext",
    "executionRate": 1000.0
  },
  "actions": {
    "OnInitialize": true,
    "OnActivated": true,
    "OnDeactivated": true,
    "OnExecute": true
  },
  "configuration": [
    {"name": "motor_id", "type": "int", "defaultValue": "0", "widget": "text"}
  ],
  "dataPorts": [
    {"name": "in", "portType": "DataInPort", "type": "RTC::TimedFloat", "position": "LEFT"},
    {"name": "out", "portType": "DataOutPort", "type": "RTC::TimedLong", "position": "RIGHT"}
  ],
  "servicePorts": [
    {"name": "control", "interfaces": [
      {"name": "Controller", "direction": "Provided", "type": "RTC::ControllerService", "instanceName": "controller", "idlFile": "Controller.idl"}
    ]}
  ],
  "language": {"kind": "C++"}
}
```

- Derive component metadata, lifecycle actions, language, configuration names/types/defaults, and port definitions from the final design and its implementation instructions. Do not copy sample-specific values as requirements or silently assume its execution rate or vendor.
- Preserve exact DataPort names, directions, and types. Map input ports to `DataInPort` and output ports to `DataOutPort`.
- Preserve ServicePort and interface names, interface types, instance names, and IDL references. Map Provider to `Provided` and Consumer to `Required` in the JSON interface `direction`.
- Locate the actual IDL files required by service interfaces or custom data types, including their dependencies. Preserve existing interface definitions; create new IDL only when the final design specifies enough information to define it compatibly.
- Keep deployment settings, rtc.conf settings, and the four implementation fields available in the saved final session; do not assume the profile converter carries these into generated code.
- Parse the JSON and compare its ports, configuration, and interfaces against the final design before conversion. If required metadata or interface details are missing, report the missing information rather than inventing them.

### Convert the JSON to RTC.xml

From the repository root, run the repository's converter with its positional input and output arguments:

```powershell
python .\json_to_rtc_xml.py "build/generated/<RTCName>/<RTCName>.json" "build/generated/<RTCName>/RTC.xml"
```

Require a successful exit status, confirm that `RTC.xml` exists and parses as XML, and inspect its component name, language, configuration, DataPorts, and ServicePorts against the JSON. The converter supports a subset of the profile format and does not perform XSD validation; successful conversion alone does not establish interface compatibility. Stop this RTC's generation if conversion or verification fails.

### Generate skeleton code with cuirtcbuilder.bat

Use the repository's `cuirtcbuilder.bat` with these options:

- `-d`: output folder.
- `-f`: path to `RTC.xml`.
- `-i`: path to an IDL file required by the RTC.

From the repository root, for an RTC without required IDL files:

```powershell
.\cuirtcbuilder.bat -d "build/generated/<RTCName>" -f "build/generated/<RTCName>/RTC.xml"
```

For an RTC requiring an IDL file:

```powershell
.\cuirtcbuilder.bat -d "build/generated/<RTCName>" -f "build/generated/<RTCName>/RTC.xml" -i "build/generated/<RTCName>/idl/Controller.idl"
```

Replace the example IDL path with the actual file path. Omit `-i` when no IDL is required. If several IDL files are required, inspect the local builder's documented handling of multiple files before invoking it; do not guess a separator or assume repeated `-i` options work.

Inspect the local launcher and prerequisites before execution. The current launcher uses Python and Java, `tool/cuirtcbuilder/lib/*`, and `%RTM_JAVA_ROOT%/utils/OpenRTP/plugins/*`; confirm the required runtime and libraries are available. ServicePort generation uses the local Java source compatibility bridge and therefore requires a JDK with Java source-file launch support (Java 11 or later). Report missing prerequisites or generator failures and preserve the JSON and XML for retry.

The local launcher accepts IDL file paths after `-i` (multiple paths may follow a single `-i`). Its Python wrapper maps these to the containing directories required by the bundled Java library. For ServicePorts, the compatibility bridge restores the IDL source paths that the bundled profile loader otherwise retains only as display values, then delegates generation to the original RTC Builder libraries. Preserve actual upstream IDL contents and dependencies.

For the camera/color/arm example verified in this repository, `scripts/prepare_final_session.py` validates `work/final-session.json`, saves the authoritative snapshot under `build/system/`, and exports semantic profiles for instantiated generated RTCs. Use `idlSourceDirectory` and `idlIncludeDirectories` in the final generated-RTC metadata to identify the actual service IDLs and their include dependencies. The current myCobot design uses the installed OpenRTM Python SDK's JARA_ARM IDLs, with source paths and SHA256 recorded in the design. The script retains a legacy UR IDL fallback for earlier designs; inspect the resolution before using it for another system. `scripts/generate_final_skeletons.py` verifies the canonical JSON/XML and generates the skeletons with recorded compatibility corrections:

- The bundled builder rejects empty string configuration defaults. Use a separate temporary profile under `work/builder-inputs/` only for generation, then restore the exact authoritative defaults in generated C++ and component configuration. Do not change the saved final session or canonical RTC JSON/XML to hide the limitation.
- Escape quotation marks, backslashes, and other C++ string-literal characters in generated configuration defaults, including the generated test scaffold. Legacy converter fixtures may contain JSON text, but do not introduce JSON-valued runtime defaults in new RTC implementations.
- Remove duplicate IDL entries from the generated CMake input list so shared includes do not create duplicate targets.
- Keep IDL generation inputs outside the output directory to avoid copying a file onto itself.
- Record these corrections and verified source hashes in `skeleton-generation.json`. Refuse to regenerate over edited skeleton sources.

Use `python scripts/test_profile_conversion.py` for converter regression checks. On Windows/MSVC, enable `/utf-8` for Japanese metadata and `/EHsc` for C++ exception handling on every applicable target, while preserving the toolchain's existing flags. Setting `CMAKE_CXX_FLAGS` to `/utf-8` alone can replace required defaults; inspect the effective compiler options and resolve related warnings. A successful skeleton build verifies generated interfaces and compilation only; report behavioral implementation and system execution separately.

Require a successful exit status and verify the expected source/build files were generated with the specified language, component name, ports, configuration, and service interfaces. Do not claim skeleton generation succeeded based only on the existence of the output directory. Do not rerun the builder over implementation changes without checking for overwrites.

Implement the RTC behavior in the generated skeleton using the final implementation instructions. Prefer adding new implementation files and keeping modifications to generated files minimal unless the project's local instructions say otherwise.

The following C++, Python, and Lua implementation rules apply only to newly generated RTCs. Build existing RTCs as obtained from upstream, following Phase 12.

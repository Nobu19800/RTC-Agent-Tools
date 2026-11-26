# Catalogs and XML Profiles

[日本語](../catalog-profiles.md)

Catalog JSON files list modules for search and selection. XML profiles describe individual modules, their interfaces, and their settings. An RTSystemDesigner session records the chosen instances, their positions, and their connections. [Session format](../agents/en/session-format.md)

## Catalog contents

| Catalog | Entries and key fields | Source |
| --- | --- | --- |
| [General RTCs](../../catalog/rtc_catalog.json) | `rtcs` lists component name, category, vendor, version, language, DataPorts, ServicePorts, and links to the repository and `RTC.xml` | `RTC.xml` in public GitHub repositories |
| [Bundled OpenRTM samples](../../catalog/openrtm_samples_catalog.json) | `rtcs` lists samples in multiple languages. When available, `launch` describes how to start the installed sample | Upstream profiles and [supplemental RTC.xml files](../../profiles/openrtm-samples/README.md) |
| [Hakoniwa assets](../../catalog/hakoniwa_catalog.json) | `assets` lists asset identities, properties, ports, launch details, and provenance. PDU ports carry robot names, channel IDs, and capacities | XML in `profiles/iso22166-202/drone-three-point/` |
| [ROS 2 nodes](../../catalog/ros2_catalog.json) | `nodes` lists package and executable names, categories, topics, services, actions, distribution notes, and launch details | XML in `profiles/iso22166-202/ros2/` |

The general RTC catalog distinguishes candidates by component name and implementation language. Periodic collection retains previously cataloged entries that a later search misses. For competing sources with the same name and language, the builder compares the latest commit affecting the directory containing `RTC.xml` on each default branch. The sample catalog is maintained separately, and the Designer prefers its entry for the same name and language. The Hakoniwa and ROS 2 catalogs record the source XML path and SHA-256. [Catalog generation and search](../../catalog/README.md)

## XML mapped to ISO 22166-202

The XML under `profiles/iso22166-202/` maps Hakoniwa asset and ROS 2 node information to the public ISO 22166-202 information model. The repository defines the namespaces and identifiers. Conformance to the official Annex B XSD has not been verified, and the conformance status is `not-assessed`. [ROS 2 profile provenance and scope](../../profiles/iso22166-202/ros2/README.md)

| XML element | What it describes |
| --- | --- |
| `GenInfo`, `IDnType`, `ModuleProp` | Overview, module identity and kind, and module properties |
| `IOVariables`, `Services` | Interfaces and operations, such as Hakoniwa PDU types, directions, and channels or ROS 2 topics, services, and actions |
| `Infra`, `ExecutableForm` | Environment and launch form. The ROS 2 catalog stores `launch: null` when executable registration could not be confirmed |
| `Evidence` | Source material and upstream references that support the profile |

For each Hakoniwa connection, verify the robot name, channel, binary layout, and field semantics. A shared message type name alone is insufficient to establish compatibility. [Serialization and transport plugins](rtc-transport-plugins.md)

## RTC.xml

OpenRTM-aist RTC profiles use `RTC.xml` with an `RtcProfile` root. The general RTC catalog extracts searchable metadata from these profiles. For an existing RTC, inspect the referenced profile for its detailed settings. For a new RTC, derive its definition JSON from the approved design, run `json_to_rtc_xml.py`, and pass the resulting `RTC.xml` to the Builder to generate a skeleton. [RTC generation workflow](../agents/en/generation.md)

| XML element | What it describes |
| --- | --- |
| `BasicInfo` and `Language` | Component name, category, vendor, version, and implementation language |
| `Actions` | Callback generation settings and documentation |
| `DataPorts` | Port name, InPort or OutPort direction, and IDL type |
| `ServicePorts` | Interfaces on a port and their Provider or Consumer roles |
| `ConfigurationSet` | Configuration parameter types and defaults |

For example, select `ConsoleIn` from the catalog, check its OutPort type in `RTC.xml`, and connect the `ConsoleIn0` instance in the session. Before launch, verify the executable, dependencies, and runtime settings for the selected version. [Designer module settings](designer-module-settings.md)

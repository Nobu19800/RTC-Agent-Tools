# RTC-Agent-Tools Environment Setup

[日本語](../setup.md)

## Who does what

- **You** open Codex or Claude Code and select a working folder. When the agent shares a design link, review the design in your browser and approve it. Follow the agent's directions if an installer or the OS requires your interaction.
- **The agent** clones the repository, checks versions and dependencies, installs required tools, checks API connectivity, and prepares the build environment. The commands below are references for the agent to run. You can follow the normal workflow without typing them into a terminal.

## Choose an environment

| Task | Prerequisites |
| --- | --- |
| Catalog search and design review | Python 3, a browser, and access to the selected catalogs and Designer |
| Public Designer integration | HTTPS access to the Designer and session API |
| RTC generation and execution | SDK and runtime for the selected language, Java and the Builder for skeleton generation, and a naming service and rtshell for runtime checks |
| Systems with ROS 2 or Hakoniwa | The selected Linux or WSL2 environment and the packages or Recipe required by the approved design |

## 1. Check out the repository and check HTTPS access

The agent clones the repository and records the commit. On Windows, the agent checks `git --version`, `python --version`, and `curl.exe --version`. If Git is missing, install it for the target shell. [RTC-Agent-Tools repository](https://github.com/Nobu19800/RTC-Agent-Tools) · [Git installation](../../AGENTS.md#git-installation)

Open the design link the agent provides in your browser. The agent checks that the session API is reachable over HTTPS. Use the quickstart to check that you can register a design, save it in the browser, and retrieve it. [Public RTSystemDesigner](https://nobu19800.github.io/RTSystemDesigner/) · [Service endpoints](../agents/en/services.md) · [Quickstart](quickstart.md)

## 2. Prepare the RTC build and runtime tools

The agent follows the runtime installation guide for Windows MSI selection and installation commands for OpenRTM-aist, ROS 2, and Hakoniwa on Ubuntu or WSL2. [Runtime installation](../agents/en/install-runtime.md)

1. Install the OpenRTM-aist SDK and dependencies for the target language. For C++, check the compiler, CMake, and CORBA libraries. For Python, check that the selected interpreter imports `OpenRTM_aist` and `omniORB`.
2. Locate Java and the Builder JAR directory. Run the environment preflight with the actual paths before generating code.
3. Locate the rtshell commands `rtcon`, `rtact`, `rtdeact`, and `rtexit` and check their help. Verify that the operator's shell can reach the naming service and the addresses advertised by the registered IORs.

~~~powershell
python -c "import OpenRTM_aist, omniORB; print(OpenRTM_aist.__file__)"
python scripts/preflight_environment.py --java "$env:JAVA_HOME\bin\java.exe" --builder-lib "$env:BUILDER_LIB"
~~~

Here, `BUILDER_LIB` points to the directory containing the Builder JARs. Confirm the service IDL files and include directories for each target RTC. [Environment checks](../agents/en/environment.md) · [Generation guide](../agents/en/generation.md)

## 3. Prepare additional Ubuntu or WSL2 dependencies

For WSL2, the agent uses `wsl --list --verbose` on Windows to identify the target distribution. The agent installs and builds dependencies in the Ubuntu environment where they will run.

- **C++ OpenRTM-aist** — After configuring the APT repository, run `apt-cache policy openrtm2`. If the candidate is `2.1.0-0`, build OpenRTM-aist from source and record the revision. If a newer candidate is available, use the APT package. If there is no candidate, check the APT configuration and target OS.
- **Naming service** — Use the endpoint in the approved design. For WSL2 without an explicit endpoint, advertise a WSL2 IP reachable from Windows in the RTC and naming service IORs. The default naming service port is `2809`. Reuse an existing service if it satisfies these conditions. [Endpoint configuration](../agents/en/runtime.md)
- **ROS 2** — The examples use Jazzy. Source the ROS 2 and workspace setup scripts in the execution shell and confirm the executable with `ros2 pkg executables <package>`. For communication with an RTC, align its ROS2Transport implementation, DDS backend, message types, DDS domain, and QoS. [ROS 2 runtime](../agents/en/ros2.md) · [ROS2Transport](../agents/en/ros2-transport.md)
- **Hakoniwa** — Follow the selected Recipe to prepare the Workspace and Foundation. Check native bindings and PDU conversion modules using the selected Python interpreter. For a viewer, prepare the viewer, configuration, codecs, and WebSocket route. [Business Pack instructions](https://github.com/hakoniwalab/hakoniwa-business-pack/blob/main/AGENTS.md) · [Hakoniwa and ROS 2](../agents/en/hakoniwa-ros2.md)
- **Spreadsheet RTCs** — ExcelControlpy uses Microsoft Excel on Windows, pywin32, PyQt5, OpenRTM-aist Python, and generated IDL bindings. For LibreOffice Calc, make UNO and OpenRTM-aist Python available in the same runtime. [Dynamic RTC ports](../agents/en/dynamic-rtc-ports.md)

Record tool versions, executable paths, dependencies, and connection reachability. Follow the operation manual to verify actual data transfer. [Operation manual](operation-manual.md)

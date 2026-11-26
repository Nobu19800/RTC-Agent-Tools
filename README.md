# RTC-Agent-Tools

[日本語](README.ja.md)

RTC-Agent-Tools helps you design, build, and run robot systems with a coding agent such as Codex. Describe the system you want, review the proposal in RTSystemDesigner, then ask the agent to build and start the approved design. [Public RTSystemDesigner](https://nobu19800.github.io/RTSystemDesigner/)

## Try it

The [illustrated quickstart](docs/en/quickstart.md) walks through five messages you can send to either Codex or Claude Code to clone the repository, review the design, build and start a simulated mobile robot, drive it with a GUI joystick, and shut it down.

Open a working folder in Codex or start Claude Code from a terminal in that folder. Send the same first message in either agent. [Claude Code installation guide](https://code.claude.com/docs/en/setup#install-claude-code)

> Clone https://github.com/Nobu19800/RTC-Agent-Tools.git into this working folder.

[View the system architecture](docs/en/operation-specification.md#system-architecture) to see how Codex, GitHub, and RTSystemDesigner exchange design data.

## Documentation

| Document | What it covers |
| --- | --- |
| [Quickstart](docs/en/quickstart.md) | Build and try the joystick-controlled simulator |
| [Environment setup](docs/en/setup.md) | Prepare runtimes and dependencies |
| [Operation manual](docs/en/operation-manual.md) | Design, build, start, verify, and stop systems |
| [Detailed operating specification](docs/en/operation-specification.md) | Session data, catalogs, and build and runtime behavior |
| [Local RTSystemDesigner integration](docs/en/local-designer.md) | Run the Designer and session server locally |
| [RTC–Hakoniwa asset integration](docs/en/rtc-hakoniwa.md) | Connect an RTC DataPort to a native Hakoniwa PDU and verify the values |
| [RTC–ROS 2 integration](docs/en/rtc-ros2.md) | Verify a round trip with ROS2Transport |
| [CalcControl example](docs/en/calccontrol-example.md) | Connect ConsoleIn and ConsoleOut through LibreOffice Calc |
| [Start from an empty session](docs/en/empty-session.md) | Design the system yourself in RTSystemDesigner and hand it to the agent |
| [RTSystemDesigner module settings](docs/en/designer-module-settings.md) | Look up settings for RTCs, ROS 2 nodes, and Hakoniwa assets |
| [OpenRTM-aist serialization and transport plugins](docs/en/rtc-transport-plugins.md) | Understand and configure the plugins for Hakoniwa and ROS 2 |
| [Catalogs and XML profiles](docs/en/catalog-profiles.md) | Explore the four catalogs, ISO 22166-202 mappings, and RTC.xml |
| [AGENTS.md](AGENTS.md) | Repository instructions for agents and links to the language-specific guides |

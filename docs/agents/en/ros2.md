# Design and start ROS 2 nodes

Find a node with `python scripts/ros2_system.py search <query>`. Use its catalog ID with `add <catalog-id> design.json --instance <name> --namespace <namespace>`, or place it in Designer using catalog load. Record `data.moduleKind: ros2`, `data.catalogId`, package, executable, namespace and instance name.

Represent topics as data ports and services/actions as service ports with the applicable `rosInterfaceKind`. Match fully qualified types and directions. Remap topic subscriptions to the publisher's name and service clients to the provider's name; use matching fully qualified action names. Resolve conflicting remaps and incompatible domains before launch. For mixed edges use [ROS2Transport](ros2-transport.md) or [Hakoniwa bridging](hakoniwa-ros2.md).

After approval, select the ROS distribution and source its setup and workspace. Use `python3 scripts/ros2_system.py plan final-session.json` to review argv and `python3 scripts/ros2_system.py run final-session.json` to launch supported local executables. Working directory and parameter-file paths resolve from the design JSON. Arguments follow POSIX quoting without shell expansion. Environment takes one `NAME=value` per line and configuration is passed as ROS parameters. Ctrl+C stops the processes started by the command. Lifecycle transitions, launch files and component containers require package-specific procedures.

## Commands and formats from the original guide

```powershell
python scripts/ros2_system.py search "robot state publisher"
python scripts/ros2_system.py add ros2:robot_state_publisher/robot_state_publisher design.json --instance robot_state --namespace /demo
python scripts/ros2_system.py plan design.json
```

```bash
python3 scripts/ros2_system.py plan final-session.json
python3 scripts/ros2_system.py run final-session.json
```

[Detailed original guide (Japanese)](../ja/ros2.md)

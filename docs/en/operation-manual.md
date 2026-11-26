# RTC-Agent-Tools Operation Manual

[日本語](../operation-manual.md)

## 1. Prepare a design

Run commands from the RTC-Agent-Tools repository root. If you ask an agent to design the system, specify the required behavior, inputs and outputs, deployment environment, and expected verification results. You can search the catalogs directly.

~~~powershell
python rtc_search.py catalog/rtc_catalog.json camera --json
python hakoniwa_search.py catalog/hakoniwa_catalog.json Drone --json
python scripts/ros2_system.py search "robot state publisher"
~~~

To design in RTSystemDesigner, add a module, choose its **Module Kind**, and configure its ports and connections. Enter RTC implementation requirements in **Implementation → Requirements**. For ROS 2, check the package, executable, and namespace. For Hakoniwa, check PDU channels and the connections on either side of the bridge. Use **JSON Export** to share a local file or **Save** to update a session.

## 2. Review and approve the design

Register the proposal with the public session server and obtain a URL for review.

~~~powershell
$api = 'https://rt-session-server.rtsystem-designer-web.workers.dev/api/sessions'
$session = Invoke-RestMethod -Method Post -Uri $api -ContentType 'application/json' -InFile .\proposal.json
$designerUrl = $session.designerUrl
if (-not $designerUrl) {
    $designerUrl = "https://nobu19800.github.io/RTSystemDesigner/?session=$($session.sessionId)"
}
$designerUrl
~~~

Open the session link and review the modules, ports, connections, and implementation requirements. Save any edits and explicitly approve the design. In the same PowerShell session, retrieve the approved version.

~~~powershell
curl.exe --fail-with-body --silent --show-error "$api/$($session.sessionId)" -o final-session.json
~~~

If you approved a JSON export from the Designer, use that file as the final design. [Service endpoints](../agents/en/services.md)

## 3. Generate and run RTCs

For a new RTC, derive its definition JSON from the approved design. Convert it to XML and generate the skeleton. Replace `MyRTC` with the target RTC name. [JSON definition format](../agents/en/generation.md)

~~~powershell
python json_to_rtc_xml.py build/generated/MyRTC/MyRTC.json build/generated/MyRTC/RTC.xml
.\cuirtcbuilder.bat -d build/generated/MyRTC -f build/generated/MyRTC/RTC.xml
~~~

Implement and build the RTC, then prepare the deployment settings. If the system provides Windows lifecycle batches, run them in the target environment.

~~~powershell
.\build\system\scripts\start_rtcs.bat
.\build\system\scripts\connect_ports.bat
.\build\system\scripts\activate_rtcs.bat
~~~

Check registration, live port connections, and activation as each step completes. Send test input and compare it with the expected output. To stop, run `deactivate_rtcs.bat` followed by `stop_rtcs.bat`. Verify that RTCs are unregistered and dedicated processes have exited. Manage a shared naming service according to its ownership. If the agent reports that GUI checks remain, follow its instructions to verify the actual window and behavior. [RTC lifecycle and shutdown](../agents/en/runtime.md) · [Verification](../agents/en/verification.md)

## 4. Run systems with ROS 2 or Hakoniwa

Source the ROS 2 environment in the Linux or WSL2 shell.

~~~bash
python3 scripts/ros2_system.py plan final-session.json
python3 scripts/ros2_system.py run final-session.json
~~~

In another terminal with the same ROS environment, use `ros2 node list`, `ros2 node info`, `ros2 topic info`, and `ros2 topic echo`. Take node and topic names from the approved design and plan output. Use `rqt_graph` if a display is available. Press Ctrl+C in the launch terminal to stop nodes started by `run`.

- **RTC and ROS 2** — Align each RTC's `rtc.conf` and the ROS settings. [ROS2Transport](../agents/en/ros2-transport.md) · [Round-trip example](../../examples/ros2-transport/README.md)
- **Hakoniwa and ROS 2** — Compare PDU values with the values received by ROS 2. For a viewer, check both the WebSocket connection and visible changes to the robot and its pose. [Hakoniwa–ROS 2 workflow](../agents/en/hakoniwa-ros2.md)
- **ExcelControlpy and Calc** — Create the dynamic ports for the cells defined in Requirements. Check that the integer from ConsoleIn is written to the cell and that ConsoleOut receives the same value. For advancing cells, send at least two different values and verify the cell order. [Spreadsheet RTC workflow](../agents/en/dynamic-rtc-ports.md)

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Session fails to open | HTTPS access, session ID, and registration response |
| RTC does not register | Startup log, naming service address, advertised IOR, and reachability from the operator's terminal |
| Ports do not connect | Live port names, directions, types, ServicePort polarity, and dynamic port creation order |
| ROS 2 nodes or topics are missing | ROS setup, namespace, DDS domain, discovery settings, and transport startup logs |
| Topic exists but values do not arrive | Publisher and subscriber roles, type, QoS, RTC state, and bridge endpoints |
| Robot is missing from the viewer | WebSocket, viewer settings, model and codec, incoming data, and rendered scene |
| Process remains after shutdown | Naming service registration, process ID and executable path, and manager ownership |

Record the design, test inputs, observations, logs, and any remaining checks. [Verification and logs](../agents/en/verification.md)

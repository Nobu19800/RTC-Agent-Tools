# Local RTSystemDesigner Integration Test

[日本語](../local-designer.md)

Place compatible RTSystemDesigner and RTC-Agent-Tools checkouts side by side. This procedure uses Windows PowerShell, Node.js 24, npm, and Python 3.

Send the quoted request to Codex or Claude Code. The agent prepares dependencies from the parent folder and keeps the local server running.

> Start local RTSystemDesigner and open a test session.

Example commands the agent runs.

~~~powershell
npm.cmd --prefix .\RTSystemDesigner ci
npm.cmd --prefix .\RTSystemDesigner run dev:integration
~~~

For the same request, the agent switches to RTC-Agent-Tools in a separate shell, registers the smoke-test session, and opens it.

Example commands the agent runs.

~~~powershell
Set-Location .\RTC-Agent-Tools
$session = python .\scripts\local_designer_session.py create .\examples\local-designer\session.json | ConvertFrom-Json
$session.designerUrl
Start-Process $session.designerUrl
~~~

In the browser, move the SmokeRTC0 node and click **Save**. Close the confirmation dialog and reload the page. The node should appear at its saved position. Retrieve the saved JSON from the terminal.

> Retrieve the saved local session.

Example commands the agent runs.

~~~powershell
python .\scripts\local_designer_session.py get $session.sessionId
~~~

Use `create <proposal-json>` and `get <sessionId> --output <path>` to register a proposal and save the reviewed design. Use the same local server throughout. Sessions are stored in memory and disappear when Vite restarts. Export any required JSON before stopping it.

The default endpoint is `127.0.0.1:5173`. The integration test API uses the same origin as the Designer and keeps sessions local. Standard `npm run dev` and `npm run build` select the public API.

## Stream a Hakoniwa Drone pose to ROS 2

Start with the design in `examples/local-designer/hakoniwa-ros2-pose-session.json`. Approve the design in the Designer, retrieve it using `local_designer_session.py get`, and pass the JSON to the verification script in WSL2.

> Verify that the Hakoniwa Drone pose reaches ROS 2.

Example commands the agent runs.

~~~bash
bash examples/local-designer/verify-hakoniwa-ros2.sh "$APPROVED_SESSION" \
  "$FOUNDATION_ROOT" "$DRONE_ROOT" "$RECIPE_WORK_DIR" "$PDU_ROS_SOURCE"
~~~

The arguments are the approved session, Business Pack Foundation, Drone runtime directory, `drone-position-pdu-live` Recipe work directory, and `hakoniwa-pdu-ros` source checkout. ROS 2 Jazzy is required in WSL2. The script connects as a reader to a dedicated memory-mapped region and compares all six fields on ROS 2 topic `/pdu/Drone/pos` with the PDU values. It prints the directory where it writes startup and receive logs.

The test uses `drone_pose_bridge.py` to read the latest PDU every 20 ms and publish it using the `hakoniwa-pdu-ros` type conversion and QoS settings. With event notifications, a pending receive event can reject the next write and stop Drone with `hako_asset_start() error: 5`. The script generates an offset initial position in the run directory. The Drone receives no flight commands during this test.

### Add the Three.js viewer

Register `examples/local-designer/hakoniwa-ros2-viewer-session.json` and pass the approved design to the same script. In WSL2, set `HAKONIWA_VISUAL_PUBLISHER` to `tools/recipe/drone_gui_visual_state.py` in the Business Pack and set `HAKONIWA_VIEWER_ROOT` to the Three.js Drone checkout.

To try the viewer, ask the agent:

> Start the test with the Three.js viewer.

The agent adds `--keep-running` as the sixth argument to keep the system running while you check the viewer connection, rendered Drone, and displayed coordinates. To stop the test, send the request below. The agent interrupts the process it started.

> Stop the test.

[Three.js viewer](http://127.0.0.1:8000/index.html?viewerConfigPath=/config/viewer-config-fleets.json&wsUri=ws://127.0.0.1:8765&wireVersion=v2)

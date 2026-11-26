# Connect Hakoniwa assets to ROS 2

Use a PDU-to-ROS bridge and show it as a distinct module. Represent the Hakoniwa leg as a PDU connection and the ROS 2 leg as a topic. Preserve the PDU robot, channel, layout, and ROS message and QoS. The local test ROS 2 bridge is modeled as a ROS 2 node. Add any viewer and WebSocket path required by the approved design.

Prepare the selected Recipe's Workspace and Foundation using the [Business Pack instructions](https://github.com/hakoniwalab/hakoniwa-business-pack/blob/main/AGENTS.md). Use the saved design after approval. Configure the bridge separately from RTC ROS2Transport. The verified Drone example sends `Drone/pos`, channel 1, 72 bytes, to `/pdu/Drone/pos` as `geometry_msgs/msg/Twist` on Jazzy. Verify all six values against the PDU and check the actual viewer when required. Preserve the selected launch settings and logs; use a dedicated test mmap. [Runnable example](../../local-designer.md)

[Detailed original guide (Japanese)](../ja/hakoniwa-ros2.md)

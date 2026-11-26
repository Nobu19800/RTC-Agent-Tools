# OpenRTM-aist Serialization and Transport Plugins

[日本語](../rtc-transport-plugins.md)

RTCs use typed DataPorts. Each connection selects a serializer and deserializer through `dataport.marshaling_type` and a communication interface through `dataport.interface_type`. The serializer converts an RTC value to the representation the peer expects. The deserializer converts received data to the InPort's RTC type. The transport plugin sends that representation and delivers received data to the connector.

| Integration | Type conversion | Communication interface |
| --- | --- | --- |
| RTC–Hakoniwa | `HakoniwaSerializer.py` converts between RTC values and PDU bytes | `HakoniwaTransport.py` registers `hakoniwa` and reads or writes native PDUs |
| RTC–ROS 2 (Python) | Converters registered by `ROS2Transport.py` for supported ROS message types | `ros2`. The reference implementation publishes and subscribes through `rclpy` |
| RTC–ROS 2 (C++) | ROS 2-compatible converters registered by `ROS2Transport` | `fast-rtps` from `FastRTPSTransport`, or `fast-dds` from a compatible `FastDDSTransport` build |

## RTC–Hakoniwa asset

| Direction | Data path |
| --- | --- |
| RTC to Hakoniwa | RTC OutPort → serializer → `hakoniwa` InPortConsumer → PDU write → asset |
| Hakoniwa to RTC | Asset → PDU read → `hakoniwa` InPortProvider → deserializer → RTC InPort |

The example maps `RTC::TimedVelocity3D` fields `vx, vy, vz` to Twist `linear.x, y, z` and `vr, vp, va` to `angular.x, y, z`. The `raw48` format contains six little-endian double-precision values. The `metadata72` format adds a 24-byte header to the same payload. Twist has no acquisition timestamp, so the example sets the received RTC timestamp to zero. This mapping carries velocity. A PDU that uses Twist for pose needs its own mapping. [Serializer implementation](../../examples/hakoniwa_transport/HakoniwaSerializer.py)

Load both plugins from the RTC's `rtc.conf`. Set `dataport.interface_type: hakoniwa` and the matching serializer, for example `dataport.marshaling_type: hakoniwa:geometry_msgs/Twist:raw48`. Match the robot name, channel ID, capacity, and layout to the asset. Prepare the Conductor and PDU region before connecting. When the asset exposes no CORBA port, use the verified single-port connection procedure on the RTC endpoint. [Transport implementation](../../examples/hakoniwa_transport/HakoniwaTransport.py) · [Connection contract and configuration](../agents/en/hakoniwa-serializer.md)

## RTC–ROS 2 node

| Direction | Data path |
| --- | --- |
| RTC to ROS 2 | RTC OutPort → ROS 2 type conversion → publisher endpoint → ROS 2 subscriber |
| ROS 2 to RTC | ROS 2 publisher → subscriber endpoint → conversion to the RTC type → RTC InPort |

For `RTC::TimedString` and `std_msgs/msg/String`, use `ros2:std_msgs/String`. In C++, ROS2Transport registers the type converters, and the selected FastRTPS or FastDDS plugin transfers topic data through DDS APIs. The named `ROS2TransportNamed` variant obtains endpoint GUIDs from the compatible `DDSEndpoints` API and announces node and endpoint information on `ros_discovery_info`. The DDS transport plugin continues to handle data topics. [C++ round-trip test and named discovery](../../examples/ros2-transport/README.md)

The launch tooling generates `manager.modules.load_path`, `manager.modules.preload`, and `manager.components.preconnect` from the approved design. Check the endpoint types, topic name, DDS domain, discovery scope, and QoS. This connection path supports Pub/Sub. [ROS2Transport settings](../agents/en/ros2-transport.md) · [Configuration generator](../../scripts/ros2_transport.py)

## Verify the connections

- **Hakoniwa** — Read the PDU and compare its values and byte length with the sent data and the PDU definition. [Native PDU verification example](../../examples/hakoniwa_transport/README.md)
- **ROS 2** — Check endpoints with `ros2 topic info` and verify actual values with `ros2 topic echo` or receiver logs. For named discovery, also use `ros2 node list` and `ros2 node info`.

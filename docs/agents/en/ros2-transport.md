# Connect RTC DataPorts to ROS 2 topics

Use typed RTC ports and OpenRTM ROS2Transport. Match direction, full topic and message type, compatible serializer, DDS domain and QoS. The [settings generator](../../../scripts/ros2_transport.py) defines supported mappings, such as `RTC::TimedString` to `std_msgs/msg/String`. Use an explicit integration for unmatched types, services or actions.

After approval run `python3 scripts/ros2_system.py transport <session> --rtc-id <id> --base-conf <file> --module <module> --output <file>`. Review the generated rtc.conf and preload settings. The standard C++ FastRTPS backend uses `fast-rtps.domain.id`; with the named variant, select the installed FastRTPS or FastDDS backend and its corresponding domain setting. The named C++ module publishes node and endpoint discovery on `ros_discovery_info` while transport runs through DDS.

Verify matching `ROS_DOMAIN_ID`, discovery settings, names, direction and real message flow. Use `ros2 node list`, `ros2 node info` and `ros2 topic echo` as applicable. Report actual value transfer separately from discovery. [Runnable round-trip example](../../../examples/ros2-transport/README.md)

## Commands and formats from the original guide

```bash
source /opt/ros/jazzy/setup.bash
python3 scripts/ros2_system.py plan final-session.json
python3 scripts/ros2_system.py transport final-session.json \
  --rtc-id echo --base-conf rtc.conf \
  --module /usr/lib/python3/dist-packages/OpenRTM_aist/ext/transport/ROS2Transport/ROS2Transport.py \
  --output rtc-ros2.conf
```

[Detailed original guide (Japanese)](../ja/ros2-transport.md)

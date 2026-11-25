"""Publish the latest Drone mmap PDU without registering a receive event."""

import struct
import sys

import hakopy
import rclpy
from rclpy.executors import ExternalShutdownException
from hakoniwa_pdu_ros.config_loader import load_config
from hakoniwa_pdu_ros.qos import to_rclpy_qos_profile
from hakoniwa_pdu_ros.type_mapper import import_ros_msg_class, pdu_bytes_to_ros_msg


def main():
    binding, = load_config(sys.argv[1]).bindings
    if binding.direction != "pdu_to_ros":
        raise ValueError("The mmap pose adapter only supports PDU to ROS")
    if not hakopy.init_for_external():
        raise RuntimeError("Cannot attach to the Drone mmap")
    rclpy.init()
    node = rclpy.create_node("hakoniwa_pdu_ros_bridge")
    try:
        message = import_ros_msg_class(binding.pdu_type)
        publisher = node.create_publisher(message, binding.topic, to_rclpy_qos_profile(binding.qos))

        def publish_latest():
            data = hakopy.pdu_read(binding.pdu_key.robot_name, binding.channel_id, binding.pdu_size)
            if data is None or len(data) != binding.pdu_size:
                return
            if struct.unpack_from("<I", data)[0] == 0x12345678:
                publisher.publish(pdu_bytes_to_ros_msg(data, binding.pdu_type))

        node.create_timer(0.02, publish_latest)
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()

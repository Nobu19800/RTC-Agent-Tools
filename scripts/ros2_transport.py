"""Build OpenRTM ROS2Transport settings for RTC DataPort endpoints."""

from dataclasses import dataclass
from pathlib import Path
import re


STD_TYPES = {
    "Float": "Float32", "Double": "Float64", "Short": "Int16", "Long": "Int32",
    "UShort": "UInt16", "ULong": "UInt32",
}
RTC_TO_ROS = {
    **{f"Timed{rtc}": f"std_msgs/msg/{ros}" for rtc, ros in STD_TYPES.items()},
    **{f"Timed{rtc}Seq": f"std_msgs/msg/{ros}MultiArray" for rtc, ros in STD_TYPES.items()},
    "TimedString": "std_msgs/msg/String",
    "TimedPoint3D": "geometry_msgs/msg/PointStamped",
    "TimedQuaternion": "geometry_msgs/msg/QuaternionStamped",
    "TimedVector3D": "geometry_msgs/msg/Vector3Stamped",
    "CameraImage": "sensor_msgs/msg/Image",
}


def serializer(rtc_type, ros_type):
    name = rtc_type.removeprefix("IDL:").removesuffix(":1.0").replace("::", "/")
    if name.startswith("RTC/") and RTC_TO_ROS.get(name[4:]) == ros_type:
        return "ros2:" + ros_type.replace("/msg/", "/")
    return None


@dataclass(frozen=True)
class Binding:
    rtc_id: str
    endpoint: str
    topic: str
    serializer: str
    domain: str
    publishes: bool

    def preconnect(self, native=False, interface=None):
        interface = interface or ("fast-rtps" if native else "ros2")
        topic = self.topic.lstrip("/") if native else self.topic
        options = (f"{self.endpoint}?interface_type={interface}&dataflow_type=push&"
                   f"marshaling_type={self.serializer}&{interface}.topic={topic}")
        if native and self.publishes:
            options += f"&{interface}.publisher.qos.reliability.kind=RELIABLE_RELIABILITY_QOS"
        return options


def render_config(base, bindings, module: Path):
    if module.name not in {"ROS2Transport.py", "ROS2Transport.so", "ROS2Transport.dll", "ROS2TransportNamed.so"}:
        raise ValueError("Select ROS2Transport.py, ROS2Transport.so/.dll, or ROS2TransportNamed.so")
    if re.search(r"[,\r\n]", str(module)):
        raise ValueError("ROS2Transport module path cannot contain commas or newlines")
    named = module.name == "ROS2TransportNamed.so"
    native = module.suffix != ".py"
    modules = [module.name]
    interface = "ros2"
    if native:
        backends = {"fast-rtps": "FastRTPSTransport", "fast-dds": "FastDDSTransport"}
        available = {
            name: plugin + module.suffix for name, plugin in backends.items()
            if module.with_name(plugin + module.suffix).is_file()
        }
        if len(available) != 1:
            raise ValueError(f"Expected exactly one DDS transport plugin beside {module.name}")
        interface, plugin = next(iter(available.items()))
        modules.insert(0, plugin)
    entries = {
        "manager.modules.load_path": [str(module.parent)],
        "manager.modules.preload": modules,
        "manager.components.preconnect": [binding.preconnect(native, interface) for binding in bindings],
    }
    if native:
        domains = {binding.domain for binding in bindings}
        if len(domains) != 1 or any(not re.fullmatch(r"\d+", domain) or int(domain) > 232 for domain in domains):
            raise ValueError("Expected one ROS domain ID between 0 and 232")
        entries[f"{interface}.domain.id"] = list(domains)
    if named:
        entries["ros2.node.name"] = [bindings[0].endpoint.split(".", 1)[0].replace("-", "_")]
    seen = set()
    lines = []
    for line in base.splitlines():
        key, sep, value = line.partition(":")
        key = key.strip()
        if sep and key in entries:
            if key in seen or value.rstrip().endswith("\\"):
                raise ValueError(f"Expected a single line for {key} in the base rtc.conf")
            seen.add(key)
            existing = [item.strip() for item in value.split(",") if item.strip()]
            if key in {"ros2.domain.id", "fast-rtps.domain.id", "fast-dds.domain.id"} and existing and existing != entries[key]:
                raise ValueError("The ROS domain ID in rtc.conf differs from the design")
            if key == "ros2.node.name" and existing:
                if len(existing) != 1 or not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", existing[0]):
                    raise ValueError("Expected one valid ROS 2 node name in rtc.conf")
                entries[key] = existing
            lines.append(f"{key}: {', '.join(dict.fromkeys(existing + entries[key]))}")
        elif any(re.match(rf"^\s*{re.escape(key)}(?:\s|=)", line) for key in entries):
            raise ValueError("Use key: value syntax for the base ROS2Transport manager settings")
        else:
            lines.append(line)
    for key, values in entries.items():
        if key not in seen:
            lines.append(f"{key}: {', '.join(values)}")
    return "\n".join(lines) + "\n"

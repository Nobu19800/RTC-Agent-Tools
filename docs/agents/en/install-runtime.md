# Install runtime environments

Identify the intended host and architecture. On Ubuntu or inside WSL2 check `/etc/os-release` and `dpkg --print-architecture`; identify the WSL distribution on Windows with `wsl --list --verbose`. Record the versions and locations actually used.

## OpenRTM-aist

- **Windows** — Select the newest compatible MSI from the [official installer directory](https://packages.openrtm.org/pub/Windows/OpenRTM-aist/). Reuse compatible Visual Studio with C++ desktop development, Python, and CMake. Install missing prerequisites and confirm the architecture, tools, SDK, and Python imports used by deployment.
- **Ubuntu and WSL2** — Use the [official Linux procedure](https://openrtm.org/ja/doc/installation/install_2_1/install_linux_2_1/install_2_1/). Download and inspect `openrtm2_install_ubuntu.sh` from the upstream repository, then run it with Bash on the intended host. For supported ROS2Transport packages, prepare the compatible ROS 2 installation first and use the documented `-l all --ros2` option.
- **C++ on WSL2** — After setting up APT, check `apt-cache policy openrtm2`. Build and use the upstream C++ runtime when the candidate is `2.1.0-0`. Use the APT package when a newer candidate is offered.

## ROS 2 on Ubuntu and WSL2

Use Humble for Ubuntu 22.04 Jammy, Jazzy for 24.04 Noble, and Lyrical for 26.04 Resolute. Respect the approved design or Recipe's required distribution by selecting a compatible Ubuntu host. Reuse a compatible installation. For new installations, check the UTF-8 locale and Universe, configure `ros2-apt-source`, and install the matching `ros-<distro>-ros-base` or `ros-<distro>-desktop` when GUI tools are required. Source `/opt/ros/<distro>/setup.bash`, run `ros2 doctor --report`, and check required package executables. [Official ROS APT setup](https://github.com/ros2/ros2_documentation/blob/rolling/source/Get-Started/Installation/_Apt-Repositories.rst)

## Hakoniwa on Ubuntu and WSL2

Start with the [Business Pack AGENTS.md](https://github.com/hakoniwalab/hakoniwa-business-pack/blob/main/AGENTS.md). Prepare the selected Recipe's Workspace and Foundation, including its native bindings, PDU configuration, viewer dependencies and preflight checks.

## Commands and formats from the original guide

```bash
curl -fL https://raw.githubusercontent.com/OpenRTM/OpenRTM-aist/master/scripts/openrtm2_install_ubuntu.sh -o openrtm2_install_ubuntu.sh
less openrtm2_install_ubuntu.sh
bash openrtm2_install_ubuntu.sh
dpkg -l 'openrtm2*'
```

```bash
(
  set -e -o pipefail
  . /etc/os-release
  test "$ID" = ubuntu
  case "$VERSION_CODENAME" in
    jammy)    rtc_ros_distro=humble ;;
    noble)    rtc_ros_distro=jazzy ;;
    resolute) rtc_ros_distro=lyrical ;;
    *) printf 'Unsupported Ubuntu release: %s\n' "$VERSION_CODENAME" >&2; exit 1 ;;
  esac
  sudo apt update
  sudo apt install curl python3 software-properties-common
  sudo add-apt-repository universe
  if ! dpkg-query -W -f='${Status}\n' ros2-apt-source 2>/dev/null | grep -qx 'install ok installed'; then
    rtc_ros_source_version=$(curl -fsSL https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest |
      python3 -c 'import json, sys; print(json.load(sys.stdin)["tag_name"])')
    test -n "$rtc_ros_source_version"
    rtc_ros_deb=$(mktemp --suffix=.deb)
    trap 'rm -f -- "$rtc_ros_deb"' EXIT
    curl -fL "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${rtc_ros_source_version}/ros2-apt-source_${rtc_ros_source_version}.${VERSION_CODENAME}_all.deb" -o "$rtc_ros_deb"
    sudo dpkg -i "$rtc_ros_deb"
  fi
  sudo apt update
  apt-cache policy "ros-${rtc_ros_distro}-ros-base"
  sudo apt install "ros-${rtc_ros_distro}-ros-base"
)
```

```bash
source /opt/ros/jazzy/setup.bash
ros2 doctor --report
```

[Detailed original guide (Japanese)](../ja/install-runtime.md)

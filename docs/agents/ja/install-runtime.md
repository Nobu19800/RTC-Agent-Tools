# 実行環境のインストール

対象ホストと確定設計の依存関係を先に確認する。Ubuntu と WSL2 では、インストールするシェルで `cat /etc/os-release` と `dpkg --print-architecture` を確認する。WSL2 の場合は Windows 側で `wsl --list --verbose` を実行し、セットアップ先のディストリビューションを特定する。導入後は使用する実行ファイルとバージョンを記録する。[環境の確認手順](environment.md)

## OpenRTM-aist / Windows

1. 公式配布ディレクトリを開き、対象アーキテクチャと利用するツールチェーンに合う最新の OpenRTM-aist MSI を選ぶ。バージョン番号を比較し、ファイル名、取得 URL、バージョンを記録する。[OpenRTM-aist Windows 配布ディレクトリ](https://packages.openrtm.org/pub/Windows/OpenRTM-aist/)
2. Visual Studio の **C++ によるデスクトップ開発**、Python、CMake を確認する。インストール済みの互換バージョンは再利用し、不足するものを公式配布元から導入する。MSI が対応する MSVC ツールセットと Python のバージョン・アーキテクチャを確認する。[OpenRTM-aist Windows の導入案内](https://openrtm.org/en/download/)
3. 取得した MSI を実行し、確定設計に必要な SDK とサンプルを選んでインストールする。新しい端末で `python --version`、`cmake --version` を確認し、Visual Studio の開発者端末で `cl` を確認する。Python RTC を使う場合は、実行予定の Python で `python -c "import OpenRTM_aist, omniORB"` を実行する。

## OpenRTM-aist / Ubuntu・WSL2

Ubuntu と WSL2 内の Ubuntu では、OpenRTM-aist 2.1 の公式 Linux 手順を使う。公式ページが案内する Ubuntu と CPU アーキテクチャを確認し、対象外の Ubuntu では配布ページで対応する導入方法を確認する。[指定の Linux インストール手順](https://openrtm.org/ja/doc/installation/install_2_1/install_linux_2_1/install_2_1/) · [公式手順の英語版](https://www.openrtm.org/openrtm/en/doc/installation/install_2_1/install_linux_2_1/install_2_1?language=en)

公式スクリプトを取得して内容を確認し、対象 Ubuntu の Bash で実行する。次は公式の一括インストールを、ダウンロードと実行に分けた例である。

```bash
curl -fL https://raw.githubusercontent.com/OpenRTM/OpenRTM-aist/master/scripts/openrtm2_install_ubuntu.sh -o openrtm2_install_ubuntu.sh
less openrtm2_install_ubuntu.sh
bash openrtm2_install_ubuntu.sh
dpkg -l 'openrtm2*'
```

公式配布の ROS2Transport を使う場合は、先に対応する ROS 2 を用意し、公式手順に示される `-l all --ros2` を使う。必要な配布パッケージと、選んだ ROS 2 との互換性を確認する。

WSL2 で **C++ 版を実行に使う場合**は、公式 APT ソースの設定後に `apt-cache policy openrtm2` を実行する。候補が `2.1.0-0` の場合は上流ソースをビルドし、その C++ 実行ファイルとライブラリを使う。これより新しい APT 版があれば APT 版を使う。ソースビルド時は使用したリビジョンとインストール先を記録する。[OpenRTM-aist ソース](https://github.com/OpenRTM/OpenRTM-aist)

## ROS 2 / Ubuntu・WSL2

WSL2 では、Windows のバージョンではなく配備先 Ubuntu のリリースで選ぶ。確定設計や箱庭 Recipe がディストリビューションを指定している場合は、その指定と Ubuntu の組み合わせを確認する。互換性がなければ、その Ubuntu に別のディストリビューション向け APT パッケージを入れず、対応する Ubuntu 環境を使う。

| Ubuntu | 既定の ROS 2 | APT パッケージ |
| --- | --- | --- |
| 22.04 Jammy | Humble | `ros-humble-ros-base` / `ros-humble-desktop` |
| 24.04 Noble | Jazzy | `ros-jazzy-ros-base` / `ros-jazzy-desktop` |
| 26.04 Resolute | Lyrical | `ros-lyrical-ros-base` / `ros-lyrical-desktop` |

対応は [Humble の公式手順](https://github.com/ros2/ros2_documentation/blob/humble/source/Installation/Ubuntu-Install-Debs.rst)、[Jazzy の公式手順](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Installation/Ubuntu-Install-Debs.rst)、[Lyrical の公式リリース案内](https://discourse.openrobotics.org/t/ros-2-lyrical-luth-released/55021) に基づく。表にないリリースとアーキテクチャは対象ディストリビューションの公式サポート情報を確認する。このリポジトリの既存連携テストを再現する場合は、各テストで指定された Jazzy の環境を使う。

対応する ROS 2 が導入済みであれば再利用する。新規導入では UTF-8 ロケールと Ubuntu の `universe` を確認し、公式 `ros2-apt-source` を設定する。以下は端末実行を前提に `ros-base` を選ぶ例である。RViz や GUI ツールも必要な構成では `desktop` を選ぶ。WSL2 で GUI を使う場合は WSLg などの表示環境を確認する。[ROS の公式 APT 設定](https://github.com/ros2/ros2_documentation/blob/rolling/source/Get-Started/Installation/_Apt-Repositories.rst)

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

利用する端末で対象ディストリビューションのセットアップを読み込む。以下は Jazzy の例である。Humble と Lyrical はパス中のディストリビューション名を置き換える。

```bash
source /opt/ros/jazzy/setup.bash
ros2 doctor --report
```

確定設計で使うパッケージは `ros2 pkg executables <package>` で確認する。実行や追加パッケージの扱いは [ROS 2 起動手順](ros2.md) に従う。

## 箱庭 / Ubuntu・WSL2

確定設計に箱庭アセットが含まれる場合は、配備先の Ubuntu または WSL2 内の Ubuntu で作業する。Business Pack の `AGENTS.md` を起点に対象 Recipe の手順を特定し、Workspace と Foundation を構築する。依存バージョン、セットアップコマンド、ビューアの要件、事前確認は選んだ Recipe とコンポーネントの手順に従う。導入後は確定設計が必要とする実行ファイル、Python バインディング、PDU 定義とビューアの構成を確認する。[Hakoniwa Business Pack の AGENTS.md](https://github.com/hakoniwalab/hakoniwa-business-pack/blob/main/AGENTS.md)

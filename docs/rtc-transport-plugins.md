# OpenRTM-aist の型変換と通信プラグイン

[English](en/rtc-transport-plugins.md)

RTC は型付き DataPort を使い、接続ごとに型変換と通信方式を選びます。`dataport.marshaling_type` はシリアライザ・デシリアライザの識別子、`dataport.interface_type` は通信インターフェースの識別子です。シリアライザは RTC の値を相手が扱う表現に変換し、デシリアライザは受信した表現を InPort の RTC 型に戻します。通信プラグインはその表現を相手に届け、受信データをコネクタに渡します。

| 連携 | 型変換 | 通信インターフェース |
| --- | --- | --- |
| RTC–箱庭 | `HakoniwaSerializer.py` が RTC 型と PDU のバイト列を相互変換する | `HakoniwaTransport.py` が `hakoniwa` を登録し、ネイティブ PDU を読み書きする |
| RTC–ROS 2（Python） | `ROS2Transport.py` が登録する ROS メッセージ型別の変換を使います | `ros2`（参照実装は `rclpy` で配信・購読します） |
| RTC–ROS 2（C++） | `ROS2Transport` が登録する ROS 2 互換の型変換を使う | `FastRTPSTransport` の `fast-rtps`、または対応ビルドで `FastDDSTransport` の `fast-dds` |

## RTC–箱庭アセット

| 方向 | データの流れ |
| --- | --- |
| RTC → 箱庭 | RTC OutPort → シリアライザ → `hakoniwa` の InPortConsumer → PDU 書き込み → アセット |
| 箱庭 → RTC | アセット → PDU 読み出し → `hakoniwa` の InPortProvider → デシリアライザ → RTC InPort |

サンプルの変換器は `RTC::TimedVelocity3D` の `vx, vy, vz` を Twist の `linear.x, y, z` に、`vr, vp, va` を `angular.x, y, z` に割り当てます。`raw48` はリトルエンディアンの倍精度値6個、`metadata72` は同じ本体に24バイトのヘッダーを付けた形式です。Twist には取得時刻がないため、サンプルは受信時の RTC タイムスタンプをゼロにします。この変換は速度用で、位置・姿勢に Twist を使う PDU には別の対応付けが必要になります。 [シリアライザ実装](../examples/hakoniwa_transport/HakoniwaSerializer.py)

対象 RTC の `rtc.conf` で両プラグインをロードします。接続時は `dataport.interface_type: hakoniwa` と、たとえば `dataport.marshaling_type: hakoniwa:geometry_msgs/Twist:raw48` を指定します。ロボット名、チャンネル ID、PDU 容量とレイアウトをアセット側に合わせます。接続前に Conductor と対象 PDU 領域を準備します。アセットが CORBA ポートを持たない場合は、対象 RTC のポートに対して確認済みの単一ポート接続手順を使います。 [通信プラグイン実装](../examples/hakoniwa_transport/HakoniwaTransport.py) · [接続契約と設定](agents/ja/hakoniwa-serializer.md)

## RTC–ROS 2 ノード

| 方向 | データの流れ |
| --- | --- |
| RTC → ROS 2 | RTC OutPort → ROS 2 向け型変換 → 配信端点 → ROS 2 Subscriber |
| ROS 2 → RTC | ROS 2 Publisher → 購読端点 → RTC 型への変換 → RTC InPort |

たとえば `RTC::TimedString` と `std_msgs/msg/String` を接続する場合、変換名は `ros2:std_msgs/String` です。C++ の構成では ROS2Transport が型変換を登録し、トピックのデータ送受信は選択した FastRTPS／FastDDS プラグインが DDS API で行います。名前付き構成の `ROS2TransportNamed` は、対応する `DDSEndpoints` から得た端点 GUID とノード情報を `ros_discovery_info` で通知します。データトピックの送受信は引き続き DDS プラグインが担当します。 [C++ 往復テストと名前付き構成](../examples/ros2-transport/README.md)

起動ツールは確定設計から `manager.modules.load_path`、`manager.modules.preload`、`manager.components.preconnect` を生成します。両端の型、トピック名、DDS ドメイン、探索範囲と QoS を照合します。この経路の対象は Pub/Sub です。 [ROS2Transport 設定](agents/ja/ros2-transport.md) · [設定生成コード](../scripts/ros2_transport.py)

## 接続を検証する

- **箱庭** — PDU を読み出し、フィールド値とバイト長を送信値および PDU 定義と照合します。 [ネイティブ PDU 検証例](../examples/hakoniwa_transport/README.md)
- **ROS 2** — `ros2 topic info` で端点を調べ、`ros2 topic echo` または受信ログで実際の値を確認します。名前付き構成では `ros2 node list` と `ros2 node info` も使います。

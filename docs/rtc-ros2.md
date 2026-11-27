# RTC–ROS 2 連携手順

[English](en/rtc-ros2.md)

OpenRTM-aist Python の標準 GUI サンプル `TkJoyStick` で、ROS 2 Jazzy の Turtlesim のカメを操作する例です。

```mermaid
flowchart LR
    joy["TkJoyStick0 · RTC"]
    sim["turtlesim_node · ROS 2"]
    joy -->|"pos · ROS2Transport + 専用シリアライザ · /turtle1/cmd_vel"| sim
```

## 1. 設計する

> 標準の TkJoyStick で ROS 2 の Turtlesim を操作するシステムを設計して。

RTSystemDesigner で、既存の `TkJoyStick0.pos` と既存の `turtlesim_node` の購読ポートの接続を確認します。ROS2Transport の専用シリアライザが `RTC::TimedFloatSeq` を `geometry_msgs/msg/Twist` に変換し、`/turtle1/cmd_vel` に配信します。Y を前後速度 `linear.x`、X を旋回速度 `angular.z` に換算します。中央入力や不正値はゼロ速度に変換し、速度に上限を設けます。標準 TkJoyStick の GUI とポートはそのまま使います。

## 2. 構築して起動する

> 設計完了。TkJoyStick と Turtlesim を起動して。

エージェントは ROS 2 Jazzy と Python 版 OpenRTM-aist を準備し、同じ ROS ドメインで Turtlesim と TkJoyStick を起動します。Turtlesim の起動コマンドは `ros2 run turtlesim turtlesim_node` です。TkJoyStick の RTC Manager には `rtc.conf` で ROS2Transport と専用シリアライザをロードします。

標準の TkJoyStick は Manager の起動時設定が適用された後に RTC を生成するため、`pos` の preconnect が成立しない場合があります。エージェントはネームサーバーへの登録後に `pos` のコネクタを確認します。未接続なら `PortService.connect` で `pos` 単独のコネクタを作成し、`dataport.interface_type=ros2`、`dataport.dataflow_type=push`、`dataport.marshaling_type=ros2:tkjoystick/Twist`、`dataport.ros2.topic=/turtle1/cmd_vel` を設定してから RTC を活性化します。[ROS2Transport 設定](agents/ja/ros2-transport.md)

## 3. 動作を確認して終了する

TkJoyStick の中央の丸をドラッグし、Turtlesim のカメが動くことを確認します。離して中央に戻すと停止します。エージェントは速度指令とカメの位置を確認し、配信が途絶えた場合も Turtlesim の受信タイムアウトで停止することを確認します。

```bash
ros2 topic info /turtle1/cmd_vel
ros2 topic echo /turtle1/cmd_vel
ros2 topic echo /turtle1/pose
```

> システムを終了して。

エージェントは両プロセスの終了と `TkJoyStick0` の登録解除を確認します。共有ネームサーバーは稼働を続けます。

WSL2 の Jazzy で、CLI から標準の入力コールバックに `[0, 60]` を渡すと、専用シリアライザ経由で `linear.x=1.0` が配信され、カメの X 座標は約 5.54 から 8.57 に変化しました。中央入力と配信停止の両方で停止を確認しました。別途、両ウィンドウを表示して利用者がマウス操作による動作を確認しました。この環境では `ros2 topic info` が Publisher を 0 件と表示する場合でも、`ros2 topic echo` で `Twist` を受信できました。疎通は実データと位置の変化も使って判定してください。

[専用シリアライザ](../examples/ros2-transport/TkJoyStickTwistSerializer.py)

[OpenRTM-aist の型変換と通信プラグイン](rtc-transport-plugins.md)

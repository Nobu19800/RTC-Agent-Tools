# RTC DataPort と ROS 2 トピックの接続

ローカル Designer への登録から通信確認までを試す場合は [往復テスト](../../examples/ros2-transport/README.md) を参照してください。

Designer では RTC の OutPort と ROS 2 の Subscriber、または ROS 2 の Publisher と RTC の InPort を接続できます。対応する型のポートを選ぶと、接続線に `data.transport: ros2` が付きます。起動ツールは端点のモジュール種別と方向を再検証します。既存の v2 設計でこのラベルが省略されていても、RTC と ROS 2 の組み合わせから判定します。

型は OpenRTM ROS2Transport の組み込みシリアライザに対応させます。例として `RTC::TimedString` は `std_msgs/msg/String`、`RTC::TimedFloat` は `std_msgs/msg/Float32`、`RTC::TimedFloatSeq` は `std_msgs/msg/Float32MultiArray` です。対応表は [生成コード](../../scripts/ros2_transport.py) にあります。サービス・アクションと未登録の型変換はこの接続の対象外です。

## 承認済み設計から起動

RTC と ROS 2 を同じ ROS ドメインに配置し、RTC 起動環境から利用できる OpenRTM の ROS2Transport モジュールを指定します。以下は Python 版 OpenRTM を導入済みの Linux／WSL で、RTC-Agent-Tools ルートから実行する例です。

```bash
source /opt/ros/jazzy/setup.bash
python3 scripts/ros2_system.py plan final-session.json
python3 scripts/ros2_system.py transport final-session.json \
  --rtc-id echo --base-conf rtc.conf \
  --module /usr/lib/python3/dist-packages/OpenRTM_aist/ext/transport/ROS2Transport/ROS2Transport.py \
  --output rtc-ros2.conf
```

`--rtc-id` は図のコンポーネント ID です。生成された設定には、元の rtc.conf の設定に加えて、`manager.modules.load_path`、`manager.modules.preload`、対象 RTC ポートの `manager.components.preconnect` が入ります。接続先トピック名は ROS 2 端点の名前空間と接続による remap から決まります。

RTC は通常の起動コマンドの `-f` に `rtc-ros2.conf` を渡し、通常どおり活性化します。ROS 2 側は同じ設計を `python3 scripts/ros2_system.py run final-session.json` で起動します。RTC と ROS 2 間は Manager の preconnect で接続され、RTC 同士の接続は既存のライフサイクル手順を使用します。両プロセスの ROS ドメイン、探索範囲と QoS が一致するよう設定してください。

生成した設定を使う RTC Manager は、その RTC を生成するプロセスである必要があります。同じ Manager に複数 RTC をロードする構成では、各 RTC の preconnect を同じ設定にまとめます。

OpenRTM 2.1.0 の C++ 版では、`--module` に `ROS2Transport.so` を指定すると、同じディレクトリの `FastRTPSTransport.so` もプリロードされます。C++ のインターフェース名は `fast-rtps`、DDS ドメインは `fast-rtps.domain.id` です。Fast DDS の XML プロファイルを使う場合は、そちらのドメインも一致させます。Jazzy のライブラリに合わせた再ビルドと検証方法は [C++ 往復テスト](../../examples/ros2-transport/README.md#c-rtc-で検証) を参照してください。

ROS 2 グラフに名前付きノードとして公開するには、同じ手順でビルドした `ROS2TransportNamed.so` を指定します。生成ツールは隣にあるプラグインに応じて `fast-rtps` または `fast-dds` を選び、対応する `*.domain.id` を設定します。ROS2Transport はプラグインが通知する実際の端点 GUID とノード名を、同じ DDS 参加者から `ros_discovery_info` に配信します。通知形式は ROS 2 Jazzy のグラフ実装に合わせています。

生成ツールは RTC のインスタンス名を `ros2.node.name` に設定し、元の rtc.conf で指定済みの名前があれば使用します。`ros2.node.namespace` は元の rtc.conf で設定でき、既定値は `/` です。ノード単位は RTC Manager プロセスです。

FastRTPS・FastDDS の各 `DDSEndpoints` は C++ 標準ライブラリで端点の GUID、方向、シリアライザ名を記録し、作成・削除を通知します。名前付きモジュールが ROS 2 向けの端点を選び、ノード名・名前空間・端点 GUID を DDS API で配信します。プラグイン単体では端点の記録が有効で、ノード名の配信には名前付きモジュールのロードが必要です。

検証時は RTC の `*.domain.id` に合わせて ROS 2 側の `ROS_DOMAIN_ID` を設定します。`ros2 node list` と `ros2 node info` で名前と端点を、`ros2 topic echo` と受信ノードのログで RTC が加工して返した値を確認します。Jazzy の C++ `RtsdEcho` で FastRTPS と FastDDS 3.2.5 の両方を検証しました。実行コマンドは [往復テスト](../../examples/ros2-transport/README.md) にあります。

# 箱庭アセットと ROS 2 の連携

## 設計

RTSystemDesigner の v2 セッションでは、箱庭アセットと ROS 2 ブリッジ、ROS 2 ノードを個別に配置します。箱庭側の接続は **箱庭 PDU**、ROS 2 側の接続は **ROS 2 トピック** と表示します。箱庭側はロボット名、PDU 名、チャネル ID、容量、型とレイアウトを実行時定義と照合します。ROS 2 側はトピック名・完全修飾メッセージ型・方向・QoS を照合します。

`hakoniwa-pdu-ros` は PDU と ROS 2 メッセージの変換を担うブリッジです。PDU 定義、Endpoint 設定、バインディングを使用します。図で独立したモジュールとして配置し、ローカルテストの ROS 2 ブリッジは `moduleKind: ros2` とします。箱庭側に登録するアセットには箱庭カタログのプロファイルを使用します。 [公式ブリッジ](https://github.com/hakoniwalab/hakoniwa-pdu-ros)

## WSL2 での起動と検証

[Hakoniwa Business Pack の AGENTS.md](https://github.com/hakoniwalab/hakoniwa-business-pack/blob/main/AGENTS.md) を起点に対象 Recipe の Workspace・Foundation を準備します。確定セッションを取得してから起動します。`ros2_system.py` の RTC 向け設定生成とは別に、対象の PDU ブリッジを構成します。

- 検証済みの例は、Drone の mmap 上の `Drone/pos`（チャネル 1、72 バイト、`geometry_msgs/Twist`）を読み、ROS 2 Jazzy の `/pdu/Drone/pos` に `geometry_msgs/msg/Twist` として配信する一方向の構成です。この Twist の6成分は位置とオイラー角を表します。
- この例では、受信イベントの未処理中に Core が次の書き込みを拒否し、Drone がエラー 5 で停止しました。`drone_pose_bridge.py` は受信イベントを登録せず 20 ms ごとに最新値を読み、`hakoniwa-pdu-ros` の型変換と QoS 設定を使います。
- `verify-hakoniwa-ros2.sh` は専用 mmap で起動し、ROS 2 受信値の6成分を mmap から読み出した値と照合します。`--keep-running` を付けると検証後も起動を維持します。確認用シェルで Jazzy を source し、テストと同じドメイン（既定値 `91`）と `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST` を設定します。
- Three.js ビューア付き設計では、Drone の姿勢 PDU から姿勢表示データ生成、WebSocket ブリッジ、ブラウザへの経路を追加します。表示用アセットはシミュレーション開始前に登録します。ROS 2 受信に加え、ブラウザの WebSocket 接続、機体の描画、表示座標を確認します。

登録・再実行手順は [ローカル Designer 連携テスト](../local-designer.md) を参照してください。

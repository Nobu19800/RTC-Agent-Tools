# ROS2Transport 往復テスト

テスト用 v2 セッションには ROS 2 の talker、OpenRTM の `TimedString` エコー RTC、ROS 2 の listener が入っています。

```text
ROS 2 talker → /rtsd_bridge_in/chatter → RTC InPort
RTC OutPort → /rtsd_bridge_out/chatter → ROS 2 listener
```

Windows で [ローカル Designer](../../docs/local-designer.md) を起動します。WSL の Ubuntu に ROS 2 Jazzy、`demo_nodes_cpp`、Python 版 OpenRTM と ROS2Transport が必要です。RTC-Agent-Tools ルートから次を実行します。

```powershell
.\examples\ros2-transport\Invoke-DesignerTest.ps1
```

コマンドはテストセッションを登録して Designer の URL を表示します。保存された JSON を同じセッション API から取得し、RTC 側の設定を生成して WSL で起動します。ローカル探索に限定した ROS ドメインで、送信した文字列と RTC が返した文字列を照合します。正常時は `PASS` が表示され、起動したテストプロセスは停止します。Designer のセッションは引き続き開けます。

登録済みのテストセッションを再検証する場合は、URL の `session` 値を渡します。ノード位置は変更できます。配線とノード設定はテスト用の初期値を使用してください。

```powershell
.\examples\ros2-transport\Invoke-DesignerTest.ps1 -SessionId '<ID>'
```

Designer を再起動した場合は、引数なしで再登録します。

## C++ RTC で検証

WSL の RTC-Agent-Tools ルートで、C++ 版 OpenRTM 2.1.0 の開発パッケージと ROS 2 Jazzy の開発ライブラリを使用します。以下の `final-session.json` は、登録済みのテストセッションを `scripts/local_designer_session.py get` で取得したファイルです。

検証環境では配布版 `openrtm2-ros2-tp` が DDS 受信のデシリアライズ中に異常終了しました。以下では DDS 端点 API の変更を適用済みの OpenRTM-aist チェックアウトを、ローカルの Jazzy ライブラリでビルドします。`OPENRTM_SOURCE` にそのチェックアウトを指定してください。

```bash
source /opt/ros/jazzy/setup.bash
build_dir=$(mktemp -d)
cmake -S examples/ros2-transport/cpp-transport -B "$build_dir/transport" \
  -DOPENRTM_SOURCE="$OPENRTM_SOURCE" -DCMAKE_BUILD_TYPE=Release
cmake --build "$build_dir/transport" -j 2
g++ -std=c++17 $(pkg-config --cflags openrtm2) \
  examples/ros2-transport/echo_rtc.cpp -o "$build_dir/echo_rtc" \
  -lRTC2 -lomniDynamic4 -lomniORB4 -lomnithread -pthread
LD_LIBRARY_PATH="$build_dir/transport${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
  python3 -B examples/ros2-transport/verify_round_trip.py \
  --module "$build_dir/transport/ROS2Transport.so" \
  --rtc-executable "$build_dir/echo_rtc" < final-session.json
```

### ROS 2 に名前付きで公開

`--module "$build_dir/transport/ROS2TransportNamed.so"` を指定すると、C++ の実際の購読・配信端点を、選択したプラグインの DDS 参加者から `ros_discovery_info` に通知します。RTC の送受信とノード情報の通知は Fast DDS の API で行われます。通信型の変換には同じビルドの `ROS2Transport.so` のシリアライザを利用します。上記と同じ `LD_LIBRARY_PATH` で実行してください。`ROS2TransportNamed` ターゲットは依存ライブラリもビルドします。

テストは起動中に `ros2 node list --no-daemon --spin-time 5`、`ros2 node info /RtsdEcho0 --no-daemon --spin-time 5`、`ros2 topic echo /rtsd_bridge_out/chatter --once` を実行し、ノード名、購読・配信、返されたデータを検証してから停止します。

### FastDDS プラグインで検証

FastDDS プラグインへの変更も適用済みの OpenRTM-aist チェックアウトと、Fast DDS 3 の開発ライブラリを使います。`OPENRTM_SOURCE` と `FASTDDS3_PREFIX` はそれぞれそのチェックアウトとインストール先です。FastRTPS 版とはビルドディレクトリを分けます。

```bash
cmake -S examples/ros2-transport/cpp-transport -B "$build_dir/fastdds-transport" \
  -DOPENRTM_SOURCE="$OPENRTM_SOURCE" -DOPENRTM_DDS_BACKEND=FastDDS \
  -DCMAKE_PREFIX_PATH="$FASTDDS3_PREFIX" -DCMAKE_BUILD_TYPE=Release
cmake --build "$build_dir/fastdds-transport" --target ROS2TransportNamed -j 2
python3 -B examples/ros2-transport/verify_round_trip.py \
  --module "$build_dir/fastdds-transport/ROS2TransportNamed.so" \
  --rtc-executable "$build_dir/echo_rtc" < final-session.json
```

両プラグインは、OpenRTM-aist の各プラグインディレクトリにある `DDSEndpoints` API で端点の GUID、方向、シリアライザ名を通知します。名前や名前空間の設定、ROS 2 向けの端点選択と通知は ROS2Transport 側が行います。

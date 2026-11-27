# C++ ドローン操作 RTC の静的解析と単体テスト

[English](en/drone-adapter-cpp-checks.md)

Python 版と同様に、標準 TkJoyStick の `RTC::TimedFloatSeq` を受け、箱庭 Drone の legacy API に移動・離着陸を要求する C++ RTC の例です。箱庭側の PDU は C++ のシリアライザとデシリアライザを介して Foundation の C API で送受信します。この版の OpenRTM DataPort は `joystick` 入力です。Python 版が公開する箱庭向けの型付き DataPort は、C++ 版では公開していません。

> C++ 版ドローン操作アダプターをビルドし、Clang の静的解析と GoogleTest を実行して、カバレッジを表示して。

## 実行手順

エージェントが Ubuntu 24.04 または WSL2 の Bash で、RTC-Agent-Tools のルートから実行します。OpenRTM-aist 2.1、箱庭 Foundation、Clang 18、LLVM 18 の `llvm-profdata` と `llvm-cov`、Clang のプロファイルランタイム、CMake、GoogleTest を使います。Foundation のパスは実際の配置に合わせます。

```bash
src=examples/hakoniwa_transport/cpp
build=build/drone-cpp-checks
foundation="$HOME/hakoniwa-wsl-run/work-wsl/foundation/install"

cmake -S "$src" -B "$build" -DCMAKE_CXX_COMPILER=clang++-18 \
  -DHAKONIWA_ROOT="$foundation" -DDRONE_COVERAGE=ON
cmake --build "$build"

clang++-18 --analyze -std=c++17 -I/usr/include/openrtm-2.1 \
  -I/usr/include/coil-2.1 -I/usr/include/openrtm-2.1/rtm/idl \
  -I"$foundation/include/hakoniwa" -I"$foundation/include/hakoniwa/pdu" \
  "$src/DroneJoystickAdapter.cpp" -o "$build/analysis.plist"

LLVM_PROFILE_FILE="$build/adapter.profraw" "$build/drone_adapter_tests"
llvm-profdata-18 merge -sparse "$build/adapter.profraw" -o "$build/adapter.profdata"
llvm-cov-18 report "$build/drone_adapter_tests" \
  -instr-profile="$build/adapter.profdata" "$src/Control.hpp" "$src/Pdu.hpp"
```

管理者権限なしで LLVM パッケージを展開して使う場合は、CMake に `-DCLANG_PROFILE_RUNTIME=/path/to/libclang_rt.profile-x86_64.a` を指定し、展開先の LLVM コマンドを使います。RTC を実行する場合は Foundation の環境を有効にし、`libconductor` などを解決できるようにします。

## 2026-11-27 の実測結果

| 検査 | 結果 |
| --- | --- |
| C++ RTC のビルド | 成功 |
| Clang Static Analyzer | 診断 0 件 |
| GoogleTest | 5 件成功、失敗 0 件 |
| LLVM 行カバレッジ | 制御ロジックと PDU 変換の 46 行中 46 行（100%） |
| LLVM 分岐カバレッジ | 同じ対象の 40 分岐中 40 分岐（100%） |

単体テストでは入力と移動距離の上限、応答判定、PDU のパディングと不正メタデータの拒否を確認しました。カバレッジの対象は `Control.hpp` と `Pdu.hpp` です。RTC のライフサイクルや箱庭シミュレーターとの実通信は個別の動作確認が必要です。

## 箱庭との結合確認

WSL2 で `TkJoyStick0.pos` と `DroneJoystickAdapterCpp0.joystick` を接続し、両 RTC を活性化しました。標準 TkJoyStick の入力コールバックへ `[60, 0]` を渡すと、箱庭の `Drone/pos` の X 座標が約 0.000 m から 0.262 m に変化しました。Windows から Three.js の設定を HTTP で取得し、WebSocket v2 で `Drone` のバイナリフレームを受信しました。マウス操作とブラウザ上の描画はこの試験の対象外です。

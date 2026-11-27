# C++ ドローン操作 RTC の静的解析と単体テスト

[English](en/drone-adapter-cpp-checks.md)

Python 版と同様に、標準 TkJoyStick の `RTC::TimedFloatSeq` を受け、箱庭 Drone の legacy API に移動・離着陸を要求する C++ RTC の例です。箱庭側の PDU は C++ のシリアライザとデシリアライザを介して Foundation の C API で送受信します。この版の OpenRTM DataPort は `joystick` 入力です。Python 版が公開する箱庭向けの型付き DataPort は、C++ 版では公開していません。

> C++ 版ドローン操作アダプターをビルドし、Clang の静的解析と GoogleTest を実行して、カバレッジを表示して。

## 実行手順

エージェントが Ubuntu 24.04 または WSL2 の Bash で、RTC-Agent-Tools のルートから実行します。Foundation のパスは実際の配置に合わせます。

必要なソフトウェアは次のとおりです。

- OpenRTM-aist 2.1
- 箱庭 Foundation
- Clang 18 とプロファイルランタイム
- LLVM 18 の `llvm-profdata` と `llvm-cov`
- CMake
- GoogleTest

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

## Windows で単体テストを実行する

必要なソフトウェアとファイルは次のとおりです。

- Visual Studio 2022 の MSVC と Windows SDK
- CMake と CTest
- GoogleTest のソースツリー
- 箱庭 Foundation の PDU ヘッダー（`include/hakoniwa/pdu`）

エージェントが Windows の PowerShell で実行します。`$foundation` と `$gtest` は用意したファイルの場所に合わせます。今回は WSL2 にあったヘッダーと GoogleTest のソースを Windows 側にコピーし、MSVC でネイティブビルドしました。`DRONE_BUILD_RTC=OFF` では単体テストだけを構成できるため、OpenRTM と Foundation の実行ライブラリは不要です。

```powershell
$src = "examples/hakoniwa_transport/cpp"
$build = "work/drone-adapter-windows/build"
$foundation = (Resolve-Path "work/drone-adapter-windows/foundation").Path
$gtest = (Resolve-Path "work/drone-adapter-windows/googletest").Path

cmake -S $src -B $build -G "Visual Studio 17 2022" -A x64 `
  -DDRONE_BUILD_RTC=OFF "-DHAKONIWA_ROOT=$foundation" `
  "-DGTEST_SOURCE_DIR=$gtest" -Dgtest_force_shared_crt=ON
cmake --build $build --config Release --target drone_adapter_tests
ctest --test-dir $build -C Release --output-on-failure
& "$build/Release/drone_adapter_tests.exe"
```

Visual Studio 2022 の MSVC 19.44、x64 Release で **GoogleTest 5 件成功、失敗 0 件**でした。CTest ではテスト実行ファイル 1 件が成功と表示されます。この Windows 実行ではカバレッジを計測していません。

## 箱庭との結合確認

WSL2 で `TkJoyStick0.pos` と `DroneJoystickAdapterCpp0.joystick` を接続し、両 RTC を活性化しました。標準 TkJoyStick の入力コールバックへ `[60, 0]` を渡すと、箱庭の `Drone/pos` の X 座標が約 0.000 m から 0.262 m に変化しました。Windows から Three.js の設定を HTTP で取得し、WebSocket v2 で `Drone` のバイナリフレームを受信しました。マウス操作とブラウザ上の描画はこの試験の対象外です。

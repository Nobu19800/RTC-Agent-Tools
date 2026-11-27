# ドローン操作 RTC の静的解析と単体テスト

[English](en/drone-adapter-checks.md)

[C++ 版の静的解析と単体テスト](drone-adapter-cpp-checks.md)

[Lua RTC の静的解析と単体テスト](lua-rtc-checks.md)

[RTC–箱庭アセット連携手順](rtc-hakoniwa.md) で生成した `DroneJoystickAdapter.py` を対象とします。RTC-Agent-Tools のルートで、生成済みソースがあることを確認してから実行します。

> ドローン操作アダプターに Bandit と flake8 を実行し、pytest の単体テストとカバレッジを表示して。

エージェントが実行する PowerShell コマンドです。静的解析で指摘が出た場合も、単体テストは個別に実行します。

```powershell
python -m venv work/drone-adapter-checks/venv
$py = "work/drone-adapter-checks/venv/Scripts/python.exe"
& $py -m pip install bandit==1.9.4 flake8==7.5.0 pytest==9.2.0 pytest-cov==7.1.0
$src = "build/generated/DroneJoystickAdapter/DroneJoystickAdapter.py"
& $py -m bandit $src
& $py -m flake8 --statistics --count $src
$env:COVERAGE_FILE = "work/drone-adapter-checks/.coverage"
& $py -m pytest examples/hakoniwa_transport/test_drone_joystick_adapter.py --cov=DroneJoystickAdapter --cov-report=term-missing -q
```

## 2026-11-27 の実行結果

| 検査 | 結果 |
| --- | --- |
| Bandit | 指摘 0 件、終了コード 0 |
| flake8 | 指摘 31 件、終了コード 1。行長 22 件、空行 7 件、インデント 2 件 |
| pytest | 11 件成功、失敗 0 件 |
| 行カバレッジ | アダプター本体 158 行中 84 行を実行（53%） |

テストでは移動距離の上限、中央・古い・不正な入力の扱い、離着陸指令、応答の成功・拒否・タイムアウト、シリアライザのパディングと往復変換を確認します。OpenRTM と箱庭の依存はテスト用の代替に差し替えます。実際の RTC の登録、箱庭との通信、GUI 操作は別途、連携手順で確認します。flake8 の指摘は今回の測定結果として記録しています。

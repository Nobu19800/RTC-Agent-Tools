# RTC ライフサイクルの実行手順

## フェーズ13

確定 v2 設計の `components[].data.moduleKind` で対象を識別する。RTC だけをバッチの対象とし、ROS 2、箱庭、混在トランスポートの起動・接続にはそれぞれの手順を使う。承認版を `build/system/final-session.json` に保存し、以下を `build/system/scripts/` に用意する。

| バッチ | 実行内容 |
| --- | --- |
| `start_rtcs.bat` | 配備設定で専用プロセスを起動し、所有情報と名前サービスへの登録を確認する |
| `connect_ports.bat` | 実ポートの型・方向やサービスの極性を照合し、`rtcon` で接続する |
| `activate_rtcs.bat` | 前提の接続と状態を確認し、依存順に `rtact` を実行する |
| `deactivate_rtcs.bat` | 動作停止に適した順で `rtdeact` を実行する |
| `stop_rtcs.bat` | 必要なら非活性化し、`rtexit` と登録解除、専用プロセスの終了を確認する |

各バッチに実際の rtshell コマンドを記載し、別言語の実行制御スクリプトを介さない。独立実行とプラン表示を可能にする。名前付き参照は外部配備設定で解決し、未定義の値、パス、引用符、作業ディレクトリと対象プロセスを確認する。承認済み設計へ環境固有の解決済みパスを書き戻さない。

- WSL2 の既定エンドポイントと一度だけの名前サービス設定は [AGENTS.md](../../../AGENTS.md) に従う。Windows から登録 IOR と RTC の到達性を確認する。
- 起動と接続、活性化を別操作にする。等価な既存接続、既に到達した状態は明示的に扱い、不要な再作成を避ける。
- 有界の待機で登録・接続・状態を確認する。停止時は安全に独立処理できる対象を継続し、失敗一覧を集計する。PID、実行パス、開始時刻で所有を確認する。
- 共有名前サービスや無関係な RTC に影響を与えない。箱庭の共有メモリを再準備する場合は、専用領域と所有、稼働中の参加者がいないことを確認する。
- WSL2 や別ホストの引数、名前サービス、設定例、プランと復旧の詳細を確認する。ログを `build/system/logs/` に保管し、`README-runtime.txt` に順序・使用法と前提を記録する。[検証](verification.md)

## 元の手順にあるコマンド・形式の例

```text
build/system/scripts/
  start_rtcs.bat
  connect_ports.bat
  activate_rtcs.bat
  deactivate_rtcs.bat
  stop_rtcs.bat
```

[詳細な原文（英語）](../en/runtime.md)

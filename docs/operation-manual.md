# RTC-Agent-Tools 動作マニュアル

[English](en/operation-manual.md)

## 1. 設計を用意する

コマンドは `RTC-Agent-Tools` のルートを基準とする。エージェントに設計を依頼する場合は、機能と入出力、実行先、期待する検証結果を指定する。検索は次のように行う。

```powershell
python rtc_search.py catalog/rtc_catalog.json camera --json
python hakoniwa_search.py catalog/hakoniwa_catalog.json Drone --json
python scripts/ros2_system.py search "robot state publisher"
```

Designer で設計する場合は、モジュールを追加して `Module Kind` を選び、必要なポートと接続を設定する。RTC の実装要件は **Implementation → Requirements** に記入する。ROS 2 ではパッケージと実行ファイル、名前空間を確認し、箱庭では PDU チャンネルとブリッジの区間を確認する。ローカルファイルとして受け渡す場合は **JSON出力**、既存セッションを共有する場合は **保存** を使う。

## 2. レビューして確定する

提案 JSON を公開セッションサーバーへ登録し、確認用 URL を取得する。

```powershell
$api = 'https://rt-session-server.rtsystem-designer-web.workers.dev/api/sessions'
$session = Invoke-RestMethod -Method Post -Uri $api -ContentType 'application/json' -InFile .\proposal.json
$designerUrl = $session.designerUrl
if (-not $designerUrl) {
    $designerUrl = "https://nobu19800.github.io/RTSystemDesigner/?session=$($session.sessionId)"
}
$designerUrl
```

[公開版 RTSystemDesigner](https://nobu19800.github.io/RTSystemDesigner/) の設計リンクを開き、モジュール、ポート、接続、実装要件を確認する。変更した場合は保存し、確認後に「設計完了」と伝える。同じ PowerShell で承認済みの設計を取得する。

```powershell
curl.exe --fail-with-body --silent --show-error "$api/$($session.sessionId)" -o final-session.json
```

Designer から書き出した JSON を確定版にする場合は、そのファイルを指定する。[サービス設定](agents/services.md)

## 3. RTC を生成・実行する

新規 RTC の作成が必要な場合は、確定設計から対象 RTC の定義 JSON を取り出し、XML に変換してスケルトンを生成する。以下の `MyRTC` は生成対象名の例である。入力 JSON は [生成ガイド](agents/generation.md) の定義形式に従う。

```powershell
python json_to_rtc_xml.py build/generated/MyRTC/MyRTC.json build/generated/MyRTC/RTC.xml
.\cuirtcbuilder.bat -d build/generated/MyRTC -f build/generated/MyRTC/RTC.xml
```

生成後に実装・ビルドを行い、実行先の設定を用意する。生成済みの Windows 用ライフサイクルバッチを使う場合は、指定された起動環境で順に実行する。

```powershell
.\build\system\scripts\start_rtcs.bat
.\build\system\scripts\connect_ports.bat
.\build\system\scripts\activate_rtcs.bat
```

各段階で登録、実ポートの接続、活性化状態を確認する。入力を送って期待値を照合し、終了時は `deactivate_rtcs.bat`、`stop_rtcs.bat` の順に実行する。停止後は登録解除と専用プロセスの終了を確認する。共有名前サービスは運用対象の所有関係に従って扱う。[バッチの要件と終了判定](agents/runtime.md)

## 4. ROS 2 または箱庭を含むシステムを動かす

ROS 2 実行環境を読み込んだ Linux／WSL2 の端末で次を実行する。

```bash
python3 scripts/ros2_system.py plan final-session.json
python3 scripts/ros2_system.py run final-session.json
```

同じ ROS 環境を設定した別端末で、`ros2 node list`、`ros2 node info`、`ros2 topic info`、`ros2 topic echo` を使って確認する。対象ノード名とトピック名は確定設計および `plan` の結果から特定する。可視化環境があれば `rqt_graph` で接続を確認できる。`run` が起動したノード群は起動端末の Ctrl+C で停止する。

- **RTC–ROS 2** — [ROS2Transport の構成手順](agents/ros2-transport.md) に従って RTC ごとの `rtc.conf` と ROS 側の設定を揃える。[往復テスト例](../examples/ros2-transport/README.md)
- **箱庭–ROS 2** — [箱庭–ROS 2 の実行・検証手順](agents/hakoniwa-ros2.md) に従って PDU 値と ROS 2 に届いた値を比較する。ビューア付き設計では WebSocket の接続に加えて、ブラウザの機体と姿勢が更新されることを確認する。
- **ExcelControlpy／Calc** — Requirements に記載したセルに対応する動的ポートを作り、ConsoleIn の整数がセルに書き込まれ、ConsoleOut で同値を受信することを確認する。移動ありの場合は異なる値を2件以上送り、セルの順序も確認する。[スプレッドシート RTC の手順](agents/dynamic-rtc-ports.md)

## 症状から確認箇所を絞る

| 症状 | 確認箇所 |
| --- | --- |
| セッションが開かない | 公開サービスへの HTTPS 接続、セッション ID、登録時の応答 |
| RTC が登録されない | 起動ログ、名前サービスのアドレス、RTC が公開した IOR、操作端末からの到達性 |
| ポートが接続できない | 実ポート名、方向、型、ServicePort の極性、動的ポートの生成順序 |
| ROS 2 のノードやトピックが見えない | ROS のセットアップ、名前空間、DDS ドメイン、探索設定、Transport の初期化ログ |
| トピックが見えるが値が届かない | Pub/Sub の方向、型、QoS、RTC の状態、ブリッジの入出力 |
| ビューアに機体が表示されない | WebSocket、ビューア設定、モデル・コーデック、受信値と画面描画 |
| 終了後もプロセスが残る | 名前サービス上の登録、専用プロセスの PID と実行パス、共有マネージャーかどうか |

再現できるように、使用した設計、入力値、観測値、ログ、未確認事項を記録する。[検証とログ](agents/verification.md)

# RTC-Agent-Tools 動作マニュアル

[English](en/operation-manual.md)

## 1. 設計を用意する

引用文をエージェントに送ります。各コードブロックは、エージェントが `RTC-Agent-Tools` のルートを基準に実行する例です。エージェントに設計を依頼する場合は、機能と入出力、実行先、期待する検証結果を指定します。検索は次のように行います。

> カタログで必要なモジュールを探して。

エージェントが実行するコマンドの例です。

```powershell
python rtc_search.py catalog/rtc_catalog.json camera --json
python hakoniwa_search.py catalog/hakoniwa_catalog.json Drone --json
python scripts/ros2_system.py search "robot state publisher"
```

Designer で設計する場合は、モジュールを追加して `Module Kind` を選び、必要なポートと接続を設定します。RTC の実装要件は **Implementation → Requirements** に記入します。ROS 2 ではパッケージと実行ファイル、名前空間を確認し、箱庭では PDU チャンネルとブリッジの区間を確認します。ローカルファイルとして受け渡す場合は **JSON出力**、既存セッションを共有する場合は **保存** を使います。

## 2. レビューして確定する

提案 JSON を公開セッションサーバーへ登録し、確認用 URL を取得します。

> 設計案を登録して、確認用のリンクを見せて。

エージェントが実行するコマンドの例です。

```powershell
$api = 'https://rt-session-server.rtsystem-designer-web.workers.dev/api/sessions'
$session = Invoke-RestMethod -Method Post -Uri $api -ContentType 'application/json' -InFile .\proposal.json
$designerUrl = $session.designerUrl
if (-not $designerUrl) {
    $designerUrl = "https://nobu19800.github.io/RTSystemDesigner/?session=$($session.sessionId)"
}
$designerUrl
```

[公開版 RTSystemDesigner](https://nobu19800.github.io/RTSystemDesigner/) の設計リンクを開き、モジュール、ポート、接続、実装要件を確認します。変更した場合は保存し、確認後に次のメッセージを送ります。エージェントは承認済みの設計を取得します。

> 設計完了

エージェントが実行するコマンドの例です。

```powershell
curl.exe --fail-with-body --silent --show-error "$api/$($session.sessionId)" -o final-session.json
```

Designer から書き出した JSON を確定版にする場合は、そのファイルを指定します。[サービス設定](agents/services.md)

## 3. RTC を生成・実行する

新規 RTC の作成が必要な場合は、確定設計から対象 RTC の定義 JSON を取り出し、XML に変換してスケルトンを生成します。以下の `MyRTC` は生成対象名の例です。入力 JSON は [生成ガイド](agents/generation.md) の定義形式に従います。

> 確定した設計から RTC のスケルトンを生成して。

エージェントが実行するコマンドの例です。

```powershell
python json_to_rtc_xml.py build/generated/MyRTC/MyRTC.json build/generated/MyRTC/RTC.xml
.\cuirtcbuilder.bat -d build/generated/MyRTC -f build/generated/MyRTC/RTC.xml
```

生成後に実装・ビルドを行い、実行先の設定を用意します。生成済みの Windows 用ライフサイクルバッチを使う場合は、指定された起動環境で順に実行します。

> システムを起動して

エージェントが実行するコマンドの例です。

```powershell
.\build\system\scripts\start_rtcs.bat
.\build\system\scripts\connect_ports.bat
.\build\system\scripts\activate_rtcs.bat
```

各段階で登録、実ポートの接続、活性化状態を確認します。入力を送って期待値を照合し、終了時は `deactivate_rtcs.bat`、`stop_rtcs.bat` の順に実行します。停止後は登録解除と専用プロセスの終了を確認します。共有名前サービスは運用対象の所有関係に従って扱います。[バッチの要件と終了判定](agents/runtime.md)

> システムを終了して  エージェントが実行する終了コマンドの例です。  ~~~powershell .\build\system\scripts\deactivate_rtcs.bat .\build\system\scripts\stop_rtcs.bat ~~~  ## 4. ROS 2 または箱庭を含むシステムを動かす

エージェントは ROS 2 実行環境を読み込んだ Linux／WSL2 の端末で次を実行します。

> ROS 2 の構成を確認して起動して。

エージェントが実行するコマンドの例です。

```bash
python3 scripts/ros2_system.py plan final-session.json
python3 scripts/ros2_system.py run final-session.json
```

同じ ROS 環境を設定した別端末で、`ros2 node list`、`ros2 node info`、`ros2 topic info`、`ros2 topic echo` を使って確認します。対象ノード名とトピック名は確定設計および `plan` の結果から特定します。可視化環境があれば `rqt_graph` で接続を確認できます。`run` が起動したノード群は起動端末の Ctrl+C で停止します。

- **RTC–ROS 2** — [ROS2Transport の構成手順](agents/ros2-transport.md) に従って RTC ごとの `rtc.conf` と ROS 側の設定を揃えます。[往復テスト例](../examples/ros2-transport/README.md)
- **箱庭–ROS 2** — [箱庭–ROS 2 の実行・検証手順](agents/hakoniwa-ros2.md) に従って PDU 値と ROS 2 に届いた値を比較します。ビューア付き設計では WebSocket の接続に加えて、ブラウザの機体と姿勢が更新されることを確認します。
- **ExcelControlpy／Calc** — Requirements に記載したセルに対応する動的ポートを作り、ConsoleIn の整数がセルに書き込まれ、ConsoleOut で同値を受信することを確認します。移動ありの場合は異なる値を2件以上送り、セルの順序も確認します。[スプレッドシート RTC の手順](agents/dynamic-rtc-ports.md)

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

再現できるように、使用した設計、入力値、観測値、ログ、未確認事項を記録します。[検証とログ](agents/verification.md)

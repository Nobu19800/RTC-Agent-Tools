# RTSystemDesigner ローカル連携テスト

[English](en/local-designer.md)

`RTSystemDesigner` と `RTC-Agent-Tools` のローカル連携対応済みチェックアウトを同じフォルダーに置きます。Windows の PowerShell で Node.js 24、npm、Python 3 を使用します。

以下の引用文を Codex または Claude Code に送ります。エージェントは親フォルダーで依存関係を準備し、ローカルサーバーを起動したままにします。

> ローカル版 RTSystemDesigner を起動し、テストセッションを開いて。

エージェントが実行するコマンドの例です。

```powershell
npm.cmd --prefix .\RTSystemDesigner ci
npm.cmd --prefix .\RTSystemDesigner run dev:integration
```

同じ依頼で、エージェントは別のシェルで `RTC-Agent-Tools` に移動し、テスト用セッションを登録してブラウザで開きます。

エージェントが実行するコマンドの例です。

```powershell
Set-Location .\RTC-Agent-Tools
$session = python .\scripts\local_designer_session.py create .\examples\local-designer\session.json | ConvertFrom-Json
$session.designerUrl
Start-Process $session.designerUrl
```

ブラウザに `SmokeRTC0` が表示されたら、ノードを移動して「保存」をクリックします。確認ダイアログを閉じてページを再読み込みすると、移動後の位置が表示されます。保存結果の読み戻しもエージェントに依頼できます。

> 保存したローカルセッションを読み戻して。

エージェントが実行するコマンドの例です。

```powershell
python .\scripts\local_designer_session.py get $session.sessionId
```

提案の登録には `create <提案JSON>`、レビュー後の取得とファイル保存には `get <sessionId> --output <保存先>` を使います。登録から取得まで同じローカルサーバーを使用してください。セッションはメモリに保持され、Vite の再起動で消えます。停止前に必要な JSON を取得してください。

標準の待受先は `127.0.0.1:5173` です。テスト用 API は同じオリジンで動作し、公開サービスにセッションを送信しません。通常の `npm run dev` と `npm run build` では公開 API が選択されます。

## 箱庭 Drone から ROS 2 への姿勢配信テスト

`examples/local-designer/hakoniwa-ros2-pose-session.json` が設計のひな形です。設計確定後、`local_designer_session.py get` で取得したセッションを WSL2 側の検証に渡します。

> 箱庭 Drone の姿勢が ROS 2 に届くか確認して。

エージェントが実行するコマンドの例です。

```bash
bash examples/local-designer/verify-hakoniwa-ros2.sh "$APPROVED_SESSION" \
  "$FOUNDATION_ROOT" "$DRONE_ROOT" "$RECIPE_WORK_DIR" "$PDU_ROS_SOURCE"
```

引数は順に確定セッション、Business Pack の Foundation、Drone 実行ディレクトリ、`drone-position-pdu-live` のレシピ作業ディレクトリ、`hakoniwa-pdu-ros` のソースチェックアウトです。WSL2 に ROS 2 Jazzy が必要です。スクリプトは専用 mmap に読み取り用の接続を作り、ROS 2 の `/pdu/Drone/pos` の6成分を PDU の値と照合します。開始時に表示するディレクトリに起動・受信ログを記録します。

このテストでは `drone_pose_bridge.py` が最新の PDU を 20 ms ごとに読み出し、`hakoniwa-pdu-ros` の型変換と QoS 設定を使って配信します。イベント通知方式では未処理の受信イベントが次の書き込みを拒否し、Drone が `hako_asset_start() error: 5` で停止するためです。テスト用に初期位置をずらした設定を実行ディレクトリに生成し、飛行指令は送信しません。

### Three.js ビューア付き構成

`examples/local-designer/hakoniwa-ros2-viewer-session.json` を登録し、確定したセッションを同じスクリプトに渡します。WSL2 側で `HAKONIWA_VISUAL_PUBLISHER` を Business Pack の `tools/recipe/drone_gui_visual_state.py` に、`HAKONIWA_VIEWER_ROOT` を Three.js Drone のチェックアウトに設定します。

ビューア付きの検証は次のように依頼します。

> Three.js ビューア付きでテストを起動して。

エージェントは上記コマンドに第6引数 `--keep-running` を付けます。[Three.js ビューア](http://127.0.0.1:8000/index.html?viewerConfigPath=/config/viewer-config-fleets.json&wsUri=ws://127.0.0.1:8765&wireVersion=v2) の接続状態、機体の描画、表示座標を確認し、確認後は次のように依頼します。エージェントは起動したテストを Ctrl+C 相当の割り込みで停止します。

> テストを終了して。

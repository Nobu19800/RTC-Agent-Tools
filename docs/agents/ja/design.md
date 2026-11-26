# システム設計の作業手順

[AGENTS.md](../../../AGENTS.md) の共通ゲートを適用する。以下の番号順で進める。フェーズ4は [セッション形式](session-format.md) に従う。

## フェーズ1〜3　要求を把握し、既存モジュールを選ぶ

1. 必要な機能、入出力、実機かシミュレータか、通信・制御の条件、実行環境、確認する結果を整理する。安全上重要な入力解除、停止、タイムアウト、状態通知を曖昧にしない。根拠がある仮定は明示する。
2. 一般 RTC カタログを正規 URL から取得し、付属サンプル、箱庭、ROS 2 の各カタログも検索する。箱庭は XML 由来カタログを `python scripts/build_hakoniwa_catalog.py --check` で照合し、出典を確認できない場合は未検証と記録する。絞り込みで見つからなければ `--all` も確認する。
3. 要求を満たす既存実装を選び、不足する機能を新規実装とする。出所不明の項目は未確認とし、既存リポジトリやポートの意味を推測で確定しない。同じ設計の中に RTC、箱庭、ROS 2 を配置する。
4. 既存項目にはカタログ ID、リポジトリ・プロファイル URL、選定版、箱庭の XML ハッシュと PDU 設定などの根拠を保持する。新規項目には責務、型付きポート、設定、期待する振る舞いを定義する。混在接続では [接続契約](hakoniwa-serializer.md) と該当する ROS 2 手順を適用する。

既存 RTC が機能要件を満たし、DataPort の型だけが異なる場合は、両方の RTC を再利用し、独自シリアライザとデシリアライザで変換する案を優先する。元の型と実装を保持し、送受信ポート、フィールドの意味・単位、値域、異常値の処理、ワイヤ形式、共通の `dataport.marshaling_type`、プラグインのロード方法を記録する。選定した OpenRTM-aist の実装で異なる型の接続を確立できることを確認し、設計完了後に実データの変換結果を検証する。意味や接続可否を確定できない場合は未解決事項として扱う。

- 送信側は元の OutPort 型、受信側は元の InPort 型に対して、それぞれ同じ変換名で登録する。各 RTC の DataPort が生成される前に、対応するプラグインを `rtc.conf` の `manager.modules.preload` でロードする。CDR を使う場合はワイヤ上の IDL 型とバイト順を明記し、時刻の保持・変換方法も定義する。
- 実ポートの方向、IDL リポジトリ ID、両端の `dataport.marshaling_types` を照合する。`rtcon` が異なる型を事前チェックで拒否する場合は、その承認済み接続に限り、照合後に接続プロパティを指定して `PortService.connect` を呼び出す。既存接続の設定も照合し、同じ接続の重複作成を避ける。
- 異なる言語や OpenRTM-aist の版を組み合わせる場合は、実際の組み合わせで受信値を確認する。制御データでは正常値・境界値・異常値に加え、入力解除による停止と、通信断時に受信側が最後の指令を保持するかを個別に確認する。ゼロ指令を受けた後の速度出力と、実際の動作が停止するまでの挙動も区別する。

<a id="phase-7-show-the-design-link-and-stop-implementation"></a>
## フェーズ5〜7　検証、登録、提示

5. v2 JSON の一意 ID、インスタンス名、種別、ポート方向・型、エッジの両端と根拠を照合する。未実装のトランスポートや未解決設定を実行可能として扱わない。
6. [サービス手順](services.md) に従って提案を登録し、セッション ID を記録する。ローカル連携を指定された場合は同じローカルサーバーで登録と取得を行う。
7. 返された Designer URL を提示し、[AGENTS.md](../../../AGENTS.md) が定める全コンポーネントの一覧を併記する。修正指示を反映した場合も同様に提示する。ユーザーが設計完了を明示するまで、構築や実装へ進まない。

## 元の手順にあるコマンド・形式の例

```text
Required capabilities
- acquire camera/depth data
- detect target object
- determine manipulation action
- control robot arm
```

```bash
python rtc_search.py catalog/rtc_catalog.json camera --json
python rtc_search.py catalog/rtc_catalog.json "point cloud" --json
python rtc_search.py catalog/rtc_catalog.json "object detection" --json
python rtc_search.py catalog/rtc_catalog.json arm --json
python rtc_search.py catalog/rtc_catalog.json controller --json
python hakoniwa_search.py catalog/hakoniwa_catalog.json controller --json
python hakoniwa_search.py catalog/hakoniwa_catalog.json Drone --json
python hakoniwa_search.py catalog/hakoniwa_catalog.json --all --json
```

```text
existing
```

```text
generated
```

```json
{
  "summary": "",
  "requirements": "",
  "constraints": "",
  "notes": ""
}
```

```text
https://rt-session-server.rtsystem-designer-web.workers.dev/api/sessions
```

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  --data-binary "@work/session-proposal.json" \
  "https://rt-session-server.rtsystem-designer-web.workers.dev/api/sessions"
```

```text
work/current_session_id.txt
```

```text
<designerUrl returned by the server>
```

```text
https://nobu19800.github.io/RTSystemDesigner/?session=<SESSION_ID>
```

```text
設計完了しました
```

```text
カメラ画像から物体を検出し、色によってロボットアームの動作を変更するシステムを作りたい
```

```text
設計完了しました
```

[詳細な原文（英語）](../en/design.md)

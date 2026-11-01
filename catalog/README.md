# カタログ

| ファイル | 対象 | 検索 |
| --- | --- | --- |
| `rtc_catalog.json` | OpenRTMのRT-Component | `rtc_search.py` |
| `hakoniwa_catalog.json` | 箱庭アセットのXML由来プロファイル | `hakoniwa_search.py` |

## 箱庭アセット

このリポジトリの `profiles/iso22166-202/drone-three-point/*.xml` から次の4件を収録しています。

| id | 内容 | ポート数 |
| --- | --- | --- |
| `drone-service` | legacy PDU APIのDroneシミュレータ | 7 |
| `position-command` | 3点巡回の登録型Pythonコントローラ | 2 |
| `visual-state-publisher` | Pythonの姿勢→可視化PDUアダプタ | 2 |
| `web-bridge` | Core連携WebSocket bridge | 2 |

リポジトリルートで実行します。

```powershell
python hakoniwa_search.py catalog/hakoniwa_catalog.json --all
python hakoniwa_search.py catalog/hakoniwa_catalog.json HakoDroneCmdMove --json
python hakoniwa_search.py catalog/hakoniwa_catalog.json 32768 --json
python scripts/build_hakoniwa_catalog.py
python scripts/build_hakoniwa_catalog.py --check
```

生成元は既定でRTC-Agent-Toolsのルートです。別の配置では `--source-root <XMLを含むリポジトリルート>` を指定します。生成とcheckはXMLの読取のみで、プロセスを起動しません。checkはXMLから再構築したJSONとの完全一致を検証します。`sourceRootReference` は `${RTC_AGENT_TOOLS_ROOT}`、XML内の根拠・Catalog参照パスの解決先 `knowledgeRootReference` は `${BUSINESS_PACK_ROOT}` です。

### フォーマットと使い方

- ルートの `catalogKind` は `hakoniwa-assets`、エントリは `assets` 配列です。各エントリの `moduleKind` は `hakoniwa` です。RTCカタログの `rtcs` 配列へは混在させません。
- `catalogId` はこのカタログ内の安定キー、`moduleId` はXML由来のローカルUUID URNです。`catalogReferences[].componentId` はBusiness Packの提供元コンポーネントIDであり、いずれも別の識別子です。位置指令・Python可視化アダプタをDrone Coreそのものと扱いません。
- `ioVariables` に元の方向を保持し、`ports` はDesignerのDataPort記述に合わせて `portType:data`、`direction:in/out` とします。`inout` は `-in` と `-out` に分け、`sourceVariableId`、`sourceDirection`、同じrobot/channelで対応を保持します。PDUの書き込み競合制御が実装されたという意味ではありません。
- PDUの型名、robot、`channelId`、`capacityBytes`、フィールドの単位・意味を保持します。WebSocket出力にはXMLにないrobot/channel/容量を付けません。channel番号はrobot内で解釈し、グローバルIDとみなしません。
- XMLの `services` は能力の説明です。CORBA ServicePortへ変換しません。`status.states` は静的な状態説明で、現在の実行状態ではありません。
- `properties` はXMLの文字列値を保持します。実行メタデータは `executable` に引数配列・環境変数・依存・配置ルート記号参照を保存します。`${FOUNDATION_ROOT}` 等は未解決のため、そのまま実行できる設定とみなしません。dependenciesも元の構成インスタンス名のままです。
- `source` に元XMLのリポジトリ相対パスとSHA-256を保存します。`evidence` の出典と検証範囲は元XMLから転記し、今回新たなruntime検証を実施したとは扱いません。XML内の根拠ファイルパス・Catalog参照パスはBusiness Packルート相対です。
- `profile.conformanceStatus:not-assessed` を維持します。元XMLはプロジェクト独自の対応づけドラフトで、ISO Annex B準拠・認証済みとは扱いません。

`ports` は接続候補の情報であり、カタログ全体はそのままインポートするDesignerセッションではありません。構成作成時はインスタンスと配置を決め、session-formatガイドに従って `components[].data.moduleKind:hakoniwa` として使用します。実行前にPDUレイアウト・方向・チャネル・共有領域・writer所有者と、混在接続ならシリアライザを検証します。今回のカタログ作成では接続・起動・実機動作は行っていません。

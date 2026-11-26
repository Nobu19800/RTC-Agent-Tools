# カタログ

| ファイル | 対象 | 検索 |
| --- | --- | --- |
| `rtc_catalog.json` | OpenRTMのRT-Component | `rtc_search.py` |
| `openrtm_samples_catalog.json` | OpenRTM の付属サンプル RTC | `rtc_search.py` |
| `hakoniwa_catalog.json` | 箱庭アセットのXML由来プロファイル | `hakoniwa_search.py` |
| `ros2_catalog.json` | ROS 2 ノードの XML 由来プロファイル | `python scripts/ros2_system.py search "<keyword>"` |

## RTC

一般カタログの収集では、既存の `rtc_catalog.json` を引き継ぐ。今回取得して解析できた項目は同名・同言語の情報を更新し、新規項目は追加する。検索結果から外れた項目や、取得・解析に失敗した項目は既存情報を保持する。`--limit` は今回収集する件数に適用する。

GitHub 全体のコード検索から集めた結果を既存カタログに反映して保存する。その更新済みカタログに登場する全所有者について、公開リポジトリの既定ブランチの Git ツリーを走査し、`RTC.xml` を追加収集する。同じファイルは一度だけ処理する。全体検索がレート制限で中断された場合も、既存カタログの所有者から追加収集を試みる。所有者一覧は最初の保存後に確定する。

GitHub がレート制限を返した場合は、1リクエストにつき最大2回、合計60秒まで再試行を待つ。所有者の走査やプロファイル取得がレート制限で中断された場合は、取得済みの項目までを既存カタログに反映する。

`scripts/build_rtc_catalog.py` は、コンポーネント名と実装言語が同じ別のソースを比較する場合に、既定ブランチで `RTC.xml` の親フォルダ以下を最後に変更したコミットの日時を使う。XML がリポジトリのルートにある場合は、既定ブランチ全体を対象にする。日時が同じか、どちらかの履歴を確認できない場合は、既存または先に採用した候補を保持する。同名でも、たとえば C++ 版と Python 版は別々に収録する。言語名の前後の空白と大文字・小文字の違いは重複判定で区別しない。

### OpenRTM-aist 付属サンプル

上流のサンプルを対象とした追加プロファイルと入力一覧は [OpenRTM サンプルプロファイル](../profiles/openrtm-samples/README.md) にある。サンプルカタログを再生成・検索するには次を実行する。

```powershell
python scripts/build_rtc_catalog.py --openrtm-samples-only
python rtc_search.py catalog/openrtm_samples_catalog.json "ConsoleIn Python" --json
```

定期更新は `rtc_catalog.json` のみを生成する。Designer は両方のファイルを取得し、同名・同言語の候補にはサンプル側のエントリを表示する。

## ROS 2 ノード

`profiles/iso22166-202/ros2/*.xml` から100件を生成します。各エントリは `moduleKind: ros2` で、`catalogId` は `ros2:<package>/<executable>` です。英語の入出力概要は `interfaceSummary`、構造化できたトピックは `topics`、サービスとアクションは `servicesAndActions` に格納します。`source` には生成元 XML の相対パスと SHA-256、レポートの項目番号、上流の確認先と照合結果を記録します。上流の確認対象に実行ファイルの登録がない項目では `launch` は `null` です。

RTC-Agent-Tools のルートで実行します。

```powershell
# 既存の XML からカタログを再生成
python scripts/build_ros2_catalog.py
# カタログと XML の一致を検証
python scripts/build_ros2_catalog.py --check
# 元レポートから XML を作り直してカタログを更新
python scripts/build_ros2_catalog.py --report "$env:USERPROFILE/Downloads/deep-research-report.md"
```

収録範囲と適合性については [ROS 2 プロファイルの説明](../profiles/iso22166-202/ros2/README.md) を参照してください。

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

[カタログと XML プロファイル](../docs/catalog-profiles.md) · [English guide](../docs/en/catalog-profiles.md)

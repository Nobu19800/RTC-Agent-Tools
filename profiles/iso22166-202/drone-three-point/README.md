# ISO 22166-202情報モデルへの対応づけXML（4アセット）

**これはISO 22166-202:2025の情報モデル項目に対応づけたローカルXMLドラフトです。
ISO Annex B形式への正式適合を確認したファイルではありません。**

ISO公式公開ページで項目とAnnex Bの存在を確認しましたが、完全なAnnex B XMLスキーマは
公開閲覧範囲に含まれず、リポジトリにも公式XSDはありませんでした。
したがって公式XMLの要素名・型・多重度・Module ID割当規則への適合を保証できません。
正式準拠版を作るには、適法に利用できるAnnex BのXSDまたは指定された公式テンプレートとの照合が必要です。

## ファイル

| XML | 対象 |
| --- | --- |
| drone-service.xml | legacy PDU APIのDroneシミュレータ |
| position-command.xml | 3点巡回の登録型Pythonコントローラ |
| visual-state-publisher.xml | 実際に使用したPython姿勢→可視化PDUアダプタ |
| web-bridge.xml | Core連携WebSocket bridge |

Launcher、HTTPサーバー、離陸準備用external client、Three.jsブラウザは対象に含めていません。
`composition.json`はアセット間の接続をまとめた補助ファイルです。

## 記述範囲

公開されているISOの情報モデル項目に沿って、一般情報、識別、プロパティ、入出力、状態、
サービス、実行基盤、安全・セキュリティ、モデル、実行形式を整理しました。
実際のPDU名・型・方向・channel・容量、3点座標、8秒の指令間隔、起動引数、
Python/WSL2条件、Conductor所有者、制約、根拠ファイルのSHA-256を含みます。

対象は直前に検証した3点巡回の構成で、製品の全機能・全PDUを列挙したものではありません。
状態欄は状態機械やログの意味の記述であり、停止中などの現在状態を更新するAPIではありません。
`Service`は能力やライフサイクルの説明であり、新たにRPCメソッドを実装したという意味ではありません。
メーカーの正式な法人名や認証が不明な箇所は、その旨を記載しています。

- 名前空間：`urn:hakoniwa:iso22166-202:mapping:0.1`（プロジェクト独自）
- Module ID：ローカル生成UUID URN。ISOによる割当済みIDとは扱わない。
- `hakoniwa-mapping.xsd`：ローカル構造検証用。ISO公式XSDではない。
- `Evidence`および一部の要素・属性：プロジェクト独自の記述。

## 検証

XML構文、必須グループ、4件のローカルIDの一意性、接続manifest、
ローカルXSDによる構造・入出力方向・channel/容量の型を確認。
ISO公式XSD適合、標準の全要求への適合、外部SIMツールへのインポートは未検証です。
XSDの一部の補助セクションは拡張を許す構造になっており、意味的な完全性までは保証しません。

XMLはRTC-Agent-Toolsが保持します。再生成：隣接するBusiness Packルートで`python tools/iso22166/generate_drone_profiles.py`（出力先はこのフォルダ）。根拠資料とXML内のCatalog参照パスはBusiness Packルート相対です。カタログはRTC-Agent-Toolsルートで `python scripts/build_hakoniwa_catalog.py` により更新します。
XMLは同じ識別子で再生成されます。生成元は検証時のLauncher snapshotと現在のローカル実装です。
生成はシミュレータを起動せず、XMLを読んでもプロセスは起動しません。

## 出典

- ISO公式：ISO 22166-202:2025の概要と公開範囲
  https://www.iso.org/obp/ui?_escaped_fragment_=iso:std:iso:22166:-202:ed-1:v1:en
- 実装：`tools/recipe/assets/position_command/publish.py`、`tools/recipe/drone_gui_visual_state.py`
- 構成：`docs/validation/drone-three-point-pdu-2026-10-30/launcher.json`
- 実行証跡：`docs/validation/drone-three-point-pdu-2026-10-30.md`

## 配置先に依存しないパス表現

XMLにはユーザー名・ドライブ・マシン固有の絶対ディレクトリを記録しません。
実行形式のパスは次の参照で表し、各XMLの`PathReference`にも意味を記載します。

| 参照 | 実行環境が割り当てる場所 |
| --- | --- |
| `${BUSINESS_PACK_ROOT}` | Business Packのチェックアウトルート |
| `${FOUNDATION_ROOT}` | 選択したFoundationのルート |
| `${DRONE_ROOT}` | 互換性のあるDrone配布物のルート |
| `${RECIPE_ROOT}` | 生成済みRecipe runtimeのルート |

これらは配置先を示す記号参照で、具体値をXMLやcomposition.jsonへ保存しません。
XML自体に自動展開機能はなく、実行ツール側が明示的に解決する必要があります。
一般の設定ファイル名・ソースファイル名はルートからの相対表現を維持しています。
生成ツールは元snapshotから配置ルートを識別して変換し、未変換の絶対パスがあれば失敗します。
過去の検証ログは原証跡として残し、その中のパスをこのXMLへ埋め込むことはありません。

## XMLからCatalogへの参照

各XMLの`CatalogReferences/CatalogReference`に、コンポーネントID、
リポジトリ相対パス、関連種別、適用範囲を記載しています。
Catalog側にはXMLへの参照を追加しません。関連付けはXMLからCatalogへの片方向です。
この関連づけはISO公式仕様ではなく、このローカルXMLプロファイルの拡張です。

| XML | Catalog component ID | 関連種別 |
| --- | --- | --- |
| [drone-service.xml](drone-service.xml) | [hakoniwa-drone-core](../../../../hakoniwa-business-pack/catalog/components/hakoniwa-drone-core.yaml) | `implementation-profile`：実行構成のプロファイル |
| [position-command.xml](position-command.xml) | hakoniwa-drone-core | `controls`：当該シミュレータを制御する別実装 |
| [visual-state-publisher.xml](visual-state-publisher.xml) | hakoniwa-drone-core | `recipe-local-adapter-for`：姿勢出力に接続するRecipe内アダプタ |
| [web-bridge.xml](web-bridge.xml) | [hakoniwa-pdu-bridge-core](../../../../hakoniwa-business-pack/catalog/components/hakoniwa-pdu-bridge-core.yaml) | `implementation-profile`：実行構成のプロファイル |

XMLのModule IDとCatalogのcomponent IDは別の識別子です。
Catalogは提供元コンポーネント、XMLは今回の構成・実装のプロファイルなので、
常に1対1で対応するとは限りません。

特にPython可視化アダプタを、Drone Coreが配布するnative VisualStatePublisherと
同じ実装として扱ってはいません。位置指令アセットもDrone Coreそのものではありません。
それぞれ専用Catalogがあるかのような新規component IDは作成していません。

`composition.json`にも同じ関連を機械可読で保存しています。
生成ツールは参照先Catalogファイルの存在とcomponent IDの一致を検査し、参照が切れていれば失敗します。Catalog側の逆参照は要求しません。

# RTC-Agent-Tools 詳細な動作仕様書

## 責務と設計の確定

RTC-Agent-Tools は、カタログ検索、設計データの受け渡し、プロファイル変換、構成に応じた実行準備を支援する。エージェントが作る成果物と、既存スクリプトが直接処理する成果物を区別する。

| 段階 | 入力 | 出力と完了条件 |
| --- | --- | --- |
| 設計案作成 | ユーザー要件、モジュール情報 | v2 セッション案、接続と未確定事項、レビュー用 URL |
| Designer 先行設計 | ユーザーが編集した JSON または保存済みセッション | 受領した設計の読み取りとレビュー、未確定事項 |
| 設計確定 | ユーザーの明示確認 | 最新の保存済みセッションまたは確認済みエクスポートを実装入力として固定 |
| 実装・ビルド | 確定設計、取得元とリビジョン、環境設定 | 必要な既存ソース、新規 RTC の定義・スケルトン・実装、ビルド結果 |
| 実行・検証 | 指定された実行範囲と対象環境 | 接続・状態・実データ・停止の確認結果、ログ、未検証事項 |

設計確定の前後で使う情報を区別する。確定後は、確定セッション、設計中の来歴、カタログ、対象ソースの順で参照する。設計変更が入った場合は変更箇所と下流の成果物を対応づける。[設計手順](agents/design.md) · [確定設計の扱い](agents/workspace.md)

## データモデルとカタログ

セッション v2 のルートは `version: 2`、`id`、`name`、`description`、`components`、`edges` を持つ。モジュール種別は `components[].data.moduleKind` の `rtc`、`hakoniwa`、`ros2` で判定する。図上のノード型は共通して `rtc` である。エッジの両端はノード ID とポート ID を参照し、ポート名、方向、データ型、通信種別の整合を確認する。

- `rtc_catalog.json` は RTC の基本情報、ポートとプロファイルへの参照を収録する。対応版の Designer では、RTC 選択時に参照先の `RTC.xml` を取得して Activity、ポート、構成、文書の詳細を取り込む。取得エラーが表示された場合は、基本情報のみで追加するか選択できる。Activity の未指定値は `onInitialize` が ON、その他が OFF で、明示値が優先される。
- `openrtm_samples_catalog.json` は付属サンプルのプロファイル参照とインストール済みの起動設定を保持する。Designer は同名・同言語の候補にサンプル側の定義を使う。
- `hakoniwa_catalog.json` は箱庭 XML プロファイルに由来する。アセットのカタログ ID、参照コンポーネント ID、PDU チャンネル ID、プロファイルの出所とハッシュを保持する。
- `ros2_catalog.json` は ROS 2 ノード、トピック、サービス、アクションの定義を収録する。ノード配置にはカタログ ID を、起動にはパッケージ名、実行ファイル名、名前空間、インスタンス名を使う。

`deployment`、`rtcConf`、`configuration`、`implementation` に実行や実装に必要な情報を保持する。ポータブルな設計には相対パスまたは名前付き参照を記録し、実環境のパスは展開先の設定で解決する。ExcelControlpy／Calc の生成予定ポートは設計時から `data.ports` に置き、シート、開始セルまたは範囲、更新時の移動条件は `data.implementation.requirements` に記録する。[セッション形式](agents/session-format.md) · [カタログ形式](../catalog/README.md) · [動的ポート](agents/dynamic-rtc-ports.md)

## 公開セッション API

設計画面は [公開版 RTSystemDesigner](https://nobu19800.github.io/RTSystemDesigner/) が提供し、セッションの登録・取得・保存は公開セッションサーバーが扱う。[サービス設定](agents/services.md)

| 操作 | リクエスト | 結果 |
| --- | --- | --- |
| 登録 | `POST /api/sessions` に v2 の構成 JSON を送る | セッション ID を取得する |
| 取得 | `GET /api/sessions/{sessionId}` | 保存済みの構成 JSON を取得する |
| 保存 | Designer から `PUT /api/sessions/{sessionId}` | サーバー上の設計を更新する |

登録応答に `designerUrl` がある場合はその URL を使う。URL が省略された場合は、公開版の URL に `?session=<SESSION_ID>` を付ける。レビュー完了後に保存された設計を取得し、実装着手時点の JSON をファイルとして記録する。

## 接続と実行計画

| 接続 | 実行時の対応 |
| --- | --- |
| RTC 同士 | DataPort の型・方向、または ServicePort の型・Consumer／Provider を照合し、名前サービス上の実ポートを接続する |
| ROS 2 同士 | 完全修飾型を照合し、トピックやサービスの remap を計画する。アクションは両端の完全修飾名を揃える |
| RTC と ROS 2 | ROS2Transport を使い、RTC 側のシリアライザーと ROS メッセージ、トピック、方向、DDS ドメイン、QoS を揃える |
| RTC と箱庭 | `hakoniwa` カスタムインターフェースと型別シリアライザーを使い、PDU のロボット、チャンネル、容量、配置を揃える |
| 箱庭と ROS 2 | PDU–ROS 2 ブリッジを独立したモジュールとして配置し、箱庭 PDU 区間と ROS 2 トピック区間を分けて記述する |

ROS 2 の `plan` は起動引数を構成し、`run` はパッケージと実行ファイルを確認してローカルの `ros2 run` で起動する。外部ランチャー、Lifecycle 遷移、コンポーネントコンテナ、ブリッジは各構成の手順で扱う。RTC の各操作は起動・接続・活性化・非活性化・停止の5つに分かれ、確定設計から実環境用バッチを作る。[RTC の実行仕様](agents/runtime.md) · [ROS 2](agents/ros2.md) · [箱庭](agents/hakoniwa-ros2.md)

## 成果物と適用範囲

新規 RTC では、定義 JSON、`RTC.xml`、Builder のスケルトン、実装、ビルド結果の順に確認する。既存 RTC には確定設計が選定したソースを使用する。装置固有のプラグイン、パラメーター、接続設定は配備対象ごとに解決する。`prepare_final_session.py` と `generate_runtime_batches.py` は旧形式かつ特定例向けであり、v2 混在システムの汎用変換・実行処理には適用できない。

検証では、名前サービス上の登録、接続情報、状態、実データ、画面表示、停止を個別に扱う。表示が要件に含まれる場合は、実際の画面を確認する。結果には確定設計の識別子、起動条件、確認した値、ログを対応づける。[生成](agents/generation.md) · [実装](agents/implementation.md) · [検証](agents/verification.md)

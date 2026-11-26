# カタログと XML プロファイル

[English](en/catalog-profiles.md)

カタログ JSON はモジュールを検索・選択するための一覧である。XML プロファイルは個々のモジュールの型、ポート、設定などを記述する。RTSystemDesigner のセッション JSON は、選んだモジュールのインスタンス、配置、接続を記録する。 [セッション形式](agents/ja/session-format.md)

## カタログの内容

| カタログ | 収録対象と主な項目 | 作成元 |
| --- | --- | --- |
| [一般 RTC](../catalog/rtc_catalog.json) | `rtcs` にコンポーネント名、カテゴリ、ベンダー、版、言語、DataPort、ServicePort、リポジトリと `RTC.xml` の参照先を収録する | GitHub の公開リポジトリにある `RTC.xml` |
| [OpenRTM 付属サンプル](../catalog/openrtm_samples_catalog.json) | `rtcs` に各言語の付属サンプルを収録する。利用できる場合はインストール済みサンプルの起動設定を `launch` に持つ | 上流のプロファイルと [補完した RTC.xml](../profiles/openrtm-samples/README.md) |
| [箱庭アセット](../catalog/hakoniwa_catalog.json) | `assets` にアセットの名称、識別子、プロパティ、ポート、起動情報、出典を収録する。PDU ポートにはロボット、チャンネル ID、容量を記録する | `profiles/iso22166-202/drone-three-point/` の XML |
| [ROS 2 ノード](../catalog/ros2_catalog.json) | `nodes` にパッケージ名、実行ファイル名、カテゴリ、トピック、サービス、アクション、配布版の注記、起動情報を収録する | `profiles/iso22166-202/ros2/` の XML |

一般 RTC カタログではコンポーネント名と実装言語で候補を区別する。定期収集で見つからなかった既存項目は保持し、同名・同言語の別候補は既定ブランチで `RTC.xml` の親フォルダ以下を最後に変更したコミットの日時で比較する。サンプルカタログは定期収集から独立しており、Designer の候補では同名・同言語の場合にサンプル側が優先される。箱庭と ROS 2 のカタログには生成元 XML の相対パスと SHA-256 が入る。 [生成・検索手順](../catalog/README.md)

## ISO 22166-202 に対応づけた XML

`profiles/iso22166-202/` の XML は、箱庭アセットと ROS 2 ノードの情報を ISO 22166-202 の公開情報モデルに対応づけた、このリポジトリ独自の記述である。名前空間と識別子はプロジェクトで定義している。公式 Annex B XSD への適合は未検証で、適合性は `not-assessed` として扱う。 [ROS 2 プロファイルの出典と範囲](../profiles/iso22166-202/ros2/README.md)

| XML の項目 | 記述内容 |
| --- | --- |
| `GenInfo`、`IDnType`、`ModuleProp` | 概要、モジュール識別子と種別、プロパティ |
| `IOVariables`、`Services` | 入出力と操作。箱庭では PDU の型・方向・チャンネルなど、ROS 2 ではトピックやサービス・アクションなど |
| `Infra`、`ExecutableForm` | 前提環境と起動形式。ROS 2 の起動登録が確認できない場合は、カタログの `launch` が `null` になる |
| `Evidence` | 参照資料や上流の確認先など、記載内容の根拠 |

同じメッセージ型名でも、箱庭 PDU のバイナリ配置やフィールドの意味が ROS 2 メッセージと一致するとは限らない。接続時は型に加え、ロボット名、チャンネル、バイナリ配置、フィールドの意味を確認する。 [型変換と通信プラグイン](rtc-transport-plugins.md)

## RTC.xml

`RTC.xml` は OpenRTM-aist の RTC プロファイルで、ルート要素は `RtcProfile` である。一般 RTC カタログはこのファイルから検索に必要な情報を抽出する。既存 RTC を選んだときは参照先のプロファイルで詳細を確認する。新規 RTC では確定設計から RTC の定義 JSON を作り、`json_to_rtc_xml.py` で `RTC.xml` に変換して Builder のスケルトン生成に渡す。 [RTC 生成手順](agents/ja/generation.md)

| XML の項目 | 記述内容 |
| --- | --- |
| `BasicInfo` と `Language` | コンポーネント名、カテゴリ、ベンダー、版、実装言語など |
| `Actions` | コールバックの生成設定やドキュメント |
| `DataPorts` | ポート名、InPort／OutPort の方向、IDL 型 |
| `ServicePorts` | ポートに含まれるインターフェースと Provider／Consumer の役割 |
| `ConfigurationSet` | 設定パラメーターの型や既定値 |

たとえば、カタログで既存の `ConsoleIn` を選び、`RTC.xml` で OutPort の型を確認し、セッションで `ConsoleIn0` の接続先を決める。実際に起動するには、版ごとの実行ファイル、依存関係、実行設定も確認する。 [Designer の設定項目](designer-module-settings.md)

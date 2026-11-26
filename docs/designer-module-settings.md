# RTSystemDesigner のモジュール設定項目

[English](en/designer-module-settings.md)

キャンバス上でモジュールをクリックすると設定欄が開く。表示される項目は **Module Kind** によって異なる。配備設定は、エージェントが実行環境を準備・起動する際に参照する。

## 共通設定

| タブ | 設定内容 |
| --- | --- |
| General | Module Name は実装名、Instance Name は配置した個体の一意な名前、Module Kind は RTC／Hakoniwa Asset／ROS 2 Node の区分。State は表示用。 |
| Deployment | Host は配備先、Executable は実行ファイル、Working Directory は作業ディレクトリ、Arguments は起動引数、Environment は環境変数。ROS 2 の実行ファイルは General の executable に指定する。 |
| Configuration | Parameter Name と Default Value（RTC）または Parameter Value（その他）を指定する。ROS 2 のパラメーターファイルは General で指定する。 |
| Ports | 名前、方向、型と接続先を揃える。型の候補から選ぶか、必要な完全修飾型を入力する。 |
| Implementation | Summary は役割、Requirements は動作・変換・セル割当などの要件、Constraints は制約、Notes は補足や未確定事項を記録する。 |

## RTC

| タブ・欄 | 設定内容 |
| --- | --- |
| General → Basic Profile | Module Overview、Version、Vendor、Category、Maximum Instances、Execution Rate (Hz)、Overview、RTC Type、Component Type、Activity Type、Execution Context、Generation Language、Choreonoid を設定する。 |
| General → rtc.conf | CORBA Name Servers は実行時の名前サービス、manager.shutdown_auto はマネージャーの自動終了設定。 |
| Activity | 各 Callback の Generate を選び、概要・事前条件・事後条件を記録する。未指定時は onInitialize が ON、他は OFF。明示設定が優先される。 |
| FSM | Use FSM、StaticFSM／DynamicFSM、イベント用のポート・変数を指定し、SCXML を作成・読込・編集する。イベント一覧には遷移情報が表示される。 |
| Documentation | 概要、入出力、アルゴリズム、参考資料、連絡先、ライセンスを記録する。 |
| Container | 対象 OS、作業場所、言語、構成、機能モジュール、ライブラリ、リポジトリの URL とブランチなどを指定する。 |
| RTC.xml | RTC プロファイル XML を確認・編集する。接続中のポートを削除・改名する場合は、先に接続を外す。 |

**Ports** では InPort、OutPort、ServicePort を追加する。DataPort では RTC の型と、意味や単位などの補足を設定する。ServicePort ではインターフェース名、IDL 型、Consumer／Provider を指定する。候補には OpenRTM-aist の IDL 定義を含む。**Configuration** では型、変数名、単位、制約、Widget を指定できる。Step は slider または spin で使う。

## ROS 2 Node

**General → ROS 2** の `package`、`executable`、`namespace`、`parametersFile` を設定する。起動引数と環境変数は **Deployment** に記録する。**Ports** でトピックの方向とメッセージ型、または Service／Action の名前、型、利用側・提供側を指定する。名前空間を含めた完全修飾名を確認する。RTC との接続では、型の対応、トピック名、トランスポート設定も記録する。[RTC–ROS 2 連携](rtc-ros2.md)

## Hakoniwa Asset

選定したアセットのプロファイルに従い、PDU ポート名、方向、型、**Channel ID** を確認する。**Implementation → Requirements** にロボット名、PDU 名、容量、配置、転送条件を記録する。RTC との接続ではシリアライザと型の対応も指定する。[RTC–箱庭アセット連携](rtc-hakoniwa.md)

[空のセッションから設計する](empty-session.md)

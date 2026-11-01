# 箱庭用DataPortインターフェースとシリアライザ

このガイドは [AGENTS.md](../../AGENTS.md) の必須手順の一部です。箱庭用の転送プラグイン、型変換、シリアライザを作成・変更するときに読みます。
この作業自体は既存の設計手順を拡張するツール保守です。新しいRTCシステムの実装・起動を伴う場合は、通常の設計承認と実行範囲の規則も適用します。

## 責任の分離

```text
RTCの型付きDataPort
  -> 型別シリアライザ（RTC/IDL型 <-> 箱庭PDUバイト列）
  -> 共通インターフェース（PDUバイト列のread/write）
  -> hakopy / 箱庭共有メモリ
```

- `interface_type=hakoniwa` はメッセージの内容を解釈しません。robot、channel、PDU全長とバイト列だけを扱うため、RTCデータ型・箱庭メッセージ型ごとに作り直す必要はありません。
- `marshaling_type` はRTC型と箱庭メッセージ型、さらにバイナリ形式を識別します。型変換は原則として型ごとに登録します。構造が似ているだけで全型に適用できるとは判断しません。
- ROSの型名を使用しても、箱庭PDUはROS 1のwire formatやROS 2 CDRと同じとは限りません。ROS用シリアライザをそのまま流用しません。
- 共通化の範囲はDataPort転送です。CORBA ServicePortのサービスIDLまで共通化するものではありません。

## RTCと箱庭アセットを結ぶときの必須設計契約

RTC→箱庭、箱庭→RTCのDataPort接続は、**OpenRTM-aistの独自インターフェースと型別シリアライザを使用します**。RTCは型付きDataPortを維持し、RTC側の `dataport.interface_type:hakoniwa` と `dataport.marshaling_type` を明示します。箱庭アセット自身がCORBA DataPortを公開しているとは仮定しません。通常のCORBA接続だけでnative PDUに到達する構成や、JSON文字列DataPortへの置換は作りません。

構成設計では両方のカタログを検索し、混在edgeごとに次を記録します。

| 項目 | 必須内容 |
| --- | --- |
| 端点 | edge ID、source/targetのインスタンスID・port ID、`moduleKind`、送受信方向 |
| 型変換 | RTC/IDL型、箱庭PDUメッセージ型、フィールド対応、単位・座標系・時刻・欠損値の意味 |
| 転送 | `dataport.interface_type:hakoniwa`、`dataport.marshaling_type`、push/pullの要件、RTC側consumer/providerの役割と初期化・バインド方法 |
| PDU | robot、channelId、割当容量、実ペイロード長、メタデータ・offset・padding・endiannessの契約 |
| 所有・配置 | native PDUを利用するプロセス/ホスト、同一共有領域、互換Foundation、asset登録またはexternal-I/O初期化、Conductor所有者、PDU領域生成後に通信する順序 |
| 競合・準備状態 | writer/reader所有者、request/response同一channelの場合の書き込み分担、reset/停止時の扱い、実装・検証済み範囲と未解決事項 |

契約の保持先と最終設計への追従は [session-format.md](session-format.md) に従います。Designerが独自プロパティを保持・解釈する保証はないため、未確認のedge拡張だけに実行条件を預けません。`rtc.conf` のモジュールロードとconnector設定の生成・バインドは、設計承認後に最終構成を入力として実装します。箱庭端点がCORBAオブジェクトを持たない場合のconnector準備手順も確認し、存在しないCORBA peerや `rtcon` 引数を捏造しません。

既存の共通転送を再利用し、必要なRTC型/PDU型のシリアライザがなければ追加実装として設計します。未実装の組を接続済みと扱わず、`planned` / `unresolved` と根拠を記載し、その接続の実行を保留します。設計提案の段階では不足を明記してレビュー可能にし、実装は通常の設計承認後に行います。

共通サンプルは `RTC.TimedVelocity3D` と速度を意味するTwistのraw48/metadata72に対応します。承認済みドローン操作システムでは、別の共有IDLと `build/generated/common/DroneSerializers.py` を追加しました。`HakoDroneCmdMove`、`HakoDroneCmdTakeoff`、`HakoDroneCmdLand` はFoundation変換器の出力を割当容量104/88/88バイトへpaddingします。位置・姿勢を意味する `Drone.pos` は専用の `hakoniwa:geometry_msgs/Twist:pose-metadata72` を使用し、速度シリアライザを流用しません。`DroneVisualStateArray` はnativeのpublisher/bridge間で扱い、RTC用シリアライザは実装していません。カタログに型があることとシリアライザが実装済みであることを区別します。

Python試作の役割はRTC→PDU書き込みのInPortConsumer、PDU→RTC受信のInPortProviderです。pushだけをサポートしているため、pullや厳密なstep同期の要求を既存試作で満たすとは判断しません。Windows側RTCからWSL2内のPDUへ接続する場合も、共有メモリを直接共有できると仮定せず、nativeプラグインを配置できる環境や追加の通信経路を設計・検証します。

## 作成手順

### ロードと接続設定をRTCソースから分離する

独自インターフェースとシリアライザは `rtc.conf` の設定でロードします。RTCソースにプラグインのimport・factory登録・robot/channel/codec指定・単一ポートconnectを埋め込みません。ファイル名に対応した `ModuleNameInit(manager)` を用意し、RTC生成前に登録します。

```ini
manager.modules.load_path: /mnt/c/workspace/codex-test3/RTC-Agent-Tools/build/generated/common
manager.modules.preload: HakoniwaTransport.py, DroneSerializers.py
```

設定例の絶対パスはこのWSL配置用です。別環境では実際の配布先を指定します。一般的なロード手順は[ユーザー指定のPython独自インターフェース開発ガイド](https://h8892-inaba.github.io/my-jekyll-site/ja/doc/developersguide/advanced_rt_system_programming/implement_dataport_interface_type/python/)も参照します。

接続プロパティは接続時に渡します。`rtcon` のヘルプだけで相手ポート省略の可否を判断せず、インストール済みの実装と実接続で確認します。この配置のrtctree `DataPort.connect` は空のdestinationリストを `WrongPortTypeError` で拒否します。OpenRTM Managerの `manager.components.preconnect` は相手省略の処理を持ちますが、起動時にnative PDU領域が利用可能である必要があります。

このシステムでは起動と接続を分けるため、`build/system/teleop/native-connections.ini` と `scripts/single_port_connections.py` を使用します。`connect_ports` で7本のnative接続を生成・照合し、`activate_rtcs` はそれらの存在とプロパティを確認してからactivateします。単一ポート接続のこの例外に限り、外部スクリプトが公開 `PortService.connect` APIを使います。通常のRTC間接続とライフサイクルは引き続きrtshellを使います。

転送プラグインは `dataport.hakoniwa.init_for_external: YES` が指定された場合だけ、接続時にそのプロセス内で `hakopy.init_for_external()` を一度実行します。ロードだけでは共有メモリの初期化もシミュレーションの起動も行いません。Conductor・PDU領域の準備は接続前に外部の起動手順で確認します。通常assetの初期化方式と混同しません。

native接続はdeactivateで切断しません。再activateで重複接続せず、設定変更はdeactivate後に旧INIでdisconnectし、新INIでconnect・照合してからactivateします。自動設定変更や別writerとの同時操作は行いません。

1. 接続先の箱庭revision、メッセージ定義、生成されたoffset/ctype、PDU全長、メタデータの有無を確認します。サンプルのサイズだけを根拠に形式を決めません。
2. RTC型から各フィールドへの対応、単位、座標系、時刻、配列長、欠損値を定義します。標準RTC型で足りなければ共有IDLを作成します。
3. `OpenRTM_aist.ByteDataStreamBase` を継承し、`serialize(data) -> (status, bytes)` と `deserialize(bytes, data) -> (status, typed_data)` を実装します。サイズ・形式を検証してから出力を変更します。
4. `SerializerFactories.instance().addSerializer(name, class, RTC型)` で登録します。ポートの対応形式の検出に間に合うよう、コンポーネント生成・ポート初期化より前に登録します。`addSerializerGlobal` は全型を共通処理できる根拠がある場合だけ使用します。
5. 転送は既存の共通プラグインを再利用します。新規の場合はInPortConsumerの `put` が書き込み、InPortProviderが受信バイト列を `connector.write` へ渡すpush方式を実装します。ファクトリ、初期化関数、切断時の停止を含めます。
6. `rtc.conf` でロードし、接続プロファイルで `dataport.interface_type` と `dataport.marshaling_type` を明示します。データ型が同じでも形式・PDUサイズ・channelの不一致は別途検出する必要があります。
7. 単体変換、上流バイト互換、実OpenRTMコネクタ、箱庭実通信を別々に検証します。実通信未検証の実装は試作として扱います。

プラグイン自体はミドルウェア統合のため、通常RTCの「OpenRTM統合は生成スケルトン内」という規則の対象とは区別します。通常RTCのアルゴリズムやポート操作をプラグインへ移動してはいけません。

## Python試作

実装は [examples/hakoniwa_transport](../../examples/hakoniwa_transport/README.md) にあります。

| ファイル | 責任 |
| --- | --- |
| `HakoniwaTransport.py` | 型非依存のPDU転送、push consumer/provider、停止処理 |
| `HakoniwaSerializer.py` | `RTC.TimedVelocity3D` とTwistの型変換、形式別登録 |
| `test_hakoniwa.py` | 実OpenRTM APIとメモリ内PDUバックエンドによる検証 |

対応フィールドは `vx,vy,vz -> linear.x,y,z`、`vr,vp,va -> angular.x,y,z` です。線速度はm/s、角速度はrad/sを前提とし、座標変換は行いません。接続先の座標系を必ず確認します。
Twistには時刻がありません。送信では `tm` が失われ、受信では `tm=(0,0)` を「取得時刻不明」として明示的に設定します。現在時刻をセンサ取得時刻として捏造しません。時刻保持が必要なら時刻付きメッセージと対応シリアライザを別途設計します。

### 48バイト本体と72バイト形式を混同しない

調査revisionでは、Cサンプルの `Hako_Twist` はfloat64が6個の48バイトです。一方、Pythonの `hako_binary.binary_writer` は24バイトのメタデータ領域を付けて72バイトを生成します。`examples/pdu_communication/custom.json` の `pdu_size:48` だけでPython形式との互換性を判断できません。

| marshaling_type | PDU全長 | 対象 |
| --- | --- | --- |
| `hakoniwa:geometry_msgs/Twist:raw48` | 48 | メタデータなしのC構造体形式 |
| `hakoniwa:geometry_msgs/Twist:metadata72` | 72 | 調査revisionのPython変換器形式 |

両方little endian限定です。metadata72はmagic `0x12345678`、version 1、base offset 24、heap offset 72、total size 72を検証します。可変長配列や一般のメタデータ形式を実装したものではありません。接続先が別の形式なら専用codecを追加し、長さだけ合わせて流用しません。

## 実行責任と制限

- 試作はpushのみです。pull/duplexは未実装です。
- 通常assetとして利用する場合、アプリケーションが同一プロセス内の `hakopy.asset_register`、`hakopy.start`、reset、終了とシミュレーション時刻同期を所有します。external-I/Oで利用する場合は `init_for_external` と外部の箱庭start/PDU領域生成が必要です。プラグインのロードでは登録・起動しません。`put/read` が呼ばれる前に箱庭のAPIとPDU実領域が利用可能になっている必要があります。
- `hakopy` の共有メモリは同一ホストの箱庭環境が前提です。CORBAでポート同士を接続しても箱庭PDUをリモートホストへ配送する機能は増えません。
- 1 channelにつきwriterは1つです。受信は壁時計間隔で最新値をサンプリングします。新規性判定、全サンプル配送、厳密なstep同期、exactly-onceは保証しません。同値の連続受信も正常です。接続時点で存在する値も受信し得ます。
- providerはconnector設定後にスレッドを開始します。read失敗・buffer拒否はログを残して受信を停止し、復旧後の再接続が必要です。write失敗は `PORT_ERROR` に変換します。ブロッキングbufferと同期read/writeは拒否します。
- disconnectで停止要求とjoinを行います。native readが2秒で戻らない場合は停止失敗を報告します。ネイティブ呼び出しを強制中断する機能はありません。
- 接続時のPDU型・offset・writer重複の自動検証、ConnectorDataListener通知の完全な実装、箱庭resetとの連携は未実装です。実運用前に補います。

設定は `rtc.conf` とconnector propertiesを使用し、データペイロードをJSONにしません。箱庭上流が要求する `custom.json` はその外部API契約として残ります。このJSON依存を「runtime JSON撤廃済み」と報告してはいけません。生成RTCの独自設定にJSONを広げず、上流のファイルを無根拠にYAMLへ置き換えません。

## 実装例と検証記録

型非依存の転送、型別codec、初期化前のfactory登録、単一RTCポートのnativeバインドを共通手順として扱います。metadata付きchannelの未書き込み全ゼロ領域を除外する場合は、明示的な `dataport.hakoniwa.skip_zero_packet: YES` を使います。raw形式では全ゼロも有効なので、既定値falseを維持します。

GUIドローン例はrequest/result/ackの順序を管理し、結果のクリアを観測して次の指令を送ります。最新値の転送自体には指令の新規性・完了・取消の保証がありません。これらはRTCの状態機械が所有し、入力停止と実行中移動の完了を区別します。

[2026-10-30の参照revision・失敗履歴・native/GUI検証](../validation/hakoniwa-transport-2026-10-30.md)は履歴として保持します。後日のブラウザ描画結果はrun内の `viewer-render-*.json` と画像を参照し、当初のHTTP/WebSocketのみの確認と区別します。

現在の検証には [verification.md](verification.md) を適用します。`scripts/run_teleop_unit_tests.py --output <run-directory>` は実行結果を記録し、`scripts/finalize_gui_drone.py` は同じ実装fingerprintのunit/GUI証跡だけを集約します。古い証跡から成功や全edge検証済みを捏造せず、設計・契約の実行可否も自動変更しません。

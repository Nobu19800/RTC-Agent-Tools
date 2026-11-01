# RTC外での箱庭接続設定（2026-10-30 JST）

ユーザー指定により、プラグインのロードと接続先・転送形式の選択をRTCのソースから分離した。既存の埋め込み処理の除去は明示的に許可された。IDL、ポート名、制御アルゴリズム、シリアライザのバイト形式は変更していない。

## 設定と操作

- `build/system/teleop/teleop-controller-1.conf`: `manager.modules.load_path` と `manager.modules.preload` で `HakoniwaTransport.py`、`DroneSerializers.py` をRTC生成前にロードする。
- `build/system/teleop/native-connections.ini`: 7本のポート名、向き、robot、channel、サイズ、codec、push/flush、バッファ、poll間隔を指定する。
- `scripts/single_port_connections.py`: INIを読み、公開PortService APIで単一ポートを接続する。全ポートの向き・広告形式・既存接続を先に照合し、同一設定を再利用する。設定の衝突は変更せず失敗し、途中失敗では新規作成分のみを戻す。RTCのactivate/deactivate/exitを行わない。
- `connect_ports.sh/.bat`: 通常RTC間はrtcon、native端点だけは上記ツールを呼ぶ。`activate_rtcs` は7本の接続プロパティを照合してからactivateする。
- `scripts/teleop_connection_settings.py`、`scripts/configure_gui_drone.py`、`scripts/generate_teleop_batches.py`: 再生成しても同じ方式を保持する。

`dataport.hakoniwa.init_for_external: YES` により、転送プラグインが接続時に一度だけそのプロセスのexternal-I/Oを初期化する。ロードでは初期化・Conductor起動・PDU領域作成をしない。通信前に同じ専用共有領域でシミュレータ・PDUの準備が必要である。RTCが使用するsimulation clockの参照はアプリケーション動作として残る。

native接続はdeactivateで維持され、再activate時に作り直さない。設定変更時はdeactivateし、旧INIでdisconnect、新INIでconnect・check、その後activateする。終了時はOpenRTMがポートを解放する。

## rtconの相手省略の確認

使用環境のrtshellはFoundation Python配下、OpenRTM-aistは `/usr/lib/python3/dist-packages/OpenRTM_aist`。`rtcon.py` は1引数でも `connect_ports` に到達するが、rtctree `DataPort.connect` が空のdestination配列を `WrongPortTypeError` で拒否する。

実RTCの `move_request` を相手指定なしで試した結果も、終了コード1、`rtctree.exceptions.WrongPortTypeError: Wrong port type.` だった。ログとロード後のポート広告は [external-preload-20261030T114128-21298](../../build/system/logs/external-preload-20261030T114128-21298/rtcon-single-port.txt) と同ディレクトリの `preloaded-ports.txt` に保存した。RTCはINACTIVEのままで検証した。

OpenRTM `Manager.initPreConnection` にはpeer省略で `CORBA_RTCUtil.connect(..., RTC.PortService._nil)` を呼ぶ分岐がある。この作業では、起動と接続のフェーズを独立させるため外部ツールを選択し、rtc.conf preconnect自体のnative実通信は検証していない。

一般的なpreloadの根拠は[ユーザー指定のPython独自インターフェースガイド](https://h8892-inaba.github.io/my-jekyll-site/ja/doc/developersguide/advanced_rt_system_programming/implement_dataport_interface_type/python/)のTestIF例と、インストール済みOpenRTM Managerの実装で確認した。

## 実行結果と制限

最初の実通信試行はWindowsから編集した2本の `.sh` がCRLFとなり、Bashの `set` / sourceで失敗した。対象をLFに修正し、失敗ログは `external-connections-20261030T114346-21687` に保持した。その前のpreflightでは広告プロパティ名を単数と誤認して拒否したため、OpenRTMの `dataport.marshaling_types` に修正し、正常終了を再確認した。

修正後の [external-connections-20261030T114443-22557](../../build/system/logs/external-connections-20261030T114443-22557/verification.log) は終了コード0。23件の単体検証（skipなし）、7本のnative接続生成・同一設定再利用、Tk widgetイベントによる離陸・X/Y/Z/yaw・入力release後の新規指令抑止・着陸を確認した。7本のmixed edgeは各要求・応答ackログとpose測定により対応づけた。さらにdeactivate後の接続維持、再activate後の照合、明示disconnect/reconnect、RTC終了と専用シミュレーションの停止まで確認した。

この検証はWSL2内のnative PDU通信とWSLgのGUIイベント操作を対象とする。ブラウザ描画、Windowsネイティブ共有メモリ、実機は今回の対象外で、以前のブラウザ証跡を現在の検証として扱わない。

ログには上流ドローン設定の `configVersion` / `validatedWith` / GPS accuracy未指定の警告、nativeログ長256バイトの切り詰め警告が残る。WebSocketブリッジのmonitorにも `runtime init failed: mux open error=8` が残る。同じmonitorエラーは変更前の `teleop-20261030T061612-8629` と `teleop-20261030T071718-13719` にも存在する。今回のコントローラPDU操作は成功したが、monitorの原因・復旧は未解決であり、システム全体をエラーなしとは報告しない。

最終ファイルの証跡と現在性は `build/system/implementation-verification.json` と `build/system/verification-index.json` を参照する。以前の検証・ソース・構成は `build/system/history/before-external-connections-*` に保持した。

最終停止監査では、検証用シェルが `rtexit` の非同期登録解除を待たずに専用Managerを終了させたため、controllerの到達不能な名前登録が1件残った。各プロセスの停止を確認し、当該登録だけを `rtdel -z` で除去して再監査した。検証用シェルにも `wait_absence` を追加した。通常の停止バッチは既に登録解除待ちを持ち、共有NameServiceと他RTCの登録は保持した。

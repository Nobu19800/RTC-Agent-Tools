# 箱庭転送・シリアライザの検証履歴（2026-10-30）

このファイルは当時の検証範囲を保存する履歴です。後日の設定・コードに対する検証結果ではありません。



調査用ソースは `build/reference/` に分離しました。上流ソースの改変やインストールスクリプトの実行はしていません。

- [箱庭サンプル](https://github.com/toppers/hakoniwa-core-cpp-client/tree/aff152810ced4dd509e3b9329c2f007440aa6603/examples)、同revisionの `bindings/python/hako_asset_python.cpp`、`hako_binary/{binary_io,binary_writer,binary_reader}.py` とoffset定義を確認。
- [独自インターフェースPython例](https://github.com/Nobu19800/openrtm_testinterface/tree/bec19b44f2a13c0d69a02add129b2dff569492b5/Python)：ファクトリ登録、consumer/providerとシリアライザの分離を参考にしました。ファイルポーリングのbusy loopは採用していません。
- [独自ROS 2シリアライザ例](https://github.com/Nobu19800/testOpenRTMSerializer/blob/eedc5818b00cc1e8b60ca94e42deccc3d34080a1/TestRos2Serializer/TestRos2Serializer.cpp)：TimedVelocity3Dのフィールド対応と型別登録を確認。ROS 2 wire format自体は流用していません。
- [OpenRTM-aist-Python API](https://github.com/OpenRTM/OpenRTM-aist-Python/tree/b58852f1ef7e515030c4673723406b7d2c749a0c/OpenRTM_aist)：ByteDataStreamBase、SerializerFactories、pushコネクタの契約を確認し、インストール済みPython 3.12の実OpenRTM APIでテスト。

`python -m unittest discover -s examples/hakoniwa_transport -v` で7件成功（skipなし）。raw48のC構造体レイアウト、metadata72の上流Python writerとの完全一致とreaderによる復号、型別factory、異なるPDUサイズの共通転送、実OpenRTM pushコネクタ経由の往復、接続プロパティの購読、異常長・不正設定の拒否、転送失敗、受信停止・joinを確認しました。Python構文チェックも成功しました。未登録型の拒否テストではOpenRTM factoryの `createObject return None` が標準出力に現れますが、期待した未登録結果をassertしています。
上流互換テストは参照checkoutがない場合skipになります。skipを含む成功を互換検証済みと報告しません。

初回のWindows検証では `hakopy` が見つからず、WSLアクセスもサンドボックスで拒否されました。その時点ではnative実通信は未検証でした。以下は、ユーザー指定によりWSLアクセスを許可して追加検証した結果です。

## WSL2 native検証（2026-10-30 11:18 JST）

Ubuntuの `/usr/bin/python3` 3.12.3と `/usr/lib/python3/dist-packages/OpenRTM_aist` を使用しました。単体テスト7件がskipなしで成功しました。
未配置だった `hakopy` は上記client revisionとcore submodule `e2ada4d0d6ae99d4a6cf7617e6fa21f1d1023b04` から専用ビルドしました。システムへのインストールと上流ソースの変更は行っていません。

再実行用 [verify_native.py](../../examples/hakoniwa_transport/verify_native.py) は次を行います。

1. 一意のログディレクトリと専用mmap領域を作り、`HAKO_CONFIG_PATH` で選択します。既存の箱庭共有領域に接続しません。
2. native conductorとexternal-I/Oを初期化し、48/72バイトの2チャネルを登録します。
3. 同じビルドの `hako-cmd start` で空のシミュレーションをrunningへ遷移させ、PDU領域の生成を確認します。
4. 実 `OutPort` と `InPort` を接続し、両形式で `OutPort.write -> hakopy.pdu_write -> mmap -> hakopy.pdu_read -> InPort.read` の6フィールド一致と時刻不明の扱いを確認します。
5. 別Pythonプロセスから同じPDUを書き換え、InPortがその値を取得することを確認します。writerは順番に使用し、同時書き込みはしません。
6. 接続プロファイルの消滅、providerスレッドの終了、箱庭 `status=stopped`、conductor停止、テスト用CORBA servant解放とOpenRTM終了を確認します。

最終結果は終了コード0です。ログは [native.log](../../build/system/logs/hakoniwa-wsl-20261030T021810.690208Z/native.log)、[unit.log](../../build/system/logs/hakoniwa-wsl-20261030T021810.690208Z/unit.log)、同ディレクトリの `peer-0.log`、`peer-1.log`、`environment.txt`、`run.txt` に保存しました。native/peerの終了後ログに未解決の例外・ORBエラーはありません。ビルド構成時には上流のCMake CMP0135警告とpyenv不在によるsystem Pythonフォールバック警告がありました。ビルドログにコンパイラwarning/errorはありません。

この検証は **同一プロセス内の実DataPort接続と、別プロセス間のnative PDU共有** です。別プロセスに配置したRTC間のCORBA接続、登録assetのstep同期・reset、実機動作は未検証です。空のシミュレーションをstart/stopするため、初回試案の「masterをstoppedのまま検証する」手順は使用しません。

### 発見した上流不整合と失敗履歴

- `conductor_start` はC++実装のbool成功をC APIがintの1として返す一方、Python wrapperは0を成功と扱います。同様に `pdu_create` も成功時にPythonへFalseを返します。上流の `src/conductor/src/hako_conductor.cpp`、`src/assets/src/hako_asset.cpp`、`src/assets/src/hako_asset_impl.cpp`、`bindings/python/hako_asset_python.cpp` で確認しました。検証スクリプトは戻り値をログに残し、実初期化・PDU作成・read/writeで成功を判定します。上流の修正は未実施です。
- チャネル登録後、startによるPDU領域生成前にwriteすると、調査revisionでは `hako_mmap_open id=256` 失敗後にnative segmentation faultが起きました。**チャネル登録の成功だけでread/writeを開始しません。** 本ガイドの起動前提にはPDU領域生成も含みます。
- 最初のテスト用DataPort接続はPOA未activateでタイムアウトしました。検証用Managerのactivate/runを追加して解消しました。これはRTCの実機動作のactivateではありません。
- 通信成功後、所有RTCがいないテスト用ポートを解放せずORB終了すると、omniORB object table assertionでabortしました。明示的なservant解放を追加し、正常終了を再確認しました。

失敗ログも `build/system/logs/hakoniwa-wsl-*` に保持しています。初回のFalse判定失敗では終了時にpure virtual methodエラーも発生し、途中失敗の一部は正常停止へ到達していません。最終版は正常切断・停止・終了まで確認済みです。検証専用mmapファイルは証跡として残し、プロセス終了後は利用していません。

## GUIドローンシステムでの追加検証（2026-10-30 JST）

`build/generated/DroneTeleopControllerRTC` は、実際のRTCポートを1つだけ含む `RTC.ConnectorProfile` を `port.connect` に渡し、native端点へバインドします。箱庭アセットに存在しないCORBAポートを作りません。GUIとの2接続は通常のCORBA/rtshellで接続します。コントローラのactivate内でexternal-I/Oを初期化し、7つの指令・応答・pose接続を作成、deactivateで切断します。

未書き込みの全ゼロ領域を返すmetadata付き指令channelには、明示設定 `dataport.hakoniwa.skip_zero_packet: YES` を使用します。既定値はfalseです。raw形式では全ゼロが有効データになり得るため、全channelへ無条件に適用しません。

Foundation生成器とのバイト一致、状態機械とGUI入力の単体テスト10件、共通転送の8件、および実WSLg/Tkウィジェットイベントを使用した離陸・X/Y/Z/yaw・着陸が成功しました。停止入力後に新しい移動指令が増えないことと、進行中の移動の整定を分けて確認しています。実際の応答・ackのクリアを待って次の指令を送ります。poseに取得時刻はなく、時刻不明の扱いを維持します。

結果は `build/system/implementation-verification.json` と、その `runtimeLogDirectory` にある `gui-smoke-result.json`、単体テストログ、`viewer-stream-result.json` に保存します。HTTP配信とWebSocketバイナリフレームも確認済みですが、Windowsデスクトップの実マウス操作・WebGL描画・実機・厳密なstep同期は検証範囲外です。操作方法と停止手順は `build/system/scripts/README-runtime.txt` を参照します。

# 箱庭用Python転送プラグイン試作

[作成手順・契約・検証範囲](../../docs/agents/hakoniwa-serializer.md) を先に確認してください。
通常RTCの追加やシミュレーション自動起動ではなく、再利用可能なDataPort拡張の例です。

リポジトリルートを作業ディレクトリとするロード設定例：

```ini
manager.modules.load_path: ./examples/hakoniwa_transport
manager.modules.preload: HakoniwaTransport.py, HakoniwaSerializer.py
```

接続プロファイルのプロパティ例（INI形式で表示。これ自体は接続コマンドではありません）：

```ini
dataport.interface_type: hakoniwa
dataport.dataflow_type: push
dataport.subscription_type: flush
dataport.marshaling_type: hakoniwa:geometry_msgs/Twist:metadata72
dataport.hakoniwa.robot: Robot
dataport.hakoniwa.channel: 0
dataport.hakoniwa.pdu_size: 72
dataport.hakoniwa.poll_interval: 0.01
dataport.buffer.write.full_policy: overwrite
dataport.sync_readwrite: NO
```

これはPython変換器形式の例です。接続先がCサンプルの本体形式なら登録名を `hakoniwa:geometry_msgs/Twist:raw48`、サイズを48に変更します。送信先・受信元が同じrobot/channelを参照する必要があります。箱庭構成の型と実際の割当サイズも確認してください。

アプリケーションは既存の箱庭サンプルに従ってasset登録・実行を所有し、利用可能な時点でDataPortを読み書きしてください。プラグインだけのロードでは箱庭へ接続できません。一般的な任意RTCをそのまま起動できると想定しないでください。

ローカル検証（OpenRTM-aist-Python / RTC / omniORBが利用可能なPython環境）：

```powershell
python -m unittest discover -s examples/hakoniwa_transport -v
```

OpenRTM自体は実物を使い、箱庭native APIだけをメモリ内バックエンドに置き換えます。上流writerとの互換検証には、ガイド記載revisionの `build/reference/hakoniwa-core-cpp-client` checkoutも必要です。
WSL2ではnative共有メモリを使った実DataPort往復と、別プロセスからのPDU受信まで検証済みです。再実行はリポジトリルートから次を実行します（システムにインストールせず専用ビルドを使用）。

```bash
cmake -S build/reference/hakoniwa-core-cpp-client -B build/wsl-hakoniwa -DPython_EXECUTABLE=/usr/bin/python3
cmake --build build/wsl-hakoniwa --target hako_asset_python hako-cmd -j 4
python3 examples/hakoniwa_transport/verify_native.py --native-library build/wsl-hakoniwa/bindings/python/libhako_asset_python.so
```

事前に参照checkoutのcore submoduleが必要です。CMakeはnlohmann/jsonを取得する場合があります。今回の構成では既存のローカルjsonソースを `FETCHCONTENT_SOURCE_DIR_JSON` で指定して再利用しました。Python開発ヘッダ、CMake、C++コンパイラ、OpenRTM-aist-PythonとomniORBも必要です。

スクリプトは検証専用mmap領域とログを一意の `build/system/logs/hakoniwa-wsl-*` に作成し、空の箱庭シミュレーションをstart/stopします。全体30秒、peer10秒、コマンド3秒、受信3秒のタイムアウトを設けています。
上流の `conductor_start` / `pdu_create` に成功時Falseを返す不整合があるため、戻り値と実際の動作を分けて判定します。詳細、失敗履歴、未検証のstep同期・別プロセスRTC接続はガイドを参照してください。

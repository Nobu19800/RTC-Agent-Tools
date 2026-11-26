# OpenRTM 付属サンプルの選択と起動

[AGENTS.md](../../../AGENTS.md) から参照する手順である。

## 設計時

定期更新される `catalog/rtc_catalog.json` と、個別に管理する [openrtm_samples_catalog.json](../../../catalog/openrtm_samples_catalog.json) の双方を検索する。たとえば Python 版の ConsoleIn を探すには、RTC-Agent-Tools のルートで次を実行する。

```powershell
python rtc_search.py catalog/openrtm_samples_catalog.json "ConsoleIn Python" --json
```

検索は部分一致である。結果の `componentName` と `language` を照合する。Designer では **モジュール追加 → カタログ読込（RTC・OpenRTM サンプル・箱庭・ROS 2）** を押し、候補に表示される言語と **OpenRTM サンプル** の表記を確認する。同名・同言語の候補が両方にあればサンプル側を優先する。設計には選択した言語、起動情報、上流ソースのリビジョンを保持する。公開版の Designer がカタログと XML を読むには、これらのファイルが GitHub の `main` にある必要がある。

## 確定後の起動

1. 確定設計に保存された `launch` を確認する。設定がなければ、選択した言語と上流の出所を照合してサンプルカタログから取得する。ユーザーが指定した配備設定は保持する。
2. `launch.kind: installed` の場合は次の配布物を使う。Windows 上の Designer から WSL2 に配備する場合、C++ の選択には Linux 側の起動定義を使う。

   | 言語 | 起動設定と確認事項 |
   | --- | --- |
   | C++ | `launch.platforms.windows` または `launch.platforms.linux` を選び、インストールされた例題実行ファイルと共有ライブラリを確認する。 |
   | Python | `launch.deployment` を使う。対象の Python で `OpenRTM_aist` をインポートし、インストール先の例題スクリプトと生成済み IDL が揃っていることを確認する。 |
   | Java | `launch.deployment` を使う。対応する Java、インストール済み例題クラス、OpenRTM-aist Java 本体と依存 JAR を含むクラスパスを確認する。 |

3. `executable`、`workingDirectory`、`arguments` の記号参照を対象ホストの設定で解決する。記号の定義は [インストール済み起動設定](../../../profiles/openrtm-samples/README.md#インストール済みサンプルの起動) に従う。必要な `rtc.conf`、名前サービスや実行コンテキストの設定を確定設計から補う。必要な配布物がなければ、その環境での起動は保留して不足を報告する。
4. `launch: null` の項目は、インストール済み起動設定が未登録である。Lua や旧サンプルは対象の上流手順と配備環境を確認する。
5. [実行手順](runtime.md) に従い、登録、接続、活性化、実データ、停止を確認する。C++ 版を WSL2 で用意する場合の APT・ソースビルドの選択は [AGENTS.md](../../../AGENTS.md#c-openrtm-aist-in-wsl2) に従う。

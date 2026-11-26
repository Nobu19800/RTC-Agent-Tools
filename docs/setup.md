# RTC-Agent-Tools 環境構築手順書

[English](en/setup.md)

## 作業の分担

- **ユーザーが行う作業** — Codex または Claude Code を起動し、作業フォルダを指定する。設計リンクが提示されたらブラウザで設計を確認し、採用する構成を承認する。インストーラーや OS がユーザー本人の操作を求めたときは、エージェントの案内に従う。
- **エージェントが行う作業** — クローン、バージョンと依存関係の確認、必要なツールの導入、API の接続確認、ビルド環境の準備を行う。以降のコマンドはエージェントが実行するための参照例であり、通常の進め方ではユーザーが端末に入力する必要はない。

## 構成を選ぶ

| 作業 | 必要な環境 |
| --- | --- |
| カタログ検索と設計レビュー | Python 3、ブラウザ、選択したカタログと Designer へのアクセス |
| 公開 Designer 連携 | ブラウザと公開セッション API への HTTPS 接続 |
| RTC の生成・実行 | 対象言語の SDK と実行環境。スケルトン生成には Java と Builder、実行確認には名前サービスと rtshell |
| ROS 2 または箱庭を含む実行 | 選択した Linux／WSL2 環境と、確定設計が指定する ROS 2 パッケージまたは箱庭 Recipe |

## 1. チェックアウトと公開サービスへの接続

[RTC-Agent-Tools](https://github.com/Nobu19800/RTC-Agent-Tools) を取得し、使用するコミットを記録するのはエージェントの作業である。Windows では PowerShell で `git --version`、`python --version`、`curl.exe --version` を確認する。

ユーザーはエージェントが案内した設計リンクから [公開版 RTSystemDesigner](https://nobu19800.github.io/RTSystemDesigner/) を開く。設計の登録と読み戻しには公開セッション API を使う。Designer の利用に必要な準備は、ブラウザと API の HTTPS 接続確認である。[サービス設定](agents/services.md)

[クイックスタート](quickstart.md) のサンプルを使い、登録、ブラウザでの保存、再取得を確認する。

## 2. RTC の生成と実行に必要な環境

エージェントは設計に必要な実行環境を準備する。Windows の MSI 選択、Ubuntu・WSL2 での OpenRTM-aist、ROS 2、箱庭の導入コマンドは [実行環境のインストール](agents/install-runtime.md) に従う。

1. 対象言語の OpenRTM-aist SDK と依存ライブラリを用意する。C++ の場合は対応するコンパイラ、CMake、CORBA のライブラリを確認する。Python の場合は実行に使うインタープリターで `OpenRTM_aist` と `omniORB` をインポートする。
2. Java と Builder の JAR を確認する。Builder の実際のライブラリディレクトリを指定して、生成前に環境を検査する。
3. rtshell の `rtcon`、`rtact`、`rtdeact`、`rtexit` の実体とヘルプを確認する。実行先の名前サービスへの到達性と、登録された IOR が操作端末から到達可能なアドレスを指すことを確認する。

```powershell
python -c "import OpenRTM_aist, omniORB; print(OpenRTM_aist.__file__)"
python scripts/preflight_environment.py --java "$env:JAVA_HOME\bin\java.exe" --builder-lib "$env:BUILDER_LIB"
```

`BUILDER_LIB` は使用する Builder の JAR ディレクトリを指す環境変数の例である。必要なサービス IDL と include ディレクトリは生成対象ごとに確認する。[依存確認](agents/environment.md) · [生成手順](agents/generation.md)

## 3. Ubuntu・WSL2 の追加環境

WSL2 を使う場合、エージェントは Windows 側の `wsl --list --verbose` で対象ディストリビューションを確認する。Ubuntu と WSL2 のどちらでも、導入やビルドは配備先の Ubuntu 内で行う。

- **C++ OpenRTM-aist** — APT リポジトリを設定した後、`apt-cache policy openrtm2` で候補版を確認する。リポジトリの方針では候補が `2.1.0-0` の場合は OpenRTM-aist のソースからビルドし、候補がそれより新しければ APT 版を使う。ビルド時は使用したソースリビジョンを記録する。候補なしの場合は APT の設定と対象 OS を確認する。
- **名前サービス** — 確定設計に明示されたエンドポイントを使う。指定がない WSL2 構成では、Windows から到達できる WSL2 IP を RTC と名前サービスの IOR に公開する。名前サービスの既定ポートは `2809` である。既存サービスが条件を満たす場合は再利用する。[エンドポイント設定](agents/runtime.md)
- **ROS 2** — サンプルの対象は Jazzy である。実行に使う端末で ROS 2 と必要なワークスペースのセットアップを読み込み、`ros2 pkg executables <package>` で対象実行ファイルを確認する。RTC と通信する場合は対象言語の ROS2Transport、DDS バックエンド、型・DDS ドメイン・QoS を揃える。[ROS 2 起動](agents/ros2.md) · [ROS2Transport](agents/ros2-transport.md)
- **箱庭** — 選択した Recipe に従い、配備先の Ubuntu または WSL2 で Workspace と Foundation を構築する。使用する Python でネイティブバインディングと PDU 変換モジュールを確認する。ビューア付き構成では、ビューア本体、設定、コーデック、WebSocket 経路も準備する。[Business Pack の手順](https://github.com/hakoniwalab/hakoniwa-business-pack/blob/main/AGENTS.md) · [箱庭と ROS 2 の連携](agents/hakoniwa-ros2.md)
- **スプレッドシート RTC** — ExcelControlpy は Windows 上の Microsoft Excel、pywin32、PyQt5、OpenRTM-aist Python と生成済み IDL バインディングを使う。LibreOffice Calc は UNO と OpenRTM-aist Python を同じ実行環境に用意する。[動的ポートの手順](agents/dynamic-rtc-ports.md)

準備の完了条件は、対象ツールのバージョン、実行パス、依存モジュール、通信の到達性を確認できることである。実際のデータ転送の確認は [動作マニュアル](operation-manual.md) の手順で行う。

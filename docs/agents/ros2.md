# ROS 2 ノードの設計と起動

RTC-Agent-Tools ルートで検索し、カタログ ID を指定して v2 セッションに配置します。既存の設計を指定すると、他のコンポーネントと接続を保持したままノードを追加します。

```powershell
python scripts/ros2_system.py search "robot state publisher"
python scripts/ros2_system.py add ros2:robot_state_publisher/robot_state_publisher design.json --instance robot_state --namespace /demo
python scripts/ros2_system.py plan design.json
```

Designer では「モジュール追加」→「カタログ読込（RTC・箱庭・ROS 2）」で RTC-Agent-Tools の GitHub リポジトリから各カタログを取得し、キーワードで絞り込んで配置できます。既にある設計は「JSON読込」、ローカル保存は「JSON出力」を使います。レビューをセッションサーバーで行う場合は [サービス手順](services.md) に従い、承認後は最新の設計を取得して使用します。

## セッション形式

- `data.moduleKind` は `ros2`、図上の `type` は `rtc` です。`data.catalogId` にカタログ ID を保存し、起動には `data.ros2.package`、`executable`、`namespace` と `data.instanceName` を使用します。
- トピックは `portType: data` と `direction: in/out` で表現します。パブリッシャーから同じ完全修飾メッセージ型のサブスクライバーへ接続します。サービスとアクションは `portType: service`、`rosInterfaceKind: service/action` とし、同じ完全修飾型の consumer から provider に接続します。カタログにあるサーバーは provider として取り込まれます。クライアントはポート編集で追加できます。
- トピックはサブスクライバーをパブリッシャーの完全修飾名へ、サービスはクライアントをサーバーの完全修飾名へ remap します。アクションは両端が同じ完全修飾名になるよう設計してください。異なる ROS ドメインや競合する remap はエラーになります。
- RTC の DataPort と ROS 2 トピックを接続する場合は [ROS2Transport の設定](ros2-transport.md) を使います。箱庭アセットの場合は [箱庭–ROS 2 連携](hakoniwa-ros2.md) に従い、PDU と ROS 2 トピックをブリッジで接続します。

## 承認済み設計から起動

必要なパッケージと依存関係を導入して ROS 2 とワークスペースを source 済みの Linux または WSL の端末で、RTC-Agent-Tools ルートから実行します。

```bash
python3 scripts/ros2_system.py plan final-session.json
python3 scripts/ros2_system.py run final-session.json
```

`plan` は Windows でも実行でき、実際に起動せず argv を確認できます。`run` はローカルの `ros2 pkg executables` で全ノードの実行ファイルを確認してから、ROS 2 ノードをフォアグラウンドで起動します。標準出力・標準エラーは端末に出ます。Ctrl+C または起動済みプロセスの異常終了時には、このコマンドが起動したプロセスグループを停止します。

Deployment の `Host` はローカルです。`Working Directory` は設計 JSON のあるディレクトリを基準に解決します。`Arguments` は POSIX の引用規則で引数配列に分割し、シェル展開は行いません。`Environment` は1行1件の `NAME=value`、Configuration の各値は ROS 2 の `-p name:=value` に渡します。General タブの ROS 2 欄でパッケージ・実行ファイル・名前空間・任意の `parametersFile` を設定します。パラメーター YAML のパスも設計 JSON を基準に解決します。

起動機能の対象は単体の `ros2 run` です。Lifecycle 遷移、launch ファイル、コンポーネントコンテナ、外部ブリッジは各パッケージの手順で構成してください。実行可否はカタログの記録に加え、実際のインストールと依存関係で確認します。

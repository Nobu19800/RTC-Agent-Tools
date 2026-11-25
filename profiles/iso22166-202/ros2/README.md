# ROS 2 ノードの ISO 22166-202 対応づけ

`deep-research-report.md` の番号付き一覧から ROS 2 ノード100件を収録しています。ファイル名は `<package>__<executable>.xml` です。ローカル Module ID はパッケージ名と実行ファイル名を組み合わせて決定するため、異なるパッケージに同名の実行ファイルがあっても区別できます。

既存の箱庭プロファイルと同様に [ISO 22166-202:2025 の公開情報モデル](https://www.iso.org/obp/ui?_escaped_fragment_=iso%3Astd%3Aiso%3A22166%3A-202%3Aed-1%3Av1%3Aen) に対応づけたローカル XML です。公式 Annex B XSD を入手していないため、正式な要素名・型・多重度への適合と Annex F の詳細な対応規則は未検証です。名前空間と UUID はこのリポジトリで定義し、適合性欄は `not-assessed` としています。

カテゴリ・説明・入出力概要・ディストリビューション注記は英語です。明示されたトピック、サービス、アクションを構造化し、型が特定できた場合は `dataType` を記録します。`upstream-review.json` の根拠 URL と照合結果は XML の `Evidence` と JSON の `source` に反映します。Jazzy の登録定義、他ブランチの登録定義、確認対象に登録がない項目はステータスで識別できます。実行形式は `ros2 run` の基本形です。追加引数や実行環境は別途確認が必要です。

Nav2 の Docking Server は Jazzy の登録情報に従って `opennav_docking/opennav_docking` としています。`rosbridge_tcp` は元レポートとの対応を保つために残し、Jazzy のインストール定義に登録が見つからなかったため実行形式を省略しています。`pcl_ros/bag_to_pcd` の登録根拠は上流の `ros2` ブランチです。

各ファイルの `Evidence` には元レポートのファイル名、一覧の項目番号、元ファイルの SHA-256 を保存しています。カタログの再生成と照合は [カタログ手順](../../../catalog/README.md#ros-2-ノード) を参照してください。

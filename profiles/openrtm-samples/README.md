# OpenRTM サンプルプロファイル

上流の実装から、`RTC.xml` がないサンプル RTC の基本情報、コールバック、ポート、設定の既定値を抽出した。実行時に決まるイベントポートの型など、確定できない項目は空欄とした。テスト用ディレクトリ、テンプレート、接続専用のランチャーは収録対象から外した。複数の派生サンプルに同名・同言語の実装がある場合、XML はソースの相対ディレクトリごとに配置し、カタログの各組み合わせには代表の1件を使う。

| 言語 | 上流の確認先 | 生成した RTC.xml | カタログ掲載 |
| --- | --- | ---: | ---: |
| C++ | [OpenRTM-aist](https://github.com/OpenRTM/OpenRTM-aist/tree/712e3417286d4b08a52b9180c7d271fedf266829/examples) | 26 | 31 |
| Python | [OpenRTM-aist-Python](https://github.com/OpenRTM/OpenRTM-aist-Python/tree/6dc2e8c37e8955cb1decd68b94210176d3914ae8/OpenRTM_aist/examples) | 42 | 33 |
| Java | [OpenRTM-aist-Java](https://github.com/OpenRTM/OpenRTM-aist-Java/tree/6617008b7f4ab844adb145702ff6fda130960df5/jp.go.aist.rtm.RTC/src/RTMExamples) | 22 | 18 |
| Lua | [RTM-Lua](https://github.com/Nobu19800/RTM-Lua/tree/1189126774c3eb3ebcbd9c7aa839b4cfc7b70528/examples) | 10 | 10 |

`catalog-entries.json` はカタログ生成時の入力である。`source.revision` と `source.path` に上流実装の出所を記録する。`source.profilePath` がある項目は、このリポジトリの XML を読み込む。上流に XML がある C++ サンプルは `source.upstreamProfilePath` に元の XML を記録する。

## インストール済みサンプルの起動

カタログの `launch.kind: installed` は、インストール済みの配布物に対する起動設定である。C++ は `launch.platforms.windows` または `launch.platforms.linux` を選ぶ。Python と Java は `launch.deployment` を使う。記号参照は起動先に合わせて解決し、実ファイル、依存ライブラリ、実行環境を確認した上で確定設計の配備設定へ反映する。

| 記号参照 | 設定する値 |
| --- | --- |
| `${OPENRTM_CPP_EXAMPLES_DIR}` | `ConsoleInComp.exe` または `ConsoleInComp` があるインストール先の例題バイナリディレクトリ |
| `${PYTHON_EXECUTABLE}` | 対象の OpenRTM-aist Python を利用できる Python 実行ファイル |
| `${OPENRTM_PYTHON_EXAMPLES_DIR}` | インストール済みの `OpenRTM_aist/examples` ディレクトリ |
| `${JAVA_EXECUTABLE}` | 配布版が対応する Java 実行ファイル |
| `${OPENRTM_JAVA_EXAMPLES_DIR}` | インストール済みの `RTMExamples` クラスディレクトリを含む親ディレクトリ |
| `${OPENRTM_JAVA_CLASSPATH}` | 例題のクラスルート、OpenRTM-aist Java 本体と依存 JAR を含むクラスパス。区切り文字は起動先 OS に合わせる |

起動引数に必要な `rtc.conf`、名前サービスと実行コンテキストの設定は確定設計に従って追加する。古い実装や現在の配布対象外のサンプル、Lua 版の `launch` は `null` とした。配布版によっては設定済みのサンプルも省かれるため、対象ファイルの存在確認が必要である。

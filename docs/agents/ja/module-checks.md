# 新規モジュールの静的解析・単体テスト

[AGENTS.md](../../../AGENTS.md) から参照する手順である。新規作成した C++、Python、Lua モジュールに適用する。静的解析と単体テストは、依頼された項目だけを実行する。設計、生成、ビルド、起動、動作確認を行う際の自動実行や、定期ワークフローへの追加は行わない。

既存のテスト設定とコンパイル設定を確認する。単体テストの依頼時に対象のテストがなければ、確定した要件に基づき、OpenRTM や実機を起動せず実行できるコアのテストを用意する。正常系・境界値・異常入力のうち、対象機能に関係するケースを確認する。テスト用の依存関係とカバレッジ計測は、明示的に選ぶテストビルドやテスト環境で有効にする。

## C++

- **静的解析** — Clang Static Analyzer を使う。CMake などで対象の実ビルドと同じコンパイルオプション、インクルード、生成 IDL を含むコンパイルデータベースを用意する。例として、Clang-Tidy の `clang-analyzer-*` チェッカーを実行する。パスは対象モジュールの構成に置き換える。[Clang Static Analyzer](https://clang.llvm.org/docs/ClangStaticAnalyzer.html)

  ```bash
  clang-tidy -p build/analysis --checks='-*,clang-analyzer-*' src/ExampleCore.cpp src/Example.cpp
  ```

- **単体テストとカバレッジ** — GoogleTest でコアをテストする。計測用ビルドでは、対象モジュールとテスト実行ファイルを Clang で構築し、計測するソースのコンパイルとテスト実行ファイルのリンクに `-fprofile-instr-generate -fcoverage-mapping` を適用する。次は計測済みのテストバイナリを使う Bash の例である。Windows の場合は実行ファイル名や環境変数の設定方法を使用するシェルに合わせる。[CMake の GoogleTest 対応](https://cmake.org/cmake/help/latest/module/GoogleTest.html) · [Clang のカバレッジ手順](https://clang.llvm.org/docs/SourceBasedCodeCoverage.html)

  ```bash
  mkdir -p build/coverage
  LLVM_PROFILE_FILE=build/coverage/example.profraw ./build/coverage/example_tests
  llvm-profdata merge -sparse build/coverage/example.profraw -o build/coverage/example.profdata
  llvm-cov report ./build/coverage/example_tests -instr-profile=build/coverage/example.profdata src/ExampleCore.cpp
  ```

## Python

- **静的解析** — 対象モジュールの Python 環境で Bandit と flake8 の両方を実行する。Bandit はセキュリティに関する指摘、flake8 は構文・スタイルなどの指摘を確認する。

  ```bash
  python -m bandit src/Example.py src/ExampleCore.py
  python -m flake8 src/Example.py src/ExampleCore.py
  ```

- **単体テストとカバレッジ** — pytest と pytest-cov を使い、対象ソースのカバレッジと未実行行を端末に表示する。以下の `src` と `tests` は対象モジュールのパスに置き換える。[pytest-cov のレポート](https://pytest-cov.readthedocs.io/en/latest/reporting.html)

  ```bash
  python -m pytest tests --cov=src --cov-report=term-missing
  ```

## Lua

- **静的解析** — 対象モジュールで使う Lua のバージョンとプロジェクトのグローバル定義を確認し、Luacheck を実行する。[Luacheck](https://github.com/lunarmodules/luacheck)

  ```bash
  luacheck Example.lua ExampleCore.lua
  ```

- **単体テストとカバレッジ** — LuaUnit のテストランナーを、LuaCov を読み込んだ Lua インタープリターで実行する。例の `tests/test_example.lua` は `luaunit.LuaUnit.run()` の結果を終了コードに反映するテストランナーである。LuaCov の設定で対象モジュールを指定し、計測結果には今回の実行分を使う。[LuaUnit](https://github.com/bluebird75/luaunit) · [LuaCov](https://github.com/lunarmodules/luacov)

  ```bash
  lua -lluacov tests/test_example.lua
  luacov
  cat luacov.report.out
  ```

## 結果の提示

実行したコマンド、対象ファイル、解析の指摘、テストの成功・失敗件数を報告する。単体テストを実行した場合はカバレッジの集計値と測定対象を表示し、ファイルに出力した場合は場所も示す。既定の合格率は設けず、ユーザーが基準を指定した場合はその基準に従う。依存関係の不足やテスト失敗でレポートが得られない場合は、理由を明記する。

# 環境と依存関係の確認

導入・生成・配備の前に読み取り中心の事前確認を行い、対象ホスト、使用する版、実行パスと不足項目を記録する。[導入手順](install-runtime.md)

- Java は実際の実行ファイルと有界のバージョン確認を使い、Builder JAR の必要クラスも確認する。
- Python は配備時に使うインタープリターで OpenRTM、omniORB、生成 IDL、rtshell、必要な箱庭のネイティブバインディングを確認する。ABI、Foundation の版、ライブラリ検索パスを記録する。
- WSL2 ではディストリビューションと表示環境を確認する。RTC と名前サービスの IOR は [実行手順](runtime.md) と [AGENTS.md](../../../AGENTS.md) に従って Windows から検証する。
- ビューアのモデル、設定、JS コーデック、サブモジュールを確認し、使用した版と検証範囲を記録する。HTTP 応答だけで描画成功と判断しない。
- インストールスクリプトは内容を確認してから使い、依存元、必要なリビジョン、配備ファイルのハッシュを記録する。実際の導入や起動はユーザーの依頼範囲で行う。
- `scripts/preflight_environment.py` の `--java`、`--builder-lib`、`--teleop`、`--viewer-root` を対象に合わせて使い、必要に応じて `--output` で記録を残す。ネイティブ Python の確認は対象 Foundation 内で行う。

[詳細な原文（英語）](../en/environment.md)

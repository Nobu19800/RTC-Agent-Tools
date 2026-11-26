# RTC-Agent-Tools

[English](README.md)

RTC-Agent-Tools は、Codex などのエージェントと一緒にロボットシステムを設計・構築・実行するためのツール集である。エージェントに作りたいシステムを伝えると、設計案を RTSystemDesigner で確認できる。設計を確定した後は、その内容に沿って構築と起動を依頼できる。[公開版 RTSystemDesigner](https://nobu19800.github.io/RTSystemDesigner/)

## すぐに試す

[画像付きクイックスタート](docs/quickstart.md) では、GUI ジョイスティックで物理シミュレータ上の移動ロボットを操作する。クローンから設計確認、起動、終了まで、Codex と Claude Code のどちらでも使える5つのメッセージを掲載している。

Codex で作業フォルダを開くか、そのフォルダの端末で Claude Code を起動する。どちらでも同じメッセージから始める。[Claude Code の公式インストール手順](https://code.claude.com/docs/en/setup#install-claude-code)

> この作業フォルダに https://github.com/Nobu19800/RTC-Agent-Tools.git をクローンして。

[システム構成図](docs/operation-specification.md#システム構成)で、Codex、GitHub、RTSystemDesigner 間の設計情報の流れを確認できる。

## ドキュメント

| ドキュメント | 内容 |
| --- | --- |
| [クイックスタート](docs/quickstart.md) | Codex または Claude Code でサンプルシステムを構築し、画面で動作を確認する |
| [環境構築手順書](docs/setup.md) | 実行環境と依存ツールを準備する |
| [動作マニュアル](docs/operation-manual.md) | 設計、構築、起動、停止の操作手順を確認する |
| [詳細な動作仕様書](docs/operation-specification.md) | 設計情報、カタログ、構築・実行時の処理を確認する |
| [ローカル版 RTSystemDesigner の連携手順](docs/local-designer.md) | ローカルの Designer とセッションサーバーを使う |
| [RTC–箱庭アセット連携手順](docs/rtc-hakoniwa.md) | RTC の DataPort と箱庭 PDU を接続し、値を照合する |
| [RTC–ROS 2 連携手順](docs/rtc-ros2.md) | ROS2Transport で往復通信を確認する |
| [CalcControl を使ったシステム構築事例](docs/calccontrol-example.md) | LibreOffice Calc を経由して ConsoleIn と ConsoleOut を接続する |
| [空のセッションから設計する](docs/empty-session.md) | RTSystemDesigner で構成を作り、エージェントに渡す |
| [RTSystemDesigner のモジュール設定項目](docs/designer-module-settings.md) | RTC、ROS 2 ノード、箱庭アセットの設定項目を確認する |
| [OpenRTM-aist の型変換と通信プラグイン](docs/rtc-transport-plugins.md) | 箱庭・ROS 2 連携で使うプラグインの役割と設定を確認する |
| [カタログと XML プロファイル](docs/catalog-profiles.md) | 各カタログ、ISO 22166-202 対応 XML、RTC.xml の内容を確認する |
| [AGENTS.md](AGENTS.md) | エージェント向けの作業指示と、日英の作業ガイドへの入口 |

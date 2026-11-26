# RTC-Agent-Tools クイックスタート

[English](en/quickstart.md)

Codex または Claude Code に5つのメッセージを順に送り、GUI ジョイスティックで物理シミュレータ上の移動ロボットを操作します。画面例は Windows 上で Raspberry Pi Mouse を操作したときのもので、選ばれるコンポーネントや構成は実行環境と確定した設計によって変わります。

## エージェントと作業フォルダを準備する

作業用に空のフォルダを作成します。この例では `rtc-demo` とします。Codex を使う場合は、Codex をインストールしてサインインします。[Codex を使うための ChatGPT デスクトップアプリの案内](https://learn.chatgpt.com/docs/app)

Claude Code でも同じ5つのメッセージを使えます。利用する OS 向けの手順でインストールし、作業フォルダを開いた端末で `claude` を起動してサインインします。そのセッションで手順1から進めます。[Claude Code の公式インストール手順](https://code.claude.com/docs/en/setup#install-claude-code)

Codex を使う場合は、サイドバーにある「プロジェクト」横の「＋」を押します。

<a href="images/quickstart/codex-add-project.png"><img src="images/quickstart/codex-add-project.png" alt="Codex のサイドバーにあるプロジェクト追加ボタン" width="600"></a>

プロジェクト名を入力し、ソースフォルダーに作成した作業フォルダを追加します。「プロジェクトを作成」を押し、そのプロジェクトで新しいチャットを開きます。以降のメッセージは同じチャットで送ります。

<a href="images/quickstart/codex-project-folder.png"><img src="images/quickstart/codex-project-folder.png" alt="Codex のプロジェクト作成画面" width="600"></a>

## 1. RTC-Agent-Tools をクローンする

> この作業フォルダに https://github.com/Nobu19800/RTC-Agent-Tools.git をクローンして。

作業フォルダの直下に `RTC-Agent-Tools` が作成されたことを、エージェントの返信で確認します。Git の導入が必要な場合は、利用環境に合った手順で導入してからクローンします。

<a href="images/quickstart/codex-message-1.png"><img src="images/quickstart/codex-message-1.png" alt="Codex にクローンを依頼したときの返信例" width="600"></a>

## 2. システムの構築を依頼し、設計案を確認する

> AGENTS.md に沿って、GUI ジョイスティックで移動ロボットを操作するシミュレーションを作って。

エージェントの返信で、コンポーネント一覧と設計セッションのリンクを確認します。

<a href="images/quickstart/codex-message-2.png"><img src="images/quickstart/codex-message-2.png" alt="Codex が設計リンクとコンポーネント一覧を提示した例" width="600"></a>

返信のセッションリンクから公開版 RTSystemDesigner を開き、コンポーネント、ポートの型と方向、接続を確認します。修正する場合は、Codex に伝えるか、画面で編集して「保存」を押します。設計は公開サービスに登録されるため、機密情報を入力しないでください。[公開版 RTSystemDesigner](https://nobu19800.github.io/RTSystemDesigner/)

<a href="images/quickstart/rtsystemdesigner.png"><img src="images/quickstart/rtsystemdesigner.png" alt="公開版 RTSystemDesigner に表示されたジョイスティックとシミュレータの設計例" width="600"></a>

## 3. 設計完了を伝える

設計に問題がなく、変更が保存されていることを確認してから送ります。

> 設計完了

エージェントが確定設計を読み込み、必要なコンポーネントの取得、実装、ビルド、実行設定を進めます。返信で構築結果と起動に必要な条件を確認します。

<a href="images/quickstart/codex-message-3.png"><img src="images/quickstart/codex-message-3.png" alt="設計完了を伝えた後に Codex が構築結果を報告した例" width="600"></a>

## 4. 起動して画面で確認する

> システムを起動して

エージェントの返信で起動結果と接続状態を確認します。画面操作の確認は、ユーザーが実際のシミュレータ画面を見ながら行います。

<a href="images/quickstart/codex-message-4.png"><img src="images/quickstart/codex-message-4.png" alt="Codex がシステムの起動と接続状態を報告した例" width="600"></a>

以下は画面例の操作手順です。実際の構成に応じて エージェントが案内した操作に従います。

1. `TkJoystick` とシミュレータのウィンドウを開きます。
2. ジョイスティック中央の円を上下にドラッグし、ロボットが前後に移動することを確認します。
3. 円を左右にドラッグし、ロボットが旋回することを確認します。
4. マウスボタンを離し、ロボットが停止することを確認します。

<a href="images/quickstart/joystick.png"><img src="images/quickstart/joystick.png" alt="TkJoystick の中央にあるドラッグ用の円" width="400"></a>

<a href="images/quickstart/raspberry-pi-mouse-simulator.png"><img src="images/quickstart/raspberry-pi-mouse-simulator.png" alt="物理シミュレータに表示された Raspberry Pi Mouse" width="600"></a>

RTSystemEditor を使う場合は、起動中の RTC と接続も確認できます。

<a href="images/quickstart/rtsystemeditor.png"><img src="images/quickstart/rtsystemeditor.png" alt="RTSystemEditor に表示された起動中の RTC とポート接続の例" width="600"></a>

## 5. システムを終了する

> システムを終了して

エージェントの返信で、対象の RTC プロセスの終了と名前サービスからの登録解除を確認します。

<a href="images/quickstart/codex-message-5.png"><img src="images/quickstart/codex-message-5.png" alt="Codex が RTC の終了と登録解除を報告した例" width="600"></a>

## 関連ドキュメント

- [環境構築手順書](setup.md)
- [詳細な動作仕様書](operation-specification.md)
- [動作マニュアル](operation-manual.md)

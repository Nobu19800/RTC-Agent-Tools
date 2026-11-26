# 確定設計とビルド作業領域

<a id="phase-8-on-design-complete-load-the-final-design"></a>
## フェーズ8　確定設計を取得する

ユーザーの設計完了確認後、保存済みセッションの最新 JSON または確認済みの **JSON出力** を `work/final-session.json` に保存する。エージェントが作ったセッションは会話中の ID または `work/current_session_id.txt` を使う。必要な情報が得られなければ、確定版のファイルか URL を確認する。[サービス手順](services.md)

JSON を検証し、コンポーネントとエッジの ID を保持する。混在接続の `work/connection-contracts.json` と根拠資料を照合し、古い接続設定を取り除く。未解決のバインディングは実行に使わない。

## フェーズ9　作業領域を準備する

既存のソースを `build/existing/`、新規 RTC を `build/generated/`、確定設計と実行設定を `build/system/` に置く。確定 JSON のコピーを `build/system/final-session.json` に保存する。ソースのリビジョン、ネイティブ依存、実行先と配備設定を記録する。名前付き参照を配備設定で解決し、未定義の参照をシェル評価や推定で補わない。

## フェーズ10　既存 RTC を準備する

確定設計で実際に使用する RTC だけを対象にする。リポジトリは `build/existing/` に取得し、同一リポジトリは一度だけ取得する。URL と版を記録する。付属サンプルのインストール済み起動設定がある場合は [サンプルの手順](openrtm-samples.md) に従う。取得失敗や出所不明は報告し、独立に進める作業を続ける。

[生成](generation.md) → [実装・ビルド](implementation.md) → [実行バッチ](runtime.md) の順で進め、成果物と未検証事項を報告する。

## 元の手順にあるコマンド・形式の例

```text
https://rt-session-server.rtsystem-designer-web.workers.dev/api/sessions/<SESSION_ID>
```

```bash
curl -L \
  "https://rt-session-server.rtsystem-designer-web.workers.dev/api/sessions/<SESSION_ID>" \
  -o work/final-session.json
```

```text
build/
```

```text
build/
  existing/
    <RTC-name-or-repository-name>/
  generated/
    <GeneratedRTCName>/
  system/
    final-session.json
```

```text
build/system/final-session.json
```

```text
build/existing/<repository-or-rtc-name>/
```

```bash
git clone "<repositoryUrl>" "build/existing/<name>"
```

[詳細な原文（英語）](../en/workspace.md)

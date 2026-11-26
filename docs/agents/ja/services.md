# リポジトリのツールとサービス

- 一般 RTC カタログは正規 URL から更新し、`python rtc_search.py catalog/rtc_catalog.json <語> --json` で検索する。付属サンプルは `catalog/openrtm_samples_catalog.json` も検索する。コンポーネント名・言語・型・出所を照合する。
- 箱庭は `hakoniwa_search.py` と XML 由来カタログの確認を併用する。ROS 2 は `python scripts/ros2_system.py search` を使う。

[一般 RTC カタログ](https://raw.githubusercontent.com/Nobu19800/RTC-Agent-Tools/refs/heads/main/catalog/rtc_catalog.json) · [カタログ形式](../../../catalog/README.md)

## セッション

公開サーバーの `POST /api/sessions` で登録、`GET /api/sessions/<ID>` で取得する。Designer は保存時に `PUT /api/sessions/<ID>` を使う。返された `designerUrl` を優先し、省略時は Designer の URL に `?session=<ID>` を付ける。公開 API に送信する設計は公開サービスで取り扱われる。機密情報を含めない。

- [公開セッション API](https://rt-session-server.rtsystem-designer-web.workers.dev/api/sessions)
- [公開版 Designer](https://nobu19800.github.io/RTSystemDesigner/)
- [ローカル連携手順](../../local-designer.md)

ローカル連携の依頼時は、登録・編集・取得を同じ稼働中のサーバーで行う。

## 元の手順にあるコマンド・形式の例

```bash
python rtc_search.py catalog/rtc_catalog.json camera --json
python rtc_search.py catalog/rtc_catalog.json "object detection" --json
python rtc_search.py catalog/rtc_catalog.json robot --json
python rtc_search.py catalog/rtc_catalog.json --all --json
python rtc_search.py catalog/openrtm_samples_catalog.json "ConsoleIn Python" --json
```

```bash
python hakoniwa_search.py catalog/hakoniwa_catalog.json --all
python hakoniwa_search.py catalog/hakoniwa_catalog.json HakoDroneCmdMove --json
```

```text
https://raw.githubusercontent.com/Nobu19800/RTC-Agent-Tools/refs/heads/main/catalog/rtc_catalog.json
```

```text
catalog/rtc_catalog.json
```

```bash
curl -L "https://raw.githubusercontent.com/Nobu19800/RTC-Agent-Tools/refs/heads/main/catalog/rtc_catalog.json" -o catalog/rtc_catalog.json
```

```text
https://rt-session-server.rtsystem-designer-web.workers.dev
```

```text
POST /api/sessions
```

```text
GET /api/sessions/:id
```

```text
PUT /api/sessions/:id
```

```text
https://nobu19800.github.io/RTSystemDesigner/
```

```text
https://nobu19800.github.io/RTSystemDesigner/?session=<SESSION_ID>
```

[詳細な原文（英語）](../en/services.md)

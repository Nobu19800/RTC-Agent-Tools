# RTSystemDesigner セッション形式

## フェーズ4　v2 JSON を作る

ルートに `version: 2`、`id`、`name`、`description`、`components`、`edges` を置く。セッション ID とシステム ID を区別する。各ノードの `type` は図上の `rtc`、実際の種別は `data.moduleKind` の `rtc`、`hakoniwa`、`ros2` で区別する。各ノードに安定した ID、位置、`data.name`、一意の `data.instanceName` を設定する。

- 既存候補はカタログ ID、ソース URL、選定版、XML の出所を記録する。箱庭のカタログ ID・コンポーネント ID・PDU チャンネル ID は区別する。
- `data.implementation` の `summary`、`requirements`、`constraints`、`notes` に責務、要求、制約、未確定事項を記録する。ExcelControlpy／Calc のセル対応は [動的ポート手順](dynamic-rtc-ports.md) に従う。
- `deployment`、`rtcConf`、`configuration` に対象に応じた設定を置く。マシン固有のパスは名前付き参照で表現し、配備時に別の設定で解決する。未定義の値は明記し、シェル展開を前提にしない。
- `data.ports` の安定した ID を `sourceHandle`／`targetHandle` で参照する。データ接続は出力から入力、サービス接続は利用側から提供側にし、型・役割とエッジの種別を照合する。箱庭の `channelId` と ROS 2 の完全修飾型を維持する。
- 混在エッジの配備・変換契約は、必要に応じて別ファイルに保存する。Designer 保存後に接続先、型、カタログ ID、PDU チャンネルと契約の整合を読み戻して確認する。
- 旧形式の `nodes`／`rtcTemplates` を出力しない。旧形式専用の準備・バッチ生成スクリプトは対応を確認してから使用する。

## 元の手順にあるコマンド・形式の例

```json
{
  "version": 2,
  "name": "Example system",
  "description": "Example RTC module",
  "id": "example-system",
  "components": [
    {
      "id": "source-rtc-1",
      "type": "rtc",
      "position": { "x": 80, "y": 180 },
      "data": {
        "moduleKind": "rtc",
        "name": "SourceRTC",
        "instanceName": "SourceRTC0",
        "state": "INACTIVE",
        "ports": [
          { "id": "out", "name": "out", "portType": "data", "direction": "out", "dataType": "RTC::TimedVelocity2D" }
        ],
        "deployment": { "host": "localhost", "executable": "", "workingDirectory": "", "arguments": "", "environment": "" },
        "rtcConf": { "corbaNameServers": "localhost", "managerShutdownAuto": "NO" },
        "configuration": [],
        "implementation": { "summary": "Produce velocity commands", "requirements": "Output typed velocity data", "constraints": "", "notes": "" }
      }
    }
  ],
  "edges": []
}
```

```json
{
  "host": "WSL2-Ubuntu",
  "executable": "${PYTHON_EXECUTABLE}",
  "workingDirectory": "${WORKSPACE_ROOT}",
  "arguments": "\"${WORKSPACE_ROOT}/build/generated/ExampleRTC/ExampleRTC.py\" -f \"${RECIPE_ROOT}/ExampleRTC.conf\"",
  "environment": "HAKO_CONFIG_PATH=${RECIPE_ROOT}/config/cpp_core_config.json"
}
```

```json
{ "id": "velocity_in", "name": "velocity_in", "portType": "data", "direction": "in", "dataType": "RTC::TimedVelocity2D", "channelId": 12 }
```

```json
{
  "id": "edge-source-asset",
  "source": "source-rtc-1",
  "sourceHandle": "out",
  "target": "asset-1",
  "targetHandle": "velocity_in",
  "data": { "connectionType": "data" },
  "markerEnd": { "type": "arrowclosed" }
}
```

[詳細な原文（英語）](../en/session-format.md)

# 新規 RTC のプロファイルとスケルトン生成

## フェーズ11

1. 確定設計に配置された新規 RTC を抽出する。型付きポート、サービス IDL、設定とコアの責務を整理し、設計と配備の値を照合する。
2. 各 RTC について、Designer のセッション JSON とは別に、`rtc_sample.json` 形式のモジュール定義 JSON を作る。使用しないポート、サービス、設定は空配列とする。項目名と具体例は同じ章の原文にある定義を参照する。
3. `json_to_rtc_xml.py` で `RTC.xml` を生成し、名前、言語、ポート、型、IDL、設定が定義と一致することを確認する。
4. `cuirtcbuilder.bat` の `-d`（出力先）と `-f`（RTC.xml）を指定し、カスタム IDL が必要なら対応する `-i` を指定する。Java、Builder と IDL の依存を確認し、生成コマンド・警告・成果物を記録する。
5. 既存の実装済みファイルを再生成で上書きしない。既存の生成記録を確認し、必要であれば別ディレクトリで生成して差分を反映する。MSVC の UTF-8 と例外設定は既存のフラグを保ちながら確認する。
6. スケルトン生成・コンパイル、コア実装、実データを用いた動作確認を区別する。既存 RTC に新規生成手順を適用しない。

```powershell
python json_to_rtc_xml.py build/generated/MyRTC/MyRTC.json build/generated/MyRTC/RTC.xml
.\cuirtcbuilder.bat -d build/generated/MyRTC -f build/generated/MyRTC/RTC.xml
```

旧形式専用の生成補助スクリプトを v2 にそのまま適用しない。[実装・ビルド](implementation.md)

## 元の手順にあるコマンド・形式の例

```text
build/generated/<RTCName>/
```

```text
build/generated/<RTCName>/<RTCName>.json
```

```json
{
  "profileVersion": "0.3",
  "basicInfo": {
    "name": "SampleRTC",
    "description": "Example RT component",
    "version": "1.0.0",
    "vendor": "AIST",
    "category": "example",
    "componentType": "STATIC",
    "activityType": "PERIODIC",
    "componentKind": "DataFlowComponent",
    "maxInstances": 1,
    "executionType": "PeriodicExecutionContext",
    "executionRate": 1000.0
  },
  "actions": {
    "OnInitialize": true,
    "OnActivated": true,
    "OnDeactivated": true,
    "OnExecute": true
  },
  "configuration": [
    {"name": "motor_id", "type": "int", "defaultValue": "0", "widget": "text"}
  ],
  "dataPorts": [
    {"name": "in", "portType": "DataInPort", "type": "RTC::TimedFloat", "position": "LEFT"},
    {"name": "out", "portType": "DataOutPort", "type": "RTC::TimedLong", "position": "RIGHT"}
  ],
  "servicePorts": [
    {"name": "control", "interfaces": [
      {"name": "Controller", "direction": "Provided", "type": "RTC::ControllerService", "instanceName": "controller", "idlFile": "Controller.idl"}
    ]}
  ],
  "language": {"kind": "C++"}
}
```

```powershell
python .\json_to_rtc_xml.py "build/generated/<RTCName>/<RTCName>.json" "build/generated/<RTCName>/RTC.xml"
```

```powershell
.\cuirtcbuilder.bat -d "build/generated/<RTCName>" -f "build/generated/<RTCName>/RTC.xml"
```

```powershell
.\cuirtcbuilder.bat -d "build/generated/<RTCName>" -f "build/generated/<RTCName>/RTC.xml" -i "build/generated/<RTCName>/idl/Controller.idl"
```

[詳細な原文（英語）](../en/generation.md)

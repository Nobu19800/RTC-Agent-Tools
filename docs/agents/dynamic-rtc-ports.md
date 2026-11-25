# 接続先から DataPort を生成する RTC

## 対象と根拠

ExcelControlpy と OOo Calc は、GUI で接続先の DataPort を選ぶと、その型に対応する逆方向の DataPort を実行時に作成できる既存 RTC として扱う。ExcelControlpy の `MainWindow.py` は相手の `port.port_type` から方向を決める。OOo Calc の `CalcControl.py` は `mAddInPort` / `mAddOutPort` で接続先の型を解決し、`autoCon` 時は接続も行う。`CalcControl.py` は共通クラスなので、起動対象は OOo Calc 側のエントリーポイントから確認する。 [ExcelControlpy のソース](https://github.com/Nobu19800/openrtm_utils/tree/1429152/ExcelControlpy/ExcelControlpy)、[OOo Calc のソース](https://github.com/Nobu19800/OOoRTCs/blob/b779d50/OOoRTC/CalcControl.py)

## v2 設計生成時の自動設定

1. 選んだ RTC を `moduleKind: rtc`、既存実装として配置し、ソースの URL と確認したリビジョンを記録する。カタログ ID は実在する登録を確認できた場合に設定する。
2. 接続予定の相手のコンポーネント ID とポート ID を解決する。相手は方向と型が確認できる RTC DataPort とし、同じ型を選択した版の `CalcDataPort.py` の `GetDataType` / `GetDataSType` が扱えるか確認する。接続先が曖昧、型が不明、または未対応なら、設計上の未解決事項として記録する。
3. 相手が OutPort なら自分側に同型の InPort、相手が InPort なら同型の OutPort を作る。同じ相手ポートへの重複作成を避け、衝突しない安定した ID を付ける。表示用の名前は相手のインスタンス名・ポート名から決め、実際の生成名が確認できる場合はそれに合わせる。
4. 生成ポートを RTC の `data.ports` に追加し、出力から入力への `connectionType: data` の edge を作る。edge のハンドルには各ポートの ID を使う。たとえば `sensor/reading` が `RTC::TimedLong` の OutPort なら、ExcelControlpy 側に `RTC::TimedLong` の InPort を追加し、`sensor/reading → ExcelControlpy の InPort` と結ぶ。
5. RTSystemDesigner の **Implementation → Requirements**（`components[].data.implementation.requirements`）に、スプレッドシート側のポートごとに下記のセル設定を記入する。実行時生成であることや相手のポート ID などの補足は `data.implementation.notes` に記録する。登録したセッションを読み戻し、Requirements、生成ポートの方向・型、edge の両ハンドルが保持されていることを確認する。

## Requirements に記入する内容

ポートごとに、ポート名と方向、読み書きするシート名、開始セル（複数セルを使う場合は開始範囲）、セルを移動するかどうかを明記する。移動ありの場合は、移動の方向、幅、きっかけも記入する。確認できない設定は「未確定」と記入し、実行設定を作る前に確定する。

```text
ConsoleIn0out（InPort）: Sheet1!B1 に書き込み。セル移動なし。受信のたびに B1 を上書き。
ConsoleOut0in（OutPort）: Sheet1!B1 から読み出し。セル移動なし。B1 の値を送信。
```

入力を行単位で蓄積する例は「`ConsoleIn0out`（InPort）で `Sheet1!B1` から書き込み、1 件を書き込むたびに次の行へ 1 行進む（B1 → B2 → B3）」と記入する。標準の移動設定は開始列を固定し、処理後に行番号を 1 増やす。OutPort の移動は読み出し・送信処理に伴うため、入出力を同じセルに割り当てて受信ごとに同期させたい場合は、出力のトリガーも要件に記載して実装の動作を確認する。

## 実行時

1. **ExcelControlpy** は Microsoft Excel がインストールされた Windows 上で起動する。OpenRTM-aist Python、omniORBpy、PyQt5、pywin32 と、プロジェクトの `SpreadSheet.idl` に対応する Python バインディングを用意する。 `ExcelControlpy.py` を起動し、設定画面と対象ブックを開く。OpenRTM-aist の型付きリスナーを使う版では、`CalcControl.py` の `DataListener` がデシリアライズ済みデータを受け取り、ステータスとデータを返す版を使用する。経過時間表示が有効な場合は、そのセル（既定は `Sheet1!A1`）をデータ用セルから外す。
2. **LibreOffice Calc** は LibreOffice と Python UNO、OpenRTM-aist Python を同じ実行環境で用意する（WSL2 で実行可）。OOoRTCs の `OOoCalcRTC.py`（`OOoCalcControl`）を、対象の Calc 文書に接続する経路で起動する。セル操作には Calc の UNO 接続を使う。
3. 両方とも、接続先 RTC を同じ名前サービスに登録してから対象ポートを選ぶ。GUI または `mAddInPort` / `mAddOutPort` でポートを作るときに、Requirements のシート名、開始列、開始行、範囲の終端列（単一セルは空欄）、移動フラグ（なしなら偽、ありなら真）を反映する。
4. RTC をアクティブ化して試験値を送り、対応セルの値と受信側 RTC の値を照合する。セル移動を指定した場合は少なくとも異なる 2 値を送信し、指定した順にセルを移動したことも確認する。固定の場合は同じセルが更新されることを確認する。

確定設計から接続先とシート設定を取り出し、対象 RTC の GUI またはソースで確認済みの設定経路を使って動的ポートを作る。ポート生成後、実際の公開名・方向・型を照合する。`autoCon` が作った接続は接続バッチで重複作成せず、接続状態と実データを確認する。自動接続を使わない構成ではポートが公開されてから通常の接続処理を行う。

設計 JSON のポートは図に表示される予定ポートである。実行時の確認結果は設計 ID と実ポート名の対応として記録する。

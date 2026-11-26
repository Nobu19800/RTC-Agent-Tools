# RTCs that create DataPorts from peer ports

ExcelControlpy and LibreOffice Calc RTCs can create a port with the peer's type and opposite direction. Read the implementation entry point and check that the type is supported by the selected revision. For LibreOffice use `OOoCalcRTC.py`; `CalcControl.py` provides common behavior.

1. Place the module as an existing RTC and record its source and revision.
2. Resolve the peer's component ID, port ID, direction, and type. Add a corresponding planned port with a stable ID and an ordinary data edge. Create one port for each distinct peer port and preserve known generated names.
3. In **Implementation → Requirements**, record sheet name, first cell or range, read/write direction, whether advancing is enabled, and its direction, interval and trigger. Mark missing settings unresolved. For example, a fixed input can overwrite `Sheet1!B1`; an advancing input can write to B1, B2 and B3 on consecutive samples. Check the saved design round trip.
4. Use Windows Excel with pywin32, PyQt5, and the matching OpenRTM Python and IDL bindings for ExcelControlpy. For Calc use LibreOffice UNO and OpenRTM Python in the same environment. Check the Excel listener API against the installed SDK. Keep the elapsed-time cell, typically A1, separate from sample data.
5. Register peers, create ports through the GUI or `mAddInPort` / `mAddOutPort`, then verify the actual names, types, and connections. Avoid duplicating connectors created by `autoCon`. Verify values and, when enabled, cell advancement with at least two distinct inputs. Check output triggers separately when input and output share a range.

## Commands and formats from the original guide

```text
ConsoleIn0out（InPort）: Sheet1!B1 に書き込み。セル移動なし。受信のたびに B1 を上書き。
ConsoleOut0in（OutPort）: Sheet1!B1 から読み出し。セル移動なし。B1 の値を送信。
```

[Detailed original guide (Japanese)](../ja/dynamic-rtc-ports.md)

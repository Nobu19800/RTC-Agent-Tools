# Hakoniwa DataPort interface and serializer

Use the custom interface and a type-specific serializer for each RTC–Hakoniwa DataPort edge. Preserve the typed RTC endpoint and map PDU type, robot, channel, capacity and binary layout. Keep module registration and connector creation out of RTC lifecycle callbacks. Verify actual binding and transfer before reporting the connection operational.

For an RTC/Hakoniwa edge use `dataport.interface_type: hakoniwa` and a type-specific `dataport.marshaling_type`. Record the RTC type and direction, PDU schema, robot, channel, capacity, format, field conversion, byte order, endpoint ownership, and verification status in the connection contract. Resolve mismatches and unimplemented bindings before runtime.

Keep typed ports and business logic in the RTC. Load transport modules via `manager.modules.load_path` and `manager.modules.preload` in rtc.conf. Supply robot, channel, capacity and codec settings through deployment/connection settings. Verify whether the rtshell version can create the single-ended binding. If it cannot, use a verified rtc.conf preconnection or external configuration-driven connector. Preserve normal CORBA behavior for RTC-to-RTC edges.

Treat PDU layouts independently. A 48-byte data payload and a 72-byte native format require an explicit mapping rather than interchangeable buffers. Confirm headers, offsets and padding against the selected native API, not just names or declared type. Keep serialization separate from endpoint access. First test codec round trips and failure cases, then verify factory registration, binding, runtime ownership, and actual native data transfer. Report each level separately.

See the [implementation and test example](../../../examples/hakoniwa_transport/README.md) and [verification requirements](verification.md).

## Commands and formats from the original guide

```text
RTCの型付きDataPort
  -> 型別シリアライザ（RTC/IDL型 <-> 箱庭PDUバイト列）
  -> 共通インターフェース（PDUバイト列のread/write）
  -> hakopy / 箱庭共有メモリ
```

```ini
manager.modules.load_path: /mnt/c/workspace/codex-test3/RTC-Agent-Tools/build/generated/common
manager.modules.preload: HakoniwaTransport.py, DroneSerializers.py
```

[Detailed original guide (Japanese)](../ja/hakoniwa-serializer.md)

# Static analysis and unit tests for the C++ drone control RTC

[日本語](../drone-adapter-cpp-checks.md)

The C++ RTC accepts the standard TkJoyStick `RTC::TimedFloatSeq` input and sends movement, takeoff, and landing requests to the Hakoniwa Drone legacy API. It uses a serializer and deserializer with the Foundation C API. Its OpenRTM interface exposes the `joystick` input port. The Python version also exposes the Hakoniwa-side typed ports.

Run the [build, analyzer, and coverage commands](../drone-adapter-cpp-checks.md) in Ubuntu 24.04 or WSL2 from the RTC-Agent-Tools root. Set the Foundation path to your installation.

Required software:

- OpenRTM-aist 2.1
- Hakoniwa Foundation
- Clang 18 and its profile runtime
- LLVM 18 `llvm-profdata` and `llvm-cov`
- CMake
- GoogleTest

| Check | Results from 2026-11-27 |
| --- | --- |
| C++ RTC build | Passed |
| Clang Static Analyzer | 0 diagnostics |
| GoogleTest | 5 passed, 0 failed |
| LLVM line coverage | 46 of 46 lines (100%) in the control and PDU conversion code |
| LLVM branch coverage | 40 of 40 branches (100%) in the same code |

The tests cover input and movement limits, response handling, PDU padding, and rejection of invalid metadata. Coverage applies to `Control.hpp` and `Pdu.hpp`. Live RTC lifecycle and simulator communication require separate integration checks.

## Windows unit tests

Required software and files:

- Visual Studio 2022 with MSVC and a Windows SDK
- CMake and CTest
- GoogleTest source tree
- Hakoniwa Foundation PDU headers under `include/hakoniwa/pdu`

Follow the [Windows PowerShell commands](../drone-adapter-cpp-checks.md#windows-で単体テストを実行する) from the repository root. The test-only configuration uses `DRONE_BUILD_RTC=OFF` and needs only the Foundation headers. The verification copied the headers and GoogleTest sources from WSL2 and compiled a native Windows executable with MSVC 19.44 in x64 Release mode.

**GoogleTest passed all 5 cases.** CTest reported one passing test executable. Coverage was not collected on Windows.

## Simulator integration check

Both RTCs were activated in WSL2 after connecting `TkJoyStick0.pos` to `DroneJoystickAdapterCpp0.joystick`. Passing `[60, 0]` to the standard TkJoyStick input callback moved the simulator's `Drone/pos` X coordinate from approximately 0.000 m to 0.262 m. Windows fetched the Three.js configuration over HTTP and received a binary `Drone` frame over WebSocket v2. Mouse interaction and browser rendering were outside the scope of this check.

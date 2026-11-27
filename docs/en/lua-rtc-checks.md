# Lua RTC static analysis and unit tests

[日本語](../lua-rtc-checks.md)

`TimedLongLimiter` accepts `RTC::TimedLong`, clamps the value to −100 through 100, and publishes the result with the original timestamp. It can sit between ConsoleIn and ConsoleOut using ordinary DataPort connections with matching types.

Run the following from the RTC-Agent-Tools root in Ubuntu or WSL2 with Lua 5.1 and LuaRocks. For RTC deployment, follow the RTM-Lua installation section in AGENTS.md.

```bash
# Install the tools in the same Lua 5.1 LuaRocks tree
luarocks --lua-version=5.1 --local install luacheck
luarocks --lua-version=5.1 --local install luaunit
luarocks --lua-version=5.1 --local install luacov
eval "$(luarocks --lua-version=5.1 --local path)"

# Run from the RTC-Agent-Tools root
src="$(realpath examples/lua-rtc-checks)"
luacheck --std lua51 "$src/TimedLongLimiter.lua" "$src/limit.lua" "$src/test_limit.lua"

# Collect coverage in a fresh temporary directory
run="$(mktemp -d)"
cp "$src/.luacov" "$run/"
(
    cd "$run"
    export LUA_PATH="$src/?.lua;${LUA_PATH:-;}"
    lua5.1 -lluacov "$src/test_limit.lua"
    luacov
    cat luacov.report.out
)
```

## Results from 2026-11-27

| Check | Result |
| --- | --- |
| Luacheck | 3 files, 0 warnings, 0 errors |
| LuaUnit | 3 passed, 0 failed |
| LuaCov | 8 of 8 executable lines (100%) in `limit.lua` |

The tests cover lower and upper saturation, including boundary and in-range values. Coverage measures the limiter logic. The run used Lua and LuaUnit extracted from Ubuntu packages and Luacheck and LuaCov from their upstream source trees.

## Live RTC communication on Windows and WSL2

The agent runs the following steps. See [AGENTS.md](../../AGENTS.md#openrtm-lua-rtm-lua) for the CORBA endpoint fix and the WSL2 UUID pin.

1. On Windows, extract the official RTM-Lua 0.5.0 x64, Lua 5.1, `corba_cdr` distribution. From its `examples` directory, set `LUA_PATH=..\lua\?.lua;.\?.lua;` and `LUA_CPATH=..\clibs\?.dll;`. Place both limiter source files there and launch each RTC with `..\bin\lua.exe <RTC>.lua -f <RTC>.conf`. Add `-e 'io.stdout:setvbuf("no")'` before the script name when capturing unbuffered logs.
2. In WSL2, install RTM-Lua 0.5-3 in a Lua 5.1 user rock tree. This run used the official checkout's rockspec after the published source rock failed to unpack. Pin UUID to `0.2-1` and add the tree and limiter source directory to the Lua search path. From the upstream `examples` directory, launch each RTC with `lua5.1 <script path> -f <RTC>.conf`.
3. Set the shared NameService and a distinct CORBA endpoint in each config. This run used `127.0.0.1:2809` from Windows and the Windows WSL gateway on port `2809` from WSL2. The RTC ports were `2821` through `2823`, with `naming.formats: %n.rtc`.
4. Connect `ConsoleIn0.out → TimedLongLimiter0.in` and `TimedLongLimiter0.out → ConsoleOut0.in`. This run used `PortService.connect` with `corba_cdr`, `push`, and `flush`. Activate ConsoleOut, the limiter, then ConsoleIn.
5. Enter the test integers, check the ConsoleOut log, and stop the three RTCs. Keep the shared NameService running.

| Environment | ConsoleIn input | ConsoleOut output |
| --- | --- | --- |
| Native Windows | −250, −100, 0, 42, 100, 250 | −100, −100, 0, 42, 100, 100 |
| WSL2 Ubuntu | −250, −100, 0, 42, 100, 250 | −100, −100, 0, 42, 100, 100 |

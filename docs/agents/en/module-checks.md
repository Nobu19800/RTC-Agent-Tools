# On-request module checks

Run static analysis or unit tests for a new module only when the user explicitly asks for that check. Keep tests out of automatic workflows and default builds. If requested unit tests are absent, create core tests that implement the approved behavioral requirements and run independently of OpenRTM or hardware.

| Language | Static analysis | Unit tests and coverage |
| --- | --- | --- |
| C++ | Clang Static Analyzer, for example `clang-tidy -p build/analysis --checks='-*,clang-analyzer-*' <sources>` with actual compilation settings and generated IDL. | Run GoogleTest against a separate Clang coverage build. Instrument compilation with `-fprofile-instr-generate -fcoverage-mapping`, link the profiling runtime, write a fresh `LLVM_PROFILE_FILE`, merge with `llvm-profdata merge -sparse`, and display `llvm-cov report`. |
| Python | Run both `python -m bandit <sources>` and `python -m flake8 <sources>` in the target environment. | Run `python -m pytest tests --cov=src --cov-report=term-missing` with pytest-cov, adapting paths to the module. |
| Lua | Run `luacheck <sources>` with the target Lua version and project globals. | Use LuaUnit and a fresh LuaCov run. Run `lua -lluacov tests/test_example.lua`, then `luacov`, and display `luacov.report.out`. Ensure the runner returns the LuaUnit result as its exit status. |

Report commands, scope, findings, passed/failed counts and the actual coverage report. Use a threshold only if requested. Explain unavailable reports or missing dependencies.

[Detailed original guide (Japanese)](../ja/module-checks.md)

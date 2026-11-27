# Static analysis and unit tests for the drone control RTC

[日本語](../drone-adapter-checks.md)

[C++ static analysis and unit tests](drone-adapter-cpp-checks.md)

[Lua RTC static analysis and unit tests](lua-rtc-checks.md)

These checks target the generated `DroneJoystickAdapter.py` from the [RTC–Hakoniwa integration guide](rtc-hakoniwa.md). Run them from the RTC-Agent-Tools root after generating the adapter.

> Run Bandit and flake8 on the drone control adapter, then run pytest and show coverage.

The agent runs these PowerShell commands. Run the unit tests independently of the static analysis exit codes.

```powershell
python -m venv work/drone-adapter-checks/venv
$py = "work/drone-adapter-checks/venv/Scripts/python.exe"
& $py -m pip install bandit==1.9.4 flake8==7.5.0 pytest==9.2.0 pytest-cov==7.1.0
$src = "build/generated/DroneJoystickAdapter/DroneJoystickAdapter.py"
& $py -m bandit $src
& $py -m flake8 --statistics --count $src
$env:COVERAGE_FILE = "work/drone-adapter-checks/.coverage"
& $py -m pytest examples/hakoniwa_transport/test_drone_joystick_adapter.py --cov=DroneJoystickAdapter --cov-report=term-missing -q
```

## Results from 2026-11-27

| Check | Result |
| --- | --- |
| Bandit | 0 findings, exit code 0 |
| flake8 | 31 findings, exit code 1. 22 line length, 7 blank line, and 2 indentation findings |
| pytest | 11 passed, 0 failed |
| Line coverage | 84 of 158 executable lines in the adapter (53%) |

The tests cover movement limits, centered, stale and invalid input, takeoff and landing requests, successful, rejected and timed-out responses, and serializer padding and round trips. OpenRTM and Hakoniwa dependencies are replaced with test doubles. Use the integration guide to verify live RTC registration, Hakoniwa communication, and GUI interaction. The flake8 findings are recorded as observed.

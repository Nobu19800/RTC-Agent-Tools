# Choose and run OpenRTM sample RTCs

Search [the sample catalog](../../../catalog/openrtm_samples_catalog.json) alongside the general RTC catalog. For example, run `python rtc_search.py catalog/openrtm_samples_catalog.json "ConsoleIn Python" --json` and verify the exact name and language. Preserve the selected source revision and launch information in the design. Designer lists the language with the sample name and prefers the sample when both catalogs contain the same name and language.

After approval, inspect `launch.kind: installed` and honor explicit deployment settings. C++ uses `launch.platforms.windows` or `launch.platforms.linux` for the actual target. Python and Java use `launch.deployment`. Resolve the executable, working directory, arguments and classpath against the installed environment, and check the actual files and dependencies. For WSL2, select Linux even when viewing Designer from Windows. `launch: null` means no installed launch configuration is provided.

Apply the final design's naming service and execution-context settings. Verify registration, connections, activation, data and shutdown. [Launch reference meanings](../../../profiles/openrtm-samples/README.md) · [Runtime](runtime.md)

## Commands and formats from the original guide

```powershell
python rtc_search.py catalog/openrtm_samples_catalog.json "ConsoleIn Python" --json
```

[Detailed original guide (Japanese)](../ja/openrtm-samples.md)

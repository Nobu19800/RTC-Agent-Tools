param(
    [string]$OpenRTMDirectory = $env:RTM_ROOT,
    [string]$Generator = 'Visual Studio 17 2022'
)
$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent $PSScriptRoot
if (-not $OpenRTMDirectory) { throw 'Set RTM_ROOT or pass -OpenRTMDirectory.' }
$session = Get-Content -LiteralPath (Join-Path $workspace 'build/system/final-session.json') -Raw | ConvertFrom-Json
$results = @()
foreach ($node in $session.nodes) {
    if ($node.data.origin -ne 'generated') { continue }
    $rtcName = $node.data.name
    if ($rtcName -notmatch '^[A-Za-z][A-Za-z0-9_]*$') { throw 'Invalid RTC name.' }
    $sourcePath = Join-Path $workspace "build/generated/$rtcName"
    $binaryPath = Join-Path $workspace "build/system/checks/$rtcName"
    $configureLog = Join-Path $workspace "work/configure-$rtcName.log"
    $buildLog = Join-Path $workspace "work/build-$rtcName.log"
    & cmake -S $sourcePath -B $binaryPath -G $Generator -A x64 "-DOpenRTM_DIR=$OpenRTMDirectory/cmake" '-DCMAKE_CXX_FLAGS=/utf-8' *> $configureLog
    $configured = $LASTEXITCODE
    $compiled = $null
    if ($configured -eq 0) {
        & cmake --build $binaryPath --config Release *> $buildLog
        $compiled = $LASTEXITCODE
    }
    $results += [PSCustomObject]@{ name=$rtcName; configureExit=$configured; buildExit=$compiled; configureLog=$configureLog; buildLog=$buildLog }
}
$results | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $workspace 'build/system/build-checks.json') -Encoding utf8
$results | Format-Table name,configureExit,buildExit
if (@($results | Where-Object { $_.configureExit -ne 0 -or $_.buildExit -ne 0 }).Count -gt 0) { exit 1 }

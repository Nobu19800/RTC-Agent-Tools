param(
    [string]$OpenRtmRoot = 'C:/Program Files/OpenRTM-aist/2.1.0',
    [string]$OpenCvRoot = 'C:/Program Files/OpenRTM-aist/2.1.0/OpenCV4.13.0'
)
$ErrorActionPreference = 'Stop'
# Windows PowerShell 5 wraps redirected native stderr as error records. Keep
# diagnostics in logs and decide failure by the native exit code, not stderr.
function Invoke-LoggedCommand {
    param([string]$Command, [string[]]$CommandArgs, [string]$Log)
    $ErrorActionPreference = 'Continue'
    & $Command @CommandArgs *> $Log
    $nativeCode = $LASTEXITCODE
    if ($nativeCode -ne 0) { throw "$Command exited $nativeCode; see $Log" }
}
$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot
$savedPath = $env:PATH
try {
    New-Item -ItemType Directory -Force work | Out-Null
    $rtcNames = @('ColorObjectDetector', 'PlaneTargetProjector', 'ColorActionPlanner', 'ArmActionExecutor')
    foreach ($rtcName in $rtcNames) {
        Invoke-LoggedCommand cmake @('-S', "build/generated/$rtcName", '-B', "build/system/checks/$rtcName",
            '-G', 'Visual Studio 17 2022', '-A', 'x64', "-DOpenRTM_DIR=$OpenRtmRoot/cmake",
            "-DOpenCV_DIR=$OpenCvRoot", '-DCMAKE_CXX_FLAGS=/utf-8') "work/configure-implemented-$rtcName.log"
        Invoke-LoggedCommand cmake @('--build', "build/system/checks/$rtcName", '--config', 'Release') "work/build-implemented-$rtcName.log"
        Write-Output "Built $rtcName (DLL and executable)"
    }
    Invoke-LoggedCommand cmake @('-S', 'build/generated/tests', '-B', 'build/system/checks/ManipulationCoreTests',
        '-G', 'Visual Studio 17 2022', '-A', 'x64', "-DOpenCV_DIR=$OpenCvRoot", '-DCMAKE_CXX_FLAGS=/utf-8') 'work/configure-core-tests.log'
    Invoke-LoggedCommand cmake @('--build', 'build/system/checks/ManipulationCoreTests', '--config', 'Release') 'work/build-core-tests.log'
    $env:PATH = "$OpenCvRoot/x64/vc16/bin;$savedPath"
    Invoke-LoggedCommand ctest @('--test-dir', 'build/system/checks/ManipulationCoreTests', '-C', 'Release', '--output-on-failure') 'work/core-tests.log'
    Get-Content work/core-tests.log
    & python scripts/report_manipulation_build.py
    if ($LASTEXITCODE -ne 0) { throw 'Implementation evidence recording failed' }
} finally {
    $env:PATH = $savedPath
    Pop-Location
}

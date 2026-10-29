param(
    [Parameter(Mandatory=$true)][ValidateSet('Start','Check','Cleanup')][string]$Mode,
    [Parameter(Mandatory=$true)][string]$Node,
    [string]$Settings = ''
)
# Process management only: no rtshell, CORBA, port or RTC state operations here.
$ErrorActionPreference = 'Stop'
try {
    if (-not $Settings) { $Settings = Join-Path $PSScriptRoot 'runtime-settings.json' }
    $config = Get-Content -LiteralPath $Settings -Raw | ConvertFrom-Json
    $rtc = @((@($config.nodes) + @($config.infrastructure)) | Where-Object id -eq $Node)
    if ($rtc.Count -ne 1) { throw 'Unknown process definition.' }
    $rtc = $rtc[0]
    $stateDirectory = $config.processDirectory
    New-Item -ItemType Directory -Force $stateDirectory | Out-Null
    $recordPath = Join-Path $stateDirectory ($Node + '-pid.json')
    $process = $null
    if (Test-Path -LiteralPath $recordPath) {
        $record = Get-Content -LiteralPath $recordPath -Raw | ConvertFrom-Json
        $candidate = Get-Process -Id $record.pid -ErrorAction SilentlyContinue
        if ($candidate) {
            if ($candidate.StartTime.ToUniversalTime().Ticks -ne $record.startTicks -or $candidate.Path -ne $record.executable) {
                throw 'PID ownership no longer matches; refusing to operate on another process.'
            }
            $process = $candidate
        }
    }
    if ($Mode -eq 'Check') {
        if (-not $process) { throw 'No live process owned by these batches.' }
        exit 0
    }
    if ($Mode -eq 'Cleanup') {
        if ($process -and -not $process.WaitForExit(2000)) {
            Stop-Process -Id $process.Id -ErrorAction Stop
            if (-not $process.WaitForExit(15000)) { throw 'Owned manager did not terminate.' }
        }
        if (Test-Path -LiteralPath $recordPath) { Remove-Item -LiteralPath $recordPath }
        exit 0
    }
    if ($process) { throw 'Owned process already runs; inspect registration instead of starting a duplicate.' }
    if ($Node -eq 'nameserver') { New-Item -ItemType Directory -Force $rtc.workingDirectory | Out-Null }
    foreach ($property in $rtc.environment.PSObject.Properties) {
        Set-Item -LiteralPath ('Env:' + $property.Name) -Value $property.Value
    }
    New-Item -ItemType Directory -Force $config.logDirectory | Out-Null
    $startArguments = @{
        FilePath = $rtc.command[0]
        WorkingDirectory = $rtc.workingDirectory
        WindowStyle = 'Hidden'
        PassThru = $true
        RedirectStandardOutput = (Join-Path $config.logDirectory ($Node + '-stdout.log'))
        RedirectStandardError = (Join-Path $config.logDirectory ($Node + '-stderr.log'))
    }
    if ($rtc.argumentLine) { $startArguments.ArgumentList = $rtc.argumentLine }
    $process = Start-Process @startArguments
    $record = [PSCustomObject]@{
        pid = $process.Id
        startTicks = $process.StartTime.ToUniversalTime().Ticks
        executable = $process.Path
    }
    $record | ConvertTo-Json | Set-Content -LiteralPath $recordPath -Encoding utf8
    Write-Output ('Started ' + $Node + ', PID=' + $process.Id)
} catch {
    Write-Error $_
    exit 1
}

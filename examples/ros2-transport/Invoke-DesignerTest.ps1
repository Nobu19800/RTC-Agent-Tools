param(
    [string]$SessionId,
    [int]$Port = 5173
)

$ErrorActionPreference = 'Stop'
$repository = Join-Path $PSScriptRoot '../..'
Push-Location -LiteralPath $repository
try {
    $client = @('-B', 'scripts/local_designer_session.py', '--port', $Port)
    if (-not $SessionId) {
        $registered = python @client create examples/ros2-transport/session.json
        if ($LASTEXITCODE -ne 0) { throw 'Local registration failed.' }
        $session = $registered | ConvertFrom-Json
        $SessionId = $session.sessionId
        Write-Host "Designer: $($session.designerUrl)"
    } else {
        Write-Host "Designer: http://127.0.0.1:$Port/RTSystemDesigner/?session=$SessionId"
    }
    $design = python @client get $SessionId
    if ($LASTEXITCODE -ne 0) { throw 'Local session retrieval failed.' }
    $design | wsl.exe --exec bash -c 'source /opt/ros/jazzy/setup.bash && exec python3 -B examples/ros2-transport/verify_round_trip.py'
    if ($LASTEXITCODE -ne 0) { throw 'ROS2Transport smoke test failed.' }
} finally {
    Pop-Location
}

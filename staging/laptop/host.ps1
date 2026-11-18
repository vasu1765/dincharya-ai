[CmdletBinding()]
param([ValidateSet('Power','Supervise','Observe','Ollama')][string]$Mode='Power',
      [string]$Distro='Ubuntu',[string]$Checkout,[string]$Python='python3',
      [string]$Revision,[string]$Daemon)
$ErrorActionPreference='Stop'
if ($Mode -eq 'Power') {
    foreach ($arguments in @('/a','/getactivescheme','/query')) {
        & powercfg.exe $arguments
        if ($LASTEXITCODE -ne 0) { throw 'Power diagnostics unavailable' }
    }
    return
}
if ($Mode -eq 'Ollama') {
    $timer=[Diagnostics.Stopwatch]::StartNew()
    $response=Invoke-RestMethod -TimeoutSec 90 -Method Post -Uri 'http://127.0.0.1:11434/api/generate' -ContentType 'application/json' -Body '{"model":"qwen2.5:3b","prompt":"Reply OK","stream":false,"options":{"num_predict":4}}'
    $models=(Invoke-RestMethod -TimeoutSec 5 'http://127.0.0.1:11434/api/ps').models
    @{complete=($response.done -eq $true); milliseconds=$timer.ElapsedMilliseconds; gpuResident=[bool]($models | Where-Object {$_.name -eq 'qwen2.5:3b' -and $_.size_vram -gt 0})} | ConvertTo-Json -Compress
    return
}
if ($Revision -notmatch '^[0-9a-f]{40}$' -or $Daemon -notmatch '^[a-zA-Z0-9:-]+$' -or $Checkout -notmatch '^/[A-Za-z0-9_./-]+$' -or $Python -notmatch '^[A-Za-z0-9_./-]+$' -or $Distro -notmatch '^[A-Za-z0-9_-]+$') { throw 'Explicit approved host paths and pins required' }
function Invoke-Stage($action,$seconds) {
    $arguments=@('-d',$Distro,'--cd',$Checkout,'--exec',$Python,'-B','staging/laptop/control.py',$action,'--daemon',$Daemon,'--revision',$Revision)
    $p=Start-Process -FilePath 'wsl.exe' -ArgumentList $arguments -PassThru -NoNewWindow
    if (-not $p.WaitForExit(1000*$seconds)) { $p.Kill(); throw 'WSL operation timed out' }
    return ($p.ExitCode -eq 0)
}
if ($Mode -eq 'Observe') { if (!(Invoke-Stage status 20)) {throw 'Staging unhealthy'}; return }
$mutex=New-Object Threading.Mutex($false,'Local\DincharyaLaptopStaging')
if (!$mutex.WaitOne(0)) {throw 'Supervisor already active'}
try {
    $desktop=Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'
    if (!(Get-Process -Name 'Docker Desktop' -ErrorAction SilentlyContinue)) {
        if (!(Test-Path -LiteralPath $desktop -PathType Leaf)) {throw 'Docker Desktop missing'}
        Start-Process -FilePath $desktop
    }
    $ready=$false
    for ($attempt=0;$attempt -lt 5;$attempt++) {
        if (Invoke-Stage start 150) {$ready=$true; break}
        Start-Sleep -Seconds 10
    }
    if (!$ready) {throw 'Staging startup failed'}
    $misses=0
    while ($true) {
        Start-Sleep -Seconds 15
        if (Invoke-Stage status 20) {$misses=0} else {$misses++}
        if ($misses -ge 2) {throw 'Two health checks failed; owner review required'}
    }
} finally { $mutex.ReleaseMutex(); $mutex.Dispose() }

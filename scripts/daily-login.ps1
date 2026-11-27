# Invoke from an explicitly approved interactive-login task. Registration is separate.
param([Parameter(Mandatory=$true)][string]$Distribution,
      [Parameter(Mandatory=$true)][string]$Checkout,
      [Parameter(Mandatory=$true)][string]$Revision,
      [Parameter(Mandatory=$true)][string]$ReleaseEnvironment)
$ErrorActionPreference = 'Stop'
if ($Revision -notmatch '^[0-9a-f]{40}$' -or !$Checkout.StartsWith('/') -or !$ReleaseEnvironment.StartsWith('/')) { throw 'Invalid release inputs' }
for ($n=0; $n -lt 30; $n++) {
    & wsl.exe -d $Distribution --exec timeout 3 docker info --format '{{.ID}}' *> $null
    if ($LASTEXITCODE -eq 0) {
        & wsl.exe -d $Distribution --cd $Checkout --exec bash scripts/daily-host.sh $Revision $ReleaseEnvironment
        exit $LASTEXITCODE
    }
    Start-Sleep -Seconds 2
}
throw 'Docker Desktop or WSL unavailable'

$ErrorActionPreference = "Stop"

$projectRoot = "D:\SiSennKoToBa"
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$artifactDir = Join-Path $projectRoot "artifacts"
$projectCache = Join-Path $projectRoot ".cache\paddlenlp"
$legacyCache = Join-Path $env:USERPROFILE ".paddlenlp"
$verificationOutput = Join-Path $artifactDir "environment_verification.log"
$verificationError = Join-Path $artifactDir "environment_verification.stderr.log"

Set-Location -LiteralPath $projectRoot
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PPNLP_HOME = $projectCache

New-Item -ItemType Directory -Path $projectCache -Force | Out-Null

if (Test-Path -LiteralPath $legacyCache) {
    Get-ChildItem -LiteralPath $legacyCache -Force | ForEach-Object {
        Move-Item -LiteralPath $_.FullName -Destination $projectCache
    }
    if (-not (Get-ChildItem -LiteralPath $legacyCache -Force)) {
        Remove-Item -LiteralPath $legacyCache
    }
}

$verificationProcess = Start-Process `
    -FilePath $venvPython `
    -ArgumentList @("-B", (Join-Path $projectRoot "scripts\verify_environment.py")) `
    -NoNewWindow `
    -Wait `
    -PassThru `
    -RedirectStandardOutput $verificationOutput `
    -RedirectStandardError $verificationError

if (Test-Path -LiteralPath $verificationError) {
    $errorText = Get-Content -LiteralPath $verificationError -Raw
    if ($errorText) {
        Add-Content -LiteralPath $verificationOutput -Value "`n[stderr]`n$errorText"
    }
}
if ($verificationProcess.ExitCode -ne 0) {
    throw "Environment verification failed with exit code $($verificationProcess.ExitCode)"
}

$installedVersionsPath = Join-Path $artifactDir "installed_versions.json"
$installedVersions = Get-Content -LiteralPath $installedVersionsPath -Raw | ConvertFrom-Json
$installedVersions.modelCache = $projectCache
$installedVersions.modelCacheBytes = (Get-ChildItem -LiteralPath $projectCache -Recurse -File |
    Measure-Object -Property Length -Sum).Sum
$installedVersions | ConvertTo-Json |
    Set-Content -LiteralPath $installedVersionsPath -Encoding UTF8

@{
    status = "success"
    completedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss zzz")
    verification = "CPU Taskflow inference succeeded after model cache relocation"
} | ConvertTo-Json |
    Set-Content -LiteralPath (Join-Path $artifactDir "setup_status.json") -Encoding UTF8

$ErrorActionPreference = "Stop"

$projectRoot = "D:\SiSennKoToBa"
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$artifactDir = Join-Path $projectRoot "artifacts"
$stdoutPath = Join-Path $artifactDir "schema_v1_run.log"
$stderrPath = Join-Path $artifactDir "schema_v1_run.stderr.log"

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PPNLP_HOME = Join-Path $projectRoot ".cache\paddlenlp"

$process = Start-Process `
    -FilePath $venvPython `
    -ArgumentList @("-B", (Join-Path $projectRoot "scripts\run_schema_v1.py")) `
    -NoNewWindow `
    -Wait `
    -PassThru `
    -RedirectStandardOutput $stdoutPath `
    -RedirectStandardError $stderrPath

if (Test-Path -LiteralPath $stderrPath) {
    $errorText = Get-Content -LiteralPath $stderrPath -Raw
    if ($errorText) {
        Add-Content -LiteralPath $stdoutPath -Value "`n[stderr]`n$errorText"
    }
}

if ($process.ExitCode -ne 0) {
    throw "Schema v1 zero-shot run failed with exit code $($process.ExitCode)"
}

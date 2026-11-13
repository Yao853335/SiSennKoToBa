$ErrorActionPreference = "Stop"

$projectRoot = "D:\SiSennKoToBa"
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$mirror = "https://pypi.tuna.tsinghua.edu.cn/simple"
$artifactDir = Join-Path $projectRoot "artifacts"
$thirdPartyDir = Join-Path $projectRoot "third_party"
$traditionalRepo = Join-Path $thirdPartyDir "Information-Extraction-Chinese"
$logPath = Join-Path $projectRoot "logs\complete_setup.log"
$zipPath = Join-Path $artifactDir "Information-Extraction-Chinese-master.zip"

Set-Location -LiteralPath $projectRoot
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$ProgressPreference = "SilentlyContinue"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PPNLP_HOME = Join-Path $projectRoot ".cache\paddlenlp"
$env:GIT_TERMINAL_PROMPT = "0"

Start-Transcript -Path $logPath -Force

try {
    Write-Host "[1/4] Completing traditional-model source download"
    $traditionalReadme = Join-Path $traditionalRepo "README.md"
    if (-not (Test-Path -LiteralPath $traditionalReadme)) {
        if (Test-Path -LiteralPath $traditionalRepo) {
            $suffix = Get-Date -Format "yyyyMMdd_HHmmss"
            $partialPath = Join-Path $thirdPartyDir "_partial_Information-Extraction-Chinese_$suffix"
            Move-Item -LiteralPath $traditionalRepo -Destination $partialPath
            Write-Host "Moved incomplete Git checkout to $partialPath"
        }

        Invoke-WebRequest `
            -Uri "https://github.com/crownpku/Information-Extraction-Chinese/archive/refs/heads/master.zip" `
            -OutFile $zipPath
        Expand-Archive -LiteralPath $zipPath -DestinationPath $thirdPartyDir -Force
        $extractedRepo = Join-Path $thirdPartyDir "Information-Extraction-Chinese-master"
        Move-Item -LiteralPath $extractedRepo -Destination $traditionalRepo
        Remove-Item -LiteralPath $zipPath
    }

    Write-Host "[2/4] Recording package and repository versions"
    & $venvPython -m pip install "chardet==5.2.0" -i $mirror
    if ($LASTEXITCODE -ne 0) {
        throw "chardet installation failed with exit code $LASTEXITCODE"
    }

    $versionsOutput = Join-Path $artifactDir "_versions_raw.json"
    $versionsError = Join-Path $artifactDir "_versions_error.log"
    $versionsProcess = Start-Process `
        -FilePath $venvPython `
        -ArgumentList @("-B", (Join-Path $projectRoot "scripts\collect_versions.py")) `
        -NoNewWindow `
        -Wait `
        -PassThru `
        -RedirectStandardOutput $versionsOutput `
        -RedirectStandardError $versionsError
    if ($versionsProcess.ExitCode -ne 0) {
        throw "Version collection failed with exit code $($versionsProcess.ExitCode)"
    }
    $versions = Get-Content -LiteralPath $versionsOutput -Raw | ConvertFrom-Json
    Remove-Item -LiteralPath $versionsOutput, $versionsError
    $paddleNlpCommit = (& git -C (Join-Path $thirdPartyDir "PaddleNLP") rev-parse HEAD 2>&1 | Out-String).Trim()

    [ordered]@{
        python = $versions.python
        pythonImplementation = $versions.pythonImplementation
        paddle = $versions.paddle
        paddlenlp = $versions.paddlenlp
        paddleNlpCommit = $paddleNlpCommit
        paddleNlpSourceTag = "v2.6.1"
        traditionalRepoSource = "GitHub master ZIP"
        traditionalRepoUrl = "https://github.com/crownpku/Information-Extraction-Chinese"
        modelCache = $env:PPNLP_HOME
        generatedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss zzz")
    } | ConvertTo-Json |
        Set-Content -LiteralPath (Join-Path $artifactDir "installed_versions.json") -Encoding UTF8

    Write-Host "[3/4] Running CPU Taskflow smoke test"
    $verificationOutput = Join-Path $artifactDir "environment_verification.log"
    $verificationError = Join-Path $artifactDir "environment_verification.stderr.log"
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

    Write-Host "[4/4] Environment verification completed"
    @{
        status = "success"
        completedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss zzz")
    } | ConvertTo-Json |
        Set-Content -LiteralPath (Join-Path $artifactDir "setup_status.json") -Encoding UTF8
}
catch {
    @{
        status = "failed"
        completedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss zzz")
        error = $_.Exception.Message
    } | ConvertTo-Json |
        Set-Content -LiteralPath (Join-Path $artifactDir "setup_status.json") -Encoding UTF8
    Write-Error $_
    throw
}
finally {
    Stop-Transcript
}

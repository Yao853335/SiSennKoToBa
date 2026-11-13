$ErrorActionPreference = "Stop"

$projectRoot = "D:\SiSennKoToBa"
$pythonSeed = "D:\python3.8.0\python.exe"
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$mirror = "https://pypi.tuna.tsinghua.edu.cn/simple"
$paddlenlpVersion = "2.6.1"
$paddleNlpTag = "v2.6.1"
$logDir = Join-Path $projectRoot "logs"
$artifactDir = Join-Path $projectRoot "artifacts"
$thirdPartyDir = Join-Path $projectRoot "third_party"

Set-Location -LiteralPath $projectRoot
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PIP_DISABLE_PIP_VERSION_CHECK = "1"
$env:PPNLP_HOME = Join-Path $projectRoot ".cache\paddlenlp"

New-Item -ItemType Directory -Path $logDir -Force | Out-Null
New-Item -ItemType Directory -Path $artifactDir -Force | Out-Null
New-Item -ItemType Directory -Path $thirdPartyDir -Force | Out-Null
New-Item -ItemType Directory -Path $env:PPNLP_HOME -Force | Out-Null

$transcriptPath = Join-Path $logDir "setup_environment.log"
Start-Transcript -Path $transcriptPath -Force

try {
    Write-Host "[1/5] Creating project virtual environment with Python 3.8"
    if (-not (Test-Path -LiteralPath $venvPython)) {
        & $pythonSeed -m venv (Join-Path $projectRoot ".venv")
        if ($LASTEXITCODE -ne 0) {
            throw "Virtual environment creation failed with exit code $LASTEXITCODE"
        }
    }

    & $venvPython -m pip install --upgrade "pip==24.0" "setuptools<70" wheel -i $mirror
    if ($LASTEXITCODE -ne 0) {
        throw "pip bootstrap failed with exit code $LASTEXITCODE"
    }

    Write-Host "[2/5] Installing PaddlePaddle 2.6.2 and PaddleNLP $paddlenlpVersion"
    & $venvPython -m pip install "paddlepaddle==2.6.2" -i $mirror
    if ($LASTEXITCODE -ne 0) {
        throw "PaddlePaddle installation failed with exit code $LASTEXITCODE"
    }

    & $venvPython -m pip install "paddlenlp==$paddlenlpVersion" -i $mirror
    if ($LASTEXITCODE -ne 0) {
        throw "PaddleNLP installation failed with exit code $LASTEXITCODE"
    }

    Write-Host "[3/5] Cloning reference repositories"
    $paddleNlpRepo = Join-Path $thirdPartyDir "PaddleNLP"
    if (-not (Test-Path -LiteralPath (Join-Path $paddleNlpRepo ".git"))) {
        git clone --depth 1 --branch $paddleNlpTag https://github.com/PaddlePaddle/PaddleNLP.git $paddleNlpRepo
        if ($LASTEXITCODE -ne 0) {
            throw "PaddleNLP clone failed with exit code $LASTEXITCODE"
        }
    }

    $traditionalRepo = Join-Path $thirdPartyDir "Information-Extraction-Chinese"
    if (-not (Test-Path -LiteralPath (Join-Path $traditionalRepo ".git"))) {
        git clone --depth 1 https://github.com/crownpku/Information-Extraction-Chinese.git $traditionalRepo
        if ($LASTEXITCODE -ne 0) {
            throw "Information-Extraction-Chinese clone failed with exit code $LASTEXITCODE"
        }
    }

    Write-Host "[4/5] Recording package and repository versions"
    $versions = [ordered]@{
        python = (& $venvPython --version 2>&1 | Out-String).Trim()
        paddle = (& $venvPython -c "import paddle; print(paddle.__version__)" 2>&1 | Out-String).Trim()
        paddlenlp = (& $venvPython -c "import paddlenlp; print(paddlenlp.__version__)" 2>&1 | Out-String).Trim()
        paddleNlpCommit = (& git -C $paddleNlpRepo rev-parse HEAD 2>&1 | Out-String).Trim()
        traditionalRepoCommit = (& git -C $traditionalRepo rev-parse HEAD 2>&1 | Out-String).Trim()
        generatedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss zzz")
    }
    $versions | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $artifactDir "installed_versions.json") -Encoding UTF8

    Write-Host "[5/5] Running CPU Taskflow smoke test"
    & $venvPython -B (Join-Path $projectRoot "scripts\verify_environment.py") 2>&1 |
        Tee-Object -FilePath (Join-Path $artifactDir "environment_verification.log")
    if ($LASTEXITCODE -ne 0) {
        throw "Environment verification failed with exit code $LASTEXITCODE"
    }

    @{
        status = "success"
        completedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss zzz")
    } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $artifactDir "setup_status.json") -Encoding UTF8
}
catch {
    @{
        status = "failed"
        completedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss zzz")
        error = $_.Exception.Message
    } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $artifactDir "setup_status.json") -Encoding UTF8
    Write-Error $_
    throw
}
finally {
    Stop-Transcript
}

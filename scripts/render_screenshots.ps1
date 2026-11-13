$ErrorActionPreference = "Stop"

$projectRoot = "D:\SiSennKoToBa"
$artifactDir = Join-Path $projectRoot "artifacts"
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
$profile = Join-Path $env:TEMP "codex_uie_edge_profile"

New-Item -ItemType Directory -Path $profile -Force | Out-Null

function Render-Screenshot {
    param(
        [string]$HtmlPath,
        [string]$ImagePath,
        [string]$Size
    )

    $uri = ([System.Uri]::new($HtmlPath)).AbsoluteUri
    $node = Start-Process `
        -FilePath $edge `
        -ArgumentList @(
            "--headless",
            "--disable-gpu",
            "--hide-scrollbars",
            "--no-first-run",
            "--user-data-dir=$profile",
            "--force-device-scale-factor=1",
            "--window-size=$Size",
            "--screenshot=$ImagePath",
            $uri
        ) `
        -WindowStyle Hidden `
        -Wait `
        -PassThru

    if ($node.ExitCode -ne 0) {
        throw "Edge screenshot failed for $HtmlPath with exit code $($node.ExitCode)"
    }
    if (-not (Test-Path -LiteralPath $ImagePath)) {
        throw "Screenshot was not created: $ImagePath"
    }
}

Render-Screenshot `
    -HtmlPath (Join-Path $artifactDir "environment_verification.html") `
    -ImagePath (Join-Path $artifactDir "environment_verification.png") `
    -Size "1600,1200"

Render-Screenshot `
    -HtmlPath (Join-Path $artifactDir "schema_v1_results.html") `
    -ImagePath (Join-Path $artifactDir "schema_v1_results.png") `
    -Size "1900,1700"

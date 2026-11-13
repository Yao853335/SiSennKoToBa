$ErrorActionPreference = "Stop"

$projectRoot = [System.IO.Path]::GetFullPath("D:\SiSennKoToBa")
$thirdPartyRoot = [System.IO.Path]::GetFullPath((Join-Path $projectRoot "third_party"))
$targets = @(
    (Join-Path $projectRoot ".write_test"),
    (Join-Path $projectRoot "elevated_write_test"),
    (Join-Path $thirdPartyRoot "_partial_Information-Extraction-Chinese_20261018_185849")
)

foreach ($target in $targets) {
    $fullPath = [System.IO.Path]::GetFullPath($target)
    if (-not $fullPath.StartsWith($projectRoot + "\", [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove path outside project: $fullPath"
    }
    if ($fullPath -eq $projectRoot) {
        throw "Refusing to remove the project root"
    }
}

foreach ($target in $targets) {
    if (Test-Path -LiteralPath $target) {
        Remove-Item -LiteralPath $target -Recurse -Force
    }
}

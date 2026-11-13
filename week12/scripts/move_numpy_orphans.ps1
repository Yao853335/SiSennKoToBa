# Move numpy 2.0.2 orphan files out of the uie_cpu site-packages into a backup dir.
# Reversible: nothing is deleted. If any precheck fails, no file is moved.

$ErrorActionPreference = 'Stop'

$sp       = 'D:\anaconda\envs\uie_cpu\Lib\site-packages'
$bak      = Join-Path $sp '_numpy202_orphan_backup'
$manifest = 'D:\SiSennKoToBa\week12\logs\numpy202_orphan_manifest.txt'

if (-not (Test-Path -LiteralPath $manifest)) {
    Write-Output 'MANIFEST_MISSING'
    exit 2
}
if (-not (Test-Path -LiteralPath $sp)) {
    Write-Output 'SITEPACKAGES_MISSING'
    exit 2
}
if (Test-Path -LiteralPath $bak) {
    Write-Output ('BACKUP_DIR_ALREADY_EXISTS ' + $bak)
    exit 3
}

$rels = @(Get-Content -LiteralPath $manifest |
          Where-Object { $_.Trim() -ne '' } |
          ForEach-Object { $_.Trim() })
Write-Output ('entries=' + $rels.Count)

# ---------- Phase 1: precheck every exact source and destination ----------
$plan     = New-Object System.Collections.ArrayList
$missing  = New-Object System.Collections.ArrayList
$conflict = New-Object System.Collections.ArrayList

foreach ($r in $rels) {
    $src = Join-Path $sp  $r
    $dst = Join-Path $bak $r
    if (-not (Test-Path -LiteralPath $src)) { [void]$missing.Add($r);  continue }
    if (      Test-Path -LiteralPath $dst)  { [void]$conflict.Add($r); continue }
    [void]$plan.Add([pscustomobject]@{ Rel = $r; Src = $src; Dst = $dst })
}

Write-Output ('plan=' + $plan.Count + ' missing=' + $missing.Count + ' conflict=' + $conflict.Count)
$missing  | Select-Object -First 10 | ForEach-Object { Write-Output ('MISSING  ' + $_) }
$conflict | Select-Object -First 10 | ForEach-Object { Write-Output ('CONFLICT ' + $_) }

if ($missing.Count -gt 0 -or $conflict.Count -gt 0) {
    Write-Output 'PRECHECK_FAILED_NO_FILE_MOVED'
    exit 3
}

# ---------- Phase 2: move (single shell, end to end) ----------
$moved  = 0
$failed = New-Object System.Collections.ArrayList

foreach ($p in $plan) {
    try {
        # .NET API avoids Windows PowerShell 5.1 中 Split-Path -LiteralPath -Parent
        # 的参数集歧义（该写法在 5.1 下抛 AmbiguousParameterSet 终止性错误）
        $parent = [System.IO.Path]::GetDirectoryName($p.Dst)
        if ($parent -and -not ([System.IO.Directory]::Exists($parent))) {
            [System.IO.Directory]::CreateDirectory($parent) | Out-Null
        }
        Move-Item -LiteralPath $p.Src -Destination $p.Dst
        $moved++
    } catch {
        [void]$failed.Add($p.Rel)
        Write-Output ('MOVE_FAIL ' + $p.Rel + ' :: ' + $_.Exception.Message)
        break   # stop on first failure, do not switch strategy
    }
}

Write-Output ('moved=' + $moved + ' failed=' + $failed.Count)

# ---------- Phase 3: verify sources gone and backup populated ----------
$stillPresent = 0
foreach ($p in $plan) {
    if (Test-Path -LiteralPath $p.Src) { $stillPresent++ }
}
Write-Output ('source_still_present=' + $stillPresent)

$bakFiles = @(Get-ChildItem -LiteralPath $bak -Recurse -File -Force | Measure-Object).Count
Write-Output ('backup_files=' + $bakFiles)

# 1.26.4 integrity spot checks (must remain in place)
$keep = @(
    (Join-Path $sp 'numpy\core\_multiarray_umath.cp39-win_amd64.pyd'),
    (Join-Path $sp 'numpy\_core\__init__.py'),
    (Join-Path $sp 'numpy\_core\multiarray.py'),
    (Join-Path $sp 'numpy\_core\_multiarray_umath.py'),
    (Join-Path $sp 'numpy-1.26.4.dist-info\RECORD'),
    (Join-Path $sp 'numpy.libs\.load-order-numpy-1.26.4'),
    (Join-Path $sp 'pandas\__init__.py'),
    (Join-Path $sp 'paddle\__init__.py'),
    (Join-Path $sp 'paddlenlp\__init__.py')
)
$keepMissing = New-Object System.Collections.ArrayList
foreach ($k in $keep) {
    if (-not (Test-Path -LiteralPath $k)) { [void]$keepMissing.Add($k) }
}
Write-Output ('kept_files_missing=' + $keepMissing.Count)
$keepMissing | ForEach-Object { Write-Output ('KEPT_MISSING ' + $_) }

if ($failed.Count -eq 0 -and $stillPresent -eq 0 -and $keepMissing.Count -eq 0) {
    Write-Output 'RESULT_OK'
    exit 0
}
Write-Output 'RESULT_PARTIAL_CHECK_OUTPUT'
exit 4

# 滚动展示日志尾部（清除 ANSI 转义码），供截图窗口使用。
param([Parameter(Mandatory = $true)][string]$Path)

$ansi = [regex]::Escape([char]27) + '\[[0-9;]*[A-Za-z]'
while ($true) {
  try {
    $lines = Get-Content -LiteralPath $Path -Tail 32 -ErrorAction Stop
    Clear-Host
    foreach ($l in $lines) { [regex]::Replace($l, $ansi, '') | Write-Output }
  } catch { Start-Sleep -Seconds 1 }
  Start-Sleep -Seconds 2
}

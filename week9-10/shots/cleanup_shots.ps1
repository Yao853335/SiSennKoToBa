# 清理本次截图流程遗留的展示窗口进程（仅匹配 SHOT_UIE 标题 / tail_clean 命令行）
$k = 0
Get-CimInstance Win32_Process -Filter "Name='cmd.exe'" | ForEach-Object {
  if ($_.CommandLine -match 'SHOT_UIE') {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    $k++
  }
}
Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | ForEach-Object {
  if ($_.CommandLine -match 'tail_clean') {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    $k++
  }
}
Write-Output "killed=$k"

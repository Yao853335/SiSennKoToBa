# 截图执行器：打开真实控制台窗口展示内容，等待渲染后用 PrintWindow 抓窗存 PNG。
# 用法：powershell.exe -NoProfile -ExecutionPolicy Bypass -File shot_run.ps1 -Kind <text|nvidia|tail> -Title <窗口标题> -Payload <文本文件/日志文件> -Out <png 路径>

param(
  [Parameter(Mandatory = $true)][string]$Kind,     # text | nvidia | tail
  [Parameter(Mandatory = $true)][string]$Title,
  [Parameter(Mandatory = $true)][string]$Out,
  [string]$Payload = ""
)

. "$PSScriptRoot\capture_lib.ps1"

switch ($Kind) {
  "text" {
    $inner = "title $Title & mode con:cols=165 lines=44 & type `"$Payload`" & echo. & echo (以上为当日真实运行日志，按任意键结束展示)"
    $p = Start-Process cmd.exe -ArgumentList @("/k", $inner) -PassThru -WindowStyle Normal
  }
  "nvidia" {
    $inner = "title $Title & mode con:cols=165 lines=44 & nvidia-smi & echo. & echo (训练进行中实时执行 nvidia-smi)"
    $p = Start-Process cmd.exe -ArgumentList @("/k", $inner) -PassThru -WindowStyle Normal
  }
  "tail" {
    $inner = "title $Title & mode con:cols=165 lines=44 & powershell -NoProfile -ExecutionPolicy Bypass -File `"$PSScriptRoot\tail_clean.ps1`" -Path `"$Payload`""
    $p = Start-Process cmd.exe -ArgumentList @("/k", $inner) -PassThru -WindowStyle Normal
  }
}

$deadline = (Get-Date).AddSeconds(90)
$h = [IntPtr]::Zero
while ((Get-Date) -lt $deadline) {
  $h = [CapGdi]::FindBySubstring($Title)
  if ($h -ne [IntPtr]::Zero) { break }
  Start-Sleep -Milliseconds 300
}
if ($h -eq [IntPtr]::Zero) { throw "window not found: $Title" }

[CapGdi]::Front($h, 10, 10, 1620, 950)
Start-Sleep -Seconds 4          # 等窗口完成绘制/日志滚动

Save-CaptureWindow $h $Out
Write-Output "captured -> $Out"

# 关闭展示窗口（按本次 Start-Process 的 pid 定向清理）
taskkill /F /T /PID $p.Id | Out-Null

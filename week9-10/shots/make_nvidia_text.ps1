# 生成 nvidia-smi 摘要展示文本（UTF-16LE，供 cmd type 正确显示）。
# 用法：powershell -File make_nvidia_text.ps1 -Out <txt路径>   （需训练正在运行才有占用数据）
param([Parameter(Mandatory = $true)][string]$Out)

$ErrorActionPreference = "SilentlyContinue"
$raw = & nvidia-smi.exe 2>$null | Out-String -Stream
$lines = @($raw | Where-Object { $_.Trim() -ne "" })
$head = $lines[0..14]
$procLines = @($lines | Select-String -Pattern "PID|python.exe" | Select-Object -First 5 | ForEach-Object { $_.Line })
$text = ($head + @("| Processes (节选，训练进程 python.exe 在列)") + $procLines +
         @("", "(训练进行中实时执行 nvidia-smi，2026-10-31)")) -join "`r`n"
[System.IO.File]::WriteAllText($Out, $text, [System.Text.Encoding]::Unicode)
Write-Output "written -> $Out"

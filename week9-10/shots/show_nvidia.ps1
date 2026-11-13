# 展示 nvidia-smi 摘要（顶部汇总表 + 训练进程行），供截图窗口使用。
# 需要训练正在运行时执行，才能拍到真实占用数值。
$ErrorActionPreference = "SilentlyContinue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$o = & nvidia-smi.exe 2>$null | Out-String -Stream
$lines = @($o | Where-Object { $_ -ne "" })
$lines[0..14]
Write-Output "| Processes:"
$lines | Select-String -Pattern "python.exe|Type.*Process" | Select-Object -First 6 | ForEach-Object { $_.Line }

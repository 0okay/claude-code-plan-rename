# 调试版：无条件写日志（验证 Hook 是否被调用）
$logPath = "C:\Users\Administrator\AppData\Local\Temp\plan-rename-debug.log"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

# 立即写入启动标记
"[$timestamp] HOOK CALLED" | Out-File -FilePath $logPath -Append -Encoding UTF8

# 读取 stdin
$raw = [Console]::In.ReadToEnd()
"[$timestamp] STDIN LENGTH: $($raw.Length)" | Out-File -FilePath $logPath -Append -Encoding UTF8
"[$timestamp] STDIN CONTENT:`n$raw`n---`n" | Out-File -FilePath $logPath -Append -Encoding UTF8
exit 0

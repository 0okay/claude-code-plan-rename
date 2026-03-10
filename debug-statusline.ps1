$log = "C:\Users\Administrator\.claude\statusline-debug.log"
$timestamp = Get-Date -Format "HH:mm:ss.fff"

# 读 stdin
$stdin = $null
if (-not [Console]::IsInputRedirected) {
    Add-Content $log "[$timestamp] stdin is TTY (not redirected)"
    Write-Host "[debug] no stdin"
    exit 0
}

$stdin = [Console]::In.ReadToEnd()
$len = $stdin.Length

Add-Content $log "[$timestamp] stdin len=$len preview=$($stdin.Substring(0,[Math]::Min(80,$len)))"
Write-Host "[debug] stdin=$len chars"

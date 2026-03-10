$p = (Get-ChildItem "$env:USERPROFILE\.claude\plugins\cache\claude-hud\claude-hud" | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
& "C:\Users\Administrator\.bun\bin\bun.exe" (Join-Path $p "src\index.ts")

# plan-rename.ps1
# Stop Hook：Claude 每次完成响应后，扫描项目根目录
# 将三词随机名计划文件（word-word-word.md）重命名为 <title-slug>-<YYYYMMDD>-v<N>-plan.md

$ErrorActionPreference = "SilentlyContinue"

# 读取 stdin JSON（Stop hook 提供 session_id、cwd 等）
$raw = [Console]::In.ReadToEnd()
if (-not $raw) { exit 0 }
try { $data = $raw | ConvertFrom-Json } catch { exit 0 }

# 获取项目根目录
$projectDir = $data.cwd
if (-not $projectDir) { $projectDir = $env:CLAUDE_PROJECT_DIR }
if (-not $projectDir) { exit 0 }

# 扫描项目根目录，找所有三词随机名 .md 文件
$candidates = Get-ChildItem -Path $projectDir -Filter "*.md" -File -ErrorAction SilentlyContinue |
    Where-Object {
        $_.Name -match '^[a-z]+-[a-z]+-[a-z]+\.md$' -and
        $_.LinkType -ne "SymbolicLink"
    }

if (-not $candidates) { exit 0 }

$dateStr = Get-Date -Format "yyyyMMdd"

foreach ($file in $candidates) {
    $filePath = $file.FullName

    # 读取文件内容提取标题
    $content = Get-Content $filePath -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
    if (-not $content) { continue }

    # 取第一行非空内容
    $firstLine = ($content -split "`n" | Where-Object { $_.Trim() -ne "" } | Select-Object -First 1).Trim()

    # 去掉 Markdown 标题符号
    $titleRaw = $firstLine -replace '^#+\s*', ''

    # 转为 slug
    $slug = $titleRaw -replace '[：:【】《》「」『』（）\(\)\[\]\{\}\|\\\/\*\?\!\.\,，。、；;""''`~@#\$%\^&\+=]', ''
    $slug = $slug -replace '[\s\-_]+', '-'
    $slug = $slug.Trim('-')
    if ($slug.Length -gt 40) { $slug = $slug.Substring(0, 40).TrimEnd('-') }
    if (-not $slug) { $slug = "plan" }

    # 版本号递增
    $version = 1
    while (Test-Path (Join-Path $projectDir "$slug-$dateStr-v$version-plan.md")) {
        $version++
    }

    $newName = "$slug-$dateStr-v$version-plan.md"
    $newPath = Join-Path $projectDir $newName

    # 重命名
    Rename-Item -Path $filePath -NewName $newName -Force -ErrorAction Stop

    # 原路径建软连接
    New-Item -ItemType SymbolicLink -Path $filePath -Target $newPath -ErrorAction SilentlyContinue | Out-Null

    Write-Host "[plan-rename] $($file.Name) -> $newName"
}

exit 0

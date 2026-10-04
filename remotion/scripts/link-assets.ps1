# 把项目 assets/ 同步进 remotion/public/。
# Sync the project's assets/ into remotion/public/.
#
# 为什么是复制而不是目录 junction：
#   Remotion 打包时要把 public/ 里的链接「转发」进临时 bundle 目录，这一步用的是
#   fs.symlink；而 Windows 上创建符号链接需要管理员权限（或开发者模式）。
#   本机两者都没有 → 报 `EPERM: operation not permitted, symlink`，整个渲染链失败。
#   复制没有这个限制，代价只是几十 MB 磁盘。
#
# Why copy instead of a directory junction: Remotion forwards symlinks found in
# public/ into its temporary bundle via fs.symlink, which on Windows needs admin
# rights (or Developer Mode). Neither is available here, so junctions fail with
# EPERM and take the whole render down. Copying has no such requirement.
#
# 防漂移：同步后写 public/.assets-manifest.json（各文件相对路径 + 大小 + mtime）。
# 素材改过但忘了同步时，跑 -Check 就能发现。
#
# 复测指令 / How to re-run:
#   powershell -NoProfile -ExecutionPolicy Bypass -File remotion\scripts\link-assets.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File remotion\scripts\link-assets.ps1 -Check
#
# 注意：本文件含中文，必须保存为 UTF-8 with BOM，否则 Windows PowerShell 5.1
# 会按 GBK 解码并报出与真实原因无关的语法错误（见 docs/issues/003）。

param(
    # 只检查是否已同步，不做修改；不一致时退出码 1。
    [switch]$Check
)

$ErrorActionPreference = 'Stop'

$here     = Split-Path -Parent $MyInvocation.MyCommand.Path   # remotion\scripts
$remotion = Split-Path -Parent $here                          # remotion
$root     = Split-Path -Parent $remotion                      # 项目根
$public   = Join-Path $remotion 'public'
$assets   = Join-Path $root 'assets'
$manifestPath = Join-Path $public '.assets-manifest.json'

if (-not (Test-Path $assets)) {
    throw "assets/ 不存在 / not found: $assets"
}

# 需要同步的三类素材。字体 17MB / 图片 3MB / 音频 9.6MB，合计约 30MB。
$names = @('fonts', 'images', 'audio')

function Get-AssetManifest {
    $entries = @{}
    foreach ($name in $names) {
        $dir = Join-Path $assets $name
        if (-not (Test-Path $dir)) { continue }
        Get-ChildItem -LiteralPath $dir -Recurse -File | ForEach-Object {
            $rel = $_.FullName.Substring($assets.Length + 1) -replace '\\', '/'
            $entries[$rel] = "$($_.Length):$($_.LastWriteTimeUtc.Ticks)"
        }
    }
    return $entries
}

$source = Get-AssetManifest

if ($Check) {
    if (-not (Test-Path $manifestPath)) {
        Write-Host "[FAIL] 尚未同步过（缺 .assets-manifest.json），请先跑一次不带 -Check 的同步"
        exit 1
    }
    $saved = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $savedMap = @{}
    foreach ($p in $saved.PSObject.Properties) { $savedMap[$p.Name] = $p.Value }

    $diff = @()
    foreach ($k in $source.Keys) {
        if (-not $savedMap.ContainsKey($k)) { $diff += "新增/new: $k" }
        elseif ($savedMap[$k] -ne $source[$k]) { $diff += "已变/changed: $k" }
    }
    foreach ($k in $savedMap.Keys) {
        if (-not $source.ContainsKey($k)) { $diff += "已删/removed: $k" }
    }

    if ($diff.Count -eq 0) {
        Write-Host "[ok] public/ 与 assets/ 一致（$($source.Count) 个文件）"
        exit 0
    }
    Write-Host "[FAIL] public/ 与 assets/ 不一致，共 $($diff.Count) 处："
    $diff | Select-Object -First 20 | ForEach-Object { Write-Host "    $_" }
    Write-Host "-> 跑不带 -Check 的同步命令修复 / re-run without -Check"
    exit 1
}

# ── 同步 / Sync ────────────────────────────────────────────────────────────
if (Test-Path $public) {
    # 只清掉会被重建的部分
    foreach ($name in $names) {
        $dst = Join-Path $public $name
        if (Test-Path $dst) { Remove-Item -LiteralPath $dst -Recurse -Force }
    }
}
New-Item -ItemType Directory -Force -Path $public | Out-Null

foreach ($name in $names) {
    $src = Join-Path $assets $name
    if (-not (Test-Path $src)) {
        Write-Host "[skip] assets\$name 不存在"
        continue
    }
    $dst = Join-Path $public $name
    Copy-Item -LiteralPath $src -Destination $dst -Recurse -Force
    $n = (Get-ChildItem -LiteralPath $dst -Recurse -File).Count
    Write-Host "[ok]   public\$name  ($n files)"
}

# 写清单（排序后输出，保证可复现）
$ordered = [ordered]@{}
foreach ($k in ($source.Keys | Sort-Object)) { $ordered[$k] = $source[$k] }
$ordered | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

Write-Host ""
Write-Host "同步完成 / synced: $($source.Count) files -> public\"

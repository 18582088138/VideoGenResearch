# 整片渲染薄壳 / Full-video render shell.
#
# 为什么需要这个脚本：DSH 会话内的沙箱禁止「非继承 stdio 的进程间管道」，
# 而 Remotion 4.x 的整片编码由原生 Rust compositor 子进程完成，父子进程靠
# stdin/stdout 管道通信（compositor.js:47 的 spawn 未传 stdio，Node 默认 'pipe'）。
# 因此 `npx remotion render` 在沙箱内必然以 `write EOF` 失败 —— 这是架构前提，
# 无 flag 可绕（见 docs/issues/005-render-blocked-by-pipe-sandbox.md）。
#
# 所以：**本脚本请在沙箱外的普通终端执行。**
#
# 复测指令 / How to re-run:
#   powershell -NoProfile -ExecutionPolicy Bypass -File remotion\scripts\render.ps1 -Composition ShortLandscape
#   powershell -NoProfile -ExecutionPolicy Bypass -File remotion\scripts\render.ps1 -Composition MidPortrait -Crf 20
#   powershell -NoProfile -ExecutionPolicy Bypass -File remotion\scripts\render.ps1 -All
#
# 注意：本文件含中文，必须保存为 UTF-8 with BOM，否则 Windows PowerShell 5.1
# 会按 GBK 解码并报出与真实原因无关的语法错误（见 docs/issues/003）。

param(
    # 要渲染的 Composition id；与 -All 二选一
    [string]$Composition = '',
    # 渲染全部 4 个 Composition
    [switch]$All,
    # H.264 质量；越小越清晰、体积越大。规范见 docs/design/00_platform_output_spec.md
    [int]$Crf = 0,
    # 并发；留 0 则用 remotion.config.ts 的值（4）
    [int]$Concurrency = 0,
    # 渲染输出目录（相对项目根）
    [string]$OutDir = 'out'
)

$ErrorActionPreference = 'Stop'

$here     = Split-Path -Parent $MyInvocation.MyCommand.Path   # remotion\scripts
$remotion = Split-Path -Parent $here                          # remotion
$root     = Split-Path -Parent $remotion                      # 项目根
$outRoot  = Join-Path $root $OutDir

# 规范：横屏 CRF 18 / 竖屏 CRF 20（见 design/00_platform_output_spec.md §3）
$spec = @{
    'ShortLandscape' = @{ dir = 'short'; name = 'short_landscape_1080p.mp4';       crf = 18 }
    'ShortPortrait'  = @{ dir = 'short'; name = 'short_portrait_1080x1920.mp4';    crf = 20 }
    'MidLandscape'   = @{ dir = 'mid';   name = 'mid_landscape_1080p.mp4';         crf = 18 }
    'MidPortrait'    = @{ dir = 'mid';   name = 'mid_portrait_1080x1920.mp4';      crf = 20 }
}

$targets = if ($All) { @($spec.Keys) } elseif ($Composition) { @($Composition) } else {
    throw "请指定 -Composition <id> 或 -All。可选：$($spec.Keys -join ', ')"
}

# DSH 会话里 npm 的缓存目录被沙箱挡在工作区外；这里显式指向工作区内，
# 沙箱外执行时也保持行为一致（无害）。
$env:npm_config_cache = Join-Path (Split-Path -Parent $root) '.npm-cache'
$env:npm_config_tmp   = Join-Path (Split-Path -Parent $root) '.npm-tmp'

# ── 关键：临时目录也必须落在工作区内 ─────────────────────────────────────────
# Remotion 把预编码的 mp4 写到 %TEMP%\<react-motion-renderXXXX>\pre-encode.mp4。
# 若 %TEMP% 指向工作区外的 C:\Users\<user>\AppData\Local\Temp，DSH 沙箱会拒绝写入，
# ffmpeg 报 "Error opening output ... Permission denied"，
# 而 Node 侧只看到 compositor 崩溃并抛出**极具误导性**的 `Error: write EOF`
# （表象像管道问题，真因是写文件被拒）。
#
# Remotion writes its pre-encode mp4 into %TEMP%. If that resolves outside the
# workspace the sandbox denies the write and Node only surfaces a misleading
# `write EOF`. Pointing TMP/TEMP inside the workspace fixes it.
$renderTmp = Join-Path (Split-Path -Parent $root) '.render-tmp'
New-Item -ItemType Directory -Force -Path $renderTmp | Out-Null
$env:TMP  = $renderTmp
$env:TEMP = $renderTmp
Write-Host "临时目录 / temp dir: $renderTmp"

Push-Location $remotion
try {
    foreach ($id in $targets) {
        if (-not $spec.ContainsKey($id)) { throw "未知 Composition: $id" }
        $s = $spec[$id]
        $dir = Join-Path $outRoot $s.dir
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
        $outFile = Join-Path $dir $s.name
        $crf = if ($Crf -gt 0) { $Crf } else { $s.crf }

        $args = @('remotion', 'render', 'src/index.ts', $id, $outFile,
                  '--codec=h264', "--crf=$crf", '--pixel-format=yuv420p',
                  '--audio-codec=aac', '--audio-bitrate=192K')
        if ($Concurrency -gt 0) { $args += "--concurrency=$Concurrency" }

        Write-Host ""
        Write-Host "==> $id  ->  $outFile   (crf=$crf)" -ForegroundColor Cyan
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        & npx @args
        $code = $LASTEXITCODE
        $sw.Stop()

        if ($code -ne 0) {
            Write-Host "[FAIL] $id 退出码 $code（耗时 $([math]::Round($sw.Elapsed.TotalSeconds,1))s）" -ForegroundColor Red
        } elseif (Test-Path $outFile) {
            $mb = [math]::Round((Get-Item $outFile).Length / 1MB, 1)
            Write-Host "[ok]   $id  $mb MB  耗时 $([math]::Round($sw.Elapsed.TotalSeconds,1))s" -ForegroundColor Green
        } else {
            Write-Host "[FAIL] $id 退出码 0 但输出文件不存在" -ForegroundColor Red
        }
    }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "产物 / artifacts:"
Get-ChildItem -Recurse $outRoot -Filter '*.mp4' -ErrorAction SilentlyContinue |
    ForEach-Object { "  {0,8:N1} MB  {1}" -f ($_.Length / 1MB), $_.FullName.Replace($root, '.') }

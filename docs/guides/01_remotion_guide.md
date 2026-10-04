# Remotion 工程上手 / Remotion project guide

> **什么时候加载**：第一次跑这个 Remotion 工程、换机器、或渲染报错时。
> 输出参数见 [../design/00_platform_output_spec.md](../design/00_platform_output_spec.md)（唯一权威处）。

## 1. 前置条件

| 项 | 要求 | 本机实测 |
|---|---|---|
| Node | 22（仓库未声明 `engines`，CI 与文档一律用 22） | v22.16.0 ✅ |
| npm | 10+ | 10.9.2 ✅ |
| 磁盘 | 约 400 MB（node_modules 185 包 + Chrome Headless Shell 113 MB） | ✅ |

## 2. 三条必须遵守的规则（都是踩过的坑）

### 规则 1 — npm 必须带工作区内的 cache/tmp

DSH 沙箱把 `%LocalAppData%` 挡在工作区外，npm 默认缓存目录在那儿 → `EPERM`。
**每条 npm / npx 命令前都要设这两个变量**：

```powershell
$env:npm_config_cache='C:\Users\75203\Downloads\xkd\.npm-cache'
$env:npm_config_tmp='C:\Users\75203\Downloads\xkd\.npm-tmp'
```

见 [../issues/001-npm-cache-blocked-by-sandbox.md](../issues/001-npm-cache-blocked-by-sandbox.md)。

### 规则 2 — 素材走**复制**，不用 junction

Remotion 打包时会把 `public/` 里的符号链接「转发」进临时 bundle，用的是 `fs.symlink`；
**Windows 上建符号链接需要管理员权限或开发者模式**，本机两者都没有
→ `EPERM: operation not permitted, symlink` → **整条渲染链失败**。

所以 `remotion/public/{fonts,images,audio}` 是 `assets/` 的**复制副本**，
由脚本生成（`public/` 已 gitignore）：

```powershell
# 同步（素材更新后必须跑）
powershell -NoProfile -ExecutionPolicy Bypass -File remotion\scripts\link-assets.ps1

# 只检查是否已同步（CI / 提交前用）
powershell -NoProfile -ExecutionPolicy Bypass -File remotion\scripts\link-assets.ps1 -Check
```

脚本会写 `public/.assets-manifest.json`，`-Check` 靠它判断是否漂移。

### 规则 3 — 含中文的 `.ps1` 必须带 UTF-8 BOM

Windows PowerShell 5.1 在无 BOM 时按 GBK 读脚本，中文注释会把字符串截断，
**报出与真实原因完全无关的语法错误**。见 [../issues/003-powershell5-reads-utf8-as-gbk.md](../issues/003-powershell5-reads-utf8-as-gbk.md)。

## 3. 常用命令

```powershell
cd VideoGenResearch-deepseek\remotion
$env:npm_config_cache='C:\Users\75203\Downloads\xkd\.npm-cache'
$env:npm_config_tmp='C:\Users\75203\Downloads\xkd\.npm-tmp'

npm install                                  # 首次；185 包 / 约 10-40s
npx remotion compositions src/index.ts       # 列出 4 个 Composition
npx remotion studio src/index.ts             # 交互预览（改代码热更新）
npx remotion still src/index.ts ShortLandscape out/qa/f40.png --frame=40   # 单帧自检
npx remotion render src/index.ts ShortPortrait out/short_portrait.mp4      # 整片渲染
npx tsc --noEmit                             # 类型检查
```

**纪律：改任何镜头组件后先 `still` 出单帧（秒级），确认无误再整片渲染（分钟级）。**

## 4. Composition 清单

| id | 尺寸 | 帧数 | 时长 | 用途 |
|---|---|---|---|---|
| `ShortLandscape` | 1920×1080 | 1490 | 49.67s | 短视频横屏 |
| `ShortPortrait` | 1080×1920 | 1490 | 49.67s | 短视频竖屏 |
| `MidLandscape` | 1920×1080 | 4665 | 155.50s | 中视频横屏 |
| `MidPortrait` | 1080×1920 | 4665 | 155.50s | 中视频竖屏 |

**帧数与音频实测时长严格对应**（49.66s / 155.48s @30fps 向上取整）。
改素材音频后这两个数字必须重算 —— `tests/test_timeline.py` 会红，这是有意的护栏。

## 5. 目录结构

```
remotion/
├── package.json          Remotion 4.0.484 / React 19.2.7
├── remotion.config.ts    h264 + yuv420p + concurrency 4
├── tsconfig.json
├── scripts/link-assets.ps1   素材同步（复制 + 清单）
├── public/               ← 由脚本生成，不入库
│   ├── fonts/            NotoSansSC-VF.ttf
│   ├── images/           7 张素材图
│   ├── audio/            2 个 wav + 2 个 srt
│   └── .assets-manifest.json
└── src/
    ├── index.ts          registerRoot（必须单独文件，否则 Studio 不能热更新）
    ├── Root.tsx          4 个 Composition 注册
    ├── compositions/     成片组装
    │   ├── types.ts        FilmProps / ShotSpec —— props 契约（封闭镜头集）
    │   ├── FilmShell.tsx   成片公共骨架（音频 + 镜头序列 + 字幕轨）
    │   ├── CaptionTrack.tsx SRT 解析 + 字幕铺轨
    │   ├── ShortFilm.tsx   短视频 6 镜默认分镜
    │   └── MidFilm.tsx     中视频 10 镜默认分镜
    ├── shots/            镜头组件（每个对应一张镜头卡）
    │   ├── ShotRenderer.tsx 类型分发（未实现的走占位）
    │   └── TitleReveal.tsx  片头字标（letterspace-materialize 的运动语法）
    └── theme/            主题与基础件
        ├── theme.ts        cyan-noir token + 字体族 + 数字字重
        ├── fonts.ts        字体加载（delayRender 门禁）
        ├── layout.ts       横竖屏版式派生 + 安全区
        ├── Caption.tsx     字幕条
        └── ShotScaffold.tsx 镜头公共外框（背景 + 字体门禁）
```

## 6. 关键设计决定（改代码前先读）

### 6.1 横竖屏是两个 Composition，不是缩放

`--scale` 只能**同比例**放大，1920×1080 缩到 1080 宽得到 1080×608，**不是 9:16**。
所以布局一律由 `useVideoConfig()` 的 `width/height` 派生（`theme/layout.ts`），
**镜头组件里禁止硬编码 1920/1080**。

### 6.2 字体必须等加载完再渲染

Remotion 跑在无头 Chromium 上，字体加载失败**不报错**、只静默 fallback，
而且**逐帧渲染可能导致前后帧字体不一致**。
`theme/fonts.ts` 用 `delayRender()` 卡住渲染直到字体就绪，`ShotScaffold` 未就绪时返回 `null`。
**不要把 `delayRender` 改成乐观加载。**

### 6.3 镜头类型是封闭集合

`compositions/types.ts` 里的 `ShotType` 是枚举。LLM（或人）**只能从这个集合里选**，
未实现的类型由 `ShotRenderer` 落到**明显可辨的占位**，不会静默渲成空白。
见 [../architecture/00_pipeline.md](../architecture/00_pipeline.md)。

### 6.4 确定性渲染

禁 `Date.now()` / `Math.random()` / 无参 `new Date()`。
伪随机用固定种子（`mulberry32`，seed 从 index 派生），保证逐帧可复现、渲染间零抖动。

## 7. 已知待修

| 项 | 说明 |
|---|---|
| 竖屏字幕框偏宽 | 实测左右各只留 ~60px，比设计的左 60 / 右 180 更满。需把 `Caption` 的 `maxWidth` 收紧到安全框内 |
| 仅 `title-reveal` / `outro-lockup` 已实现 | 其余 8 种镜头类型走占位，按 [../design/02_storyboard.md](../design/02_storyboard.md) 逐个落地 |
| 字体未子集化 | 用完整 17 MB 的 `NotoSansSC-VF.ttf`，打包偏慢。可用 `fonttools` 按实际用字子集化到数十 KB |
| BGM 未接入 | 按 memory D10 默认关闭；要开需自己加 `bgm` inputProp（`template/` 也没有实现，见调研结论） |

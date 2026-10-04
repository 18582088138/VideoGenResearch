# 视频制作调参手册 / Video Tuning Handbook

> **这份文档解决一个问题：不动业务逻辑就能把视频风格调成你要的样子。**
>
> 面向「手工调超参数」的场景。每一节都给出**改哪个文件、改哪个值、值变大/变小会怎样**。
>
> This is the manual for adjusting the look of the videos by hand: which file,
> which knob, and what happens when you turn it.

## 目录 / Contents

| 节 | 内容 | 何时读 |
|---|---|---|
| [1](#1-最短路径三条命令) | 最短路径：三条命令 | 想立刻看到改动效果 |
| [2](#2-调参地图改哪里) | 调参地图：什么改哪里 | 知道想改什么但不知改哪 |
| [3](#3-全局旋钮tuning对象) | 全局旋钮 `TUNING` | 调字号/留白/素材尺寸 |
| [4](#4-版式与安全区) | 版式与安全区 | 内容位置、头重脚轻 |
| [5](#5-改分镜增删镜头改顺序) | 改分镜：增删镜头、改顺序 | 调内容与节奏 |
| [6](#6-节奏规则与上限) | 节奏规则与上限（≤5s） | 视频太快/太慢 |
| [7](#7-字幕工程) | 字幕工程（ASR + 切分） | 字幕太长/不同步 |
| [8](#8-动效调参) | 动效调参 | 想改动画手感 |
| [9](#9-新增一个镜头类型) | 新增一个镜头类型 | 想加全新画面 |
| [10](#10-配色) | 配色 | 换主题色 |
| [11](#11-踩坑清单) | 踩坑清单 | **改完没效果 / 渲染炸了** |

---

## 1. 最短路径：三条命令

```powershell
cd C:\Users\75203\Downloads\xkd\VideoGenResearch-deepseek\remotion

# ① 看单帧（秒级，不编码，最常用）
npx remotion still src/index.ts ShortPortrait ..\out\qa\probe.png --frame=560

# ② 开可视化预览，拖时间轴实时看（改代码自动热更新）
npx remotion studio src/index.ts

# ③ 出一整条成片
npx remotion render src/index.ts ShortPortrait ..\out\short\short_portrait_1080x1920.mp4 `
  --crf=20 --codec=h264 --pixel-format=yuv420p --audio-codec=aac --audio-bitrate=192K
```

> ⚠️ **必须先设临时目录**，否则渲染会以极具误导性的 `Error: write EOF` 失败
> （真因是 Remotion 把预编码文件写到工作区外的 `%TEMP%`，见
> [issues/005](issues/005-render-fails-outside-workspace-temp.md)）：
>
> ```powershell
> $env:TMP='C:\Users\75203\Downloads\xkd\.render-tmp'; $env:TEMP=$env:TMP
> New-Item -ItemType Directory -Force -Path $env:TMP | Out-Null
> ```
>
> 用 `remotion\scripts\render.ps1` 则已内置。

**四条 Composition**：`ShortLandscape` / `ShortPortrait`（1490 帧 ≈ 49.7s）、
`MidLandscape` / `MidPortrait`（4665 帧 ≈ 155.5s），全部 30fps。

---

## 2. 调参地图：改哪里

| 你想改的东西 | 改这个文件 | 关键词 |
|---|---|---|
| **字号、留白、素材大小** | `src/theme/theme.ts` | `TUNING` |
| 安全区、内容居中位置、字幕基线 | `src/theme/layout.ts` | `deriveLayout` |
| 分镜（镜数/顺序/文案/时长） | `src/compositions/ShortFilm.tsx` | `SHORT_SHOTS` |
| 中视频分镜 | `src/compositions/MidFilm.tsx` | `MID_SHOTS` |
| 某个镜头的动效 | `src/shots/<Type>.tsx` | 见 §8 |
| 镜头共用的入场/退场骨架 | `src/theme/ShotScaffold.tsx` | — |
| 字幕条样式 | `src/theme/Caption.tsx` | — |
| 配色 | `src/theme/theme.ts` | `CYAN_NOIR` |
| 输出编码（CRF/像素格式） | `remotion.config.ts` + 命令参数 | — |

**改完怎么验证**：`npx tsc --noEmit`（类型）→ `npx remotion still`（看画面）→
`npx remotion render`（出片）。

---

## 3. 全局旋钮：`TUNING` 对象

`src/theme/theme.ts` 里的 `TUNING` 是**唯一应该改尺寸的地方**。各镜头组件都从这里读，
所以改一处全局生效 —— 这避免了"每个组件各写一份字号、改不干净"。

| 旋钮 | 默认 | 调大的效果 | 调小的效果 |
|---|---|---|---|
| `portraitTopBias` | 0.14 | 内容整体下移，上方留白更多 | 内容更靠上 |
| `landscapeTopBias` | 0.16 | 同上（横屏） | 同上 |
| `captionSizePortrait` | **40** | 字幕更大更醒目（但会挤占画面） | 字幕更小更精致 |
| `captionSizeLandscape` | 38 | 同上 | 同上 |
| `captionShrinkAbove` | 22 | 更少自动缩小（长句也保持大字） | 更早自动缩小 |
| `portraitImageHeightRatio` | 0.42 | **竖屏图片更大**（用户反馈偏小） | 图片更小 |
| `landscapeImageHeightRatio` | 0.62 | 同上（横屏） | 同上 |
| `imageWidthRatio` | 0.94 | 图片更宽 | 更窄 |
| `titleSizePortrait` | 70 | 片头主标更大 | 更小 |
| `titleSizeLandscape` | 92 | 同上 | 同上 |
| `subtitleSizePortrait` | 32 | 片头副标更大 | 更小 |
| `subtitleSizeLandscape` | 30 | 同上 | 同上 |
| `figureTitlePortrait` | 42 | 图文卡标题更大 | 更小 |
| `figureBodyPortrait` | 29 | 图文卡正文更大 | 更小 |

> **字幕字号的历史**：v1 是 46px（竖屏），用户反馈"过大"，已降到 40px。
> 这是 m 系平台竖屏的正常区间（1080 宽下 38–44px）。

---

## 4. 版式与安全区

### 4.1 三个坐标的区别（**这是最容易搞混的地方**）

`src/theme/layout.ts` 提供三个含义不同的 y 坐标，**镜头必须用对**：

| 字段 | 含义 | 竖屏值 | 谁该用 |
|---|---|---|---|
| `safe` | 内容安全框（**含**字幕带位置） | top 120 / bottom 600 | 需要贴着边缘放东西时 |
| `contentCenterY` | **可用内容区的垂直中心**（已扣掉字幕带） | ≈ 570 | **图文类镜头：内容在此居中** |
| `captionCenterY` | 字幕条的垂直中心 | ≈ 810 | 只给 `Caption` 用 |

竖屏安全框的构成（`deriveLayout`）：

```
1080×1920
├─ top 120          ← 顶部留白
├─ 内容可用区 (contentHeight = 1020)
│   └─ contentCenterY ≈ 570   ← 镜头内容在这里居中
├─ 字幕带 180
└─ bottom 420       ← 抖音/小红书底部 UI 遮挡（账号名、文案、音乐条）
```

### 4.2 治「头重脚轻」

**症状**：内容全挤在上半屏，下方大片空白（用户反馈过）。

**病因**：镜头从 `layout.safe.top` 往下**顶对齐**，而 `safe` 把字幕带也算进去了，
于是内容从 y=120 开始堆，到 y≈700 就结束，下面 1200px 全空。

**修法**：内容块改为在 `contentCenterY` 上**居中**：

```tsx
<div style={{
  position: "absolute",
  left: layout.safe.left,
  top: layout.contentCenterY,   // ← 不是 safe.top
  width: layout.safeWidth,
  transform: "translateY(-50%)", // ← 高度自适应，要点多少都不悬空
  display: "flex", flexDirection: "column",
}}>
```

用 `translateY(-50%)` 而不是手算高度：**内容高度不确定时不要算像素**，
这在 `TimelineTravel` 上踩过坑（写死 `top: axis-250`，竖屏换行后卡片悬空）。

### 4.3 改安全区

```ts
// src/theme/layout.ts
const PORTRAIT_BOTTOM_INSET = 420;   // 平台 UI 遮挡高度 —— 改平台就改这里
const PORTRAIT_RIGHT_INSET  = 180;   // 右侧按钮栏
const CAPTION_BAND_PORTRAIT = 180;   // 字幕带高度
```

改完**必须**用 `still` 确认字幕仍高于遮挡区、右侧内容不被按钮栏压住。

---

## 5. 改分镜：增删镜头、改顺序

全部在 `src/compositions/ShortFilm.tsx` 的 `SHORT_SHOTS` 数组里。
**数组顺序 = 播放顺序**，`from` 字段不用手写（校验器/运行时会按顺序排）。

```tsx
{
  type: "figure-panel",          // 镜头类型（见 §9 的类型表）
  from: 0,                       // 占位，实际顺序由数组位置决定
  durationInFrames: 132,         // 时长：30fps 下 150 帧 = 5.00s
  eyebrow: "AUTHORS",            // 角标（等宽小字）
  text: "三家单位联合署名",        // 主文案
  bullets: [                     // 要点；**双星**标强调色
    "清华大学自动化系 **赵明国**团队",
    "字节跳动 **Seed**",
  ],
  footer: "真机平台：加速进化人形机器人",  // 底部结论条
},
```

**加一个镜头**：复制一段，改 `type` 与字段，放在你想放的位置。
**删一个镜头**：整段删掉 —— 不用管其他镜头的 `from`，运行时会重排。

**镜头时长必须满足**：`45 ≤ durationInFrames ≤ 150`（1.5s–5s）。
超出会怎样见 §6。

### 5.1 各类型必填字段

| 类型 | 必填 | 可选 |
|---|---|---|
| `title-reveal` | `text` | `subtext` `eyebrow` |
| `page-spotlight` | `image` `text` | `source` `targets` |
| `number-roll` | `text` `metrics[{label,value}]` | — |
| `scan-annotate` | `image` `targets[{x,y,w,h,label}]` | `text` |
| `radar-reveal` | `image` `text` | `subtext` |
| `counter-burst` | `text` `metrics` | — |
| `before-after` | `image` `imageAfter` `text` | — |
| `slow-push` | `image` `text` | `subtext` |
| `timeline-travel` | `text` `stops[{label,note}]` | `metrics` |
| `outro-lockup` | `text` | `tagline` |
| `figure-panel` | `text` `bullets[]` | `eyebrow` `footer` |
| `stat-compare` | `text` `metric` `sides[{label,value,display}]` | `footer` |
| `flow-diagram` | `text` `nodes[{label,sub}]` | `eyebrow` `footer` |

`targets` 的 `x/y/w/h` 是**图片内的百分比**（0–1），不是像素。

---

## 6. 节奏规则与上限

**核心约束：单镜 ≤ 5 秒（150 帧 @30fps）。**

> 这条来自用户明确反馈：「每个分镜不要超过5s，除非素材严重不足可以适当延长长度，
> 不然视频节奏会变慢」。

因为总时长由音频锁定，所以**多出来的时间只能变成更多镜头**，不能靠拉长单镜：

| | 早期版本 | 现在 |
|---|---|---|
| 短视频镜数 | 6 镜（平均 8.3s） | **12 镜（平均 4.1s）** |
| 单镜上限 | 700 帧（23s） | **150 帧（5s）** |

### 校验器的处理优先级

`src/videogen/validate.py` 按这个优先级处理冲突：

1. **总帧数 = 音频时长**（最高优先，否则音画不同步）
2. **每镜 ≤ 5s**：超了就**切分**成等长若干段（复制内容，不丢信息）
3. **卡数区间**（短 5–6 / 中 8–10）：只在不违反第 2 条时才合并

> **第 3 条会主动放弃。** 如果合并必然产生超 5s 的镜头，校验器**不合并**并在
> `repair_log` 留痕「主动放弃合并：合并后必然超过 5s 上限，节奏优先于镜数」。
> 这是刻意的取舍。

### 相关常量

```python
# src/videogen/validate.py
MIN_SHOT_FRAMES = 45            # 单镜最短 1.5s
MAX_SHOT_FRAMES = 150           # 单镜最长 5.0s  ← 节奏旋钮
ABSOLUTE_MAX_SHOT_FRAMES = 700  # 硬护栏
SHOT_COUNT_RANGE = {"short": (5, 6), "mid": (8, 10)}
```

> ⚠️ 改 `SHOT_COUNT_RANGE` 时**必须同步三处**：这里、`plan/planner.py`、
> `docs/architecture/01_spec_schema.md` §5、`plan/prompts/system.md`。
> 少改一处就会出现「文档说 6 镜、实际给 12 镜」的脱节 —— 这个坑踩过一次。

---

## 7. 字幕工程

### 7.1 为什么换了字幕源

原素材的 `shortvideo.zh.srt` 是按**长句**切的，单条最长约 10 秒 —— 直接导致节奏拖沓，
且与画面不同步。现在改为 **MiniMax ASR 重新识别 + 按停顿重新切分**。

```powershell
cd C:\Users\75203\Downloads\xkd\VideoGenResearch-deepseek
$py = "C:\Users\75203\miniforge3\envs\ov_env_py312\python.exe"

# 首次：调 ASR（会产生 1 次计费，按音频时长）
& $py scripts\asr_subtitles.py --kind short

# 之后调切分参数：复用缓存的 ASR 结果，零费用
& $py scripts\asr_subtitles.py --kind short --reuse --max-chars 16
```

产物：`assets/audio/asr_short.json`（ASR 原始结果，**缓存以免重复计费**）+
`assets/audio/short.asr.srt`（切分后字幕）。

### 7.2 切分参数（`src/videogen/subtitle.py` 的 `SubtitleParams`）

| 参数 | 默认 | 作用 |
|---|---|---|
| `max_chars` | 20 | 单条最大字数；**调小 = 字幕更短更碎** |
| `min_chars` | 12 | 低于此值遇到弱边界也不切 |
| `pause_gap` | 0.28 | 字间静音 ≥ 此值 → **必切** |
| `soft_gap` | 0.12 | ≥ 此值**且**已达 `min_chars` → 可切 |
| `merge_below_seconds` | 0.9 | 更短的条目与上一条合并（避免一闪而过） |
| `max_seconds` | 6.0 | 单条最长显示时长 |

实测效果（短视频，`max_chars=18`）：

```
原素材：  5 条，平均 10.0s
现在：   20 条，平均 2.18s，平均 13.9 字，最长 3.30s
```

**数字保护**：切分不会把数字切断（`零点三|四四米` 会被读坏）。
`subtitle.py` 的 `_NUMERIC` 集合定义了哪些字属于数字簇。

### 7.3 字幕样式

`src/theme/Caption.tsx`。字号来自 `TUNING.captionSizePortrait`（§3）。
字幕带位置来自 `layout.captionCenterY`（§4），**不允许**镜头自行写死 y 坐标。

---

## 8. 动效调参

所有动效都是 `interpolate(frame, [in], [out], { easing, extrapolateX: "clamp" })`。
四个常用旋钮：

| 想调什么 | 改什么 |
|---|---|
| 快慢 | `interpolate` 的输入帧区间跨度（`[0, 14]` → `[0, 24]` 变慢） |
| 手感 | `easing`：`Easing.out(Easing.cubic)` 平滑收尾 / `Easing.out(Easing.back(1.5))` 轻微过冲 / `Easing.out(Easing.poly(4))` 前快后慢 |
| 错峰节奏 | 组件里的 `STAGGER` / `stagger` 常量（每项间隔帧数） |
| 位移距离 | `transform: translateY(${(1-a) * 12}px)` 里的 `12` |

**两条硬规则**（踩过坑）：

1. **禁止** `Date.now()` / `Math.random()` / 裸 `new Date()` —— 渲染必须可复现。
   需要"随机"就用帧号派生：`const r = Math.sin(index * 12.9898) * 43758.5453;`
2. `interpolate` 的 `inputRange` 与 `outputRange` **长度必须一致**。
   写 `interpolate(frame, [fireFrame], [0, 1])` 会运行时崩溃，要写 `[fireFrame, fireFrame+8]`。

`useCurrentFrame()` 在 `<Sequence>` 内返回的是**局部帧号**（从该 Sequence 起点算）。

### 每个镜头的动效清单

| 镜头 | 主运动语法 |
|---|---|
| `title-reveal` | 字距结晶（letter-spacing 收）+ 逐字解锁 + 遮罩上移 |
| `page-spotlight` | 聚光椭圆扫入 → 锁定 → 呼吸；角标打字机 |
| `number-roll` | 里程表式滚动，每位数错峰停住 + 落定脉冲 |
| `scan-annotate` | 扫描线纵移 → 命中即定框 + 标签弹出 |
| `radar-reveal` | 角部聚光扩张 + 旋转扫描 + 数据线描边生长 |
| `counter-burst` | 大数字计数 + 52 片确定性彩纸抛物线 |
| `before-after` | 拉杆横向擦除（clip-path） |
| `slow-push` | 缓推 + 暗角收拢 |
| `timeline-travel` | 相机跟随式横移 + 刻度 pop + 卡片弹立 |
| `outro-lockup` | 标落位 + 标语展开 + 光晕脉冲 |
| `figure-panel` | 标题上移淡入 + 要点**逐条左滑入**（左侧强调竖条） |
| `stat-compare` | 双条**竞赛式生长**（outQuart）+ 胜方高亮脉冲 |
| `flow-diagram` | 节点错峰 pop + 连线 draw-on + 频率徽章脉冲 |

---

## 9. 新增一个镜头类型

四步，缺一不可（漏了第三步会显示占位框）：

1. **写组件** `src/shots/MyShot.tsx`
   ```tsx
   export interface MyShotProps {
     text?: string;
     theme: ThemeTokens;
     layout: Layout;
     durationInFrames: number;
   }
   export const MyShot: React.FC<MyShotProps> = ({ text, theme, layout, durationInFrames }) => {
     const frame = useCurrentFrame();
     // 用 layout.contentCenterY 居中；字号从 TUNING 读
   };
   ```

2. **加类型** `src/compositions/types.ts`
   ```ts
   export type ShotType = /* ... */ | "my-shot";
   // 若有新字段，同步加到 ShotSpec
   ```

3. **注册分发** `src/shots/ShotRenderer.tsx`
   ```tsx
   case "my-shot":
     return <MyShot text={shot.text} {...base} />;
   ```

4. **（可选）接入 Python 契约**：`src/videogen/spec.py` 的 `SHOT_TYPES`
   与 `REQUIRED_FIELDS`，以及 `plan/prompts/system.md`。

---

## 10. 配色

改 `src/theme/theme.ts` 的 `CYAN_NOIR`，**并同步**
`docs/design/01_theme_palettes.md`（文档与代码不一致会造成"改了没反应"的假配置）。

| token | 值 | 用途 |
|---|---|---|
| `bg` | `#04080A` | 全局底 |
| `surface` | `#0B1418` | 卡片面 |
| `surface2` | `#15242A` | 轨道、进度底 |
| `primary` | `#2DD4BF` | 主强调：数字、进度条 |
| `accent` | `#7DF9FF` | 次强调：高光、关键数字 |
| `alert` | `#F97362` | 警示/落后一方 |
| `text` | `#E8F1F2` | 正文 |
| `textMuted` | `#7A8C90` | 次要文字、来源标注 |
| `border` | `#1E3138` | 描边 |

选新色后用 `scripts/make_palette_swatch.py` 生成色卡核对对比度。

---

## 11. 踩坑清单

| 现象 | 真因 | 修法 |
|---|---|---|
| 渲染报 `Error: write EOF` / `EPERM` | Remotion 把预编码 mp4 写到工作区外的 `%TEMP%` | 设 `$env:TMP`/`$env:TEMP` 到工作区内。**排查时去全量日志搜 `denied`，不要只看尾部** |
| 改了 `TUNING` 没反应 | 组件里写死了字号，没读 `TUNING` | 组件一律从 `TUNING` 读（§3） |
| 内容挤在上半屏、下方大片空 | 用了 `safe.top` 顶对齐 | 改用 `contentCenterY` + `translateY(-50%)`（§4.2） |
| 元素悬空/错位 | 写死了像素位置，竖屏换行后高度变了 | 用**边锚定**（`top: axis; transform: translateY(-100%)`） |
| `inputRange (1) and outputRange (2) must have the same length` | `interpolate` 两数组长度不等 | 补成等长（§8 规则 2） |
| 渲染结果每帧都不一样 | 用了 `Date.now()`/`Math.random()` | 用帧号派生伪随机（§8 规则 1） |
| 中文不显示 / 变方框 | `msyh.ttc` 是 TTC 集合，face 选择不可靠 | 用 `NotoSansSC-VF.ttf`（[issues/002](issues/002-cjk-font-ttc-face-ambiguity.md)） |
| `.ps1` 报莫名语法错 | PowerShell 5.1 把无 BOM 的 UTF-8 当 GBK 读 | 存成 **UTF-8 with BOM**（[issues/003](issues/003-powershell5-reads-utf8-as-gbk.md)） |
| 打包报 `EPERM: symlink` | Remotion 转发 `public/` 软链，Windows 需管理员/开发者模式 | 用**复制**而非软链（[issues/004](issues/004-remotion-symlink-public-dir.md)） |
| `npx` 从 Python 调用失败 `WinError 2` | `npx` 是 `.cmd` shim，`CreateProcess` 不解析 | 直调 `node <remotion-cli.js>` |
| 字幕与画面文字叠在一起 | 收尾镜旁白本身就是 CTA | 收尾镜不铺字幕（`CaptionTrack` 的 `excludeRanges`） |
| 抽帧看到数字是错的 | 抽在了动画**中途** | 抽在动画落定后（先算锁定帧，再换算秒） |
| 卡数/时长约束"文档有、实际不生效" | 契约写了但校验器没实现 | **契约写了就必须有代码兜底**，并补单测 |

---

## 附：常用帧号换算

30fps 下：`帧号 ÷ 30 = 秒`，`秒 × 30 = 帧号`。

| 秒 | 帧 |
|---|---|
| 1.5s（单镜下限） | 45 |
| **5.0s（单镜上限）** | **150** |
| 3.8s | 114 |
| 4.4s | 132 |
| 49.66s（短视频全长） | 1490 |
| 155.48s（中视频全长） | 4665 |

抽帧时 `ffmpeg -ss <秒>` 用秒，`remotion still --frame=<帧>` 用帧，**别混**。

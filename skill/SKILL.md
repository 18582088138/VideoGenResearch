# videogen-shotcraft — 代码驱动视频生成

> 项目专属 skill。供 `Agent_VideoGen_Module` 或任何需要「把稿件做成视频」的 Agent 引用。
> 本项目：`C:\Users\75203\Downloads\xkd\VideoGenResearch-deepseek`
> 完整文档入口：[../docs/00_INDEX.md](../docs/00_INDEX.md)　跨会话记忆：[../memory/project.md](../memory/project.md)

## 何时用这个 skill

用户要求把**一篇已定稿的稿件**（含现成配音 + 字幕 + 配图）做成视频，且：

- 要**横屏和/或竖屏**版本
- 要**科技感 / 电影感**，不要 PPT 感
- 接受「用代码渲染」而不是「AI 文生视频」

**不适用**：需要纯 AI 生成画面（Sora / 可灵 / 即梦）—— 那不在本项目范围。

## 一句话机制

```
字幕时轴（权威骨架） + 素材语义索引  →  VideoSpec(JSON)  →  Remotion 渲染  →  mp4
                          ↑
                   LLM 只能从**封闭镜头集**里选卡与填参数
```

**核心约束：LLM 绝不产出 JSX/TSX。** 它只输出可校验的 JSON，镜头类型是枚举。
这是本项目对「黑盒 spec」问题的正面解法，详见
[../docs/architecture/00_pipeline.md](../docs/architecture/00_pipeline.md)。

## 五阶段流水线（照此执行）

| 阶段 | 做什么 | 产物 | 花钱? |
|---|---|---|---|
| 1 素材理解 | 解析 srt/wav、盘点图片 | `Timeline` + `ImageAsset[]` | 否 |
| 2 LLM 规划 | DeepSeek **一次调用**产出 `VideoSpec` | `spec.json` | ✅ 是 |
| 3 校验编译 | 校验 + 修复降级 + 编译 props | `props_<kind>_<aspect>.json` | 否 |
| 4 渲染 | Node 薄壳调 Remotion | `mp4` | 本地算力 |
| 5 归档 | spec 与成片同目录 + manifest | `out/<run_id>/` | 否 |

## 快速上手

```powershell
$py = "C:\Users\75203\miniforge3\envs\ov_env_py312\python.exe"
cd C:\Users\75203\Downloads\xkd\VideoGenResearch-deepseek

# 1) 素材入工程（图片/音频/字体 → remotion/public，复制 + 清单防漂移）
powershell -NoProfile -ExecutionPolicy Bypass -File remotion\scripts\link-assets.ps1

# 2) 列 Composition 确认工程健康
cd remotion
$env:npm_config_cache='C:\Users\75203\Downloads\xkd\.npm-cache'
$env:npm_config_tmp='C:\Users\75203\Downloads\xkd\.npm-tmp'
npx remotion compositions src/index.ts

# 3) 改镜头后先出**单帧**自检（秒级），不要直接整片渲
npx remotion still src/index.ts ShortPortrait out\qa\check.png --frame=500
```

## ⚠️ 三条会卡住你的硬规则

### 1. 整片渲染前必须把 `TMP`/`TEMP` 指进工作区

Remotion 把**预编码的 mp4** 写到 `%TEMP%`。若 `%TEMP%` 在工作区外，
沙箱拒绝写入 → ffmpeg 报 `Permission denied` → compositor 崩溃 →
Node 只抛出**极具误导性**的 `Error: write EOF`（看着像管道问题，其实不是）。

```powershell
$env:TMP  = 'C:\Users\75203\Downloads\xkd\.render-tmp'
$env:TEMP = $env:TMP
New-Item -ItemType Directory -Force -Path $env:TMP | Out-Null
```

`remotion/scripts/render.ps1` 与 `videogen/render/remotion.py` 都已内置这段设置。
详见 [issues/005](../docs/issues/005-render-fails-outside-workspace-temp.md)。

> **排查提示**：见到 `write EOF` 时**去全量日志搜 `denied`/`failed`**，
> 真因通常被截断在更上面。只看日志尾部会得出错误结论。

### 2. npm 必须带工作区内的 cache/tmp

否则撞沙箱的文件访问限制（[issues/001](../docs/issues/001-npm-cache-blocked-by-sandbox.md)）。

### 3. 镜头组件不能用 `maxHeight` 单独约束图片

标注按百分比定位时，图被压窄会导致整条标注被裁。
必须用 `fitSize()` 按**宽高双约束**算出确定尺寸
（[guides/00_dev_principles.md](../docs/guides/00_dev_principles.md) §8）。

## 可用镜头集（10 种，封闭枚举）

| type | 组件 | 语义 | 何时用 |
|---|---|---|---|
| `title-reveal` | `TitleReveal` | 片头字标逐字结晶 | 开场 |
| `page-spotlight` | `PageSpotlight` | 聚光扫过页面锁定 | 展示来源/权威性 |
| `number-roll` | `NumberRoll` | 多位指标滚轮锁定 | 一组并列数字 |
| `scan-annotate` | `ScanAnnotate` | 扫描线匀速标注 | 解读白底图表 |
| `radar-reveal` | `RadarReveal` | 角落匀速显影 | 高潮：单张强图 |
| `counter-burst` | `CounterBurst` | 计数冲刺 + 纸屑抢拍 | 里程碑数字 |
| `before-after` | `BeforeAfter` | 快甩慢扫对比杆 | 效果对比 |
| `slow-push` | `SlowPush` | 匀加速推近 + 暗角 | 情绪转沉 |
| `timeline-travel` | `TimelineTravel` | 横向时间轴旅行 | 发展史/战绩 |
| `outro-lockup` | `OutroLockup` | 收束 + 逐字 lockup | 收尾 CTA |

**未实现的 type 会渲染成明显可辨的占位**（写着类型名），不会静默出空白 ——
这是有意的设计，避免「看着像成品」。

## 视觉规范（不要自行发挥）

- **主题**：`cyan-noir`，token 唯一权威在
  [../docs/design/01_theme_palettes.md](../docs/design/01_theme_palettes.md)
- **白底图表**：必须卡片化承载 + 压暗一档，**不改图内像素**
- **字体**：`NotoSansSC-VF.ttf`（思源黑体可变字重，OFL 可商用）。
  **禁用 TTC 集合字体**（`msyh.ttc` 会静默 fallback，[issues/002](../docs/issues/002-cjk-font-ttc-face-ambiguity.md)）
- **安全区**：数值唯一权威在
  [../docs/design/00_platform_output_spec.md](../docs/design/00_platform_output_spec.md)；
  `layout.ts` 已把字幕带高度扣掉，**不要另写死坐标**
- **确定性**：禁 `Date.now()` / `Math.random()`；伪随机用 index 派生

## 从镜头卡新增一个镜头组件

1. 在 `docs/research/shot_catalog.md` 里选卡，读**卡片正文全文**
2. 按卡上「参考实现」定位并读**准确 demo 源码**（SKILL.md 硬规则：
   凭卡名新写＝放弃全部调校积累）
3. `assets/lib/` 的组件要 **copy 进 `remotion/src/ui/`**，不 import 源库
4. 卡上「已知坑/命门」标注的参数**不得降档**
5. 加进 `shot_catalog` 枚举 + `ShotRenderer` 分发
6. 出**横竖屏各一张静帧**自检，再更新分镜文档

## 成本

| 项 | 量级 |
|---|---|
| LLM | **每支视频 1 次** DeepSeek 调用（输入 3–5k / 输出 2–4k token） |
| 单帧自检 | 秒级 |
| 短视频整片 | 分钟级（1490 帧 × 方向数） |
| 中视频整片 | 数分钟级（4665 帧 × 方向数） |
| BGM | **0**（项目自带 5 首免版权曲；程序化合成 1–10 秒/条） |

⚠️ **Remotion 许可**：免费仅限「个人 / ≤3 员工营利组织 / 非营利 / 评估期」。
**自动化批量渲染属 Automators 档（$0.01/次 + $100/月保底）** ——
做成产品前必须评估（[../docs/research/04_bgm_and_audio.md](../docs/research/04_bgm_and_audio.md)）。

## 纪律

- **不做全量测试**：只跑本次改动对应的节点（`pytest tests/test_xxx.py::test_yyy`）
- **改镜头先出单帧**：`still` 秒级，`render` 分钟级
- **AI 不执行 git commit/push**：指令写进 [../docs/git_commands.md](../docs/git_commands.md)
- **注释**：核心/跨层 API 中英双语；内部 helper 单语、只写「为什么」
- **单文件 ≤500 行**

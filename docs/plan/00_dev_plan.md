# 开发方案 — VideoGenResearch-deepseek

> **什么时候加载**：开工前、方案调整后、想知道「下一步做什么 / 为什么这么排」时。
> 本文档是**进度与范围的唯一权威处**。方案调整**原地更新本文档**，不新开文件。

状态图例：`✅ 已完成` · `🔄 进行中` · `⬜ 未开始` · `⛔ 阻塞`

## 1. 范围（本期做什么 / 不做什么）

### 做

| 交付物 | 说明 |
|---|---|
| **4 个 mp4** | 短视频（49.66s）× 横竖屏 + 中视频（155.48s）× 横竖屏 |
| **调研文档** | Remotion 使用方法、video-shotcraft 使用方法、工具横评、BGM/音频结论 |
| **可复用 Python 模块** | `src/videogen/`，唯一入口 `generate_video()` |
| **架构文档** | 生成流程 / prompt / script / workflow |
| **设计文档** | 主题配色 + 样图、平台输出规格、分镜设计 |
| **项目专属 skill** | `skill/`，video-shotcraft + Remotion 的薄壳调用协议 |

### 不做（本期）

- ❌ 纯 AI 文生视频（Sora / 可灵 / 即梦等）—— 预留扩展位，不实现
- ❌ 语音生成（TTS）—— 素材配音已是成品
- ❌ 全量测试与全功能回归 —— 只在用户点名时做
- ❌ BGM 的 AI 生成 —— 项目自带 5 首免版权 BGM，零生成成本

## 2. 阶段进度

| 阶段 | 状态 | 落盘物 |
|---|---|---|
| 调研 | ✅ 完成 | `docs/research/00~04`（两份手册约 4500 行）、`shot_catalog.md`、`docs/issues/001~004` |
| 构建方案 | ✅ 完成（本文档） | `docs/plan/00_dev_plan.md` |
| 方案讨论&调整 | 🔄 待用户确认 §8 四项 | 本文档原地更新 |
| 开发 | 🔄 B1/B3/B4 完成，B5/B7/B8/B9 未开始 | `src/videogen/`、`remotion/` |
| 测试 | 🔄 26 单测全绿 + 7 张静帧视觉验证 | `tests/`、`docs/03_unit_tests.md`、`out/qa/` |
| debug&修改 | 🔄 已记录 **5** 个问题（001–005） | `docs/issues/` |
| 代码审阅（人工） | ⬜ 未开始 | `docs/reviews/` |
| git cmd（人工执行） | ✅ 已产出 14 组分步指令 | `docs/git_commands.md` |

### ✅ 曾经的阻塞已解除（Round 8 修正）

**初判为「沙箱禁止管道」，是错的。** 真因：Remotion 把预编码 mp4 写到 `%TEMP%`，
而 `%TEMP%` 在工作区外被沙箱拒绝写入（ffmpeg 报 `Permission denied`），
compositor 随之崩溃，Node 侧只抛出**极具误导性**的 `write EOF`。

→ **修法**：把 `TMP`/`TEMP` 指进工作区（已内置到 `render.ps1` 与 `build_env()`）。
→ **整片渲染在本会话内可行**，不需要沙箱外执行。

详见 [issues/005](../issues/005-render-fails-outside-workspace-temp.md)，
其中完整留档了我两次误判的过程与「不能只看日志尾部」的教训。

## 3. 已实测确认的可行性（不是推断）

| 项 | 实测结果 |
|---|---|
| conda `ov_env_py312` | ✅ Python 3.12.14 |
| Node / npm | ✅ v22.16.0 / 10.9.2 |
| ffmpeg / ffprobe | ✅ 可用 |
| Remotion 打包 | ✅ 1.9 s（缓存后） |
| Chrome Headless Shell | ✅ 自动下载 113 MB（`149.0.7790.0`） |
| **4 个 Composition 注册** | ✅ `ShortLandscape` / `ShortPortrait` 1490 帧 49.67s；`MidLandscape` / `MidPortrait` 4665 帧 155.50s —— **与音频实测时长严格对应** |
| `remotion still` 单帧 | ✅ 横竖屏均出图 |
| **中文字体命中** | ✅ 实测非 fallback，Noto Sans SC 可变字重生效，逐字解锁动效正常 |
| **主题蒙皮** | ✅ 深青 `cyan-noir` 生效，与 Ink Press 米白衬线完全不同 |
| 竖屏安全区 | ✅ 字幕落在 y≈1350，避开底部 420px 遮挡区 |
| 镜头卡 | ✅ 157 张 / 10 类，索引已生成 |
| 音频素材 | ✅ 短 49.66s / 中 155.48s（实测） |
| SFX | ✅ **149 个 / 16 类**（三方核对：本机实测 = 仓库文档；两子代理报的 151 为误计） |

**结论：环境与渲染链全部打通，可以进入镜头实现阶段。**

### 3.1 成片实测（Round 8）

| 成片 | 大小 | 渲染耗时 | 核验结果 |
|---|---|---|---|
| `short_landscape_1080p.mp4` | 4.7 MB | 164.8 s | ✅ h264 / 1920×1080 / 30fps / yuv420p / aac 48kHz stereo 189kbps / 49.73s |
| `short_portrait_1080x1920.mp4` | 3.6 MB | 212.3 s | ✅ h264 / 1080×1920 / 30fps / yuv420p / aac 48kHz stereo 189kbps / 49.73s |
| `mid_landscape_1080p.mp4` | 11.9 MB | 599.7 s | ✅ h264 / 1920×1080 / 30fps / yuv420p / aac 48kHz stereo 189kbps / 155.56s |
| `mid_portrait_1080x1920.mp4` | 10.9 MB | 617.1 s | ✅ h264 / 1080×1920 / 30fps / yuv420p / aac 48kHz stereo 189kbps / 155.56s |

**4 个成片全部产出**，逐项符合
[design/00_platform_output_spec.md](../design/00_platform_output_spec.md) §2/§3。
时长 49.73s / 155.56s 与音频实测 49.66s / 155.48s 的差值为容器/编码开销，在预期内。

**从真实 mp4 抽帧品检**（不只是静帧）：画面、中文字体、数字滚动终值
（`0.344 / 0.186 / 64%` 准确）、字幕、安全区均正常。

> 品检教训：第一次抽帧抽在动画**中途**（数字尚在滚动，显示 `0.900`），
> 一度误判为数字算错。**抽帧必须抽在动画落定后** —— 先算该镜的锁定帧再换算秒。
> 已写入 [guides/00_dev_principles.md](../guides/00_dev_principles.md) §8。

## 4. 模块划分

```
VideoGenResearch-deepseek/
├── src/videogen/                 可复用 Python 模块
│   ├── paths.py          ✅      路径解析（唯一允许知道「项目在哪」的地方）
│   ├── models.py         ✅      领域模型（ShotCard / ImageAsset / Timeline / VideoResult）
│   ├── assets.py         ✅      素材加载 + 尺寸核对
│   ├── shot_catalog.py   ✅      镜头卡索引加载（按需读正文）
│   ├── timeline.py       ✅      SRT 解析 + 时间轴（阶段 1）
│   ├── spec.py           ⬜      VideoSpec 数据结构（阶段 3 的数据契约）
│   ├── validate.py       ⬜      spec 校验 + 降级修复策略
│   ├── plan/             ⬜      LLM 规划（阶段 2，唯一花钱处）
│   │   ├── planner.py            DeepSeek 调用
│   │   ├── client.py             DeepSeek HTTP 客户端
│   │   └── prompts/              system.md / user.j2（纯文本，便于迭代）
│   ├── render/           ⬜      渲染编排（阶段 4，Node 薄壳）
│   │   └── remotion.py           subprocess 调 npx remotion
│   └── pipeline.py       ⬜      稳定入口 generate_video()
├── remotion/                     Remotion 工程（镜头组件在此）
│   ├── src/
│   │   ├── Root.tsx              注册 Composition（横竖屏各一组）
│   │   ├── compositions/         ShortLandscape / ShortPortrait / MidLandscape / MidPortrait
│   │   ├── shots/                从 shot_catalog 落地的镜头组件
│   │   ├── ui/                   Caption / Panel / NumberRoll 等基础件
│   │   └── theme/                主题 token（cyan-noir）
│   ├── public/                   fonts / images / audio（软链或复制）
│   └── package.json
├── scripts/                      薄壳脚本（零业务逻辑）
│   ├── build_shot_catalog.py     ✅
│   ├── make_palette_swatch.py    ✅
│   ├── npm.ps1                   ⬜  统一 npm 环境变量（见 issues/001）
│   └── render.py                 ⬜  调 videogen.pipeline
├── tests/                        单元测试
├── docs/                        全部文档（00_INDEX.md 是唯一入口）
├── assets/                      素材（图片/音频/字体/索引）
└── out/                         渲染产物（只放产物）
```

**分层铁律**（对标 DailyNewsAssistant）：
```
scripts → pipeline → {plan, validate} → {timeline, assets, shot_catalog, spec} → paths
remotion（Node）只消费 props JSON，不含业务决策
```
**禁止反向 import**；`scripts/` 只是薄壳。

## 5. 接口草案

```python
def generate_video(
    srt: Path,
    audio: Path,
    assets: list[Path],
    *,
    kind: Literal["short", "mid"],
    aspect: Literal["landscape", "portrait", "both"] = "both",
    theme: str = "cyan-noir",
    out_dir: Path | None = None,
) -> VideoResult:
    """字幕 + 配音 + 素材 → 成片。
    Narration + voiceover + assets → rendered video(s).
    确定性：同一组输入必得同一支视频。
    """
```

调用方（`Agent_VideoGen_Module`）**不需要知道 Remotion 存在**。

## 6. 开发批次（每个批次一次人工审阅）

| 批次 | 内容 | 验收手段 | 预估费用 |
|---|---|---|---|
| **B1** ✅ | 阶段 1 基础：`timeline` / `assets` / `shot_catalog` / `paths` / `models` | ✅ 已达成：`pytest tests/test_timeline.py tests/test_assets.py` **26 passed** | 0 元 |
| **B2** ✅ | `spec.py` + `validate.py`：VideoSpec 数据契约 + 校验降级 | ✅ 已达成：`pytest tests/test_validate.py` **20 passed**；覆盖 12 个修复分支 + 不可修复报错 + 时间轴对齐 + 序列化往返 | 0 元 |
| **B3** ✅ | Remotion 工程骨架：4 个 Composition + 主题 token + 字体门禁 + 版式派生 + 字幕条 + 素材同步脚本 | ✅ 已达成：`compositions` 列出 4 个且帧数与音频吻合；横竖屏 `still` 均出图；中文字体实测命中；竖屏避开安全区 | 0 元（仅本地渲染） |
| **B4** ✅ | 短视频 6 个镜头组件 | ✅ 已达成：横竖屏静帧逐镜验证（`out/qa/`）；`tsc` 零错误 | 0 元（仅本地渲染） |
| **B5** ✅ | 中视频新增 4 个组件（`counter-burst` / `before-after` / `slow-push` / `timeline-travel`）+ 分镜落地 | ✅ 已达成：4 个新镜头横屏静帧验证通过；**10 种镜头类型全部实现**，占位分支只剩防御性保留 | 0 元（仅本地渲染） |
| **B6** | 整片渲染出 4 个 mp4 | 🔄 **短视频 2 个已完成并核验**（见 §3.1）；中视频 2 个渲染中 | 本地算力（约 3–6 分钟/个） |
| **B7** ✅ | `plan/` LLM 规划（DeepSeek）+ `prompts/` + 入口脚本 | ✅ 已达成：**真实调用 2 次**（合计 prompt 17,959×2 + completion 628/902 token，各 3.0–3.5s）；模型输出**一次通过校验，0 条修复**；`scripts/plan.py` 端到端落盘 `out/short/spec.json` | 约 2 次 LLM 调用（≈¥0.05） |
| **B8** ✅ | `compile.py` + `render/` + `pipeline.generate_video()` 端到端 | ✅ 已达成：**props 驱动渲染实测通过** —— Python 编译的 spec 真被 Remotion 吃到（静帧显示 `SCAN · 00/04` 与模型的 4 个标注目标、模型文案与模型选的素材，确证非内置兜底分镜）；`pytest tests/test_pipeline.py` **18 passed** | 0 元（静帧渲染） |
| **B9** ✅ | 项目专属 skill + 架构 spec 契约文档 | ✅ 已达成：`skill/SKILL.md`（含 10 种镜头集与操作流程）+ `docs/architecture/01_spec_schema.md` | 0 元 |

**说明**：B4–B6 先**手工把分镜实现出来并渲出成片**（这是用户要的「先出两支视频」），
B7–B8 再把 LLM 与编排接上。这个顺序保证「即使 LLM 阶段延期，样片也已交付」。

## 7. 成本估算

| 项 | 估算 | 依据 |
|---|---|---|
| LLM（DeepSeek） | 每支视频 **1 次调用**；输入 3–5k token（catalog 占大头），输出 2–4k token | 架构文档 §5 |
| 单帧自检 | 秒级 | 已实测 |
| 短视频整片 | 分钟级（1490 帧 × 2 方向） | 待实测 |
| 中视频整片 | 数分钟级（4665 帧 × 2 方向） | 待实测 |
| 调优 | 主要成本是**反复渲染** → 纪律：先 `still` 出单帧，确认后再整片 | 开发守则 §3.7 |

> 实测值回填到 `out/<run_id>/manifest.json` 并汇总进本文档。

## 8. 待用户确认（阻塞进入 B2）

1. **配色**：采用 `cyan-noir`？（见 [design/01_theme_palettes.md](../design/01_theme_palettes.md) 色卡）
2. **BGM**：确认「默认关闭、作为可选开关」？
3. **镜头数**：短视频 **6 镜**、中视频 **10 镜**（用户给的是 5–6 / 8–10，取上限偏多），是否合适？
4. **开发顺序**：确认「先渲出样片（B4–B6）再接 LLM（B7–B8）」这个顺序。

## 9. 修订记录

| 日期 | 变更 |
|---|---|
| 2026-10-02 | 初版。确认可行性、模块划分、B1 完成、B2–B9 排期 |

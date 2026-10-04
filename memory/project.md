# project memory — VideoGenResearch-deepseek

> 跨会话恢复用。新会话接手先读这一份 + [docs/00_INDEX.md](../docs/00_INDEX.md)，不要考古。
> 只写「决策」与「硬事实」，不写过程流水。有矛盾时以**最新**的为准，并覆盖此处旧结论。

## 一句话目标

用 Remotion + video-shotcraft 把中文科技新闻稿（含现成配音 wav + srt）做成横/竖屏视频，
并沉淀出可被 `Agent_VideoGen_Module` 复用的 Python 模块。

## 环境（已实测）

| 项 | 值 |
|---|---|
| 工作区根 | `C:\Users\75203\Downloads\xkd` |
| 本项目 | `C:\Users\75203\Downloads\xkd\VideoGenResearch-deepseek` |
| Python | `C:\Users\75203\miniforge3\envs\ov_env_py312\python.exe`（3.12.14） |
| Node / npm | v22.16.0 / 10.9.2 |
| ffmpeg / ffprobe | ✅ 可用（N-127054） |
| git | 仓库已 init，**尚无 commit** |

**不要**用 `conda run ... python -c`（会吞 `-c` 参数），直接调上面的解释器绝对路径。

## 关键决策（含否决）

| # | 决策 | 理由 |
|---|---|---|
| D1 | **不借鉴 `VideoGenResearch-minimax`** | 用户判定：成片质量不可用、仓库无包边界、一次性脚本当实现、未真正用上 video-shotcraft 特性。仅**借用**它目录下 clone 的 `video-shotcraft` 源码本身 |
| D2 | `video-shotcraft` 源仓库路径固定为 `..\video-shotcraft`（工作区根下） | 全盘仅此一份 clone（`Vincentwei1021/video-shotcraft` @ `5ddbf52`，1284 项 / 236.7 MB，git 工作树干净）。**不再复制一份**，避免漂移。原位于 `VideoGenResearch-minimax\` 下，已由用户移至工作区根 |
| D3 | v1 只做**「代码即渲染」**族 | 纯 AI 文生视频（Sora/可灵等）本期不做，预留扩展位 |
| D4 | 交付 = 调研报告 + 最小可跑 demo + **可复用 Python 模块** | 模块是 `Agent_VideoGen_Module` 的地基，也是 `DailyNewsAssistant` 的功能拓展 |
| D5 | LLM 后端用 **DeepSeek API**（`.env` 已配好） | 后续工程化按此设计，生成流程/prompt/script/workflow 都要整理成文档 |
| D6 | 渲染输出**横屏 1920×1080 + 竖屏 1080×1920** 各一版 | 满足小红书/抖音横竖屏要求；见 [docs/design/00_platform_output_spec.md](../docs/design/00_platform_output_spec.md) |
| D7 | video-shotcraft 的 `assets/lib/*` 一律 **copy 进本工程再改**，不 import 源库 | 源库自己的规定（SKILL.md §资产使用方式） |
| D8 | 镜头数：短视频 5–6 张卡（开场+数字翻转+雷达入场+收尾），中视频 8–10 张 | 用户指定 |
| D9 | 主题配色采用 **`cyan-noir`（暗青水墨）**：`bg #04080A` / `surface #0B1418` / `surface2 #15242A` / `primary #2DD4BF` / `accent #7DF9FF` / `alert #F97362` | 由 `scripts/make_palette_swatch.py` 生成 5 套候选供用户挑选；AI 推荐 cyan-noir（近黑+青绿，电影感最强；能衬托 4 张白底学术图表卡）。**用户尚未否决**，若有异议按最新为准 |
| D10 | BGM **作为可选开关实现，但默认不开启**；默认只出「无 BGM + 含 SFX」版 | 遵循省成本准则（配 BGM 需同时间线出两版 → 渲染次数翻倍）。BGM 素材本身项目自带 5 首免版权曲，**零生成算力开销** |
| D11 | Remotion 版本以**实际安装的 v4.0.484** 为准（用户给的是 v3 文档链接） | `video-shotcraft/template/package.json` 锁定 `remotion@4.0.484` / `react@19.2.7`；文档标注 v3→v4 差异 |
| D12 | 中文字体统一用 **`NotoSansSC-VF.ttf`（思源黑体可变字重）** | TTC 集合的 `msyh.ttc` 在 `@font-face` 下取 face 不可靠且静默 fallback；OFL 可商用，见 issues/002 |
| D13 | **BGM 不经 AI 生成**；程序化合成留作将来「每条独一无二」时的备选 | **MusicGen 权重 CC-BY-NC 禁止商用**（代码 MIT 但权重不是）；Stable Audio 需 GPU 且许可阈值未确证；Magenta 在 Py3.12+Windows 装不上；Suno/Udio 无稳定 API。程序化合成（numpy + `scipy.signal.lfilter`）1–3 分钟曲子仅需 **1–10 秒** CPU |
| D14 | 横竖屏用**两个 Composition**，不用 `--scale` | 官方明确 `--scale` **只能同比例放大**，无法 16:9↔9:16；且仓库无任何 `--scale` 用例，推荐「设计坐标系隔离」 |
| D15 | 自动化批量渲染需评估 **Remotion Automators 档（$0.01/次 + $100/月保底）** | 免费范围仅「个人 / ≤3 员工营利组织 / 非营利 / 评估期」。核心包是 Remotion License，**非 MIT**（仅子包标 MIT）。已记入 dev_plan §7 成本模型 |

### ⚠️ 两条必须记住的坑（会直接影响命令写法）

1. **Windows 上 `remotion render --props` 不能传内联 JSON，必须传文件路径**（官方警告）
   → 本架构本来就落盘 props JSON，天然合规；但不要在脚本里图省事写内联。
2. **Remotion 自动下载的 Chromium 不含 MP3/MP4 编解码器** → 本项目旁白是 WAV（PCM）无碍；
   但**素材里 5 首 BGM 是 MP3**，若启用 BGM 需留意，可考虑转成 WAV。

## 已核实的硬事实（可直接依赖，不必重查）

| 事实 | 值 | 来源 |
|---|---|---|
| 镜头卡总数 | **157**（11/26/28/10/13/15/19/11/17/7，无重无漏） | 实测 + 子代理复核 |
| Remotion 全家族版本 | **4.0.484**，React **19.2.7** | `template/package.json` |
| Node | 22（无 `engines` 声明；CI 与 README 一律 22） | 源码 + 实测 v22.16.0 |
| SFX | **149 个 mp3 / 16 类**（camera 10 · counter 4 · crowd 3 · data 13 · film 8 · fluid 5 · glass 4 · impact 14 · light 10 · mech 8 · paper 10 · riser 1 · scifi 5 · text 13 · transition 23 · ui 18） | 主上下文逐文件复核 ⚠️ |
| BGM | **5 首免版权**（Mixkit Free），BPM 实测 124/129/86/123/103 | `assets/audio/ATTRIBUTION.md` |
| three.js 隔离 | 157 张卡的 demo **无一** import three；仅 `assets/lib/FlatPanel.tsx` 与 `assets/lib/helpers/camera.tsx` 用到 | 子代理复核 |
| `@remotion/motion-blur` | 恰好 8 个文件（`DeckDealFlyin.tsx` 只在注释提及，不依赖） | 子代理复核 |
| `implementationStatus` | 全库为空（`STYLE_STATUS = {}`）→ 手册里「仅供参考/缺少预览」降级标注**不触发**，不要写成必有分支 | 子代理复核 |
| 多分辨率 | 仓库**无 `--scale`**；推荐做法是「设计坐标系隔离」 | 子代理复核 |
| 模板 BGM | `template/` 是 **SFX-only**，`bgm` prop 需自己新增 | 子代理复核 |
| 实测渲染能力 | 打包 **1.9s**（缓存后）→ 自动下载 Chrome Headless 113MB → `compositions` 与 `still` 均通过 | 主上下文实测 |
| 本工程 Remotion 工程 | `remotion/`（4 个 Composition 全部注册成功）：`ShortLandscape`/`ShortPortrait` = 1490 帧 49.67s，`MidLandscape`/`MidPortrait` = 4665 帧 155.50s | 主上下文实测 |
| 素材进 Remotion 的方式 | **复制，不用 junction** —— Remotion 打包时对 `public/` 内的符号链接调 `fs.symlink`，Windows 建符号链接需管理员/开发者模式（本机两者都无）→ `EPERM` 整链失败 | 见 [docs/issues/004](docs/issues/004-remotion-symlink-public-dir.md) |
| CJK 字体渲染 | ✅ 已实测命中（非 fallback）：Noto Sans SC 可变字重生效，逐字解锁动效正常 | 主上下文看静帧确认 |

> ⚠️ **数字分歧留痕**：调研子代理报 SFX 为「151」，主上下文逐文件复核为 **149**（非 mp3 文件 0 个）。
> 以 **149** 为准，详见 [docs/research/02_video_shotcraft_usage.md](docs/research/02_video_shotcraft_usage.md) 开头「校正 1」。

## 测试尺度（用户明确口径）

- 默认**只跑本次改动对应的单测节点**；不做全量回归。
- **必要且仅当「功能可行性验证」时**才做真实付费渲染，目的是确保功能真的可用；开销记录进文档。
- 用户会**阶段性**点名做整体 review 与全功能测试。

## git 纪律

AI **不执行** `commit` / `push`。只把分步、按功能切分的指令写进
[docs/git_commands.md](../docs/git_commands.md)（**一次性文件**，覆写前先 `git log` 核对上一组已执行）。

## 素材（已实测）

路径：`..\DailyNewsAssistant\outputs\articles\20260919\登上Science-Robotics顶刊-清华团队耗时22年-终于教会机器人踢足__39558d8b`

| 资产 | 实测值 |
|---|---|
| `shortvideo.zh.wav` | **49.66s**（44.1k? 否：24000Hz mono 16bit） |
| `narration.zh.wav` | **155.48s** |
| `tts/seg_001..011_narrator.wav` | 累计 **152.97s**，逐段时长见素材分析文档 |
| `shortvideo.zh.srt` | 5 条，0.000→49.664 |
| `narration.zh.srt` | 11 条，0.000→155.480 |
| `images/` | 7 张 jpg/png（约 80KB~980KB），带同名 `.json` 元数据 |
| `article.md` / `summary.zh.md` / `references.md` | 原文与摘要 |

字幕时轴是**权威时间轴**，分镜预算按它排。

## 待确认 / 未定

- BGM 是否启用（默认关闭，见 D10）。若启用需自加 `bgm` inputProp。
- 主题配色是否改为非 `cyan-noir`（默认已按 cyan-noir 实现，见 D9）。

## 开发进度快照（Round 3 末）

| 批次 | 状态 |
|---|---|
| B1 Python 基础层（paths/models/timeline/assets/shot_catalog） | ✅ |
| B2 spec 契约 + 校验降级（spec.py/validate.py） | ✅ |
| B3 Remotion 工程骨架（4 Composition/主题/字体/版式/字幕） | ✅ |
| B4 短视频 6 镜 | ✅ |
| B5 中视频新增 4 镜 —— **10 种镜头类型全部实现** | ✅ |
| B6 整片渲染 4 个 mp4 | ✅ **4/4 完成并核验** |
| B7 LLM 规划（DeepSeek）+ prompt + 入口脚本 | ✅ **真实调用已验证** |
| B8 compile/ + render/ + pipeline.generate_video() 端到端 | ✅ **props 驱动渲染实测通过** |
| B9 项目专属 skill + spec 契约文档 | ✅ |

**测试**：92 个节点全绿（0.61s，默认排除 1 个 `.live`），零费用。
**真实 LLM 实测**：3 次调用（短×2 + 中×1）。
- 短视频：prompt 17,959 + completion 628，3.0s，**0 条修复**
- 中视频：prompt 18,592 + completion 1,683，5.7s，**1 条修复**（11 镜 → 10 镜）
**端到端验证**：Python 编译的 spec → props JSON → Remotion 静帧，
画面确证是**模型产出**而非内置兜底（`SCAN · 00/04` + 模型文案 + 模型选的素材）。
**视觉验证**：16 张静帧（`out/qa/`），横竖屏均有。

## 一条重要的实测教训（Round 6）

**契约写了、prompt 说了，但校验器没实现 = 没人保证。**

卡数区间（短 5–6 / 中 8–10）在 `01_spec_schema.md` 与 `system.md` 里都有，
但 `validate.py` **从来没校验过它**。中视频真实调用给出 **11 镜**却直接通过 ——
只有真跑真实模型才会暴露这类「文档与实现脱节」。

同类风险的检查清单（新增约束时逐条问）：
1. 文档写了吗？→ 2. prompt 告诉模型了吗？→ 3. **校验器有代码兜底吗？** → 4. 有单测吗？

## 两条竖屏专属教训（Round 6）

1. **横屏验过 ≠ 竖屏成立。** 中视频新组件只在横屏验过，竖屏一出图就发现
   `TimelineTravel` 的卡片悬空（写死 `top: axis-250px`，竖屏换行后高度不同）。
2. **高度不确定的元素用边锚定**，不要算像素：
   `top: axis; transform: translateY(-100%)` 而不是 `top: axis - 250`。

## 对外唯一入口（B8 交付）

```python
from videogen import generate_video
from videogen.pipeline import GenerateOptions

result = generate_video(
    srt, audio,
    options=GenerateOptions(kind="short", aspect="both"),
)
# result.outputs / .spec / .repairs / .llm_tokens / .summary()
```

**调用方不需要知道 Remotion 存在。** 归档目录 `out/runs/<kind>-<theme>-<时间戳>/`
含 `spec.json` / `props_*.json` / `manifest.json`（成本台账）。

## 两条实测换来的硬规则（写错了会浪费半天）

1. **不要用 `npx` 调 Remotion** —— Windows 上 `npx` 是 `.cmd` shim，
   `subprocess` 的 `CreateProcess` 不解析它，直接 `FileNotFoundError`。
   必须用 `node <remotion-cli.js>`（见 `render/remotion.py:_cli_command`）。
2. **子进程 cwd 是 `remotion/`，所有路径必须 `.resolve()` 成绝对路径** ——
   否则 Remotion 会报「`--props` 既不是合法 JSON 也不是合法文件路径」。

## LLM 链路的实测结论（Round 4）

| 项 | 实测值 |
|---|---|
| provider / model | `deepseek` / `deepseek-chat` @ `https://api.deepseek.com/v1` |
| prompt token | **17,959**（catalog 157 张卡占大头） |
| completion token | 628（真实规划）/ 902（可行性测试） |
| 耗时 | 3.0–3.5 s，`attempts=1`（无重试） |
| 输出质量 | **6 镜全部合法，0 条 repair**；镜[4] 文案「学习策略全面包住规则系统」正确复用了素材语义判读，而非照抄旁白 |
| 成本 | 每支视频 1 次调用 ≈ **¥0.025**；两次验证合计 ≈¥0.05 |

**关键设计验证**：模型把 `from` 全填 0 —— 这正是设计意图，
帧号由 `validate_and_repair` 按音频时长重排（服务端权威，不信模型自算）。

## 已实现的 10 种镜头类型（封闭集合）

`title-reveal` · `page-spotlight` · `number-roll` · `scan-annotate` · `radar-reveal` ·
`counter-burst` · `before-after` · `slow-push` · `timeline-travel` · `outro-lockup`

代码真源：`remotion/src/compositions/types.ts` 的 `ShotType`
与 `src/videogen/spec.py` 的 `SHOT_TYPES` —— **两处必须同步**。

## Round 9：短视频优化（用户反馈驱动）

### 用户的核心反馈（务必记住）
1. **单镜 ≤5s**，否则节奏变慢 —— 这是最硬的约束，已写进校验器
2. **视频内容文案要与语音文案分离**：画面应有自己的信息密度，可画表格/流程图
3. **字幕过长**导致节奏慢：每条 15–20 中文字，用 ASR 重切（**不要再用素材自带 srt**）
4. 版式**头重脚轻**、竖版图偏小、字幕字体过大
5. 动效/模板库**利用不充分**
6. 缺片头，片尾太简陋
7. **中视频暂缓优化**，聚焦短视频横竖版

### 已完成
| 项 | 结果 |
|---|---|
| MiniMax ASR | ✅ `POST https://api.minimax.cn/v1/speech_to_text`，`model=asr-1.0`，`verbose_json` + `timestamp_level=word`（中文**按字**给时间戳） |
| 字幕重切 | ✅ 49.66s → 251 单元 → **20 条**，平均 2.18s / 13.9 字（原 5 条 × 10s） |
| 5s 上限 | ✅ `MAX_SHOT_FRAMES = 150`，超限**切分**；节奏优先于卡数 |
| 图文类镜头 | ✅ 新增 `figure-panel` / `stat-compare` / `flow-diagram` |
| 分镜 v3 | ✅ 短视频 6 镜 → **12 镜**（每镜 ≤4.6s），补片头 eyebrow 与片尾 CTA |
| 调参集中化 | ✅ `theme.ts` 的 `TUNING` 对象，**调风格只改一处** |
| 版式修正 | ✅ `contentCenterY`（已扣字幕带）居中，治头重脚轻；字幕 46→40px |
| 调参手册 | ✅ [docs/guides/02_video_tuning.md](docs/guides/02_video_tuning.md) |
| 成片 | ✅ 短视频横竖版均重渲（49.73s） |

### 三个本轮的硬教训
1. **`_relayout` 的余数必须均摊**，不能塞给末镜 —— 塞给末镜会造出 1000+ 帧的巨物，
   切分时反复超限（改了一轮才收敛）
2. **收敛顺序不可调换**：`relayout ⇄ split` 迭代 → `converge` → `resequence`。
   `_resequence` 是专门为「合并后收尾」写的，**不能再切分**（否则镜数立刻反弹）
3. **字号必须按最长行自适应**：中文 1.0em / 拉丁 0.55em 折算，
   否则「清华团队登 Science Robotics」会在单词中间折行（`Science Rob|otics`）

### 中视频状态
**本轮明确暂停优化。** 其镜数 10 镜 / 4665 帧，单镜平均 15.5s **严重超出 5s 上限** ——
下次优化时会被校验器切成大量镜头，需要重新设计分镜而不是靠校验器硬切。


**「整片渲染被沙箱管道拦」是错误判断。** 真因：Remotion 把预编码 mp4 写到 `%TEMP%`，
`%TEMP%` 在工作区外被沙箱拒绝写入 → ffmpeg 报 `Permission denied` → compositor 崩溃 →
Node 侧只抛出**极具误导性**的 `write EOF`。

**修法**：`TMP`/`TEMP` 指进工作区（`render.ps1` 与 `build_env()` 已内置）。
**整片渲染在本会话内可行。**

⚠️ **排查纪律**：见到 `write EOF` / `EPERM` / 此类底层报错，
**必须去全量日志搜 `denied`/`failed`**，真因通常被截断在更上面。
我因为只看了日志尾部而白查两轮，详见
[docs/issues/005](docs/issues/005-render-fails-outside-workspace-temp.md)（含误判过程留档）。

> **Round 10 补充**：`write EOF` 还有一个成因 —— **字幕 404**。
> `delayRender()` 在 fetch 失败时不 release，渲染管线挂起 → 管道写超时 → 报成 `write EOF`。
> 同一个根因（路径前缀被拼两次）在竖屏报 `404`、在横屏报 `write EOF`。
> 所以搜日志时要**同时搜 `404`**。

## Round 10：换一篇文章验证兼容性与易用性

### 任务
用 `20261004` Omni-IO Skills 素材，**只用脚本**生成短视频，验证程序能否直接复用。

### 结论：主干可复用，但暴露 6 个缺陷（详见 [issues/006](docs/issues/006-new-article-compatibility-gaps.md)）

| # | 缺陷 | 性质 |
|---|---|---|
| 1 | TS 加了 3 个图文镜头类型，**Python 契约没同步** | 「改了 A 没改 B」 |
| 2 | Composition 的 `durationInFrames` **写死**成老素材的 1490/4665 | 「为单一素材写死」 |
| 3 | 脚本硬编码素材名；`slugify` 截断导致**同一素材重复导入** | 「为单一素材写死」 |
| 4 | `_relayout` 收敛顺序坑（前轮已修，本轮再验证） | 已修 |
| 5 | **来源标注写死在 `FilmShell`** → 新素材成片仍显示上一家的出处 | 「为单一素材写死」 |
| 6 | **镜数不足 → 镜头被切分 → 同一画面重复播** | 规格冲突（最严重） |

### 缺陷 6 的完整因果（本轮最有价值的一条）
```
音频 48.16s = 1445 帧
单镜上限 150 帧 → 至少需要 10 镜
但 prompt 的 constraints 写 5–6 镜（素材集体系之前的常量，未同步）
模型给 8 镜 → _relayout 撑满 1445 帧 → 每镜 ≈180 帧 → 超限被切分
→ 切分是复制内容 → 同一画面播 2–3 遍
```

**教训：「切分」这个兜底会把「规划错误」转译成「观感缺陷」。**
兜底保住了时长与节奏，但代价是内容重复 ——
**兜底不能替代正确的规划，约束必须前移到 prompt。**

**修法**：`planner.build_user_prompt` 算 `min_for_pacing = ceil(total_frames/150)`，
`shot_lo = max(区间下限, 它)`、`shot_hi = shot_lo + 3`（留 3 镜余量，
因为总帧数不可能整除）；`constraints["shot_duration_max_frames"]` 从 **700 改成 150**
（与 `validate.MAX_SHOT_FRAMES` 对齐 —— 两边原本不一致）；
`system.md` 加自检公式与后果说明。

**效果（同素材同模型）**：8 镜 / 5 镜被切 / 内容重复 / 3 种镜头类型
→ **11 镜 / 0 切分 / 无重复 / 7 种镜头类型**。

### 本轮新建的基建
| 模块 | 作用 |
|---|---|
| [`videogen/sources.py`](../src/videogen/sources.py) | **素材集抽象**：`AssetSet` / `load_set` / `import_from_article` / `list_sets` / `find_set_by_source`（防重复导入） |
| [`scripts/import_article.py`](../scripts/import_article.py) | 导入一篇 DailyNewsAssistant 产物为素材集（自动提取标题/副标/口播/图片/来源标注） |
| [`scripts/render_set.py`](../scripts/render_set.py) | **一条命令出片**：编译 props → 镜像素材到 `public/` → 渲染两个方向 |
| [`remotion/src/theme/assetPath.ts`](../remotion/src/theme/assetPath.ts) | 资源路径解析（`imageUrl`/`audioUrl`），修掉前缀被拼两次导致的 404 |
| `Root.tsx` 的 `SetLandscape`/`SetPortrait` | **通用 Composition**：时长/帧率从 props 读（`calculateMetadata`），一个 id 服务任意素材 |

### 素材集（现有）
- `omni-io-skills`：arXiv:2609.31847，48.16s / 4 图 / 11 镜 / 来源标注 `arXiv:2609.31847`
- 内置 `short` / `mid`：清华机器人足球（**尚未迁入素材集体系**，仍是 legacy 路径）

### 费用
本轮 **2 次 ASR + 2 次 LLM 规划**（第一次规划因缺陷 6 重做），合计约 ¥0.15。
ASR 与 LLM 结果均有缓存，重跑调参时零费用。

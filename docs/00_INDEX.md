# VideoGenResearch-deepseek — 文档索引

> **按需加载**。默认只读本文件 + [memory/project.md](../memory/project.md)。
> 每份文档都标了「什么时候加载它」——不要一次性把 `docs/` 读进来（那是主要成本来源）。

## 这是什么

一个**技术验证 + 技术调研**项目：验证 Remotion + video-shotcraft 做「代码驱动视频」的用法与上限，
并沉淀出可被后续 `Agent_VideoGen_Module` 复用的 Python 模块。

**不是**：一次性宣传片脚本集合。见 memory D4。

## 开发守则

完整准则见 [guides/00_dev_principles.md](guides/00_dev_principles.md)（含省 token 的工程习惯）。
第一次接手必读；之后按需查。

## 阶段与文档

流程：`调研 → 构建方案 → 讨论&调整 → 开发 → 测试 → debug&修改 → 代码审阅(人工) → git cmd(人工)`

### 0. 调研（research）

| 文档 | 内容 | 什么时候加载 |
|---|---|---|
| [research/00_tool_landscape.md](research/00_tool_landscape.md) | 「代码即渲染」工具横评与选型结论 | 质疑选型时 / 想换工具时 |
| [research/01_remotion_usage.md](research/01_remotion_usage.md) | Remotion v3/v4 使用方法与核心 API | 写/改任何 Remotion 代码前 |
| [research/02_video_shotcraft_usage.md](research/02_video_shotcraft_usage.md) | **video-shotcraft 技术手册**（2481 行）：八阶段工作流 / 27 条审美准则 / 157 卡汇总 / 组件 props / 音频 / 渲染命令。**开头有 3 条校正，务必先读那一节** | 选镜头卡、用资产、走工作流前 |
| [research/shot_catalog.md](research/shot_catalog.md) | 镜头卡速查索引（157 张，脚本生成勿手改） | 选卡、算时长预算时 |
| [research/03_article_materials.md](research/03_article_materials.md) | 本次素材分析：时轴、关键数字、7 张图语义判读 | 排分镜 / 写 spec 时 |
| [research/04_bgm_and_audio.md](research/04_bgm_and_audio.md) | BGM 能力与算力开销结论 | 决定是否加 BGM 时 |
| [research/_ref/](research/_ref/) | 调研中间产物（源组件 TSX 副本、157 卡 frontmatter 原文、library.json） | 需要查组件原始接口时 |

### 1. 方案（plan）

| 文档 | 内容 | 什么时候加载 |
|---|---|---|
| [plan/00_dev_plan.md](plan/00_dev_plan.md) | 模块划分、接口草案、单测清单、成本估算 | 开工前 / 方案调整后 |
| [plan/01_git_commits.md](plan/01_git_commits.md) | 分步 git 提交规划（与实现对齐） | 提交前 |

### 2. 设计（design）

| 文档 | 内容 | 什么时候加载 |
|---|---|---|
| [design/00_platform_output_spec.md](design/00_platform_output_spec.md) | 小红书/抖音 横竖屏输出规格 + 安全区 | 定渲染参数、排字幕位置时 |
| [design/01_theme_palettes.md](design/01_theme_palettes.md) | 科技感主题配色 + 样图 + 白底图表处理规范 | 做蒙皮 / 调色时 |
| [design/02_storyboard.md](design/02_storyboard.md) | 短视频 6 镜 / 中视频 10 镜的分镜选型与时间码 | 排分镜、实现镜头时 |

### 3. 架构（architecture）

| 文档 | 内容 | 什么时候加载 |
|---|---|---|
| [architecture/00_pipeline.md](architecture/00_pipeline.md) | 生成流程 / prompt / script / workflow 架构 | 工程化、接 LLM 时 |
| [architecture/01_spec_schema.md](architecture/01_spec_schema.md) | VideoSpec 字段契约 + 修复策略（LLM 输出契约） | 改 spec 结构 / 写 prompt 时 |

### 4. 操作指南（guides）

| 文档 | 内容 | 什么时候加载 |
|---|---|---|
| [guides/00_dev_principles.md](guides/00_dev_principles.md) | 开发守则（用户口径 + 省 token 习惯）。**§5.1 是 `git_commands.md` 的更新机制** | 首次接手 / 写 git 指令前 |
| [guides/01_remotion_guide.md](guides/01_remotion_guide.md) | Remotion 工程上手：3 条硬规则、命令、结构、设计决定、待修项 | 跑工程 / 换机器 / 渲染报错时 |
| [guides/02_video_tuning.md](guides/02_video_tuning.md) | **视频制作调参手册**：改哪个文件/哪个值、值变大变小会怎样、版式、动效、新增镜头、踩坑清单 | **动手调风格前必读** |
| [03_unit_tests.md](03_unit_tests.md) | 测试总览 + 按改动定位该跑哪个节点 + 复测指令 | 想知道跑哪个测试时 |

### 4.1 多素材集工作流（换一篇文章）

素材按**目录**组织，不在代码里写死：`assets/sets/<name>/`。
完整流程见 [issues/006](issues/006-new-article-compatibility-gaps.md)，三步命令：

```powershell
& $py scripts\import_article.py "<DailyNewsAssistant 产物目录>"
& $py scripts\asr_subtitles.py --set <name>
& $py scripts\plan.py --set <name>          # 1 次 LLM 调用
& $py scripts\render_set.py --set <name>    # 两个方向出片，零费用
```

> ⚠️ **唯一需要人工介入的一步**：`images/index.json` 的图片语义标注
> （原始抓取元数据 caption 全为 null，无法自动生成）。它是规划质量的主要输入。

### 7. 验证证据（out/qa）

渲染自检静帧（每次改镜头后的产物归档处）：`out/qa/` 与 `out/<素材集>/qa/`。
**这是最快的视觉验收手段**；整片渲染耗时约 4 分钟/方向，配置见
[guides/02_video_tuning.md](guides/02_video_tuning.md) §1。

### 5. 问题记录（issues）

`docs/issues/NNN-<slug>.md`，一问题一文件。**发现的问题写这里，不写在代码注释里。**

### 6. 审查（reviews）

`docs/reviews/` —— 人工审阅与阶段 review 的结论。

## 项目专属 skill

- [skill/](../skill/) —— 调用 video-shotcraft + Remotion 的薄壳 skill，供 `Agent_VideoGen_Module` 引用。

## 目录约定

```
assets/    素材（图片、音频、字体）——只放素材
docs/      全部文档，本索引是唯一入口
memory/    跨会话记忆
out/       渲染产物（只放产物；脚本绝不进这里）
scripts/   可执行脚本（薄壳，业务逻辑在 src/）
skill/     项目专属 skill
src/       可复用 Python 包 videogen/
tests/     单元测试（每功能一个节点，注释内含复测指令）
```

# git 提交指令 / git commit commands

> **交给人工执行。AI 不执行 `commit` / `push`**（开发守则 §5）。
> **本文件是一次性的**：覆写前先 `git log --oneline` 核对上一组已经执行过。
>
> 全部命令在 `C:\Users\75203\Downloads\xkd\VideoGenResearch-deepseek` 下执行。
> 当前仓库状态：`master` 分支、**尚无任何 commit**、全部文件为 untracked。

## 提交前检查（必须）

```powershell
cd C:\Users\75203\Downloads\xkd\VideoGenResearch-deepseek

# 1) 密钥绝不能进库 —— 这条必须空输出
git status --porcelain | Select-String '\.env'
# .env 已被 .gitignore 覆盖；若上面有输出，先停下来修 .gitignore

# 2) 素材副本与生成物不应入库（应看到 public/ 与 out/ 被忽略）
git check-ignore -v remotion/public/fonts/NotoSansSC-VF.ttf assets/images/01_mmbiz-qpic-cn.jpg

# 3) 测试仍全绿
& "C:\Users\75203\miniforge3\envs\ov_env_py312\python.exe" -m pytest -q
```

> **注意**：`assets/` 下**图片与音频被 .gitignore 排除**（外部素材，不入库），
> 但 `assets/images/index.json`（人工判读的语义索引）与 `assets/shot_catalog.json`
> （脚本生成）**必须入库** —— 它们是代码的输入，不是可再生素材。
> `git add assets/` 会自动遵守 .gitignore；下面用 `-f` 显式加那两个索引。

---

## 第 1 步：项目骨架与开发守则

```powershell
git add .gitignore README.md pyproject.toml
git add docs/00_INDEX.md docs/guides/00_dev_principles.md docs/03_unit_tests.md
git commit -m "chore: 项目骨架、开发守则与测试约定

- pyproject.toml: pytest 默认排除 live/slow 标记（成本护栏）
- .gitignore: 排除密钥、渲染产物、node_modules、Remotion public 副本、外部素材
- docs/00_INDEX.md: 文档按需加载的唯一入口
- docs/guides/00_dev_principles.md: 测试尺度、git 纪律、注释规范、省 token 习惯
- docs/03_unit_tests.md: 按改动定位该跑哪个测试节点"
```

## 第 2 步：路径与领域模型

```powershell
git add src/videogen/__init__.py src/videogen/paths.py src/videogen/models.py
git commit -m "feat(videogen): 路径解析与领域模型

- paths.py: 唯一允许知道「项目在哪」的地方，支持 VIDEOGEN_PROJECT_ROOT 覆盖
- models.py: ShotCard / ImageAsset / SubtitleSegment / Timeline / VideoResult
  用 dataclass 而非 pydantic，因为 spec 校验要输出中文可读的修复建议"
```

## 第 3 步：字幕解析与时间轴（阶段 1）

```powershell
git add src/videogen/timeline.py tests/conftest.py tests/test_timeline.py
git commit -m "feat(videogen): SRT 解析与时间轴构建

- 按时间码行切块而非「序号+空行」，容忍 BOM/CRLF/点号毫秒/缺序号
- 总时长取音频实测值而非字幕末条，保证片尾不被截断
- 锁定真实素材帧数：短 1490 帧、中 4665 帧（30fps）
- tests: 13 个节点（含 5 个真实素材集成断言），0.11s 全绿"
```

## 第 4 步：素材语义索引与镜头卡目录

```powershell
git add assets/images/index.json assets/shot_catalog.json
git add src/videogen/assets.py src/videogen/shot_catalog.py
git add tests/test_assets.py
git commit -m "feat(videogen): 素材语义索引与镜头卡目录加载

- assets/images/index.json: 7 张图的人工语义判读（原始抓取 caption 全为 null）
  含 narrative_use 与 suggested_shots，供 LLM 规划阶段消费
- assets/shot_catalog.json: 由 scripts/build_shot_catalog.py 生成，157 张卡/10 类
- assets.py: 加载 + 尺寸核对（素材被替换后静默错版会红）
- shot_catalog.py: 只读 frontmatter 索引，卡片正文按需单独读取（省 token）
- tests: 13 个节点，0.21s 全绿"
```

## 第 5 步：调研脚本（可复现）

```powershell
git add scripts/build_shot_catalog.py scripts/make_palette_swatch.py
git commit -m "feat(scripts): 镜头卡索引与配色色卡生成脚本

- build_shot_catalog.py: 从 video-shotcraft/references/shots 抽 157 张卡 frontmatter
- make_palette_swatch.py: 生成 5 套科技感配色色卡（PNG + JSON），
  含 WCAG 亮度自适应的色块文字配色"
```

## 第 6 步：调研文档与问题记录

```powershell
git add docs/research docs/issues
git commit -m "docs: 调研文档与问题记录

- research/02_video_shotcraft_usage.md: video-shotcraft 技术手册（213KB）
  八阶段工作流 / 27 条审美准则 / 157 卡索引 / 组件 props / 音频 / 渲染命令
  开头含 3 条校正（含 SFX 数量三方核对结论：149）
- research/04_bgm_and_audio.md: Remotion 文档与 BGM 能力调研（132KB）
  结论:v3 文档站 5 个关键特性全 404、MusicGen 权重 CC-BY-NC 禁商用、
  程序化合成 1-10 秒/条、Remotion 自动化档 \$0.01/次+\$100/月
- research/03_article_materials.md: 素材分析（时轴/关键数字/7 张图判读）
- research/shot_catalog.md: 157 张卡速查表（脚本生成）
- research/_ref/: 组件源码副本与 frontmatter 原文（备查）
- issues/001~004: 沙箱缓存、TTC 字体、PowerShell 编码、Remotion symlink 权限"
```

## 第 7 步：设计文档（配色 / 输出规格 / 分镜）

```powershell
git add docs/design
git commit -m "docs(design): 主题配色、平台输出规格与分镜设计

- 01_theme_palettes.md + 色卡 PNG: 5 套候选，选定 cyan-noir；
  含白底学术图的处理规范（卡片化承载 + 压暗，不改图内像素）
- 00_platform_output_spec.md: 横竖屏分辨率/CRF/安全区，安全区为唯一权威处
- 02_storyboard.md: 短视频 6 镜、中视频 10 镜的卡选型与时间码"
```

## 第 8 步：架构文档

```powershell
git add docs/architecture
git commit -m "docs(architecture): 生成流水线与 spec 契约架构

- 五阶段流水线：素材理解 -> LLM 规划 -> 校验编译 -> 渲染 -> 归档
- 三条硬规则：镜头类型封闭集合、spec 可校验、产物可复现
- 针对 minimax 黑盒 spec 问题的正面解法（修复留痕 + 兜底 spec）
- 对外只暴露 generate_video() 一个稳定入口"
```

## 第 9 步：Remotion 工程骨架

```powershell
git add remotion/package.json remotion/package-lock.json remotion/tsconfig.json remotion/remotion.config.ts
git commit -m "feat(remotion): 工程骨架与依赖锁定

- Remotion 4.0.484 / React 19.2.7（非 v3：v3 无 zod schema/calculateMetadata 等）
- remotion.config.ts: h264 + yuv420p + concurrency 4"
```

## 第 10 步：主题与版式基础件

```powershell
git add remotion/src/theme/theme.ts remotion/src/theme/fonts.ts remotion/src/theme/layout.ts remotion/src/theme/assetDims.ts
git add remotion/src/theme/Caption.tsx remotion/src/theme/ShotScaffold.tsx
git commit -m "feat(remotion): 主题 token、字体门禁与横竖屏版式派生

- theme.ts: cyan-noir token（唯一权威在 docs/design/01_theme_palettes.md）
- fonts.ts: delayRender 门禁 —— 无头 Chromium 字体失败不报错只静默 fallback，
  而且逐帧渲染会让前后帧字体不一致
- layout.ts: 横竖屏**不缩放**，尺寸与安全区由 useVideoConfig 派生；
  safe.bottom 额外扣掉字幕带高度（镜头内容与字幕打架的修复）
- assetDims.ts: 素材尺寸编译期镜像，供 fitSize 算确定显示尺寸"
```

## 第 11 步：成片组装与字幕轨

```powershell
git add remotion/src/index.ts remotion/src/Root.tsx remotion/src/compositions
git commit -m "feat(remotion): 4 个 Composition、字幕轨与成片骨架

- Root.tsx: ShortLandscape/ShortPortrait 1490 帧、MidLandscape/MidPortrait 4665 帧，
  帧数与音频实测时长严格对应
- compositions/types.ts: FilmProps/ShotSpec 契约（镜头类型封闭集合）
- CaptionTrack.tsx: SRT 在渲染期解析并与 Python 侧行为对齐
- FilmShell.tsx: 音频 + 镜头序列 + 字幕轨 + 来源标注
- ShortFilm.tsx / MidFilm.tsx: 内置默认分镜"
```

## 第 12 步：镜头组件

```powershell
git add remotion/src/ui remotion/src/shots
git commit -m "feat(remotion): 6 个镜头组件与分发器

- ui/DigitRoll.tsx: 里程表数字滚动（tabular-nums，非数字位驻场不滚）
- ui/ImagePanel.tsx: 白底学术图的面板承载（压暗 + 描边 + 外阴影）
- shots/TitleReveal.tsx: 片头字标逐字解锁（继承 letterspace-materialize 运动语法）
- shots/NumberRoll.tsx: 王牌数字全屏亮相
- shots/PageSpotlight.tsx: 页面聚光锁定（继承 spotlight-hero-card 动作弧）
- shots/ScanAnnotate.tsx: 扫描线匀速标注（零缓动 + bbox 反算触发 + 实时计数）
- shots/RadarReveal.tsx: 角落匀速显影（spotlight-sweep-moves C 式）
- shots/OutroLockup.tsx: 收尾字卡 lockup（收束 + 刹车过冲 + 逐字滑入）
- ShotRenderer.tsx: 类型分发；未实现的类型落到明显可辨的占位，不静默渲空白"
```

## 第 13 步：素材同步脚本与操作指南

```powershell
git add remotion/scripts/link-assets.ps1 docs/guides/01_remotion_guide.md
git commit -m "feat(remotion): 素材同步脚本与工程上手文档

- link-assets.ps1: 用复制而非 junction —— Remotion 打包对 public/ 内的
  symlink 调 fs.symlink，Windows 建符号链接需管理员/开发者模式，
  两样都没有会 EPERM 并拖垮整条渲染链
  带 -Check 开关与 .assets-manifest.json 防漂移；文件含中文必须带 UTF-8 BOM
- guides/01_remotion_guide.md: 三条硬规则、命令清单、Composition 表、待修项"
```

## 第 14 步：开发方案与进度

```powershell
git add docs/plan
git commit -m "docs(plan): 开发方案、批次排期与成本模型

- 范围/模块划分/接口草案/9 个开发批次
- 已实测确认的能力清单（渲染链全部打通）
- 成本模型含 Remotion 自动化档计费提醒"
```

## 第 15 步：spec 契约与校验降级（LLM 输出契约）

```powershell
git add src/videogen/spec.py src/videogen/validate.py tests/test_validate.py
git commit -m "feat(videogen): VideoSpec 数据契约与校验降级

- spec.py: LLM 输出契约的 Python 侧真源，与 remotion/types.ts 逐字段对齐；
  镜头类型是封闭枚举；dict 往返与 UTF-8 落盘（中文不转义，便于人工 grep）
- validate.py: 阶段 3 的校验与就地修复；12 个修复分支各自留痕
  （素材缺失/时长越界/标注越界/指标超量/文案超长/字幕段号越界…）
- 未知镜头类型**报错而非猜测** —— 猜类型会静默改掉创作意图
- 末镜吸收总帧数余数，保证片尾不留空（音频还在响）
- tests: 20 个节点覆盖每个修复分支 + 不可修复报错 + 时间轴对齐 + 序列化往返"
```

## 第 16 步：中视频 4 个新镜头组件

```powershell
git add remotion/src/ui/Confetti.tsx remotion/src/shots/CounterBurst.tsx
git add remotion/src/shots/BeforeAfter.tsx remotion/src/shots/SlowPush.tsx remotion/src/shots/TimelineTravel.tsx
git commit -m "feat(remotion): 中视频 4 个镜头组件

- ui/Confetti.tsx: 52 片真物理彩纸，参数由 index 派生（确定性）
- shots/CounterBurst.tsx: easeOutQuart 计数冲刺 + scale 过冲 + 纸屑抢拍
  （纸屑比计数落定早 0.04 归一化时间 —— 卡上明确要求这半拍）
- shots/BeforeAfter.tsx: 快甩 12f vs 慢扫 48f（5:1）+ 过冲回弹 + 手柄速度差分拉伸
- shots/SlowPush.tsx: Easing.in(quad) 匀加速推近 1.0→1.14 + 暗角同曲线
- shots/TimelineTravel.tsx: 分段变速 + 相机跟随活动刻度 + 闭式反解弹立时机
  （早先用「世界匀速左移 + 总量估算」会把末刻度推出画外，已返工）"
```

## 第 17 步：中视频分镜与类型接线

```powershell
git add remotion/src/compositions/MidFilm.tsx remotion/src/compositions/ShortFilm.tsx
git add remotion/src/compositions/types.ts remotion/src/shots/ShotRenderer.tsx
git commit -m "feat(remotion): 中视频 10 镜分镜与镜头分发接线

- types.ts: 新增 ShotStop，并导出 FilmProps/ShotSpec 契约
- MidFilm.tsx: 10 镜落地，覆盖 8 种镜头类型
- ShotRenderer.tsx: 10 种类型全部分发；未实现类型落到明显可辨的占位
- ShortFilm.tsx: 收尾镜改用 tagline 字段（与 OutroLockup 的 props 对齐）"
```

## 第 18 步：操作指南与 git 指令

```powershell
git add docs/guides/01_remotion_guide.md docs/guides/00_dev_principles.md docs/git_commands.md
git commit -m "docs: Remotion 操作指南、动画常见坑与 git 指令

- guides/01_remotion_guide.md: 3 条硬规则、命令清单、Composition 表、待修项
- guides/00_dev_principles.md §8: 动画代码 4 条常见坑
  （interpolate 区间不等长、maxHeight 裁剪标注、flex/absolute 混用、内容撞字幕）
- git_commands.md: 分步提交指令（本文件为一次性文件）"
```

## 第 19 步：项目专属 skill 与 spec 契约文档

```powershell
git add skill/SKILL.md docs/architecture/01_spec_schema.md
git commit -m "docs: 项目专属 skill 与 spec 字段契约

- skill/SKILL.md: 供 Agent_VideoGen_Module 引用的薄壳 skill
  含五阶段流水线、10 种镜头集、3 条会卡住的硬规则、成本与许可提醒
- architecture/01_spec_schema.md: spec 字段级约束与修复顺序（唯一权威处）"
```

## 第 20 步：LLM 配置与 DeepSeek 客户端

```powershell
git add src/videogen/llm_config.py src/videogen/llm.py
git commit -m "feat(videogen): LLM 配置装载与 DeepSeek 客户端

- llm_config.py: 唯一的密钥读取入口；Settings 的 repr/str/masked 全部打码
  （f-string 顺手打印是密钥泄露最常见的路径）；环境变量优先于 .env
- llm.py: Chat Completions 最小客户端，只做一次性 JSON 输出
  - temperature 固定 0（可复现是硬规则）
  - 429/5xx 有限退避重试；4xx 直接失败（重试无意义且烧钱）
  - 异常信息统一剥掉可能含密钥的细节
  - 容错 markdown 围栏；解析失败报出前 200 字符而不是返回空串"
```

## 第 21 步：分镜规划器与 prompt

```powershell
git add src/videogen/plan
git commit -m "feat(videogen): 分镜规划器与 prompt

- prompts/system.md: 角色与硬规则（封闭镜头集、时间轴对齐、禁止编造数字、自检清单）
- planner.py: catalog 由镜头卡索引**生成**而非手写（避免与实现漂移）；
  user prompt 的结构化数据一律用 JSON 块给出，让模型照抄而不是理解
- extract_allowed_numbers: 数字白名单从权威文本抽取，
  同时收录中文数字写法（旁白里是'六十四'这种）
- plan_video: kind/fps/总帧数/主题由服务端权威裁定，不信模型自填
- pyproject: prompts 作为 package-data 随包分发"
```

## 第 22 步：规划入口脚本与 LLM 单测

```powershell
git add scripts/plan.py tests/test_plan.py
git commit -m "feat(scripts): 分镜规划入口脚本与 LLM 单测

- scripts/plan.py: 薄壳，把素材→时轴→LLM→校验→落盘串成一条命令
  --dry-run 用内置假响应演练（零费用），假响应**故意**含越界时长，
  用于验证校验器确实在兜底
- tests/test_plan.py: 21 个零费用节点（网络全 mock）覆盖
  密钥打码/.env 装载/JSON 容错/prompt 组装/白名单抽取/服务端字段覆盖
- test_live_plan_short_video 标 live：真实调用，默认被 addopts 排除"
```

## 第 23 步：spec → props 编译

```powershell
git add src/videogen/compile.py
git commit -m "feat(videogen): spec 到 Remotion props 的编译

- Composition id / CRF / 成片命名三张映射表，与
  docs/design/00_platform_output_spec.md 一致
- compile_shot 只输出非空字段（Remotion 官方提示 defaultProps 过大会变慢）
- 字段名转 TS 侧 camelCase；durationInFrames 取自音频实测时长而非模型值
- missing_assets: 渲染前的最后一道闸，素材缺失不必等渲到一半才发现
- props 落盘为文件：Windows 上 --props 不能传内联 JSON（官方警告）"
```

## 第 24 步：渲染编排与端到端 pipeline

```powershell
git add src/videogen/render src/videogen/pipeline.py src/videogen/__init__.py
git commit -m "feat(videogen): 渲染编排与对外唯一入口 generate_video()

- render/remotion.py:
  - 用 node <remotion-cli.js> 而非 npx —— Windows 上 npx 是 .cmd shim，
    subprocess 的 CreateProcess 不解析它（实测 FileNotFoundError）
  - 路径一律 resolve 成绝对：子进程 cwd 是 remotion/，相对路径会解析错
  - 输出重定向到文件而非管道捕获（沙箱禁止非继承 stdio 的管道）
  - write EOF/EPERM 时错误信息给出沙箱外执行的指引
- pipeline.py: 五阶段编排（素材理解→LLM→校验编译→渲染→归档）
  - 归档 out/runs/<kind>-<theme>-<时间戳>/ 含 spec/props/manifest
  - manifest 记录 token 用量与耗时（成本核算凭证）
  - plan_only 模式零渲染成本，便于检查 spec
- __init__.py: 延迟导入对外入口（只想用 paths/timeline 的调用方不必付重依赖）"
```

## 第 25 步：端到端单测与中视频镜头版式修正

```powershell
git add tests/test_pipeline.py remotion/src/compositions/FilmShell.tsx remotion/src/shots/ScanAnnotate.tsx
git commit -m "test(videogen): 端到端单测与 props 驱动渲染

- FilmShell.tsx: 分镜改为 props 优先（Python spec 权威），
  空 props 时回退内置分镜，保证 Studio 不传 props 也能预览
- tests/test_pipeline.py: 18 个零费用节点（渲染被替换）覆盖
  编译映射/空字段省略/音频按 kind 推断/绝对路径与 CLI 构造/
  多方向渲染次数/修复进 manifest/token 台账/缺失素材告警
- 确证 props 驱动真的生效：静帧显示模型指定的 4 个标注目标与模型文案"
```

## 第 26 步：卡数校验（契约补实现）与竖屏版式修正

```powershell
git add src/videogen/validate.py tests/test_validate.py
git add remotion/src/shots/TimelineTravel.tsx docs/architecture/01_spec_schema.md docs/guides/00_dev_principles.md
git commit -m "fix(videogen): 补齐卡数校验，修正时间轴镜头竖屏版式

- validate.py: 新增 _converge_shot_count —— 卡数区间在 01_spec_schema.md
  与 system prompt 里都写了，但校验器**漏了实现**。
  实测暴露：中视频真实调用给出 11 镜（上限 10）却直接通过。
  - 超限 → 合并相邻最短一对，绝不丢镜头（丢镜头=丢旁白覆盖）
  - 优先合并内部对，**保护首镜 title-reveal 与末镜 outro-lockup** 的结构语义
  - 合并时字幕段取并集、文案用 · 拼接（不静默丢弃）
  - 不足 → 留痕但不硬凑（凑镜头需要创作）
- TimelineTravel.tsx:
  - 卡片垂直位置改为**底边锚定**（translateY(-100%)）——
    原先写死 top: axis-250px，竖屏卡内容换行后实际高度不同，卡片悬空
  - 轴线位置竖屏压到安全框 0.72 处，避免时间轴挤在上半屏
- 00_dev_principles.md §8: 补 3 条（边锚定而非算像素、
  契约必须代码兜底、横屏验过不等于竖屏成立）
- tests: 5 个新节点覆盖卡数合并/首末镜保护/字幕并集/不足留痕"
```

## 第 27 步：竖屏宽幅图与收尾镜字幕修正

```powershell
git add remotion/src/shots/PageSpotlight.tsx remotion/src/compositions/CaptionTrack.tsx remotion/src/compositions/FilmShell.tsx docs/guides/00_dev_principles.md
git commit -m "fix(remotion): 竖屏宽幅图收窄与收尾镜不铺字幕

- PageSpotlight.tsx: 竖屏用 0.70 × 0.32 而非 0.96 × 0.52 ——
  整页截图是宽幅图（1280×544），竖屏按宽度撑满后高度仍过大，
  把镜头文案推进图底并叠上字幕带（返工两次才收敛）。
  宽幅素材在竖屏应作**引证小图**，不是主视觉。
- CaptionTrack.tsx: 新增 excludeRanges，按帧区间跳过字幕
- FilmShell.tsx: 收尾镜的帧区间不铺字幕带 ——
  旁白此时就是 CTA，与 lockup 的字标+标语重复，两处一起显示既冗余又互相压
  （aesthetic-rules C1：「品牌收尾镜头除外，保持干净」）
- 00_dev_principles.md §8: 补 2 条（宽幅图的竖屏处理、旁白与画面文字去重）
- 补齐 page-spotlight / outro-lockup 的横竖屏静帧，10 种镜头类型全方向覆盖"
```

## 第 28 步：ASR 字幕模块（MiniMax）

```powershell
git add src/videogen/asr.py src/videogen/subtitle.py scripts/asr_subtitles.py
git add assets/audio/asr_short.json assets/audio/short.asr.srt
git commit -m "feat(asr): 接入 MiniMax ASR 并重切字幕

问题：素材自带的 srt 按长句切，单条最长约 10s —— 既拖慢节奏又对不上画面。

- asr.py: MiniMax speech_to_text 客户端
  - POST {base}/v1/speech_to_text，multipart: model=asr-1.0 + file
  - response_format=verbose_json + timestamp_level=word → **中文按字**给时间戳
  - 端点按 .cn / .minimaxi.com / .io 依次兜底；429/5xx 退避重试，
    400/401/402/413/422 直接失败（重试无意义）
  - 兼容 MINIMAX_API_KEY 与 MiniMax_API_KEY 两种环境变量名
- subtitle.py: 字级时间戳 → 合规字幕条
  - 切分优先级：强停顿 > 句末标点 > 字数上限 > 弱停顿 > 次级标点
  - **数字保护**：不得在数字中间切分（否则「零点三|四四米」读坏）
  - 过短尾条与上一条合并；导出 SRT 时钳制单条时长
- scripts/asr_subtitles.py: 薄壳；ASR 结果**缓存**以免调参时重复计费（--reuse）

实测：49.66s 音频 → 251 个单元 / 20 条字幕
      平均 2.18s、平均 13.9 字、最长 3.30s（原素材 5 条 × 平均 10s）"
```

---

## 第 29 步：节奏约束（单镜 ≤5s）与图文类镜头

```powershell
git add src/videogen/validate.py tests/test_validate.py
git commit -m "feat(validate): 单镜 5 秒上限，节奏优先于卡数

用户反馈：每个分镜不要超过 5s，否则视频节奏会变慢。

- 新增 _split_long_shots：超 150 帧的镜头**切分**为等长若干段
  （复制内容、不丢信息；总时长由音频锁定，多出的时间只能变成更多镜头）
- MAX_SHOT_FRAMES 从 700 改为 150；新增 ABSOLUTE_MAX_SHOT_FRAMES=700 硬护栏
- _relayout 改为**余数均摊到所有镜头**，不再塞给末镜
  （塞给末镜会造出 1000+ 帧的巨物，切分时反复超限 —— 实测修掉的 bug）
- _converge_shot_count 改为**只在合并后仍 ≤150 帧时才合并**，
  否则主动放弃并留痕「节奏优先于镜数」
- 新增 _resequence：合并后收尾对齐（不再切分，否则镜数立刻反弹）
- 收敛顺序：逐镜修复 → 迭代{relayout ⇄ split} → converge → resequence

测试：新增 5 个节点覆盖切分/均摊/首末镜保护/字幕并集/放弃合并；
共 96 通过（含把旧测试数据从 300 帧改为 ≤150 帧，因为新上限是正确行为）"
```

---

## 第 30 步：图文类镜头与全局调参

```powershell
git add remotion/src/shots/FigurePanel.tsx remotion/src/shots/StatCompare.tsx remotion/src/shots/FlowDiagram.tsx
git add remotion/src/shots/ShotRenderer.tsx remotion/src/compositions/types.ts
git add remotion/src/theme/theme.ts remotion/src/theme/layout.ts remotion/src/theme/Caption.tsx
git add remotion/src/shots/TitleReveal.tsx remotion/src/shots/TimelineTravel.tsx
git add remotion/src/compositions/ShortFilm.tsx remotion/src/Root.tsx
git commit -m "feat(remotion): 新增三类图文镜头，全局调参集中化，修版式

用户反馈：动效与模板库没被充分利用、画面头重脚轻、竖版图偏小、字幕偏大。

新增镜头（让画面承载**独立于旁白的内容文案**）：
- figure-panel：角标+标题+要点逐条左滑入（**双星**标强调色）+结论条
- stat-compare：双条竞赛式生长（outQuart）+ 胜方高亮脉冲，差值用长度直接看出
- flow-diagram：节点错峰 pop + 连线 draw-on + 频率徽章脉冲

调参集中化：
- theme.ts 新增 TUNING 对象 —— **调风格只改这一处**，各镜头统一读取
- Caption.tsx 字幕字号 46/44 → 40/38（用户反馈过大），改从 TUNING 读

版式修正：
- layout.ts 新增 contentHeight / contentCenterY（**已扣掉字幕带**）
- 图文镜头改为在 contentCenterY 上垂直居中 + translateY(-50%)
  → 治「头重脚轻」：原先从 safe.top 顶对齐，内容堆在上半屏、下方大片空白
- TitleReveal 字号按**最长行**自适应（中文 1.0em / 拉丁 0.55em 折算）
  → 修掉「Science Robotics」在单词中间折行
- TimelineTravel 改为自建本地坐标系
  → 修掉卡片跑出画框（外层 translateY 与内部绝对坐标冲突）

分镜 v3：短视频 6 镜 → **12 镜**（每镜 ≤4.6s），片头补 eyebrow、
片尾补 CTA lockup，引入 3 个图文类镜头
字幕源改用 ASR 重切版（Root.tsx）"
```

---

## 第 31 步：调参手册与文档同步

```powershell
git add docs/guides/02_video_tuning.md docs/00_INDEX.md
git add docs/architecture/01_spec_schema.md docs/plan/00_dev_plan.md docs/guides/00_dev_principles.md
git add docs/issues/005-render-fails-outside-workspace-temp.md docs/git_commands.md
git rm --cached docs/issues/005-render-blocked-by-pipe-sandbox.md 2>$null
git commit -m "docs: 新增《视频制作调参手册》，同步契约与问题记录

- guides/02_video_tuning.md（新增）：面向手工调参的完整手册
  - 每条旋钮给出「改哪个文件 / 改哪个值 / 变大变小会怎样」
  - 三个坐标（safe / contentCenterY / captionCenterY）的区别
  - 各镜头类型的必填字段表、动效清单、新增镜头的四步流程
  - 踩坑清单：改了没反应 / 渲染炸了 / 元素悬空 的成因与修法
- 01_spec_schema.md §5：改为「5 秒上限优先于卡数上限」，
  记录收敛顺序不可调换的原因
- 00_dev_principles.md §8：补 4 条
  （抽帧要抽动画落定后、宽幅图竖屏处理、旁白与画面文字去重、底层报错不能只看尾部）
- issues/005 重写：真因是 %TEMP% 在工作区外，**不是**管道限制；
  留档两次误判过程与「先去全量日志搜 denied」的纪律"
```

---

## 第 32 步：素材集体系（支持任意文章）

```powershell
git add src/videogen/sources.py src/videogen/paths.py
git add scripts/import_article.py scripts/render_set.py
git add scripts/plan.py scripts/asr_subtitles.py
git commit -m "feat(sources): 素材集体系，脚本支持任意文章

问题：素材名与标题写死在 plan.py 的 SOURCES 里，换一篇文章必须改代码；
Composition 的帧数也写死成老素材的 1490/4665。

- sources.py（新增）：素材集抽象
  - AssetSet：音频/字幕/图片索引/标题/口播/来源标注的统一取用接口
  - import_from_article：一行导入 DailyNewsAssistant 产物（自动提取
    主标题/副标题/口播正文，并生成短的来源标注）
  - find_set_by_source：按 set.json 记录的来源路径去重 ——
    同一篇文章永不重复导入（slugify 截断曾导致同一目录推导出两个名字）
  - list_sets / slugify（max_len 32→64，中文信息密度高）
- paths.py：新增 asset_sets_dir()，支持 VIDEOGEN_ASSET_SETS 覆盖
- import_article.py（新增）：导入入口，含图片索引尺寸校验
- render_set.py（新增）：**一条命令出片**
  编译 props → 镜像素材到 remotion/public/<set>/ → 渲染两个方向
- plan.py：--set / --set-dir / --list-sets；产物按素材集名分目录，
  换文章不再覆盖上一套 spec
- asr_subtitles.py：--set / --audio / --out 三种入口

易用性验证见 docs/issues/006（换一篇全新文章暴露的 6 个缺陷）"
```

---

## 第 33 步：跨语言契约同步与通用 Composition

```powershell
git add src/videogen/spec.py src/videogen/compile.py src/videogen/plan/planner.py
git add src/videogen/plan/prompts/system.md
git add remotion/src/compositions/types.ts remotion/src/Root.tsx
git add remotion/src/theme/assetPath.ts remotion/src/compositions/FilmShell.tsx
git add remotion/src/compositions/CaptionTrack.tsx
git add remotion/src/shots/BeforeAfter.tsx remotion/src/shots/PageSpotlight.tsx
git add remotion/src/shots/RadarReveal.tsx remotion/src/shots/ScanAnnotate.tsx
git add remotion/src/shots/SlowPush.tsx remotion/src/ui/ImagePanel.tsx
git add tests/test_pipeline.py
git add docs/issues/006-new-article-compatibility-gaps.md
git commit -m "fix(contract): 补齐跨语言契约，资源路径统一解析，修节奏规格冲突

四处「改了 A 没改 B」/「为单一素材写死」的缺陷（详见 docs/issues/006）：

1. 镜头类型契约不同步（严重）
   前一轮在 TS 加了 figure-panel / stat-compare / flow-diagram 三个类型，
   但 spec.py 的 ShotType / SHOT_TYPES / REQUIRED_FIELDS / ShotSpec 字段、
   compile_shot、to_dict/from_dict、system prompt 全没动 ——
   脚本一生成 figure-panel 就被校验器拒绝。
   - spec.py：补 3 个类型 + ShotNode/ShotSide dataclass + 6 个字段
   - compile.py：compile_shot 输出图文类字段（否则渲染成空壳）
   - system.md：字段表、JSON 模板、篇幅约束

2. 资源路径前缀被拼两次（严重）
   组件写死 staticFile 加 images/ 前缀，素材集图片在 public/<set>/images/
   → 变成 images/<set>/images/... → 404。而 404 让 delayRender() 永不
   release，最终报成**极具误导性的** Error: write EOF（竖屏报 404、
   横屏报 EOF，同一根因）。字幕路径同理。
   - 新增 theme/assetPath.ts：imageUrl / audioUrl 统一解析
   - 约定 props 里的路径是「相对 public/ 的完整路径」，组件不再拼前缀
   - compile_shot 在素材集模式下加 <set>/images/ 前缀

3. 帧数写死 + 来源标注写死
   - Root.tsx 新增通用 Composition SetLandscape/SetPortrait，
     用 calculateMetadata 从 props 读 durationInFrames/fps
   - FilmProps 新增 durationInFrames?/fps?/source?
   - compile_props 输出这三者；FilmShell 的来源标注改为从 props 取
   - AssetSet 新增 source_label（给观众看的短标注）

4. 节奏规格冲突（导致同一画面重复播）
   音频 1445 帧、单镜上限 150 帧 → 至少 10 镜，但 prompt 的 constraints
   仍写 5–6 镜。模型给 8 镜 → _relayout 均摊到每镜 180 帧 → 超限被切分
   → 切分复制内容 → 同一画面播 2–3 遍。
   **教训：切分这个兜底会把「规划错误」转译成「观感缺陷」。**
   - planner：min_for_pacing = ceil(total_frames/150)，
     shot_lo = max(区间下限, 它)，shot_hi = shot_lo + 3（留余量）
   - constraints 的 shot_duration_max_frames 700 → 150（与校验器对齐）
   - system.md：加自检公式「镜数 ≥ ceil(total_frames/150)」

效果：8 镜 / 5 镜被切 / 内容重复 → 11 镜 / 0 切分 / 无重复 / 7 种镜头类型
测试：101 通过（新增 4 个节点锁住图片路径策略、来源标注、时长来源、图文字段）"
```

---

## 第 34 步：补齐被遗漏的配置与素材元数据

> **这一步是补漏。** 前 33 步的 `git add` 都写了具体路径，于是以下几类
> **从未被任何一步 `git add` 过**，一直挂在未跟踪状态：
> `.gitignore` 的修改、`memory/`、`remotion/scripts/render.ps1`、
> 素材自带的字幕、以及新建的 `assets/sets/`。
>
> `git status` 报出来的 `_sizes.json` 与 `remotion/debug.log` **不是漏掉，
> 是不该入库** —— 已删除，并在 `.gitignore` 里加了规则防复发。

```powershell
# .gitignore 本身也是配置，必须入库（它含素材集与日志的排除规则）
git add .gitignore
# 项目记忆：跨会话接手的唯一入口，必须入库
git add memory/project.md
# 渲染脚本（此前一直是未跟踪状态）
git add remotion/scripts/render.ps1
# 素材自带的原始字幕（.gitignore 已用 !assets/audio/*.srt 显式保留）
git add assets/audio/narration.zh.srt assets/audio/shortvideo.zh.srt

# 素材集：**只加文本，不加图片与音频**（大文件由 .gitignore 排除）
git add assets/sets/omni-io-skills/set.json
git add assets/sets/omni-io-skills/images/index.json
git add assets/sets/omni-io-skills/audio/shortvideo.zh.srt
git add assets/sets/omni-io-skills/audio/omni-io-skills.asr.srt
# ASR 原始结果一并入库：23 KB，避免新机器重跑 ASR 再次计费
git add assets/sets/omni-io-skills/audio/asr_omni-io-skills.json

git commit -m "chore: 补齐遗漏的配置、记忆与素材元数据

前 33 步的 git add 都写了具体路径，导致以下几类一直未被跟踪：

- .gitignore：本次新增素材集与日志的排除规则
  - **原有规则不级联到子目录** —— assets/audio/*.wav 匹配不到
    assets/sets/x/audio/y.wav，会让素材集下 7.2 MB 图片与音频一起入库。
    补 assets/sets/*/images/* 与 assets/sets/*/audio/* 两组规则，
    保持与老 assets/ 同一套原则：**大文件不入库，索引与元数据入库**。
  - 新增 remotion/*.log 与 *.render.log
  - ⚠️ 顺带修复：本文件此前被 PowerShell Add-Content 写入了 GBK 字节
    （第 47 行中文注释乱码），导致 git 与编辑工具无法按 UTF-8 读取。
    已用 Python 统一重写为 UTF-8 无 BOM。
- memory/project.md：本项目跨会话接手的唯一入口（含 10 轮决策与教训）
- remotion/scripts/render.ps1：沙箱外渲染入口，此前一直是未跟踪状态
- assets/audio/*.srt：素材自带原始字幕（ASR 重切版的兜底来源）
- assets/sets/omni-io-skills/：素材集的文本部分
  - set.json：标题/副标/口播/来源标注/来源目录
  - images/index.json：**人工判读的图片语义标注**（规划质量的主要输入，
    原始抓取元数据的 caption 全为 null，无法自动生成）
  - audio/*.asr.srt：ASR 重切后的字幕
  - audio/asr_*.json：ASR 原始结果缓存（避免重跑计费）

图片与音频（共 7.2 MB）不入库，与项目既有原则一致。
另删除两个不该入库的文件：_sizes.json（一次性中间产物）、
remotion/debug.log（可再生日志）。"
```

### 提交前自检

```powershell
# 1) 确认大文件确实没被加进来（应该输出为空）
git diff --cached --name-only | Select-String '\.(png|wav|mp3)$'

# 2) 确认文本文件都进来了
git diff --cached --name-only | Select-String 'index.json|set.json|asr|\.srt$|memory/|render.ps1|gitignore'

# 3) 看这次提交的体积（应该只有几十 KB）
git diff --cached --stat | Select-Object -Last 1
```

---

## 核对

```powershell
git log --oneline
git status --short          # 期望：只剩未跟踪的 .env（且被忽略）
git show --stat HEAD        # 看最后一个 commit 是否只含本步该含的文件
```

**预期结果**：34 个 commit，`git status` 干净（除 `.env`）。
每个 commit 只含其功能相关的文件，消息可读、能看出实现内容。

## 后续（每个批次完成后再覆写本文件）

`docs/git_commands.md` 是本项目的**一次性文件**：下一批（B5 中视频镜头 / B7 LLM 规划）
完成后，**先 `git log --oneline` 确认上面这组已执行**，再覆写为新的指令组。

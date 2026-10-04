# git 提交指令 / Stepwise commit instructions

> **AI 不执行 `git commit` / `git push`**，只产出指令，由人工执行。
> 本文档是**一次性的**：里面只保留**当前待执行**的指令组。

## 覆写规则（判据）

```
相关文件都已 git 保存  →  可以覆写本文档
```

具体做法：

1. **先确认上一组已全部执行**：
   ```powershell
   git log --oneline            # 能看到上一组的 commit
   git status --short           # 工作区干净（除 .env）
   ```
2. 确认后，**用新的指令组替换全文**，而不是在末尾追加。
3. **不要累积历史指令组** —— 已执行的指令没有留存价值（`git log` 才是历史），
   累积只会让文件越来越长、每次都要读一堆用不上的内容。

> 本项目历史上曾累积到 **34 组 / 700+ 行**，其中 33 组早已执行完，
> 属于典型的「文档腐烂」。现在按上面的规则覆写。
>
> 这条机制的完整说明在 [guides/00_dev_principles.md](guides/00_dev_principles.md) §5.1。

## 指令组模板

每一组是一个**能独立执行、独立回滚**的功能单元。按功能切分，**不要一个大而全的 commit**。

```powershell
## 第 N 步：<一句话说明这一步做什么>

git add <具体路径，逐个写明>          # 不用 git add -A / git add . / git add --all
git add <另一个路径>
git commit -m "<type>(<scope>): <做了什么>

- 为什么改（问题是什么），不是改了什么
- 关键实现选择与理由
- 副作用 / 影响范围
- 测试：跑了哪个节点、结果如何>"
```

| 要素 | 要求 |
|---|---|
| 类型前缀 | `feat` / `fix` / `docs` / `chore` / `test` / `refactor` |
| 首行 | 一句话说清**做了什么**，不用「修改了文件」这类空话 |
| 正文 | 写**为什么**（问题/约束），以及**关键取舍的理由** |
| 数字 | 可以写（测试通过数、帧数、体积），但要提交时现算，不手抄 |
| 路径 | 逐个 `git add`，便于人工核对这一步到底动了什么 |

### 提交前自检（务必执行）

```powershell
git diff --cached --name-only          # 反查有没有漏项 / 误加
git diff --cached --name-only | Select-String '\.(png|wav|mp3|ttf|mp4)$'   # 应为空
git diff --cached --stat | Select-Object -Last 1
```

> ⚠️ **素材入库原则**：大文件不入库，索引与元数据入库。
> `.gitignore` 的 `*` **不跨目录** —— 新增素材目录结构时必须单独补规则。

---

## 待执行（14 组）

### 第 35 步：`git_commands.md` 覆写机制进开发守则

```powershell
git add docs/guides/00_dev_principles.md docs/00_INDEX.md docs/git_commands.md
git commit -m "docs(principles): 固化 git_commands 的覆写机制并瘦身 81%

用户明确要求把这套机制写进开发准则 —— 它是防止 git_commands.md
随轮次无限增长的关键。

- 00_dev_principles.md §5 拆出 5.1「git_commands.md 的更新机制」：
  - 触发时机：每次交付一组改动后 / 每次接手准备写新指令前
  - 判据（可机械判断、不依赖记忆）：相关文件都已 git 保存 → 可覆写
  - 操作规程 4 步：核对 commit → 核对工作区干净 → 替换全文（不追加）→ 自检
  - 记下「为什么必须覆写」的实测代价：曾累积 34 组 / 700+ 行，
    其中 33 组早已执行完，之后每次写新指令都要先读过期的 700 行
  - 5.2 素材入库原则 + .gitignore 不跨目录的坑
- git_commands.md 631 行 → 118 行：删掉已执行完毕的 33 组指令，
  只留「判据 + 模板 + 当前待执行 + 状态」
- 00_INDEX.md：修正过期条目（删掉已被推翻的「整片渲染需沙箱外执行」、
  指向不存在的 guides/03_*.md），补多素材集工作流"
```

### 第 36 步：交付优化方案

```powershell
git add docs/plan/01_delivery_optimization.md
git commit -m "docs(plan): 交付优化方案（字幕/分镜片段/素材主体/横竖屏独立）

branch opt_deliver 的方案文档。用户这次要的不只是成片：
字幕 SRT、每个分镜一个片段（不带字幕）、素材做视觉主体、横竖屏独立设计。

诊断部分全部是实测值，不是推测：

- **竖屏差在三个原因叠加**
  1. 可用空间被吃掉一半：安全区 L60/R180/T120/B600 → 内容高只占画布 62.5%
  2. 素材在竖屏被缩到最小边：ImagePanel 写死 maxH=safeHeight*0.62，
     同一张 16:9 图竖屏 790×444（占画布 16.9%）、横屏 970×546（25.5%）
  3. 横竖屏不是两套设计：13 个镜头里 12 个只是 portrait ? A : B 换数值，
     无一改变元素顺序；8 个镜头用 heroCenterY + panelH/2 + 常数手算文案位置，
     实测 BeforeAfter 竖屏文案已与字幕块重叠
- **一个必须承认的自身缺陷**：TUNING 的 11 个旋钮与 scaleFromDesign
  全部零引用，是死代码 —— 上一轮宣称的「调风格只改一处」并不成立，
  所有竖屏数值都是各组件内联硬编码。这是「调竖屏参数不生效」的直接原因
- **一个字幕口径的教训**：先按「15-20 字」设计了过严的重切参数，
  用户澄清「5-20 字都行」后按显示权重复核，现有字幕本来就合格
  （Omni-IO 21/22、清华 17/20），重切方案多余
- **几何约束**：素材「占面积 70-80%」在保持长宽比时数学上做不到
  （竖屏 16:9 的面积上限约 32%），用户确认按「面积尽量大」处理

方案含 7 个实施批次、验收标准、成本估算（字幕重切零费用，因为复用 ASR 缓存）"
```

### 第 37 步：版式重构为矩形区域（横竖屏两套结构）

```powershell
git add remotion/src/theme/layout.ts remotion/src/theme/theme.ts remotion/src/theme/Caption.tsx
git commit -m "refactor(layout): 版式改为三个矩形区域，横竖屏真正独立设计

用户原话：「横屏视频和竖屏视频应该是两份独立的视频结构设计，
而不是简单的改变一下分辨率」。

**从标量坐标改为矩形区域**，这是结构性改动而非换数值：
- layout.ts 提供 mediaZone / textZone / captionBox 三个 Rect，
  镜头只消费矩形、不自己算坐标
- 横屏 = 左右分栏（素材左 58%、文案右栏）
- 竖屏 = 上中下三段（素材 / 文案 / 字幕）
- 新增 fitInZone()：素材在区域内保持长宽比适配
- 新增 tune()：组件按方向读 TUNING，禁止内联 `portrait ? a : b`

竖屏安全区右侧 180 → 48px（宽度利用率 78% → 91%），
因为素材居中后不再需要为大面积右侧留白让路。

Caption.tsx 改用 captionBox 定位，字幕位置与其它区域同源。

theme.ts 的 portraitMediaFill 明确要求 ≤1 并写清原因：
大于 1 会让素材溢出 mediaZone 压住文案区（实测踩过）"
```

### 第 38 步：素材类镜头去文案 + 改用全幅素材区

```powershell
git add remotion/src/ui/ImagePanel.tsx
git add remotion/src/shots/PageSpotlight.tsx remotion/src/shots/ScanAnnotate.tsx
git add remotion/src/shots/RadarReveal.tsx remotion/src/shots/SlowPush.tsx
git add remotion/src/shots/BeforeAfter.tsx
git commit -m "feat(shots): 素材镜头去文案，素材改用全幅区

用户口径：「使用素材图片的就不要在分镜中添加文案了，素材图片+动效已经足够了」。
**判据统一为：有 image 就不写文案，没 image 才写文案。**

- 5 个素材类镜头不再渲染任何镜头内文案（text/subtext/tagline/source）：
  page-spotlight / scan-annotate / radar-reveal / slow-push / before-after。
  props 接口保留（Python 侧 spec 契约不变），只是不再渲染
- 素材从分栏区 mediaZone 改用**全幅区 mediaZoneFull**（layout.ts 新增）：
  横屏从 1020 宽的左栏变成 1760 宽的全内容区，素材因此显著更大

为什么这条口径是对的：原先素材旁压一行 text，结果是**素材被缩小给文案让位**，
同时那行字也因为缺乏对比而读不响 —— 两边都削弱。去掉后素材占满内容区，
动效成为唯一的信息载体。

**同时修掉 Ken-Burns / 推近溢出的 bug**（会引起素材被裁切）：
- 缩放必须在适配时预留空间。反例：PageSpotlight 的 zoom 1.0→1.55
  叠加素材本就 1.05 的溢出量，素材实际宽度达到画布的 148%，四边全被裁切
- SlowPush 用「除以 PUSH_MAX 预留」；ImagePanel 用「除以 zoomTo 预留」
- PageSpotlight 用**两层结构**（视窗层不加 transform、只负责 overflow:hidden
  裁切；缩放层在内层）—— 因为把 scale 加在带 overflow:hidden 的同一个元素上时，
  CSS 会把裁切边界一起缩放，裁切失效
- PageSpotlight 推近 1.55 → 1.28 → **1.08**：全幅区下素材已占满内容区，
  大幅推近只会裁掉内容（实测 1.28 时顶部标题被切），1.08 裁切约 2.5%
- ScanAnnotate 的 settle（1.75→1）是**标注框**的入场动画、RadarReveal 的
  settle 恒为 1，两者都不影响素材，故未动

实测（横屏）：素材占内容区宽 92%，标题与图表完整可读；竖屏同样受益"
```

### 第 39 步：分镜片段导出与字幕核验

```powershell
git add remotion/src/compositions/types.ts remotion/src/compositions/FilmShell.tsx
git add scripts/export_shots.py scripts/check_subtitles.py
git commit -m "feat(deliver): 分镜片段导出（不带字幕）与字幕显示核验

用户要求交付「每一个分镜的视频片段（不要渲染字幕，一个分镜一个文件）」，
以及「确保每一段字幕都满足显示的要求」。两者都做成可复跑的脚本。

- FilmProps 新增 captionsEnabled / audioEnabled 开关（默认 true）
  - 分镜片段传 false：片段用于二次修改，字幕是独立交付物；
    切碎后每段音频大多停在句子中间，单独听无意义，静音还能减小体积
- scripts/export_shots.py：
  - 逐镜头用 `--frames=<from>-<to>` 导出，`--muted` 静音
  - **并行渲染**（默认 3 路）：每个片段都是一次 Remotion 冷启动
    （bundle ≈5–8s），串行 11 个片段要 5 分钟以上，而这段时间几乎全花在
    bundle 上、CPU 是闲的；并行 3 路把墙钟时间压到约 1/3。
    并行度不宜过高 —— Remotion 内部已在多帧之间并行，过高反而争抢 CPU
  - 产出 manifest.json（帧范围/时长/文案），便于二次修改时定位
  - --dry-run 只列清单（零费用、秒级）
- scripts/check_subtitles.py：
  - 从 TS 源码**解析**字号与安全区（不做 Python 侧抄常量，避免假配置）
  - 按显示宽度算每条是否会溢出/折行（中文字宽 1em、拉丁 0.55em）
  - 实测两套素材全部合格：Omni-IO 22 条、清华 20 条，两个方向都是 1 行
    （用户口径是「5-20 字都行」；按显示权重复核 21/22 与 17/20 落在区间，
     越界的只超 1–2 个单位且 Caption 有自动缩字，故未重切）"
```

### 第 40 步：素材优先的规划策略

```powershell
git add src/videogen/plan/prompts/system.md src/videogen/plan/planner.py
git commit -m "feat(plan): 素材优先、文案补足的排布策略

用户口径：「当素材数量不足的时候再用视频文案补充分镜」。

- system.md 新增硬规则 8「素材优先，文案补足」：
  - 用素材的镜头不写 text/subtext（列出 5 个 type）
  - **素材可以复用**：同一张图换动效、或换一组 targets 标注区域，即另一镜
  - 素材用尽后才用 figure-panel / stat-compare / flow-diagram 补足剩余时长
  - 判据：有 image 就不写文案，没 image 才写文案
- system.md 新增「图文三件套的内容必须具体」，给出可自检的判据：
  **把专有名词与数字全都抹掉后，这段内容还成立吗？** 成立就是废话
  （附三个 type 的反例→正例对照）
- planner.py：constraints 增加 asset_count；user prompt 显式写出
  「我有 N 张素材，先为它们安排镜头、可复用、用尽再用图文补足」
- 顺带修掉 parts 里一句重复的文案（上一轮编辑的遗留）

实测（Omni-IO，4 张素材 / 11 镜）：4 张素材全部用上且**无文案**，
其余 7 镜由图文与字标类补足；0 切分"
```

### 第 41 步：动效卡命门修复（过冲）

```powershell
git add remotion/src/ui/DigitRoll.tsx
git commit -m "fix(shots): 补上 odometer-digit-roll 卡标注为命门的过冲

拿本项目最核心的一张卡逐条对照，证实「动效卡没充分利用」不是感觉而是事实：
11 条参数里漏了 2 条，其中过冲被卡标注为命门 ——
原文「**无过冲读作滑到即停，机械感减半**」。

尤其值得记的是：NumberRoll.tsx 的注释写着「逐位过冲锁定」——
**注释声称做了，实现没做**。

- DigitRoll 改为两段式落位：
  段一 16f 减速滚到 (目标 + 0.5 行)，段二 6f 弹回整数锁定（卡的原参数）
- 新增 settle / overshoot 两个参数（默认 6f / 0.5 行，与卡一致）
- duration 默认 22 → 16（卡里 16f 是滚动段，6f 是回弹段，总长仍 22f）

残影（2 副本 0.25/0.12、速度门控）未做，记入方案待办。
下一步要把 157 张卡的参数表抽成结构化 JSON，并加测试断言组件参数与卡一致 ——
只读 frontmatter 建索引，等于只消费了卡名，没消费卡的能力"
```

### 第 42 步：项目记忆

```powershell
git add memory/project.md
git commit -m "docs(memory): 记录 Round 11 的三条硬教训

- **假配置比没有配置更糟**：TUNING 的 11 个旋钮全部零引用，
  上一轮宣称的「调风格只改一处」不成立；新增配置项必须立刻接上消费者
- **量化要求先确认边界**：按「15-20 字」设计的字幕重切方案完全多余，
  用户实际口径是「5-20 字都行」；拿到数字要求先算现有产物的实际分布
- **动效卡的价值在参数精度**：卡的参数表精确到「+0.5 行、6f、1.035」，
  照语义手写必然丢细节（NumberRoll 漏了过冲，而注释还声称做了）"
```

### 第 43 步：产物目录按类型重构

```powershell
git add src/videogen/paths.py
git add scripts/plan.py scripts/render_set.py scripts/export_shots.py
git commit -m "refactor(paths): 产物目录按文件类型固定，脚本输出统一

用户反馈：「生成的文件要统一汇总在同一个文件夹中，并且按照文件类型整理好，
现在文件保存的乱七八糟，找都找不到」。

诊断（实测）：**同一套产物散在三处** —— 成片在 out/<set>/<kind>/、
抽帧在 out/<set>/qa/ 与 out/qa_opt/、中间 props 在 out/runs/，
另有三处验证残留（qa2/_probe/runs）。找一个文件要翻四个顶层目录。

新结构（定义在 paths.py 顶部，单一来源）：

    out/<素材集>/<kind>/
    ├── video/         成片 mp4
    ├── shots/         分镜片段（<方向>/ + manifest.json）
    ├── subtitles/     字幕 srt
    ├── storyboard/    spec.json + props + shots.txt（人可读镜头表）
    ├── qa/            抽帧品检
    └── logs/          渲染日志

- paths.py 新增 deliverable_dir/video_dir/shots_dir/subtitles_dir/
  storyboard_dir/qa_dir/logs_dir/ensure_deliverable_dirs
- plan.py 额外输出 shots.txt：spec.json 是给程序读的，
  人工核对分镜要的是那张表（帧范围/时长/类型/文案/素材一屏看完）
- render_set.py 渲染时把字幕归档进 subtitles/（字幕生成在素材集 audio/ 下，
  属"输入"侧，不归档交付目录就缺这一类文件）
- 已迁移 75 项、清理 5 个垃圾目录；清华那套旧产物归入 out/_legacy/
- 每个交付目录写一份 README.md 说明各子目录用途"
```

### 第 44 步：中文数字规范化

```powershell
git add src/videogen/numbers.py tests/test_numbers.py
git add src/videogen/validate.py scripts/asr_subtitles.py
git commit -m "feat(numbers): 文案与字幕里的中文数字改为阿拉伯数字

用户口径：「视频文案以及视频分镜中，数字就不要改成文字了，直接用数字就行了，
使用文字很奇怪」。

**为什么会出现中文数字**（根因，不是模型乱写）：旁白由 TTS 合成，
音频里读的就是「百分之四十六」；字幕又从音频 ASR 回来，
所以天然带中文数字。模型写分镜文案时也跟着旁白的读法走 ——
光靠 prompt 约束不住，必须在服务端统一收敛。

numbers.py 的 normalize()：

    零点三四四米 → 0.344米      百分之四十六 → 46%
    六十四维     → 64维          二零二五年   → 2025年
    三维         → 3维

**核心难点是「不该转的不要转」** —— 中文里「一」的构词能力极强，
误伤比不转更糟（「一起」→「1起」读起来像机翻）：

    一起接进 / 一致收敛 / 这是一个关键点 / 一般来说  → 原样保留

规则：含「点」必转；单字仅在「百分之X」或后接量词时转；
「一个」按泛指保护；非数值后缀（起/致/些/样/般/直/定…）保护。

接入两处：asr_subtitles.py（字幕）+ validate.py 的 `_repair_numerals`
（分镜文案，在服务端收敛所以 spec.json 里也是数字，并留 repair_log 痕迹）。

24 个单测专门覆盖边界（tests/test_numbers.py），
其中一半用例是「不该转」的。"
```

### 第 45 步：图片语义自动标注（视觉模型）+ OCR 扩展位

```powershell
git add src/videogen/vision.py src/videogen/ocr.py
git add scripts/annotate_images.py
git add src/videogen/sources.py
git commit -m "feat(vision): 图片语义自动标注，消掉最后一个手工环节

素材抓取时图片的 caption 全是 null，所以图片语义一直只能人工判读 ——
那是整条链路上**唯一的手工环节**，也是规划质量的主要输入
（模型不知道图里是什么，就只能瞎配镜头）。

## 提示词策略是实测出来的

**问「描述这张图」会得到泛泛而谈甚至编造；问「照抄图里最显眼的几个文字标签」
则准确得多。** 所以要求模型**先做可验证的抄录，再做用途判断**。

效果：03 图抄到 9 个标签全对
（User Query / Input Assets / Skill Planning / Select Skills /
Hierarchical Expansion / DEG / Construct & Validate / Per-Node Execution Loop /
Wave Scheduling）。专有名词也从误读的「Omni-10」修正为「Omni-IO」。

## 后端选择（MiniMax 实测）

| 模型 | 结果 |
|---|---|
| MiniMax-Text-01 | 最佳，能照抄英文原标签 |
| abab7-chat-preview | 同样准确 |
| abab6.5s-chat | 可用但会意译错（Asset Registry → 资产管理设计）|
| MiniMax-M2 | 返回无关内容 |
| MiniMax-M1 / abab6.5-chat | 明确 not support img |
| MiniMax-VL-01 | **该模型不存在** |

OpenRouter 侧配置里的 nemotron 不支持图像输入（No endpoints found that
support image input），免费视觉模型另有一批可用。

## ⚠️ 一个必须处理的 MiniMax API 陷阱

**业务错误放在 base_resp.status_code，而 HTTP 状态是 200**：

    HTTP 200 但 {\"base_resp\": {\"status_code\": 2013, \"status_msg\": \"unknown model\"}}

只看 HTTP 码会把「模型不存在」当成成功（content 是 None）。
本模块一律以 base_resp.status_code == 0 为成功判据。

## OCR 作为可选扩展（用户暂不安装）

新增 ocr.py 对接 Agentic_OCR_Module，**没装时静默降级**
（is_available() 为 False，ocr_text() 返回空串，链路照常跑）。
装了之后它有两个别处拿不到的能力：① 准确文字作为 grounding 喂给 VLM，
专有名词不再靠模型的眼力；② mineru 后端的 ROI 截图。
集成方式是子进程调用，因为它装在独立 conda 环境里，本项目 import 不到。

同时给 AssetSet 加 article_text 属性（读 meta.json 的 text 或 article.md），
为下一步「梳理文章关键信息」提供输入。"
```

### 第 46 步：一条命令跑完全链 + 一键重渲

```powershell
git add scripts/make_video.py
git commit -m "feat(make_video): 一条命令从文章到成片，含一键重渲

用户要求：「我想要生成的工具简单化，我提供文案直接就可以通过脚本渲染成
高质量的视频」+ 确认要「一条命令跑完全链」与「一键重渲（不重新规划）」。

    # 从一篇文章出片
    make_video.py --article <文章目录> --kind short

    # 一键重渲：改完 spec 或字幕，不重新规划、不重复花 LLM 钱
    make_video.py --set <素材集> --kind short --rerender

    # 先看要做什么（零费用）
    make_video.py --article <目录> --kind short --dry-run

**本脚本不实现任何业务逻辑**，只按顺序调用已有脚本（薄壳原则）：
导入 → 标注 → 字幕 → 规划 → 渲染 → 切片。每一步都能单独跑、单独调试，
出问题可以直接重跑那一步。前一步没产出预期文件就立刻停下并说清原因。

实测（H3-World 新文章，8 张图）：全链一次跑通。
过程中抓到并修掉两个自身缺陷：
- asr_subtitles.py 的 --kind/--set 是**互斥组**，同时传会 argparse 报错退出
- 素材集名按标题自动生成会长得离谱（46 字符），补 --name 参数指定短名"
```

### 第 47 步：修分镜片段导出全错 + 同一画面播两遍

```powershell
git add remotion/src/Root.tsx src/videogen/validate.py src/videogen/subtitle.py
git add tests/test_validate.py
git commit -m "fix(pipeline): 修分镜片段导出全错、同一画面播两遍、字幕切碎字母

用 H3-World 做新文章全链测试时暴露的三个真 bug。

## ① 分镜片段导出全部报错

    The \"durationInFrames\" of the <Composition /> was evaluated to be 1490,
    but frame range 1401-1544 is not inbetween 0-1489

根因：**Remotion 校验 --frames 用的是 Composition 的静态 durationInFrames，
不是 calculateMetadata 算出来的值**。成片渲染完全正常（时长由 props 决定，
51.56s），只有分镜片段会炸。
修法：静态 SHORT_FRAMES/MID_FRAMES 设成足够大的上限（30000），
真实时长永远来自 props。这个坑在文档里没有，只能踩出来。

## ② 同一画面播两遍（15 镜的视频里 11 镜内容重复）

模型给了多个 5.5s 的镜头 → 超 5s 上限 → 被切成两段 → 两段内容相同。

修法：`_rebalance_ceiling` 从「只向左右邻居借帧」改成**全局削峰填谷** ——
把超限镜头削到 150 帧，盈余**全局**分给有余量的镜头。
旧实现借不到的原因很实际：模型常常**连续给好几个超限镜头**，
邻居同样超限、没有余量，于是一个都借不到。

修完实测：15 镜 → 12 镜、0 重复、全部 ≤5s、片段 12/12 成功。

## ③ 两条附带教训（都写进注释防复发）

- 在 `_relayout` 里把均摊上限钳到 MAX_SHOT_FRAMES 会让总时长出现 drift，
  而 drift 补偿会把差额全堆到末镜 —— 实测末镜变成 550 帧。
  **分工要清楚**：`_relayout` 只负责总时长守恒，「削到 5 秒」是
  `_rebalance_ceiling` 的职责。
- 再平衡必须先查容量（总帧 > 镜数 × 上限 时什么都不做）：
  容量不足时池子分不完，丢帧会让总时长对不上音频。
  该检查必须放在**削减之前**，否则帧先被削没了。

## ④ 字幕把「WASD」切成「W A / S D」

TTS 逐字母读 W、A、S、D 时字母间有自然停顿，超过 pause_gap 被误判成
句间停顿，切成「做法是把 W A / S D 角色键和 I / J K L 相机键」三段。
两处修：`segment()` 加「逐字母缩写内部不切」保护（与既有的数字保护同理）；
`_join()` 对**单字符 ASCII 字母/数字之间不补空格**（顺带修掉 H 3 → H3）。"
```

### 第 48 步：文档与 prompt 纠正

```powershell
git add docs/guides/02_video_tuning.md docs/plan/01_delivery_optimization.md
git add src/videogen/plan/prompts/system.md src/videogen/plan/planner.py
git commit -m "docs: 动效卡用法 + 本轮踩坑；纠正图文镜头的定位

## 文档

02_video_tuning.md 新增第 12 节「动效卡用法」：卡的结构、**读卡的正确顺序**
（只读 frontmatter 等于没消费卡）、参数表怎么用（odometer-digit-roll 的
过冲 +0.5 行/6f 真实案例）、**卡名必须过索引校验**（附 minimax 的幻觉卡名
反例）、参数化 157 张卡的可行性判断、已落地的卡与组件对应表。

踩坑清单补 7 条本轮经验，每条都带「为什么」：
Remotion 静态时长坑、全局再平衡、末镜 drift、容量检查顺序、
argparse 互斥组、素材集名过长。

## prompt 纠正（用户澄清）

原作者口径「素材用尽后才用图文三件套补足剩余时长」—— 这是**凑数**逻辑，不对。
用户澄清：**图文镜头是承载图片没有表达的信息**。
文章里有关键内容（机制拆解、参数表、对比结论、流程）图里根本没画，
只靠旁白念一遍观众记不住；这才是图文镜头的职责。

所以判据从「数量」改成「信息」：
- 这段内容图里画了吗 → 用素材镜头
- 文章有、但图里没有的关键信息 → 用图文三件套结构化讲出来
- 只是为了填满时长 → 不要这样做

配套：PlanRequest 新增 article_text，把**文章正文**喂给模型 ——
只给旁白的话，模型看不到那些没被念出来的细节，就无从判断「哪些信息图里没有」。
AssetSet 新增 article_text 属性（读 meta.json 的 text 或 article.md）。"
```

---

## 当前状态

| 项 | 值 |
|---|---|
| 已提交 commit 数 | 29 |
| 分支 | `opt_deliver` |
| 待执行的指令组 | **14 组（第 35–48 步，见上）** |
| 工作区待提交 | 16 个已跟踪文件改动 + 3 个新文件 |

> 后续有新的代码改动时，按上面的模板**替换**本节，不要追加。

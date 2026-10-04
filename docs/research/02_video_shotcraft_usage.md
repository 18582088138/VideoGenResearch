# video-shotcraft 技术手册（中文实现指南）

> 调研对象：`C:\Users\75203\Downloads\xkd\video-shotcraft`（调研期间该目录从 `VideoGenResearch-minimax\video-shotcraft` 移动至工作区根，本手册所有相对路径以**仓库根**为基准）。
> 全部结论均标注来源文件与行号；未在源码/文档中找到依据的一律写「未找到」。
> 仓库自身文档：`SKILL.md`(265 行) / `README.md`(276 行) / `README_CN.md` / `references/*.md`。

---

## ⚠️ 使用前必读：三条校正（2026-10-02 复核）

本手册由调研子代理产出，**结论总体可信**（均带文件行号依据），但有 **1 处数字错误** 与
**2 处需要主上下文补充的实测结论**，以本节为准：

### 校正 1（已证实）：SFX 数量就是 **149**

本手册正文多处（§C9、§「已知坑」）记 `assets/audio/sfx/` 实测 **151** 个文件，
**这是误计**。主上下文用 `Get-ChildItem -Recurse -File` 独立复核：

```
总文件数 : 149        扩展名 : .mp3 = 149（无其它类型）
camera 10 · counter 4 · crowd 3 · data 13 · film 8 · fluid 5 · glass 4
impact 14 · light 10 · mech 8 · paper 10 · riser 1 · scifi 5 · text 13
transition 23 · ui 18        逐类相加 = 149
```

误差来源：`-Recurse` 叠加目录项计数时会多出 16 个类别目录（或 +2）。
**仓库自身文档写的「149 个 / 16 类」是正确的**；本手册的 151 是错的。

→ `memory/project.md`、`tests/test_assets.py`（不依赖该数字）与
[04_bgm_and_audio.md](04_bgm_and_audio.md) 的校正条目均按 **149** 记录。
下文正文的 151 请一律读作 149。

### 校正 2（补充）：模板无 BGM 实现 —— 与 memory D10 的决策一致

本手册发现 `template/` 是 **SFX-only**（`TEMPLATE.md:6`），`Root.tsx:10` 的 `defaultProps`
只有 `theme`，全仓 `.tsx` 里 `bgm` 仅命中工作台素材库面板。

因此「`--props=props-nobgm.json` 出双版本」这条**流程要求无法在现有模板上直接跑通**，
目标工程必须自己新增 `bgm` inputProp。

→ 本项目决策 **D10：BGM 作为可选开关实现，默认不开启**，与此发现完全吻合。
本项目自带 5 首免版权 BGM（Mixkit Free），**零生成算力开销**。

### 校正 3（补充）：多分辨率靠「设计坐标系隔离」，不是 `--scale`

本手册确认：仓库文档与脚本里**完全没有** `--scale`，也没有任何非 1920×1080 的工程或配方卡；
多分辨率的推荐做法是**设计坐标系隔离**（Motion 系 demo 用 480×270 设计坐标等比放大，
见 `demos/README.md:42-43`）。

→ 这与本项目 [design/00_platform_output_spec.md](../design/00_platform_output_spec.md) §2.1
的结论一致，并**强化了否决 `--scale` 的理由**：
`--scale` 只做等比缩放，1920×1080 缩到 1080 宽得到 1080×608，**不是 9:16**。
横竖屏必须是**两个 Composition + 两套版式分支**。

### 其它已核实的硬事实（可直接依赖）

| 事实 | 值 |
|---|---|
| 镜头卡总数 | **157**（分目录 11/26/28/10/13/15/19/11/17/7，无重无漏） |
| Remotion 全家族版本 | **4.0.484**（React 19.2.7） |
| Node | 22（无 `engines` 声明，CI 与 README 一律用 22） |
| three.js 隔离度 | 157 张卡的 demo **无一个** import three；仅 `assets/lib/FlatPanel.tsx` 与 `assets/lib/helpers/camera.tsx` 用到 |
| `@remotion/motion-blur` | 恰好 8 个文件；`DeckDealFlyin.tsx` 只在注释里提及，源码明说不依赖 |
| `implementationStatus` | 全库为空（`gallery/sync-from-cards.py:17-20` 的 `STYLE_STATUS = {}`）→ 手册里「仅供参考 / 缺少预览」的降级标注**当前一个都不触发**，实现时不要写成必有分支 |
| 仓库自述六阶段 vs 八阶段 | `SKILL.md:8-9` 写「六阶段」，本手册正文梳理为 **8 个阶段（0–7）**，以手册正文为准 |

### 本手册的能力边界（子代理自述）

- **未实际渲染任何视频**（未跑 `npm install` / `remotion render`），结论来自源码、
  文档与 `ffprobe`/文件系统实测。
- 唯一的渲染耗时数据：`@remotion/motion-blur` 的 `samples` 每 +1 约 +1 倍渲染时间
  （`deck-deal-flyin.md:30`）。

> 上述「未渲染」这一缺口已由主上下文补齐：`remotion compositions` 与 `remotion still`
> 均在本机实测通过，耗时数据见 [memory/project.md](../../memory/project.md) 与
> [plan/00_dev_plan.md](../plan/00_dev_plan.md) §3。

---

## 0. 一句话定位与三种模式

`video-shotcraft` 是一个自包含的「电影感产品视频」制作能力库：157 张镜头配方卡 + 214 条动态样片 + 已验收的完整模板工程 + 可复用组件/音频/采集脚本 + 八阶段工作流。

来源：`SKILL.md:6-11`（自述）、`SKILL.md:8-9`（157 卡 / 六阶段）、`README.md:177-180`（157 卡 / 214 样片）。

**三种互不合并的模式**（`SKILL.md:13-25`）：

| 模式 | 入口文档 | 是否逐阶段等待确认 |
|---|---|---|
| ① 直接使用模板（Ink Press） | `template/TEMPLATE.md` | 按模板替换流程走 |
| ② 自主自由创作 | `references/pipeline.md` | **不**，连续推进到成片 |
| ③ 共同创作 | `references/guided-free-creation.md` | **是**，5 个确认节点 |

例外规则（`SKILL.md:47-57`）：用户点名 Ink Press → 视为已选模板模式；用户点名镜头卡 → 镜头约束已选定，只问「自主 vs 共同」。

交付收尾三件事固定动作（`SKILL.md:170-205`）：打开动效工作台 → 建议 @ 作者（非强制）→ 邀请投稿 → 可导出剪映工程。

---

## A. 工作流总览

### A1. `references/pipeline.md`：八阶段工作流

文件标题即「八阶段制作流水线」（`pipeline.md:1`），目录见 `pipeline.md:6-15`。下面按阶段编号列出**输入 / 产出 / 判断标准**。

#### 阶段 0：产品理解与执行约束（`pipeline.md:42-54`）
- **输入**：项目只读检查（定位、主要功能、页面状态、视觉 tokens、启动方式、数据风险）+ 用户已有描述。
- **做什么**：只读检查，**不写视频代码、不采集最终素材**（`pipeline.md:44-45`）；用户指定 BGM 时先按 `music-beat-sync.md` 分析节奏（`pipeline.md:50-51`）。
- **产出**（`pipeline.md:54`）：产品简报；需求到执行决策表；明确的数据与音频约束。
- **判断标准**：敏感数据（客户/个人/内部/密钥/实时）一律先虚构、脱敏或冻结（`pipeline.md:51-52`）。

#### 阶段 1：视觉方向与 styleframe（`pipeline.md:58-111`）
- **输入**：阶段 0 的产品简报 + 项目视觉 tokens。
- **做什么**：① 生成最多 3 个文字方向，每个附「动效性格 tokens」（`pipeline.md:65-66`）；② Agent 自选方向并写入 spec（`:67-68`）；③ **不渲染视频、不写 Remotion 代码**，写纯 HTML/CSS styleframe 页含 2–3 张 1920×1080 静态关键画面（`:69-71`）；④ 用 Playwright/Puppeteer 截图验证字体/色板/材质/构图/光感/信息密度（`:72-73`）；⑤ 有参考片则 ffmpeg 抽帧（`select=eq(n,…)` 抽 ~100 帧、`tile=4x5` 拼 contact sheet）写 motion breakdown 三列表（`:74-78`）。
- **品牌→动效参数推导表**（`pipeline.md:89-96`，六预设：主时长@30fps / 入场 easing / 过冲 / squash）：

```text
| 预设（品类） | 主时长@30fps | 入场 easing | 过冲 | squash |
|---|---|---|---|---|
| 专业信赖（fintech/enterprise/B2B）| ~21f | bezier(0,0,0.2,1) | 1.0 不弹 | 0 |
| 精致高端（奢侈品/时尚）| ~48f | bezier(0.4,0,0.6,1) | ≤1.02 | 0 |
| 活力大胆（体育/游戏/startup）| ~18f | bezier(0.16,1,0.3,1) | 1.12 | 0.25 |
| 活泼愉悦（消费/社交）| ~27f | bezier(0.34,1.56,0.64,1) | 1.08 | 0.18 |
| 平静关怀（健康/教育）| ~42f | ease-in-out 对称 | 1.0 | ≤0.04 |
| 亲和友好（小微/社区）| ~26f | bezier(0.25,0.46,0.45,0.94) | 1.04 | 0.08 |
```
  - 自检两条（`pipeline.md:98-100`）：三个词描述成片动效，与品牌词对得上吗；同一套 tokens 必须同时管入场/转场/hold 节奏。
  - **判例优先**（`pipeline.md:101-102`）：预设值与库内硬判例冲突时判例赢——「落地要弹的场合 y1 必须 >1」。
- **产出**（`pipeline.md:104-105`）：选定方向的 styleframe；色板/字体/光感 tokens + 动效性格 tokens；（有参考片时）motion breakdown 表。
- **常见坑**（`pipeline.md:107-111`）：用渲染视频做风格提案太贵；参考驱动的风格 move 全局一刀切。

#### 阶段 2：功能到镜头映射（`pipeline.md:115-128`）
- **输入**：产品功能清单 + `references/shots/` 全部卡片 frontmatter。
- **做什么**：① 先列产品功能清单，逐一对应镜头；**一种动画手法全片只当一次主角**（`:120-121`）；② 扫描全部卡 frontmatter，按用途/能量/建议时长/限制/所需页面状态选首选+备选卡（`:122-124`）；③ 完整读选中卡片并按「参考实现」定位准确 demo 源码（`:125-126`）。
- **产出**（`:128`）：功能到镜头映射表；选中卡名、变体、demo 源码和参考样片定位。
- **判断标准**：核心功能漏拍等于返工；同质化即返工信号（`:120`）。

#### 阶段 3：分镜与制作放行（`pipeline.md:132-161`）
- **输入**：阶段 2 映射表 +（若有）`references/sequences/` 桥段模板。
- **做什么**：① 查 `references/sequences/` 有无适用桥段模板，有则按填空流程分配段位与帧预算（`:139-140`）；② 已有指定 BGM 先出音乐结构表，镜头边界全部锚到拍号，最强 hit 分给全片 2–3 个大 slam（`:141-143`）；③ 写完整分镜表（`:144-145`）；④ **预留 hold/rest 帧预算**（`:146-148`）：品牌字标 hold ≥1s（30f）、批量动效收尾 0.5s 静止、开场主体动作 ≥3s；⑤ 一致性检查后自行放行，转译成帧级时间轴 `| shot | from | duration | 内容 |`（`:149-152`）。
- **产出**（`:154-155`）：设计 spec（含风格 tokens + motion breakdown + 分镜表）；帧级时间轴。
- **判断标准**：节奏返工是单向的——「过快必返工、放慢从未被否」（`:147-148`）。

#### 阶段 4：最终素材采集（`pipeline.md:165-196`）
- **前置条件**（`:167-169`）：最终设计 spec 与分镜已放行；此前为 styleframe 采的安全截图不得替代最终素材。
- **做什么**：① 起产品本地 dev server（桌面端用窗口截图工具，同样出三件套）；② 复制 `assets/scripts/capture-template.mjs` 改 BASE_URL 与选择器，跑出三件套（`:177-186`）：
  - **全页 2x 截图**：viewport 1920×1080、`deviceScaleFactor: 2`；截图前 `document.fonts.ready` + 600ms settle，实时同步页额外再等 1.5–2s；
  - **per-element cutout**：按语义选择器逐元素截图；悬浮件用透明底，需「卡片飞入空板」再截空 backplate；
  - **layout.json**：每元素整页坐标系 `{x,y,w,h}` bbox + 每页 `pageH`。
  ③ 支持按页/按元素增量重采；活数据源先冻结/虚构/脱敏（`:185-186`）。
- **产出**（`:188-189`）：`public/textures/` 全页图、元素切片、空 backplate；`layout.json`；可重跑 capture 脚本。
- **常见坑**（`:191-195`）：分镜放行前做全量采集；手搓 HTML 复刻既有页面；只截整页不记 layout 坐标。

#### 阶段 5：逐镜头实现（`pipeline.md:199-266`）
- **前置条件**（`:201-203`）：可跑的 Remotion 项目（30fps、1920×1080，`src/index.ts` 注册 Composition）；新项目 `npx create-video@latest` 后 copy `assets/lib/`；模板路线直接从 `template/` 起步。
- **每镜头硬规则「先解析再三读」**（`:210-219`）：
  1. 用 `gallery/api/library.json` 校验卡名与 `style-key`；
  2. 读对应配方卡全文；
  3. 按卡片「参考实现」定位并读**准确的 demo TSX 全文**；
  4. copy `assets/lib/` 对应组件进项目；
  5. 保存该 style 的 Gallery 参考样片路径供实现对照与终检。
  - 「仅供参考，需要自定义实现」的样式不默认推荐；「缺少预览」的样式不得声称已按动态样片复刻（`:214-215`）。
  - 卡上「已知坑/命门」标注的参数**不得降档**——质量标准只升不降（`:217-218`）。
- **PageCam 是一切「真实页面」镜头的地基**（`:220-221`）。
- **静帧验收（最高频动作）**（`:222-225`）：每镜头计划里写死 2 个验收帧号，完成即跑
  `npx remotion still src/index.ts <Comp> out/qa/<name>.png --frame=<N>`，肉眼检查构图/穿帮/文字锐度。
- **每轮修改后整片渲染**（`:226-229`）：`npx remotion render src/index.ts <Comp> out/promo.mp4`，再用 `ffmpeg -i out/promo.mp4 -vf "select=eq(n,…)"` 抽关键帧回看。
- **像素级自检小工具**（`:230-231`）：crop 放大看文字锐度、两帧像素 diff、量元素 bbox 对构图。
- **确定性渲染铁律**（`:232-234`）：禁 `Date.now()` / `Math.random()` / 无参 `new Date()`；一切伪随机用固定种子（mulberry32/哈希，seed 从 index 派生）。
- **边做边对照 `aesthetic-rules.md`**（`:235-237`）：落地要弹的缓动 y1 必须 >1、光效裁进圆角、3D 下文字糊先查栅格化路径（CSS `zoom` 而非 transform scale）。
- **为动效工作台留接口**（`:241-246`）：`SHOTS` 是唯一事实源；语境级参数做带默认值 props；节奏命门保持常量；`src/workbench.ts` 补 `component`/`props`/`schema`；交付前 `cd workbench && npm run parity`。
- **产出**（`:248`）：逐镜头 commit；`out/qa/` 静帧档案；每轮全片渲染 mp4；`src/workbench.ts` 清单。
- **常见坑**（`:254-266`）：首检交给用户；跳过 demo 代码直接写；产品宣传片默认不加手持 shake；装饰性 glint/泛光群发；3D 推进下文字发糊先查素材链路；飞入动画终点悬空。

#### 阶段 6：声音设计（`pipeline.md:270-335`）
- **前置条件（最贵的顺序教训）**（`:275-277`）：**画面时间线锁定后才开始**；画面一改，钉帧表全体重对。
- **做什么**（`:279-321`）：① 读 `references/sound-design.md`，从 16 类目录定类别再挑音色；② BGM 用户已指定→只做混音（`volume ~0.34` + 首尾淡入淡出），未指定→选强鼓点电子底且**必须垫进成片试听**；BGM 用布尔 inputProp `bgm` 包住与 SFX 解耦；③ SFX 用电影系词汇按镜头语言选，禁游戏音包**音色**（`ui/` 必须逐个试听）；④ 声明式钉帧表集中管理 + **相对钉帧**（`SHOTS.x.from + offset` 或 `beatF(n)`），**绝不写裸数字帧号**；长样本（>5s，21 个）必须显式给 `durationInFrames`；⑤ 连发防机枪感三招；⑥ 留「贴画面定制」槽位；⑦ 强鼓点片 SFX 克制，大 slam 只给 2–3 处；⑧ 结尾固定句式 riser→impact→sparkle；⑨ **音量按素材实测峰值给，不照抄区间**。
- **产出**（`:323-324`）：带声整片；SFX 钉帧表（相对帧表达式+音源+音量+注释）；音频入 repo 并记录来源授权。
- **常见坑**（`:328-335`）：画面没锁就铺音效；按 UI 事件语义选音色；长样本不给 `durationInFrames`；照抄 0.2–0.6 不看峰值；散铺不建表。

#### 阶段 7：验收（`pipeline.md:339-401`）
- **做什么**：① 全片渲染最新版 + ffmpeg 抽全部关键帧（每镜头至少：入场中、动作峰值、落定后三帧）；配 BGM 的片子在此渲两版（带/无 BGM），无 BGM 版靠 `props-nobgm.json`（内容 `{"bgm":false}`）+ `--props=props-nobgm.json`（`:347-354`）；② **独立终检（必做）**：派干净上下文 subagent 做第三方审查（`:355-362`）；③ 审查 Agent 按 `final-review.md` 逐条出带帧号结论（`:363-368`）；④ 内容级自查——每镜头问「给了什么新信息」（`:369-370`）；⑤ 音画对齐终检，卡点片按 `music-beat-sync.md §5` 渲后回测，**全部切点误差 ≤3f 才算过**（`:371-373`）；⑥ 修复项回阶段 3/5/6 小循环（`:374-377`）。
- **产出**（`:379-382`）：独立审查报告 + 终渲成片（带 BGM / 无 BGM 两版）。
- **常见坑**（`:392-401`）：把验收当最后才做的事；自检报告流于「全部 ✓」；制作 agent 自己出审查报告（确认偏差不可避免）；只查「好不好看」不查「是否符合当前模式的制作基准」。

**两处执行原则**（`pipeline.md:29-34`）：
1. 最终设计 spec 与分镜共同构成制作放行；分镜表长在设计 spec 里（`| # | 时间 | 镜头 | 关键动效 |` 四列）。
2. 验收贯穿全程，不是最后一个阶段；每镜头以 `npx remotion still` 静帧验收收尾，产物按版本归档 `out/qa/`。

**桥段模板**：`references/sequences/promo-energy-arc.md` 是仓库内唯一的桥段模板（`sequences/` 目录仅含它 + `.gitkeep`）。四段位骨架表见 `promo-energy-arc.md:16-21`：

```text
| 段位 | 时长占比 | 能量 | 职责 | 候选配方卡 |
|------|----------|------|------|------------|
| ① 品牌开场 | 8–12%（30s 片）；开场+立传合计可达 20%（模板片） | 低 | 字标压印 + hold ≥1s（R1），交棒产品页面 | brand-ink-open |
| ② 单主角立传 | 12–15% | 中（质感最高、节奏最慢） | 一个主角、一条完整动作弧 ≥3s（Q5/R3） | spotlight-hero-card |
| ③ 功能爬升段 | 55–65% | 中高⇄低交替 | 每镜绑一个独特功能、一种手法只当一次主角（P4）；镜间按需插呼吸字卡 | deck-deal-flyin / type-and-filter / list-stack-press / row-embed / document-typewriter-reveal |
| ④ 发布会收场 | 13–16% | 峰值（全片最高） | 已展示功能各出代表元素合影围住字标（Q8），sign-off hold ≥1s（R1） | outro-group-photo-launch |
```
- 呼吸字卡规则（`promo-energy-arc.md:23-25`）：每 1–2 个功能镜头后插一张，单张 50–55f（≈1.8s），全片 2–4 张。
- 填空流程 5 步（`promo-energy-arc.md:27-38`）：先扣 ①②④ 与字卡预算，剩余给 ③ 均分；每镜预算内**先划走 hold/rest 帧再排动效**。
- 已知坑（`promo-energy-arc.md:42-46`）：段位占比是模板片单例实证；①hold/④峰值两端不可省；呼吸字卡写成第二遍 tagline 即删。

---

### A2. `references/guided-free-creation.md`：共同创作与自主自由创作的关键差异

差异定义（`guided-free-creation.md:1-5`、`SKILL.md:72-85`）：共同创作把**产品简报、需求决策、视觉方向、镜头映射和最终分镜**交给用户确认，把视频工程细节交给 Agent 执行；自主自由创作不读本文件，也不使用逐阶段确认节点。

**5 个确认节点**（目录 `guided-free-creation.md:7-14` + 各节）：

| # | 确认节点 | 章节 | 确认物 |
|---|---|---|---|
| 1 | 产品简报 | §1（`:16-60`） | Agent 先填的产品简报表（11 行，每行先给判断/推荐再写依据）；确认后先做**临时安全素材预检** |
| 2 | 需求到执行决策表 | §2（`:62-84`） | 7 行可追溯表；每行必须写当前项目与用户材料的依据 |
| 3 | 视觉方向 | §3（`:86-105`） | 两轮：先 3 个文字方向 → 用户选 1–2 个入围 → 做 HTML/CSS styleframe 对比页 |
| 4 | 功能到镜头映射 | §4（`:107-122`） | 每功能推荐首选+备选镜头；**映射表不是完整分镜，不得直接开始制作** |
| 5 | 分镜确认与制作放行 | §5–6（`:124-181`） | 完整分镜表 + 设计 spec；放行后不再重开已确认的业务/创意问题 |

**每轮只问 1–3 个最影响结果的问题**（`guided-free-creation.md:54`、`SKILL.md:79-80`）；每轮回复格式固定（`guided-free-creation.md:194-199`）：

```text
当前阶段：
已确认：
本轮需要确认：
确认后交付：
```

**Gallery 镜头名称解析 7 步**（`guided-free-creation.md:130-143`）——这是「共同创作」和「自主自由创作」都要用的同一套解析规则：
1. 读 `gallery/api/library.json`，用 `cards[].name` 校验 `card-name`、用 `styles[].key` 校验 `style-key`，**不要用模糊猜测代替索引校验**；
2. 用索引中的 `source` 定位并完整读取 `references/shots/*.md`；
3. 按卡片「参考实现」明确路径解析到准确 demo TSX（文档只写目录时读目录文件，按导出名/注释/样式语义确定文件）；
4. 把 `styles[].media.url` 解析为参考样片（本地 `gallery/media/` 无 mp4 先跑 `gallery/fetch-media.sh`）；
5. 需要通用组件再读并复制 `assets/lib/` 对应文件；
6. 保留 demo 已调校的缓动、时值配比、遮罩时机与「已知坑/命门」参数；
7. 只替换目标产品的截图、布局坐标、文案、品牌 token 和必要构图参数。

两种复制形式（`guided-free-creation.md:147-150`）：`spotlight-hero-card`（只用默认变体）与 `shot-transitions · whip-pan`（点名具体变体）。

**跳过与兜底规则**（`guided-free-creation.md:183-190`）：用户授权全权决定时仍须动态推导；只有项目和用户描述都没有线索时才用 **30–38 秒、1920×1080** 兜底。

**共同创作→pipeline 的交接点**（`pipeline.md:24-25`）：**不要从头重跑**，直接从阶段 4 最终素材采集继续。

---

### A3. `references/aesthetic-rules.md`：全部编号规则

**使用方式**（`aesthetic-rules.md:5-9`）：每条 = 规则 + 判例 + 自检问题；阶段 7 逐条过一遍输出 `编号 ✓` / `编号 ✗(位置)`；准则可以有意识违反，但每次违反必须写进项目说明文档。**编号体系：R(节奏) / Q(质感·运镜·构图) / S(声音) / C(文案) / P(流程)，编号一经发布不重排，新增只追加**。

#### 节奏（R）

| 编号 | 规则（一句话） | 行号 |
|---|---|---|
| **R1** | 关键信息落定后必须呼吸，品牌字标 hold 满 1 秒（承载信息的元素落定后静止 ≥1s 再切镜，呼吸优先给品牌记忆点而非普通内容卡） | `:23-26` |
| **R2** | 速度感来自加速度不是匀速快；群体运动挂物理隐喻，满板后静止 0.5s 再切下一拍 | `:28-31` |
| **R3** | 节奏宁慢勿快：初版默认放慢一档，开场主体动作弧 ≥3s，交互演示按真人操作速度 | `:33-36` |
| **R4** | 卡点约束时机不放大幅度：作用于整画面/相机层的冲击全片 ≤3 处、钉最强 hit 清单、相邻两处间隔 ≥16 拍；节拍泵类连打单次 ≤4 拍且全片 ≤1 次；其余拍点只动元素层。**计数单位是一次手法/set-piece 使用，不按内部子事件数** | `:38-41` |

#### 质感·运镜·构图（Q）

| 编号 | 规则（一句话） | 行号 |
|---|---|---|
| **Q1** | 复刻既有页面必须真实截图；手搓 UI 限非复刻场景且质量/表达达标；数据按风险口径处理 | `:47-50` |
| **Q2** | 3D 透视下 UI 纹理按原生尺寸 rasterize 后缩小使用（2–4 倍原生栅格化，放大走布局级 CSS `zoom` 而非 transform scale）；文字发糊先查纹理分辨率链路，别先动相机/DoF | `:52-61` |
| **Q3** | 镜头要稳：产品宣传片默认不加手持抖动；相机噪声只在暗场氛围片明确追求纪实感时用极小值 | `:63-66` |
| **Q4** | 高光/扫光特效宁缺毋滥：不群发，一个镜头最多给主角一次，且必须裁进圆角边界 | `:68-71` |
| **Q5** | 开场只给一个主角：单主体 + 完整动作弧（聚光→推近→悬浮→描边光→归位），胜过群体群舞 | `:73-76` |
| **Q6** | 机位服务可读性：信息密集镜头正视，文字特写侧向水平，风格化倾斜逐镜头验证，禁止全局一刀切 | `:78-81` |
| **Q7** | 物件特写四件套：侧面倾斜角 + 可感知高度 + orbit 环绕 + 反差深色材质背景 | `:83-86` |
| **Q8** | 结尾做成「发布会合影」：全片元素四方飞入围住字标，能量推到全片峰值 | `:88-91` |
| **Q9** | 飞入动画的终点必须是页面布局里的真实槽位，元素不悬浮在页面上方 | `:93-96` |
| **Q10** | 文档类镜头的 mock 内容要出版级：原生排版、文字铺满、完整版式入镜 | `:98-101` |
| **Q11** | 要被读的文字有最低有效字高：字幕有效字高 ≥56px（≥5.2% 帧高，推荐 60px 档）、辅助文字 ≥32px（≥3%）；有效字高 = fontSize × 全部祖先 scale × 透视压缩（3D 按 `cos(rotY)` 估算），**按最终像素量不按 fontSize**；文字只有「纹理」或「要读」两态，不存在中间态 | `:103-106` |

**Q2 技法展开要点**（`aesthetic-rules.md:57-61`）：
- 根因：Chromium 对 3D 合成层按 1920 布局宽栅格化再 GPU 放大 → 内容先降采样后放大必糊，与相机/景深参数无关。
- 解法：放大量走 CSS `zoom`（布局级缩放），坐标按 `Tx = 960/zoom − cx` 换算（`PageCam.tsx:100-114` 有完整推导），漏换算会跑焦点。
- 配套：全页 2x（`deviceScaleFactor: 2`）、hero 元素单独 4x 截图、推进期 6f 交叉淡入盖住低倍页面纹理。
- 排查顺序：纹理源分辨率链路（截图倍率→栅格化路径→缩放方式），最后才考虑相机。DoF 只做氛围，**永远不是清晰度的解法**。

#### 声音（S）

| 编号 | 规则（一句话） | 行号 |
|---|---|---|
| **S1** | 配乐与音效按「片种」选不按「事件」选：强鼓点电子底 + 电影系 SFX 词汇，禁游戏音包**音色（禁音色不禁动作）**——判别问句：像真实世界里那个物件发出的声音，还是像游戏引擎的反馈提示音 | `:112-121` |
| **S2** | SFX 逐拍钉帧管理；连发音效做双样本交替 + 音量阶梯递减 + 间隔加速，不同响度复读（本仓库实证**无 playbackRate 变调**） | `:123-126` |
| **S3** | 声音在画面锁定后做；时间线一动，SFX 全表重钉 | `:128-131` |
| **S4** | 拟音优先于装饰音：画面动作配该动作的真实声音，音频裁到与动作严格等长 | `:133-139` |
| **S5** | 音画对齐补两项偏移：输出音轨偏移逐渲染管线实测统一扣，音源峰值滞后逐文件量；统一公式 `from = 目标峰值帧 − 峰值滞后 − 输出偏移` | `:141-144` |

**S1 的关键细节**（易误读，`:116-119`）：否掉的是「合成器 pluck/bloop、卡通弹跳、game-over 音阶」这类游戏音包**质感**，不是「不许给点击配声」。画面里真有点击/开关/碎裂就该配拟音（S4）。模板片自己用 `click-camera.mp3` 且给了全片最高 SFX 响度 0.6。**`sfx/ui/` 不是整目录放行，恰恰是全库最需要逐个试听的一类**（18 个里既有真实开关拟音也有一半以上合成反馈音）；`sfx/glass/` 是真实碎裂材质音（4 个），不在禁列。

#### 文案（C）

| 编号 | 规则（一句话） | 行号 |
|---|---|---|
| **C1** | 文案在画面锁定后按最终镜头重写一遍，纯动画段落也配解说（品牌收尾镜头除外，保持干净） | `:150-153` |
| **C2** | 标语写「团队 + 产品功能名 + 具体收益」，抽象隐喻词一律具体化；重要功能出场前加引导字卡 | `:155-158` |
| **C3** | 3D 镜头里的注记文字活在同一 3D 空间：page-space、同透视、斜拍，大字 + 荧光笔 highlight；平面叠字与场景脱节 | `:160-163` |

#### 流程（P）

| 编号 | 规则（一句话） | 行号 |
|---|---|---|
| **P1** | 交付前必须自己渲染截帧逐一检查，不把首检交给用户 | `:169-172` |
| **P2** | 参考素材先逐帧拆解成手法清单，再逐镜头判断适配性，不全局套用 | `:174-177` |
| **P3** | 指代含糊的反馈先确认对象；改错了整 commit 干净 revert，不在错误版本上打补丁 | `:179-182` |
| **P4** | 先列功能清单逐一对应镜头；一种动画手法全片只当一次主角，重复镜头/信息一律删 | `:184-187` |

**合计 4 + 11 + 5 + 3 + 4 = 27 条**（R1–R4、Q1–Q11、S1–S5、C1–C3、P1–P4）。

---

### A4. `references/final-review.md`：终检 checklist 的检查维度与证据要求

**审查前置**（`final-review.md:3-5`）：审查 Agent 必须处于干净上下文，不参与制作；**不要给它制作过程中的理由、辩解、修改历史或预期结论**。

**审查输入 15 项**（`final-review.md:7-23`）：最新成片 MP4 + 每镜头关键帧；创作模式；产品视频简报与必须展示的功能；需求到执行决策表；视觉方向/品牌 tokens/styleframe（或跳过理由）与禁用风格；功能到镜头映射；Gallery 卡名与具体变体；`library.json` 对应记录；卡片文档定位到的准确 demo TSX；对应 Gallery 参考样片或抽帧/contact sheet；最终分镜/字幕/页面状态/SFX 计划；选中的 `references/shots/*.md`；`aesthetic-rules.md`；数据合规口径。

缺输入时标记「无法验证」，不自行猜测制作基准；索引/卡片文档/demo 源码/参考样片互相冲突时**明确报告冲突来源，不自行挑一个当真相**（`final-review.md:25-26`）。

**检查维度**（`final-review.md:28-101`）：

| 组 | 编号 | 检查内容 |
|---|---|---|
| **P 产品目标** | P1 | 产品定位、目标用户和核心卖点是否清楚 |
| | P2 | 成片是否把注意力放在当前模式确认或记录的功能优先级上 |
| | P3 | 是否出现项目不存在、未经确认或容易误导的功能宣称 |
| | P4 | 需求到执行决策表中的执行选择是否能在分镜/文案/页面状态/音频/素材中找到落地；不得用固定「受众→风格」刻板映射替代项目依据 |
| **F 功能完整性** | F1 | 每个「必须展示的功能」是否至少有一个清楚可辨的镜头 |
| | F2 | 每镜头是否提供新信息，是否存在重复功能或重复 tagline |
| | F3 | 页面状态是否能让观众理解功能，而不只是装饰性运动 |
| **V 视觉方向** | V1 | 字体/色板/材质/圆角/光感/信息密度是否符合确认或记录的视觉方向 |
| | V2 | 动效速度/过冲/停留/能量曲线是否符合确认或记录的动效性格 |
| | V3 | 是否偏离制作基准，漂移到 Ink Press、赛博霓虹或其他无关风格 |
| | V4 | 禁用的颜色/效果/品牌特征是否被使用 |
| **S 镜头卡与变体** | S1 | 功能映射中的镜头卡是否实际出现在对应镜头 |
| | S2 | 用户点名 `卡名 · 样式名` 时，`style-key`、准确 demo TSX 和参考样片是否指向同一变体，成片是否使用该变体 |
| | S3 | 对照准确 demo TSX 与参考样片，是否保留动作语法、关键时值、缓动关系和遮罩时机 |
| | S4 | 是否违反卡片标注的「已知坑/命门」 |
| | S5 | 适配后的产品截图、坐标和品牌 token 是否自然 |
| | S6 | 「仅供参考」样式是否得到用户明确点名并标注风险；「缺少预览」样式是否避免声称与样片一致 |
| **B 分镜一致性** | B1 | 镜头顺序、时长和功能信息是否符合最终分镜 |
| | B2 | 主动作、页面状态、素材来源、字幕、转场和 SFX 是否一致 |
| | B3 | 品牌字标 hold 是否 ≥1 秒，批量动效收尾是否 ≥0.5 秒静止 |
| | B4 | 是否在分镜放行后无依据地删除/替换/增加关键镜头 |
| **D 数据与素材安全** | D1 | 是否遵守真实/虚构/脱敏口径 |
| | D2 | 是否暴露客户、个人、密钥、内部地址等敏感信息 |
| | D3 | 表现真实产品页面时是否使用真实截图，而非低质量手搓复刻 |
| | D4 | 截图状态、字体、图片和动态数据是否完整加载 |
| | D5 | 公开演示数据是否有可复核的公开属性；敏感数据是否已虚构/脱敏/冻结 |
| **A 音频与节奏** | A1 | BGM 是否符合音频方向，音量是否给 SFX 和配音留空间 |
| | A2 | SFX 是否钉在真实动作关键帧，是否出现明显错位 |
| | A3 | 强节奏音乐的切点误差是否 ≤3 帧 |
| | A4 | 结尾能量峰值和 riser→impact→sparkle 句式是否成立（sparkle 一拍取自 `sfx/light/`） |
| | A5 | 长样本（>5s，库里 21 个）是否都显式给 `durationInFrames` |
| | A6 | 每条 SFX 在**渲染产物**里是否真的听得见（不看预览——预览把 volume 钳到 1.0）；轻音素材（峰值 <-12dB，库里 7 个）是否已换素材/预归一化/给足 >1 增益，且渲染后 max_volume 未削波 |
| | A7 | UI 类音效是否为真实物件质感而非合成反馈提示音；`ui-confirm-*` / `ui-*-tone` / `ui-notify-*` 若出现是否有「系统在说话」的叙事理由并写入项目说明文档 |
| | A8 | 配了 BGM 的片子是否交付带 BGM / 无 BGM（保留 SFX）两版，且两版出自同一时间线、逐帧一致 |
| | A9 | 卡点/SFX 密集片是否实测并补偿了输出音轨偏移与音源峰值滞后（`sound-design §4.6`），补偿常数为附实测记录（渲染管线四要素、探针、测法、日期），`SOURCE_BEAT0` 未被污染 |
| **Q 视觉技术质量** | Q | 完整执行 `aesthetic-rules.md`；至少检查文字锐度、构图、圆角遮罩、3D 纹理清晰度、元素落位、相机抖动、转场接缝、光效廉价感、可读时长和确定性渲染 |

**证据要求**（`final-review.md:103-116`）：每条结论使用编号，问题**必须附帧号或截图**：

```text
P1 ✓ 产品定位和核心卖点清楚。
F2 ✗ 第 340 帧：已确认的知识图谱功能没有出现在成片。
V3 ✗ 第 420 帧：大面积琥珀纸张材质偏离已确认的深蓝科技方向。
S2 ✗ 第 515 帧：用户选择 whip-pan，实际实现为 flash-cut。
Q2 ✗ 第 615 帧：3D 推近后正文文字发糊，见关键帧 f615.png。
```

最后按严重程度列出**必须修复项、建议优化项和无法验证项**；不许用没有证据的「整体不错」代替逐项检查，也不许为了报告好看全部标通过（`:115-116`）。

---

## B. 镜头卡（核心资产）

### B5. `references/shots/` 全部卡片清单

**目录结构与计数**（实测 `Get-ChildItem -Recurse`）：157 个 `.md` 卡片文件 + 1 个 `ATTRIBUTION.md`，分布在 10 个类别子目录。

| 类别目录 | 卡数（实测） | 中文名（`gallery/api/library.json` categories） |
|---|---|---|
| `opening/` | 11 | 开场与品牌 |
| `typography/` | 26 | 文字与字卡 |
| `ui-entrance/` | 28 | 界面登场与陈列 |
| `camera/` | 10 | 运镜与空间 |
| `data/` | 13 | 数据与指标 |
| `interaction/` | 15 | 交互与功能演示 |
| `transition/` | 19 | 转场 |
| `rhythm/` | 11 | 节奏与蒙太奇 |
| `effects/` | 17 | 光效与强调 |
| `outro/` | 7 | 收尾 |
| **合计** | **157** | — |

（实测命令：`Get-ChildItem references\shots -Directory | ForEach-Object { $_.Name + "`t" + (Get-ChildItem $_.FullName -File -Filter *.md | Where-Object { $_.Name -ne 'ATTRIBUTION.md' }).Count }`。10 个目录之和 = 157，与 `library.json.stats.cardCount` 一致。）

分类键定义见 `gallery/sync-from-cards.py:38-49`；中英标签同见 `library.json` 的 `categories` 字段。

#### 全量文件名（按类别）

**opening/（11）**：`brand-ink-open`、`crane-rise-reveal`、`dataviz-landscape-open`、`fracture`、`icon-field-colorize`、`letterspace-materialize`、`magician-card-flourish`、`orbit-ring-title-open`、`spotlight-hero-card`、`stroke-segment-build`、`text-as-mask`

**typography/（26）**：`blur-slide`、`brace-expand`、`cel-flash-stomp`、`countdown-arc-scatter`、`document-typewriter-reveal`、`flying-words`、`glitch-cycle`、`gradient-word-sweep`、`lead-word-zoom-assemble`、`marker-underline-title`、`outline-word-fill`、`paper-title-card`、`pill-chip-slot-cycle-handled`、`pill-slot-cycle`、`scramble`、`split-flap-title`、`text-column-converge`、`title-demote-to-label`、`type-assembly-moves`、`type-entrance-moves`、`type-rhythm-sync`、`typewriter-moves`、`typing-code-block`、`vertical-word-roll-blur-cycle`、`word-relay-filmstrip`、`word-relay-geometry`

**ui-entrance/（28）**：`avatar-bracket-carousel`、`bezier-source-converge-merge`、`card-stack`、`carousel-3d`、`cloner-depth-echo`、`deck-deal-flyin`、`doc-park-left-pill-deal`、`draw-svg-trace`、`element-body-moves`、`floating-glossy-label-pills`、`integration-hub-map`、`list-reveal`、`list-stack-press`、`morph-from-primitive`、`neon-frame-forerun`、`neon-frame-orbit-drop`、`page-waterfall-wall`、`paper-craft-moves`、`platform-hinge-rise`、`product-card-progressive-assemble`、`radial-wave`、`research-card-stack-scroll`、`row-embed`、`runway-ground-skim`、`skeleton-reveal`、`svg-shape-morph`、`value-stagger-gradient`、`wall-reveal-moves`

**camera/（10）**：`basic-3d-scene`、`crash-zoom-punch`、`cursor-flyover`、`depth-layer-moves`、`graze-face-tour`、`overhead-camera-moves`、`space-camera-moves`、`steep-tilt-glide`、`tension-camera-moves`、`terminal-3d`

**data/（13）**：`avatar-grid-radial-build-colorize`、`before-after-slider-scrub`、`chart-live-moves`、`counter-confetti`、`cycle-glass-node-morph`、`gauge-readout-moves`、`hatch-depth`、`odometer-digit-roll`、`particle-celebrate-hits`、`particle-sand-fill`、`ring-diagram-annotation-reveal`、`scroll-brake-moves`、`timeline-travel`

**interaction/（15）**：`ai-stream-response`、`autolayout-gap-dial`、`canvas-materialize-moves`、`chip-grid-single-select-blackout`、`chip-lift-to-user-pill`、`collab-cursor-moves`、`command-palette-summon`、`glass-pill-dictation-typing`、`hashtag-to-pill-materialize`、`input-trigger-moves`、`picker-carousel-feature-cycle`、`segmented-thumb-hero`、`theme-switch-moves`、`type-and-filter`、`voice-waveform-live`

**transition/（19）**：`bottom-push-stack-wipe`、`bubble-swarm-takeover`、`card-flip-reveal`、`card-flock-tumble`、`circle-match-iris`、`color-block-step-wipe`、`cube-navigation`、`gradient-transition`、`line-carry-transition`、`mosaic-reframe`、`page-turn-transitions`、`paper-plane-messenger`、`print-texture-transitions`、`shot-transitions`、`tear-streak-transitions`、`transition-hidden-cut`、`transition-travel`、`white-flash-logo-simplify-cut`、`wipe-transitions`

**rhythm/（11）**：`beat-cut-moves`、`beat-step-list-theme-cycle`、`montage-rhythm-moves`、`panel-grid-moves`、`quad-split-parallel-scenes`、`rhythm-interrupt-moves`、`sakuga-timing-shift`、`smear-multiples`、`spectrum-morph-ui`、`speed-ramp-freeze`、`trailer-grammar-moves`

**effects/（17）**：`assemble-then-type-flyin`、`aurora-bloom-bg-flip`、`brand-frame-snap`、`dashboard-glow-highlight-pill`、`fui-hud-moves`、`glow-flyline-moves`、`icon-performance-moves`、`impact-feedback`、`light-play-moves`、`line-boil`、`radial-ripple-phone-chips`、`riso-print-hits`、`scan-bracket-sweep`、`scanline-annotate-focus`、`scanline-assemble-flyin`、`slam-entrance-moves`、`spotlight-sweep-moves`

**outro/（7）**：`edit-hook-moves`、`grain-dissolve`、`logo-shrink-wordmark-lockup`、`neon-triple-marquee`、`outro-group-photo-launch`、`ui-strip-away-outro`、`ui-to-brand-morph`

#### frontmatter 字段结构

所有卡片的 YAML frontmatter 统一含下列键（实测全部 157 张，抽取脚本见附录）：

```yaml
---
name: <卡名，等于文件名>
一句话: <一句话概括>
适用: <适用场景>
时长: <建议时长（多为 "约 4.6s（82–220f）" 形式）>
能量: <能量档（低 / 低中 / 中 / 中高 / 高 / 峰值 / n/a）>
标签: <可选，多类别标签，见下>
---
```

正文固定小节（实测各卡）：`## 意图`、`## 动效核心`（部分为 `## 两式选型` / `## 三式选型` / `## 四式选型`）、`## 参数表`、`## 声音`（部分卡无）、`## 已知坑`、`## 参考实现`。

**`标签:` 字段的语义**（`gallery/sync-from-cards.py:94-100`）：目录名永远是**主类别**（分组归属），`标签:` 列出这张卡也成立的其他类别，只扩大筛选命中面。标签值必须是 `CATEGORIES` 的键，否则 `sync-from-cards.py` 硬失败（`:97-99`）。

#### 关键字段汇总表（按类别分组，全 157 张）

##### 表 A-1：全 157 张卡的关键字段（按类别分组）

「能量 / 时长 / 适用场景摘要」三列全部直接取自各卡 frontmatter 的 `能量:` / `时长:` / `适用:` 字段，未做改写。**所有 157 张卡的 demo 均只依赖 `remotion`**（含 `demos/_fixtures` 共享件）；除 `demos/ui-entrance/page-waterfall-wall` 与 `demos/ui-entrance/clipcard-looping` 两个辅助/素材组件外，库内**没有 three.js 依赖的镜头卡 demo**——`three` 只出现在 `assets/lib/FlatPanel.tsx` 与 `assets/lib/helpers/camera.tsx`（`SKILL.md:229-232`、`CI pr-checks.yml:117-119` 明确按此把两者排除出 tsc）。

| 卡名 | 能量 / 时长 | 适用场景摘要 |
|---|---|---|
| **—— opening（开场与品牌），11 张 ——** | | |
| `brand-ink-open` | 低 ／ 约 2.8s（83f） | 品牌开场；先立名号再进产品 |
| `crane-rise-reveal` | 中高 ／ 5s（特写 hold 20f + 拉升 100f + 满幅静止 30f） | 从细节到全局的开场定场 |
| `dataviz-landscape-open` | 低开缓升 ／ 5–8s（一支片 ≤1 次） | 品牌级抽象开场（数据宇宙隐喻） |
| `fracture` | 高 ／ 约 5.2s（156f） | 开场第一镜「从混沌到成形」 |
| `icon-field-colorize` | 中 ／ 3–4s | 功能全景摆满后品牌色扫翻 |
| `letterspace-materialize` | 低 ／ 3–4s | 片头/片尾品牌字标登场 |
| `magician-card-flourish` | 高 ／ 全段 4.2s | 单张卡片/海报的魔术性登场 |
| `orbit-ring-title-open` | 中 ／ 约 4.3s（130f） | 开场第一镜「这产品有一整套东西」 |
| `spotlight-hero-card` | 中 ／ 约 4.6s（82–220f） | 单一主角式产品开场 |
| `stroke-segment-build` | 低起中收 ／ 4–5s | 开场吊悬念的产品名/大数字揭晓 |
| `text-as-mask` | 中高 ／ 5s | 品牌词与产品画面二合一开场 |
| **—— ui-entrance（界面登场与陈列），28 张 ——** | | |
| `avatar-bracket-carousel` | 中 ／ 约 5.2s（156f） | 「一个位置，多种角色」能力枚举 |
| `bezier-source-converge-merge` | 中 ／ 约 5.6s（168f） | 多源整合/统一接入/数据汇聚 |
| `card-stack` | 中高 ／ 约 4.2s（126f） | 「我们有一组东西」的产品段落 |
| `carousel-3d` | 中 ／ 约 5.6s（168f） | 作品集/模板库/集成清单循环展示 |
| `cloner-depth-echo` | 中 ／ 4–5s | 多副本/多租户/规模感卖点 |
| `deck-deal-flyin` | 高 ／ 约 2.6s 发牌段（36–113f），前接约 2s 牌堆特写可选 | 内容量大/源源不断汇入的列表页与卡片墙 |
| `doc-park-left-pill-deal` | 低 ／ 约 5.8s（174f） | 旁白驱动的「分析结论逐条给出」 |
| `draw-svg-trace` | 中 ／ 约 3–4s（描边 40f + 闪黑交棒 16f + hold ≥35f） | 单个卡片/图表/标题被点名入场 |
| `element-body-moves` | A 中高 / B 低中 ／ A ~4.7s / B ~5.3s | 给「位置在变」之外补「身体在变」 |
| `floating-glossy-label-pills` | 中 ／ 约 4.0s（120f） | 多功能横向枚举（Feature A–D 各一屏） |
| `integration-hub-map` | 中高 ／ 全段 4.5–5s | 集成/生态能力段；版本翻新叙事 |
| `list-reveal` | 低 ／ 约 3.6s（108f） | 导航/侧边栏/设置面板入场 |
| `list-stack-press` | 中 ／ 约 3s（18–88f） | feed/雷达/收件箱类「每天有新东西」 |
| `morph-from-primitive` | 中低 ／ ~4.7s（呼吸 20f + 变形 24f + 淡入 12f） | 图形/图标/卡轮廓类主体入场 |
| `neon-frame-forerun` | 中高 ／ 全段 4–4.5s | 暗场品牌片给 UI 面板做登场仪式 |
| `neon-frame-orbit-drop` | 中高 ／ 全段 4–4.5s | 单页 UI 的一次性隆重登场 |
| `page-waterfall-wall` | 中 ／ 4–6s（无限循环体） | 多页面/多功能/多模板体量感段落 |
| `paper-craft-moves` | A 中 / B 中高 ／ A 3–4s / B 4–5.5s | 纸墨主视觉片的实体材料语言 |
| `platform-hinge-rise` | 中 ／ 约 3.5s（104f） | 两个主体/方案/品牌并列登场 |
| `product-card-progressive-assemble` | 中 ／ 约 5.0s（150f） | 商品/条目详情页能力展示 |
| `radial-wave` | 中高 ／ 约 3.8s（114f） | 品牌开场「系统上电」；数据网格/节点地图 |
| `research-card-stack-scroll` | 中高 ／ 约 4.8s（144f） | 「读了大量资料/处理海量文档」的量级交代 |
| `row-embed` | 中 ／ 约 2s（12–68f） | 结构化数据长进页面的详情页/列表镜头 |
| `runway-ground-skim` | 高 ／ 全段 4s | 仪表盘/卡片流界面登场 |
| `skeleton-reveal` | 中 ／ ~5.7s（172f） | 产品 UI 的「从无到有」登场叙事 |
| `svg-shape-morph` | 低 ／ 约 5.2s（156f） | 抽象概念的形态转换/有机生长表达 |
| `value-stagger-gradient` | 中高 ／ 约 5.0s（150f） | 技法演示与参数化能力展示；数据/频谱界面入场 |
| `wall-reveal-moves` | 中 ／ 单式约 4.3–5s（A 150f / B 130f / C 150f） | 功能墙/卡片墙/整页界面整体亮相 |
| **—— typography（文字与字卡），26 张 ——** | | |
| `blur-slide` | 低 ／ 约 3.8s（114f） | 几乎所有标题/副标题成对出现的场合 |
| `brace-expand` | 中 ／ 约 3.8s（114f） | 开发者/技术产品标题字卡 |
| `cel-flash-stomp` | 高 ／ 三词约 4.8s | 口号/三连词高能段落 |
| `countdown-arc-scatter` | 高 ／ 约 1.1s（33f） | 倒计时/时长承诺类文案 |
| `document-typewriter-reveal` | 低中 ／ 约 3.7s（110f） | 文档/报告/笔记类功能镜头 |
| `flying-words` | 高 ／ 约 6.0s（180f） | 关键词云/能力清单动态背景 |
| `glitch-cycle` | 中高 ／ 约 5.6s（168f） | 加载/构建/部署状态播报 |
| `gradient-word-sweep` | 高 ／ 全段 2.5–3.5s | 标语里给单个动词/卖点词充能 |
| `lead-word-zoom-assemble` | 中高 ／ 约 2.8s（84f） | 品牌名/产品名的 Introducing 字卡 |
| `marker-underline-title` | 低 ／ 总 1–1.5s | 标题里强调单个关键词 |
| `outline-word-fill` | 高 ／ 约 2.5s（75f） | 单词式利益点/口号的重锤一拍 |
| `paper-title-card` | 低 ／ 1.7–1.8s（50–55f） | 章节转场/价值主张字卡；全片呼吸位 |
| `pill-chip-slot-cycle-handled` | 中 ／ 约 5.0s（150f） | 「我们替你搞定 ___」句式卖点 |
| `pill-slot-cycle` | 中 ／ 6 词约 5.8s（demo 175f） | 功能列举类文案的最优雅解法 |
| `scramble` | 中高 ／ 约 3.2s（96f） | 技术型开场标题；版本号揭晓 |
| `split-flap-title` | 中 ／ 约 4.7s（140f） | 开场/章节大标题；机械宣告感 |
| `text-column-converge` | 中低 ／ 全段约 5–6s | 特性清单收束到产品名/口号 |
| `title-demote-to-label` | 低中 ／ A ~3s（92f）/ B ~3.5s（104f） | 章节开场（标题先当主角再让位） |
| `type-assembly-moves` | A 中 / B 中高 / C 低中 / D 中 ／ 单式 4–5s | 大标题/标语的入场（全片 ≤2 种） |
| `type-entrance-moves` | 中高 ／ 单式 4–5s | 大标题/章节字卡入场 |
| `type-rhythm-sync` | A 高 / B 中 ／ 单式 4–5s | 标题/标语与音轨强绑定的段落 |
| `typewriter-moves` | A 中高 / B 中低 ／ A ~5s / B ~5.5s | 开发者产品开场、slogan 字卡 |
| `typing-code-block` | 中 ／ 约 4.6s（138f） | 代码/配置揭示镜头 |
| `vertical-word-roll-blur-cycle` | 中 ／ 约 5.0s（150f） | 「Built for ___」句式卖点 |
| `word-relay-filmstrip` | 中低 ／ 全段 5–7s | 「一个主体 × 多种能力」枚举段 |
| `word-relay-geometry` | 中高 ／ 约 6.0s（180f） | 三点式利益陈述（更快/更好/更强） |
| **—— camera（运镜与空间），10 张 ——** | | |
| `basic-3d-scene` | 中 ／ 约 6.0s（180f） | 概念/路线图/三步法的空间化讲述 |
| `crash-zoom-punch` | 高 ／ 约 0.5s 动作 + 前后 hold（动作 6–11f） | 功能段「点名」镜头 |
| `cursor-flyover` | 中 ／ 约 6.0s（180f） | 单页产品功能巡览（光标当导游） |
| `depth-layer-moves` | 视差=中 / dolly-zoom=中高 ／ 视差 4–5s / dolly 3–4s | 平面截图要「有厚度」的段落 |
| `graze-face-tour` | 中高 ／ 单段 4–5s | 功能区巡礼；暗场+霓虹缘光「内部世界」 |
| `overhead-camera-moves` | A 中 / B 中高 ／ A ~4.8s / B ~4.7s | 用俯仰角讲故事的开场/转场 |
| `space-camera-moves` | 高 ／ A 5s / C 3–5s | 把平面页面当 3D 实体拍的高光段落（合计 ≤2 次） |
| `steep-tilt-glide` | 中高 ／ 4s（120f）单镜 | 长页面/多区块 UI 炫技巡览 |
| `tension-camera-moves` | A 高 / B 中 / C 低压升 / D 低收 ／ 单式 4–5s（全片合计 ≤2 式） | 情绪节点的运镜语言 |
| `terminal-3d` | 中 ／ 约 6.0s（180f） | 开发者产品 CLI/工作流演示 |
| **—— data（数据与指标），13 张 ——** | | |
| `avatar-grid-radial-build-colorize` | 中 ／ 约 5.6s（168f） | 「群体中浮现异常/重点」的数据叙事 |
| `before-after-slider-scrub` | 中 ／ 4–5s | AI 增强/优化/重构的效果对比 |
| `chart-live-moves` | 中高 ／ 各 4–6s | 数据叙事段落（实时性/每个数字是一个人/增长装不下） |
| `counter-confetti` | 高 ／ 约 4.6s（138f） | 里程碑/成绩数字的庆祝拍 |
| `cycle-glass-node-morph` | 中高 ／ 约 8.6s（257f） | AI agent/自动化/控制系统的感知—推理—执行循环 |
| `gauge-readout-moves` | 中高 ／ A 4–5s / B 4–5s | dashboard 开场仪式/性能指标揭晓 |
| `hatch-depth` | 中 ／ 约 4.4s（132f） | 「从草稿到真实数据」的叙事拍 |
| `odometer-digit-roll` | 中高 ／ 滚动+逐位锁定 ~63f + 脉冲 8f + hold ≥45f，约 5s | 单个王牌指标的全屏亮相 |
| `particle-celebrate-hits` | 高潮点缀型 ／ A 3–4s / B 4–5s | 里程碑数字/KPI 揭晓/成就段落 |
| `particle-sand-fill` | 中高 ／ 4–5s | 柱状图/量级对比入场；积累/汇聚语义 |
| `ring-diagram-annotation-reveal` | 中高 ／ 约 6.3s（190f） | 把抽象名词解释成结构图 |
| `scroll-brake-moves` | 高开中收 ／ A 4–5s / B 5s | changelog/发布史/长列表段落 |
| `timeline-travel` | 中高 ／ 4–5s | changelog/里程碑/发展史段落 |
| **—— interaction（交互与功能演示），15 张 ——** | | |
| `ai-stream-response` | 中高 ／ 约 4–5s（120–150f） | AI 助手/agent/search/copilot 结果生成镜头 |
| `autolayout-gap-dial` | 中 ／ ~4s（120f） | 设计工具/低代码「改一个数、界面跟着动」 |
| `canvas-materialize-moves` | 中 ／ A ~4.3s（130f）/ B ~5.3s（160f） | AI/协作工具「生成结果落到画布上」 |
| `chip-grid-single-select-blackout` | 中低 ／ 约 5.0s（150f） | 单选/套餐/档位选择的交互演示 |
| `chip-lift-to-user-pill` | 中 ／ 约 5.0s（150f） | 「从一堆候选里选中并展开这一个」 |
| `collab-cursor-moves` | A 中 / B 低中 ／ A ~4.7s（140f）/ B ~4.7s（140f） | 协作/多人/交接主题叙事段 |
| `command-palette-summon` | 中 ／ 4–5s | 效率型产品「全产品在一个输入框里」 |
| `glass-pill-dictation-typing` | 低 ／ 约 1.7s（50f） | 语音/AI 输入框登场；高能段之间的安静过渡拍 |
| `hashtag-to-pill-materialize` | 中 ／ 全段约 3.5s | 标签/分类/关键词功能演示 |
| `input-trigger-moves` | A 中 / C 高 ／ A ~5s / C ~5s | 发布片的第一人称段落 |
| `picker-carousel-feature-cycle` | 中 ／ 约 3.6s（108f） | 逐个念出功能名/场景名的列表镜头 |
| `segmented-thumb-hero` | 中 ／ ~3.5s（demo 110f） | 「模式切换/二选一」功能宣告镜头 |
| `theme-switch-moves` | A 中 / B 中高 ／ A 3–4s / B 5–6s | 深色模式/主题功能叙事段落 |
| `type-and-filter` | 中 ／ 约 2.5s（118–190f） | 搜索/筛选/进入详情的交互链路 |
| `voice-waveform-live` | 中 ／ ~5s（150f） | 语音输入/AI 助手「正在听你说」 |
| **—— transition（转场），19 张 ——** | | |
| `bottom-push-stack-wipe` | 中 ／ 单次推入 30f + 章内 hold ~1s（demo 三连推 140f） | 多章节产品片的换章骨架 |
| `bubble-swarm-takeover` | 中高 ／ ~4.3s（130f） | 章节级换景且品牌世界里有实体装饰物 |
| `card-flip-reveal` | 中高 ／ 单卡翻转 26f，三卡错峰 10f，全程 ~4.9s | 功能→成果的成对叙事（元素级转场卡） |
| `card-flock-tumble` | 极高 ／ 全段 4.5s | 能量高潮段（功能页群→品牌口号爆点转场） |
| `circle-match-iris` | 中高 ／ 4.7s | 前景有圆形元素、后景有圆形主体的接缝 |
| `color-block-step-wipe` | 中高 ／ A ~2.5s / B ~1.5–2s | 品牌色转场/章节交接；硬朗无缓动段落 |
| `cube-navigation` | 中 ／ 约 6.0s（180f） | 多模块产品的逐面导航陈列 |
| `gradient-transition` | 低 ／ 约 6.0s（180f） | 氛围底/章节底色连续变奏 |
| `line-carry-transition` | 中 ／ ~5.3s | 两个有图形亲缘的场景之间 |
| `mosaic-reframe` | 中 ／ 约 6.0s（180f） | 「同一批内容多种看法」的陈列转场 |
| `page-turn-transitions` | 中高 ／ 单式约 4.4–4.7s | 章节级换页的「翻篇」仪式 |
| `paper-plane-messenger` | 中 ／ ~5s（150f） | 「发送/邀请/分享」动作连接两个场景 |
| `print-texture-transitions` | 中 ／ 4–4.5s | 换景接缝的纸墨审美款 |
| `shot-transitions` | n/a（技法卡） ／ n/a | 任何两镜衔接处（六式：推进流白/穿暗场直航/虚焦接力/黑场字卡/whip-pan/mask-wipe） |
| `tear-streak-transitions` | 高 ／ 约 4.5s（135–140f） | 高能换页：数字故障/断裂语义 |
| `transition-hidden-cut` | n/a（技法卡） ／ n/a | 两镜衔接处需要无痕换景或仪式感开屏（三式） |
| `transition-travel` | n/a（技法卡） ／ n/a | 前后两镜存在元素/容器级空间关系的接缝（两式） |
| `white-flash-logo-simplify-cut` | 中高 ／ 约 3.6s（108f） | 品牌段落收束（华丽演绎→干净定妆） |
| `wipe-transitions` | 中 ／ 单式约 5s（150f） | 新旧页都不动、一条几何边界扫过的通用转场（两式） |
| **—— rhythm（节奏与蒙太奇），11 张 ——** | | |
| `beat-cut-moves` | 高 ／ A ~4.3s / B ~4.3s | 高光/冲刺段落把「切」本身打成鼓点 |
| `beat-step-list-theme-cycle` | 高 ／ 3 拍约 3.5s（demo 110f） | 「同一产品多种气质/多主题展示」段 |
| `montage-rhythm-moves` | 高 ／ A 4.3s / B 4.3s / C 5s | 段落级节奏设计（蓄力爆发/流程速写/开场连锁） |
| `panel-grid-moves` | A 高 / B 中 / C 中高 ／ A ~4.7s / B ~4.8s / C ~5s | 把「格子」当节奏器 |
| `quad-split-parallel-scenes` | 高 ／ 约 2.1s（63f） | 节奏段「功能很多、同时发生」的蒙太奇拍 |
| `rhythm-interrupt-moves` | B 中 / C 高 ／ B ~4.5s / C ~4.5s | 用「打断连续性」本身当节奏器 |
| `sakuga-timing-shift` | 中高 ／ ~5s | 单元素的强调性位移 |
| `smear-multiples` | 中高 ／ 元素级技法（移动 12f + 合拢回弹 8f） | 元素高速位移段要漫画式速度感 |
| `spectrum-morph-ui` | 中 ／ ~4.7s | 有音轨片子的声画同步高光段 |
| `speed-ramp-freeze` | 中高 ／ 全程 4–5s | 卡片流/长横移中把一个重点放慢/停下 |
| `trailer-grammar-moves` | A 高 / B 中 / C 高 ／ A ~4.7s / B ~5s / C ~4.5s | 预告片的三个结构性时刻 |
| **—— effects（光效与强调），17 张 ——** | | |
| `assemble-then-type-flyin` | 中高 ／ 约 5.2s（156f） | 页面/海报「自己长出来」的开场 |
| `aurora-bloom-bg-flip` | 由低到高 ／ 约 5.2s（156f） | 叙事转折点；品牌片拉到重音的那一拍 |
| `brand-frame-snap` | 中 ／ 单次翻色 ~4.3s（130f） | 双模式/双章节产品片的全片包装层 |
| `dashboard-glow-highlight-pill` | 高 ／ 约 2.0s（60f） | 金融/数据类产品的重功能揭示 |
| `fui-hud-moves` | A 中 / B 中高 ／ A 3–4s / B 2–3s | 暗场/科技感段落面板入退场；目标点名 |
| `glow-flyline-moves` | A 低 / B 中 / C 中高 ／ A ~5s / B ~4.7s / C ~5.2s | 全片唯一暗场段落的氛围与数据叙事 |
| `icon-performance-moves` | A 高潮点缀 / B 蓄势引入 ／ A 3–4s / B 4–5s | 半屏级 icon 特写段落 |
| `impact-feedback` | 高 ／ n/a（元素级技法） | 元素落位/撞击的「命中一瞬」 |
| `light-play-moves` | A 中 / B 低 / D 高 ／ A ~5.3s / B ~4.7s / D ~4.8s | 把光当第四种笔触（扫/擦/晕） |
| `line-boil` | 低 ／ 寄生型 | 标题字卡/描边元素的长 hold 段 |
| `radial-ripple-phone-chips` | 低 ／ 约 5.6s（168f） | 移动端产品「这就是它」定格镜头 |
| `riso-print-hits` | 高 ／ A 4s / B 4.7s | 标题/卡片的命中强调，纸墨审美版故障闪 |
| `scan-bracket-sweep` | 中低 ／ 约 5.0s（150f） | 「正在解析/校验这份内容」的过程镜头 |
| `scanline-annotate-focus` | 中 ／ 约 4.6s（138f） | 「AI 正在读你的页面/品牌」的分析镜头 |
| `scanline-assemble-flyin` | 中高 ／ 约 4.6s（138f） | 「页面自己生成」的开场（AI 建站/自动排版） |
| `slam-entrance-moves` | 高 ／ 单式动作段 6–22f + 余波 ~16f + hold ≥45f | 主角卡/KPI 卡的重拳入场 |
| `spotlight-sweep-moves` | 中低 ／ 单式 3.5–4.5s | 暗色调品牌片里逐个介绍 UI 面板 |
| **—— outro（收尾），7 张 ——** | | |
| `edit-hook-moves` | 低→瞬时中→低 ／ ~5s | 片尾收束（全片 ≤1 次） |
| `grain-dissolve` | 中高 ／ 约 2.0s（60f） | 收尾「XX. Now Live」式上线宣告 |
| `logo-shrink-wordmark-lockup` | 中 ／ 约 4.4s（132f） | 片尾品牌定妆（图标+字标+标语 lockup） |
| `neon-triple-marquee` | 中高 ／ 4–5s（demo 150f） | 片尾主题词复读机段落；三连词口号余韵 |
| `outro-group-photo-launch` | 峰值 ／ 约 4.8s（145f） | outro/品牌收尾；多功能产品全家福式终镜 |
| `ui-strip-away-outro` | 中 ／ ~4.3s（130f） | 「发布/完成」语义 outro |
| `ui-to-brand-morph` | 中高 ／ A ~4.3s（130f）/ B ~4.7s（140f） | 品牌收尾/outro 前最后一拍 |

#### 特别标注：科技新闻类视频最可能用到的卡型

| 类型 | 推荐卡（按优先级） | 依据 |
|---|---|---|
| **开场 / logo 类** | `brand-ink-open`、`letterspace-materialize`、`spotlight-hero-card`、`crane-rise-reveal`、`orbit-ring-title-open`、`icon-field-colorize`、`lead-word-zoom-assemble`、`text-as-mask`、`stroke-segment-build`、`magician-card-flourish`、`fracture`、`dataviz-landscape-open` | `opening/` 全 11 张；`promo-energy-arc.md:18` 把 `brand-ink-open` 列为①段位候选、`:19` 把 `spotlight-hero-card` 列为②段位候选 |
| **数字翻转（DigitRoll）类** | `odometer-digit-roll`（全屏巨号数位滚轮）、`gauge-readout-moves`（A 满弧扫针 / B 滚带定针）、`counter-confetti`（计数+彩纸）、`particle-celebrate-hits` B 式（计数器破整千迸火星）、`scroll-brake-moves`、`timeline-travel`；**组件层** `assets/lib/DigitRoll.tsx`（模板片字卡副标用的里程表滚动） | `odometer-digit-roll.md:1-53`；`gauge-readout-moves.md:15`（明确与 odometer 分工）；`DigitRoll.tsx:1` |
| **雷达 / 科技感入场类** | `wipe-transitions` A 式 `clock-wipe`（雷达指针扫一圈换页）、`gauge-readout-moves` A 式（点火自检扫针）、`radial-wave`（点阵波纹点亮）、`fui-hud-moves`（线展面 / 准星咬合）、`scanline-annotate-focus`、`scanline-assemble-flyin`、`scan-bracket-sweep`、`glow-flyline-moves`、`spotlight-sweep-moves`、`neon-frame-forerun`、`neon-frame-orbit-drop`、`dashboard-glow-highlight-pill` | `wipe-transitions.md:20`（A clock-wipe = 雷达指针扫一圈）；`gauge-readout-moves.md:10-14`；`radial-wave.md:1` |
| **地图 / 网络类** | `integration-hub-map`（五集成图标 + 五条彩虹光管连接）、`glow-flyline-moves` B 式 `flyline-arc`（飞线连接）、`bezier-source-converge-merge`（多源曲线汇聚）、`radial-wave`（节点地图）、`cycle-glass-node-morph`（机制图节点）、`ring-diagram-annotation-reveal`（同心环图解） | `integration-hub-map.md:1`；`glow-flyline-moves.md:1`；`bezier-source-converge-merge.md:1`；`radial-wave.md:1`（原文即「节点地图」） |
| **收尾 / CTA 类** | `outro-group-photo-launch`（峰值全家福）、`logo-shrink-wordmark-lockup`、`ui-to-brand-morph`、`grain-dissolve`、`neon-triple-marquee`、`text-column-converge`、`ui-strip-away-outro`、`edit-hook-moves`、`white-flash-logo-simplify-cut` | `outro/` 全 7 张 + `text-column-converge`（标签为 outro）+ `white-flash-logo-simplify-cut` |
| **字幕 / 文字动效类** | `blur-slide`（默认文字 reveal）、`paper-title-card`（呼吸字卡）、`scramble`、`split-flap-title`、`type-entrance-moves`、`type-assembly-moves`、`typewriter-moves`、`typing-code-block`、`marker-underline-title`、`outline-word-fill`、`gradient-word-sweep`、`cel-flash-stomp`、`glitch-cycle`、`pill-slot-cycle`、`vertical-word-roll-blur-cycle`、`type-rhythm-sync`；**组件层** `assets/lib/Caption.tsx`（底部通栏解说）与 `template/src/aifl/PaperTitleCard.tsx` | 见 B6；`Caption.tsx:11-13` 明确 22px 属「信息条」风格，低于 Q11 字幕线 |
| **图片 / 截图展示类** | `spotlight-hero-card`、`deck-deal-flyin`、`row-embed`、`list-stack-press`、`document-typewriter-reveal`、`page-waterfall-wall`、`card-stack`、`carousel-3d`、`wall-reveal-moves`、`mosaic-reframe`、`before-after-slider-scrub`、`runway-ground-skim`、`research-card-stack-scroll`；**组件层** `assets/lib/PageCam.tsx`（2.5D 页面相机）、`assets/lib/ClipCard.tsx`（真实 mp4 素材包成卡片） | `demos/README.md:12-23` 列出「真实纹理类」demo 名单；`PageCam.tsx:18-27`；`ClipCard.tsx:11-15` |

---

### B6. 重点精读：5 张科技新闻类最常用的卡（完整重写）

#### B6-1 `odometer-digit-roll`（数字翻转类 · 全屏巨号数位滚动）

- **来源**：`references/shots/data/odometer-digit-roll.md`（55 行，全文已精读）
- **frontmatter**（`:1-8`）：

```yaml
name: odometer-digit-roll
一句话: 里程表数字滚动大字报——全屏巨号指标每个数位像老虎机滚轮独立纵向滚动带残影，从左到右逐位过冲停稳，全部锁定瞬间整体加深脉冲
适用: 单个王牌指标的全屏亮相（"10x"/"99.98%"级）；与 impact-feedback B 式（伤害数字弹出）分工——那是元素级配菜，这是全屏级主菜
时长: 滚动+逐位锁定 ~63f + 脉冲 8f + hold ≥45f，约 5s
能量: 中高
标签: typography
```

- **意图**（`:10-17`）：数字不是飞进来的，是「算出来的」——每位一条 0–9 滚轮高速转动，从左到右逐位减速、过冲半格、咔哒锁定。滚动过程自带悬念，逐位锁定自带节奏（哒、哒、哒、哒）。与 `VerticalTicker` 的区别：**有终值、逐位停稳，不是无限滚动墙**。

- **动效核心**（`:19-29`）：
  - 每位一个 `overflow:hidden` 数位盒 + `0–9×2` 纵列 strip，`translateY = −(pos % 10) × 行高`，`posAt(f, i)` 纯帧函数。
  - 位 i 于 `20+i×7f` 开始 16f `Easing.out(cubic)` 减速至目标 +0.5 行**过冲半格**，再 6f 弹回整数锁定——锁定帧即各位的「哒」。
  - 滚动期每位叠 2 个错帧残影副本（`translateY ±行高×0.5`，opacity 0.25/0.12），按相邻帧速度门控，停稳自动摘。
  - 全体锁定帧：整体 ink→`#000`→ink 加深脉冲 8f + `1.035` 微缩放 + 下方标签条淡入。
  - 小数点与 `%` 等非数字位全程驻场不滚。

- **参数表**（`:31-39`，原样引用）：

```text
| 参数 | 典型值 | 调节手感 |
|------|--------|----------|
| 字号/字体 | 190px fw800 + fontVariantNumeric: tabular-nums | 非等宽数字每滚一格整行抖动（同 scramble 等宽判例） |
| 错峰 | 20+i×7f 起停，从左到右 | 从右往左停读作倒着算；同时停失去"哒哒哒" |
| 过冲 | +0.5 行再 6f 弹回 | 无过冲读作滑到即停，机械感减半 |
| 残影 | 2 副本 0.25/0.12，速度门控 | 3+ 副本高速下糊成一条（行高小于卡片场景） |
| 终值脉冲 | 加深 + 1.035 缩放 8f | 只加深不缩放在 190px 黑字上不可感（实渲加码） |
| 收尾 | 脉冲归零后真静止 ≥45f | R1 |
```

- **已知坑 / 命门**（`:41-51`）：
  1. demo 在灰阶/占位素材上调校通过——参数是**调校起点非实战定稿**，首次实战须以真实素材回验。
  2. **数位 ≤6（含小数点前后）**——每多一位多 7f 错峰，8 位滚完 >2.5s 观众等不起；大数换缩写（`12.4M` 不是 `12,400,000`）。
  3. 与 `impact-feedback` B（伤害数字）同片可共存但分工要清：**全屏主菜一次（本卡），卡片配菜多次（B 式）**——两处都全屏就是两次主菜。
  4. **滚动的数字必须是真值的各位**——终值 99.98 就滚 9/9/9/8，中途乱数会被暂停党抓到「假滚动」。
  5. 声音强依赖候选位：逐位锁定「哒」×N + 终值确认一声低音（`sound-design §4.5`），无声版成立但少一半爽感。

- **参考实现**（`:53-55`）：`demos/data/odometer-digit-roll/`（`OdometerDigitRoll.tsx`），实测存在（178 行）。
- **源码关键常量**（`demos/data/odometer-digit-roll/OdometerDigitRoll.tsx:14-18`）：

```ts
const ROW = 210;   // 数位行高（overflow 盒高）
const DW = 126;    // 数位盒宽
const FS = 190;    // 字号
const SPIN = 0.85; // 高速滚动速度：行/帧
const DIGITS = [9, 9, 9, 8]; // 目标数位（"99.98" 中可滚的四位）
```

- **纯帧位置函数**（`OdometerDigitRoll.tsx:20-41`，可直接照抄）：

```ts
// 位 i 的 strip 位置（单位：行，连续值）。纯帧函数，天然确定性。
const posAt = (f: number, i: number): number => {
  const d = DIGITS[i];
  const s = 20 + i * 7; // 开始减速帧
  const p0 = SPIN * s;
  // 最小再走 6 行后，落在个位 = d 的最近整数位置
  const T = Math.ceil((p0 + 6 - d) / 10) * 10 + d;
  if (f < s) return SPIN * Math.max(f, 0);
  if (f < s + 16)
    return interpolate(f, [s, s + 16], [p0, T + 0.5], {
      extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic),
    });
  if (f < s + 22)
    return interpolate(f, [s + 16, s + 22], [T + 0.5, T], {
      extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic),
    });
  return T;
};
```

- **关键帧结构**（源码注释 `OdometerDigitRoll.tsx:7-9`）：`0–20` 四位全速滚（0.85 行/帧）→ `20/27/34/41` 逐位开始减速（各 16f 减速 + 6f 回弹，锁定于 `42/49/56/63`）→ `63–71` 整体加深脉冲（ink→#000→ink，附 1.035 微缩放）→ `66–84` 下方标签条淡入 → `84–150` 全静止（66f ≥45f）。
- **残影门控写法**（`OdometerDigitRoll.tsx:82-87`）：

```tsx
const pos = posAt(frame, i);
const speed = Math.abs(pos - posAt(frame - 1, i));
const gate = interpolate(speed, [0.06, 0.5], [0, 1], {
  extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
});
// gate > 0.001 时挂 2 层 Strip：opacity 0.25*gate dy=+ROW*0.5 / opacity 0.12*gate dy=-ROW*0.5
```

- **依赖**：仅 `remotion` + `demos/_fixtures/Fixtures.tsx`（灰阶假 UI：`G` 调色板、`TitleBlock`）。不依赖 three.js。

#### B6-2 `spotlight-hero-card`（开场类 · 单主角立传）

- **来源**：`references/shots/opening/spotlight-hero-card.md`（40 行）
- **frontmatter**（`:1-8`）：`一句话` 见上表；`时长: 约 4.6s（82–220f）`；`能量: 中（质感最高的一镜，节奏慢而稳）`；`标签: effects、camera`。
- **意图**（`:10-11`）：开场只讲一件事——**这一张卡就是产品的原子单位**。聚光灯替观众做视线引导，弹起悬浮给它体积和重量，轮廓光束是「扫描/检视」的隐喻，最后贴回原位表示它属于这个页面。
- **动效核心**（`:13-19`）：
  - 游走聚光灯经几个中间站后锁定卡心，光池收拢 + 锁定瞬间脉冲，外部 vignette 压暗。
  - 相机从全页正视推进到斜侧特写（**左侧机位主导**），焦点略偏让卡落在画面偏右。
  - 卡片 `rise`（带过冲）→ 悬停 `sin bob` → `reseat`（落地微压）。
  - SVG rounded-rect 轮廓光束跑两圈：第一圈快而亮、第二圈慢而弱。
  - 卡起飞后原位铺页面底色补丁 + 强调色呼吸描边，落地瞬间增亮消失。
  - 可选 3D 悬空注记（hover-3d-annotation 手法）：卡左侧浮大衬线两行注记（字号 37、宽 230px），`translateZ 92` + sin 3px bob（周期 44f，与卡 40f 相近但不同步——共感而非镜像），关键词背后 12f 长出马克笔荧光条 `oklch(88% 0.095 85)`，向页面投椭圆软影；**注记必须活在同一 3D 空间、同一台相机透视（C3）**——第一版平面叠字被否决后重做。
- **参数表**（`:21-29`，原样引用）：

```text
| 参数 | 典型值 | 调节手感 |
|------|--------|----------|
| 选卡 | cards[3]，中心 x 恰为 960（页面中心） | 主角卡先按"推进后构图居中"选，不是随便挑一张 |
| 相机 | 静止全页 zoom 0.78（82–114f）→ 16f 推进 zoom 2.6；rotY 34° 主导 + rotX 仅 8°，persp 1200；焦点取卡心左移 30px；reseat 触地后 cx/cy/zoom/rot 全锁死 ≥15f | 侧向水平机位读感优于俯拍（"从左侧拍摄而不是从下方"，Q6）；收尾禁用 zoom 2.6→2.58 一类尾漂，呼吸必须是真静止（R1） |
| 聚光灯 | 4 个中间站（86→130f），光池半径 620→420→360 收拢，锁定 +6% 脉冲；vignette 0.16→0.42 | 中间站让"随机照射"可信；直奔目标读作程序化 |
| 动作弧 | rise 10f（bezier(0.2,1.25,0.3,1) 过冲）→ 悬停 54f（sin bob 振幅 4px 周期 40f，z=110px·lift）→ reseat 18f，落地 press 0.997 | 锁定→落地 ≈98f≈3.3s——质感镜头要"放慢到 3 秒"（R3），初版几乎总是偏快 |
| 轮廓光束 | lap1 142→156f（strokeWidth 5+2.5 双层）、lap2 162→182f（3.5+1.75、整体 opacity 0.62）；strokeDasharray "0.14 1" 走 dashoffset | 两圈快慢有别才读作"持续扫描"，一圈是眨眼；光束只给主角一次（Q4） |
| 双层影 | `0 8·lift px …, 0 46·lift px 90·lift px` 随高度生长 | 影子不随高度长，悬浮就不成立 |
```

- **声音**（`:31-32`）：弹起钉 `whoosh-big`（模板片钉在 f127），光束扫描钉 `sparkle`（f141），reseat 钉 `transition-snap`（f204）——弹起/光效/落定各有专属音（S2、S4）。
- **已知坑 / 命门**（`:34-37`）：
  1. **开场多卡群舞撑不起第一印象（Q5）**——开场曾反复推倒多次才收敛到单卡；直接从单主角 + 完整动作弧起稿。
  2. **推进特写下卡上文字会糊，根因是纹理栅格化分辨率不是 DoF**——配套技法见 Q2。
  3. **逐卡 glint 闪烁被两次否决**（Q4），光效严格只给主角。
- **参考实现**（`:39-40`）：`demos/opening/spotlight-hero-card/SpotlightHeroCard.tsx`（原 `template/src/aifl/live/SceneOpen.tsx` 82–220 段）。实测存在。
- **依赖**：需要真实页面纹理 → 用 `demos/_fixtures/PageCam2D.tsx`（`demos/README.md:12-16`）；纹理放 `public/textures/live/`。不依赖 three.js。

#### B6-3 `deck-deal-flyin`（图片/截图展示类 · 发牌式批量入场）

- **来源**：`references/shots/ui-entrance/deck-deal-flyin.md`（45 行）
- **frontmatter**（`:1-7`）：`时长: 约 2.6s 发牌段（36–113f），前接约 2s（62f）牌堆特写可选`；`能量: 高（节奏爬升段主力，不放开场第一镜）`。
- **意图**（`:9-10`）：先给悬念（这一摞是什么？），再给答案（是几十个项目，它们自己飞进页面各就各位）。
- **动效核心**（`:12-16`）：
  - 前半（`pile-orbit-open`，可选）：所有卡叠成有物理高度的实体牌堆，暗色拉丝金属背景，相机侧斜特写绕堆环绕，然后拉远、金属背景同步淡出接页面。
  - **预备拍（anticipation，迪士尼法则 2）**：首张出牌前给一拍**段落级**预备（牌堆整体微下压 + 顶卡反向回拉）。**只做段落级一次，不逐卡加**（逐卡预备会拖垮 R2 的硬加速节拍）。
  - 后半（`deck-deal`）：26 张卡按阅读序发向网格目标位，出牌间隔硬加速收缩；单卡飞行带 z 弧顶、过冲 settle、落地 press 回弹。
  - 相机追逐式向下 scroll（越来越快），满板后原地静止 0.5s，再 swoosh 回搜索框；**收尾停顿期各层不同帧停稳**——卡体先落定、阴影收敛滞后 2–4f、残影最后消散。
- **参数表**（`:18-31`，原样引用）：

```text
| 参数 | 典型值 | 调节手感 |
|------|--------|----------|
| orbit 环绕 | 帧 0→34，rotX 46/rotY −30/rotZ 9/zoom 1.95 绕到 rotX 42/rotY 26/rotZ −7/zoom 1.85，persp 1100 | 特写四件套缺一不可：侧面倾斜角+可感知高度+orbit+反差深色材质（Q7） |
| 堆叠高度 | STACK_STEP=3px 物理层高 × 26 张 → 顶卡 z≈78px；姿态抖动 px/py 按 `(((k*7)%9)−4)*2` 确定性公式 ±8px、rotZ ±3° | 抖动必须确定性伪随机，真随机会渲染间抖动 |
| 金属背景 | 4 层叠加：暖 key light radial + 两层 repeating-linear-gradient 拉丝纹（1px 白/2px 黑，100deg）+ 115deg 钢色渐变；平面 9000×9000 | 平面尺寸给足（9000²）才保证任意斜角不穿帮；拉远时金属层 34–56f 淡出与运镜同步 |
| 预备拍 | 首发 cue 前 10–14f：牌堆整体下压 40–50px + 顶卡反向回拉 ~30px，缓动 easeOut，首发瞬间释放 | **幅度必须过肉眼阈值**：4px/2px 初版用户实测完全无感，放大 12 倍（48/30px）才通过；渲染后自查"不逐帧能否看出蓄力" |
| 发牌节拍 | 第 k 张 cue = 36 + 4k − 0.0792·k(k−1)，间隔 4f 收缩到 0.2f | 均匀间隔立刻显得机械；匀加速不够狠也被否 |
| 卡量 | 10 真卡 + 16 extras = 26 张；网格向下扩 5 行、纸面延长 2036px | 卡不够多涌入感不成立；extras 落进真实扩展格位，不悬浮（Q9） |
| 单卡飞行 | deal 8f（bezier(0.3,0,0.2,1)，z 弧顶 +90px sin、scale 峰值 1.06）+ settle 4f（bezier(0.3,0,0.25,1.15) 轻过冲）+ press 0.996→1 回弹 2f | 落地要弹必须 y1>1 的 bezier；落定后强制 identity transform 防斜板亚像素漂移 |
| 收尾拖拽层级 | rest 段内分层停稳：卡体 press 回弹结束即锁定，落地阴影收敛滞后 2–4f，飞行残影 opacity 尾梢再拖 3–5f | 借鉴法则 5 的 drag hierarchy；0.5s rest 静止判例不变 |
| 运动模糊（单卡） | 飞行中 5% 路径滞后 blur(6px) 残影，opacity 0.25·(1−t) | ghost 残影比真 motion blur 便宜且够用 |
| 运动模糊（相机） | 追逐 scroll 等 ≥30px/f 的快速运镜段用 `@remotion/motion-blur` 的 `<CameraMotionBlur shutterAngle={180} samples={10}>` 包镜；用 `<Sequence>` 把范围切到快速段 | shutterAngle >270 发糊；samples 每 +1 约 +1 倍渲染时间；**只包快速段** |
| 追逐 scroll | 62→82f ~50px/f，82→98f ~70px/f，98→113f 原地 rest 15f=0.5s，再 11f swoosh 回搜索框 | 满板后 0.5s 静止是用户逐字要求（R2），砍掉必返工 |
```

- **声音**（`:33-34`）：orbit 拉远+首批发牌钉 `whoosh-big`（模板片 f308），发牌加速段钉 `whoosh-fast`（f340/356）。连发落位音防机枪感三招。
- **已知坑 / 命门**（`:36-42`）：
  1. 抽象 flood 式多轮不收敛，换「发牌」物理隐喻一轮通过——**群体运动先找物理隐喻再写代码**。
  2. **卡纹理必须真实页面元素切片（Q1）**，手搓假卡一眼假；extras 复用真卡切片错位摆放。
  3. 全部同时飞读作爆炸，**错峰递加速是灵魂**；前半 orbit 若砍掉，发牌起点要另给「牌堆从哪来」的交代。
  4. anticipation/follow-through 借鉴自迪士尼 12 法则；预备拍幅度已有用户判例；拖拽层级错帧与 R2 判例冲突时判例优先。
  5. **教科书比例（预备 = 主动作 20–30%）在拉远机位下产出的像素位移过小——先算像素再算比例**。
  6. **`<Sequence>` 重定基帧号 + CameraMotionBlur 内部 Freeze 会让 PageCam 采样错帧**（横向错模糊穿帮）——绝对帧编排的镜头给 PageCam 传 `frame` prop 还原绝对帧（lib 组件已支持，见 `PageCam.tsx:38-44`）。
- **参考实现**（`:44-45`）：`demos/ui-entrance/deck-deal-flyin/DeckDealFlyin.tsx`（原 `template/src/aifl/live/SceneFlyIn.tsx` 0–113 段）。实测存在。
- **额外依赖**：`@remotion/motion-blur`（相机模糊段）；模板工程**故意不装**它，需 `npm i @remotion/motion-blur`（`demos/README.md:25-26`、`pr-checks.yml:108-112`）。

#### B6-4 `outro-group-photo-launch`（收尾 / CTA 类 · 发布会合影）

- **来源**：`references/shots/outro/outro-group-photo-launch.md`（39 行）
- **frontmatter**（`:1-7`）：`时长: 约 4.8s（145f）`；`能量: 峰值（全片最高点）`。
- **意图**（`:9-10`）：把看过的每个功能各抽一个代表元素叫回来合影，字标压轴登场——观众离场前最后记住的是「这些东西属于同一个产品」。规格必须是发布会级。
- **动效核心**（`:12-17`）：9 个页面元素从四方带旋转飞入、落地强调色 glow；字标 letterpress 逐字登场、全员退后排让主角；crane 运镜；发布会氛围三件套（开场光带扫过、字标背后舞台光、金尘上飘）；背景页面 blur 化作景深。
- **参数表**（`:19-28`，原样引用）：

```text
| 参数 | 典型值 | 调节手感 |
|------|--------|----------|
| 元素飞入 | 9 元素 cue 从 4 起每 3f 一个，各飞 12f；起点偏移 ±360–500px；渲染顺序=cue 顺序 | 每个已展示过的功能都要有代表元素（Q8 自检项），缺谁观众都会察觉 |
| 飞入缓动 | bezier(0.34,1.4,0.44,1) | 代码注释点名教训：旧 bezier(0.25,0.9,0.3,1) "never crossed 1" 没有真过冲——落地要弹 y1 必须 >1 |
| 飞行姿态 | 飞行中 rot×2→settled rot（±5° 内）、scale ×1.12→1；ghost 残影滞后 8% blur 8px；落地强调色 glow 6f（0.35→0）multiply | 落定角度收进 ±5° 内 |
| 退后排 | 字标登场时 42–50f 全员 opacity −12%、saturate −8% | 主角登场配角必须让位 |
| crane 运镜 | `perspective(1400px) rotateX(4°→0) scale(1.06→1)` 前 40f 落下，之后缓推 +0.035 | crane 幅度 4° 已够"落机位"读感，大了会晕（推测） |
| 氛围三件套 | 光带 2–14f（600px 宽 overlay 峰值 opacity 0.12）；舞台光 42→50→58f 0→0.5→0.25；金尘 20 颗 2–3px、opacity 0.15–0.35、全参数 index 派生确定性 | 粒子/光效参数必须确定性派生（硬规则）；金尘超过 30 颗开始像雪（推测） |
| 字标 | 字母 delay=42+i·1.8、8f；rule 58→70f 长出、两端 190px 延长线 8f 射出 6f 淡去；字距 62–66f 呼吸；背景页 24f 内 blur 0→14；落定后 sign-off hold 30f | 字标落定 hold 满 1 秒（R1）；outro 不加解说 caption（C1 例外项） |
```

- **声音**（`:30-31`）：固定三拍句式——`riser-cine` 铺进组装（模板片 f945）→ `impact-deep-whoosh` 钉字标 stamp（f980，vol 0.55 全片峰值）→ `sparkle` 点 rule（f1005）。**模板片定稿后唯一从未改动的段落句式**（详见 `sound-design.md §4.3`）。
- **已知坑 / 命门**（`:33-36`）：
  1. **初版收尾几乎总是偏保守**（Q8：安静签名式→合影→发布会三级加码）——起稿就按「像一个产品发布」的规格给足 crane/舞台光/粒子。
  2. **结构先于特效**：先有「四方飞入合影」结构再加码氛围；直接堆特效没有骨架。
  3. outro tagline 与字标下方文案查重（P4 dedupe 判例），同一句话全片只出现一次。
- **参考实现**（`:38-39`）：`demos/outro/outro-group-photo-launch/OutroGroupPhotoLaunch.tsx`（原 `template/src/aifl/live/SceneOutroLive.tsx`）。实测存在。

#### B6-5 `document-typewriter-reveal`（字幕/文字动效类 · 文档自写）

- **来源**：`references/shots/typography/document-typewriter-reveal.md`（41 行）
- **frontmatter**（`:1-8`）：`时长: 约 3.7s（110f，含 history-list-stack 尾段）`；`能量: 低中（信息密度最高，节奏放稳让观众读字）`。
- **意图**（`:10-11`）：观众会读清屏幕上每个字——这一镜的说服力全在「文档是真的」。打字机式写入把静态页面变成「正在被写出来的文档」。
- **动效核心**（`:13-18`）：内容块两两一对按节拍写入（底色遮罩右锚左→右收窄、强调色 caret 骑在揭示前沿）；@-mention 在 wipe 完成后长出强调色底色；左右双栏靠底色补丁上→下收走入场；尾段 6 条历史条目逐个落入侧栏轨道，每落一条配一声 pop；相机从标题特写拉到全页，之后只做微呼吸。
- **参数表**（`:20-29`，原样引用）：

```text
| 参数 | 典型值 | 调节手感 |
|------|--------|----------|
| 写入节拍 | 20 块两两一对，第 g 对 cue = 6 + g·3.5，每块 wipe 8f，最后一对 ~49f 完成 | 逐块写会超预算——"块数×节拍要先对预算"是这卡的核心算术 |
| 写入手法 | 底色遮罩 width 100%→0，bezier(0.4,0,0.6,1)；强调色 caret 2px 只跟最新块，写完 2f 淡出 | caret 同时出现多个立刻穿帮；永远只有一个"笔尖" |
| li 圆点 | 遮罩向左多盖 28px（::marker 在文本左 ~22px） | 不多盖圆点会提前穿帮 |
| @-mention | wipe 完成后 4f 起、8f 长出强调色底色 opacity 0.7 | 高亮晚于写入才读作"重点被标出"；同帧出现读作贴图 |
| 双栏入场 | 左栏 cue 46 / 右栏 cue 54，底色补丁上→下 10f 收走 + 内缘 1.5px 强调色线随揭示生长、24f 淡去 | 双栏与正文错开节拍 |
| 历史条目落入 | 6 条，cue = 58 + i·5，每条 8f 落下；起点 −44px，bezier(0.2,1.15,0.3,1) 轻弹跳，空中影 `0 10·air px 20·air px` | 条目几何紧贴烤入纹理已有条目的下方、行高对齐 |
| 相机 | 标题特写 zoom 1.25 → 64f 全页 zoom 0.997，78/102f 1.003/0.995 微呼吸 | 全页时双栏必须都入画（Q10） |
```

- **声音**（`:31-32`）：写入段钉 `keyboard.mp3` **修剪到 44f** 盖住书写段（拟音与动作严格等长，S4）；历史条目 6 连 pop 每 5f 一发、音量 0.40→0.25 阶梯递减。
- **已知坑 / 命门**（`:34-38`）：
  1. **mock 内容必须出版级：产品原生排版、文字铺满、侧栏完整入镜（Q10）**——「贴图+标语」级的敷衍文档会导致整镜头重做。
  2. 数据合规：mock 内容里绝不出现客户/成员真名（Q1）。
  3. 素材页面是活数据源时，全量重采会刷掉已定稿纹理——用增量脚本只刷单页单键。
  4. 强调色（caret/@-mention/内缘线）适配新品牌时统一换成目标品牌强调色。
- **参考实现**（`:40-41`）：`demos/ui-entrance/document-typewriter-reveal/DocumentTypewriterReveal.tsx`（原 `template/src/aifl/live/SceneWbr.tsx`）。实测存在。
- **补充可用卡**（雷达/科技感入场，简版要点）：
  - `wipe-transitions` A 式 `clock-wipe`（`transition/wipe-transitions.md:20`、`:26-30`）：B 页上层套扇形 `clip-path polygon`，指针从屏心 12 点顺时针**匀速**扫 360°，扫过处露 B；扫描沿带**四层亮线**（26px 白 0.35 柔光 + 13px 白 0.60 + 9px 黑 0.55 暗描边 + 4px 白核）；`SEGS=72` 顶点恒定防锯齿（命门）；**A 96f 起条件卸载全部擦除结构**（opacity 0 不算摘罩）；全片 ≤2 次且 A/B 别同片连用。
  - `gauge-readout-moves` A 式 `needle-sweep-selftest`（`data/gauge-readout-moves.md:20-29`）：指针去程 ~12f ease-out **甩满 270° 全弧**，回程 ~20f 带 5–8° 过冲回摆落真值；多表错峰 3–5f；落定同帧盘下数值弹出；A 的表盘是自绘 SVG，实战优先找页面里现成的 gauge 组件特写（`:38-39`）。
  - `radial-wave`（`ui-entrance/radial-wave.md`）：17×9=153 圆点按到波源欧氏距离错峰点亮，每点 `scale` 过冲到 1.5 再落回，第二道亮蓝脉冲从外圈反向收拢回中心。

---

### B7. `gallery/api/library.json`：结构与校验方法

- **路径**：`gallery/api/library.json`，267,674 字节（实测）。
- **顶层键**（实测 `PSObject.Properties.Name`）：`generatedAt`、`revision`、`stats`、`cards`、`staticExport`、`categories`。
- **顶层标量值**（实测）：

```json
"generatedAt": "2026-07-19T05:01:54.882Z",
"revision": "bdd94be16d60fa8f",
"staticExport": true
```

- **`stats`**（实测）：

```json
{
  "cardCount": 157,
  "styleCount": 214,
  "previewCount": 214,
  "mediaCount": 214,
  "newest": "2026-09-01T15:59:12.000Z"
}
```

- **`categories`**：10 个类别键 → `{zh, en}`，与 `gallery/sync-from-cards.py:38-49` 的 `CATEGORIES` 完全一致（键：`opening`/`typography`/`ui-entrance`/`camera`/`data`/`interaction`/`transition`/`rhythm`/`effects`/`outro`）。
- **`cards[]` 字段**（实测并集）：`name`、`summary`、`use`、`duration`、`energy`、`intention`、`source`、`sourceUrl`、`styles`、`category`、`tags`、`addedAt`、`updatedAt`。
- **`cards[].styles[]` 字段**（实测并集）：`key`、`label`、`description`、`media`、`use`（可选），以及由脚本按需写入的 `implementationStatus`。
- **单卡样例**（实测 `cards[0]`，已缩排）：

```json
{
  "name": "ai-stream-response",
  "summary": "AI 响应面板先落一句可读摘要，再让带状态图标的证据行逐条汇入，最后统一收束成完成态",
  "use": "AI 助手/agent/search/copilot 的结果生成镜头；强调\u201c结论先到、证据随后、任务完成\u201d",
  "duration": "约 4–5s（120–150f，含 ≥15f 完成态静止）",
  "energy": "中高（信息持续增加，但阅读优先于速度炫技）",
  "intention": "把\u201cAI 正在工作\u201d拍成可读的因果链，而不是日志刷屏：观众先看懂答案摘要， 再看到证据/子任务逐条补齐，最后由完成态确认这轮工作结束。",
  "source": "references/shots/interaction/ai-stream-response.md",
  "updatedAt": "2026-07-15T17:25:16.871Z",
  "styles": [
    {
      "key": "ai-stream-response",
      "label": "ai-stream-response",
      "description": "AI 响应面板先落一句可读摘要，再让带状态图标的证据行逐条汇入，最后统一收束成完成态",
      "media": { "url": "./media/ai-stream-response.mp4?v=1784437314480", "type": "mp4" }
    }
  ],
  "sourceUrl": "./source/ai-stream-response.md",
  "category": "interaction",
  "tags": ["interaction"],
  "addedAt": "2026-07-19T05:45:41.000Z"
}
```

#### 校验卡名 / style-key 的准确方法

1. **卡名校验**：`cards[].name` 必须存在（`guided-free-creation.md:132`）。卡名 = `references/shots/<类别>/<name>.md` 的文件名 stem，同时 `cards[].source` 给出该 md 的仓库相对路径（写入规则见 `gallery/sync-from-cards.py:101`）。
2. **style-key 校验**：`cards[].styles[].key` 必须存在（`guided-free-creation.md:132-133`）。**不要用模糊猜测代替索引校验**（`:133`）。
3. **多式卡识别**：`card.styles.length > 1` 即为多式卡。实测 39 张卡有多个 style；样式总数 214（`stats.styleCount`）。全量多式卡清单（实测）：

```text
beat-cut-moves (2): beat-cut-accelerando | paparazzi-flash
canvas-materialize-moves (2): panel-to-canvas | diagram-cascade
chart-live-moves (3): oscilloscope-stream | unit-dot-swarm-regroup | axis-rescale-shock
collab-cursor-moves (2): dialogue-duet | cast-ensemble
depth-layer-moves (2): multiplane | dolly-zoom
element-body-moves (2): axial-stretch | contact-shadow-lift
fui-hud-moves (2): line-unfold-panel | reticle-lock-on
gauge-readout-moves (2): needle-sweep-selftest | tape-scroll-fixed-pointer
glow-flyline-moves (3): glow-orb-ambient | flyline-arc | orb-flyline-relay
icon-performance-moves (2): pop-burst-confirm | attention-bounce
impact-feedback (2): hit-counter | anime-impact
input-trigger-moves (2): cursor-performance | keycap-smash-cut
light-play-moves (3): spotlight-sweep | sheen-sweep | halation-bloom
montage-rhythm-moves (3): drop-blackout-slam | wright-triple-cut | domino-cascade
overhead-camera-moves (2): tilt-reveal | overhead-tabletop-drop
page-turn-transitions (2): cube-rotate | barn-door-split
panel-grid-moves (3): grid-flash-mosaic | flip-grid-reflow | comic-panel-split
paper-craft-moves (2): masking-tape-slap | popup-book-rise
particle-celebrate-hits (2): confetti-crossfire | counter-tick-sparks
rhythm-interrupt-moves (2): jump-cut-punch-in | strobe-black-frames
riso-print-hits (2): misregistration-hit | beat-pump
scroll-brake-moves (2): changelog-scroll-brake | brake-reticle-lock
shot-transitions (6): flash-cut | shot-transitions-4 | shot-transitions-5 | shot-transitions-6 | whip-pan | mask-wipe
slam-entrance-moves (3): kanada-perspective-snap | score-slam | impact-burst-kit
space-camera-moves (2): exploded-view | drone-dive-landing
speed-ramp-freeze (2): speed-ramp | freeze-annotate
spotlight-sweep-moves (3): glow-wake-sleep-panel | slide-spotlight-pan | corner-spotlight-reveal
tension-camera-moves (4): bullet-time-freeze-orbit | dutch-roll-to-level | slow-push-in | pull-back-isolation
theme-switch-moves (2): theme-sweep-toggle | palette-theme-ripple
trailer-grammar-moves (3): trailer-bumper | card-footage-cadence | smash-cut
transition-hidden-cut (3): invisible-cut | versus-slam | light-leak-burn
transition-travel (2): shared-element-morph | letterform-zoom
type-assembly-moves (4): split-text-stagger | drift-assembly | tracking-expand | text-on-path
type-entrance-moves (2): scramble-decode | letter-drop-physics
type-rhythm-sync (2): font-weight-pump | karaoke-fill-sync
typewriter-moves (2): terminal-typewriter | error-retype
ui-to-brand-morph (2): icon-flip-bloom | input-morph-assemble
wall-reveal-moves (3): bento-light-up | grid-wave-flip | wireframe-draw-on
wipe-transitions (2): clock-wipe | blinds-slice
```

4. **`implementationStatus` 的当前状态**：`sync-from-cards.py:17-20` 定义

```python
# Variants with a recipe/sample but no reusable demo source get 'reference-only'
# here so the workflow does not recommend them by default. Currently empty:
# every style has demo source.
STYLE_STATUS = {}
```

  → **当前 157 张卡 214 个 style 全部有 demo 源码，`implementationStatus` 字段在 `library.json` 中完全不存在**（实测无任何卡含 `reference-only` / `missing-preview`）。`app.js:97-101` 支持渲染 `referenceOnly` / `missingPreview` 标签（对应 `gallery/translations.js:46` 的「仅供参考，需要自定义实现」），但当前数据为空。**因此 `pipeline.md:214-215` 与 `guided-free-creation.md:156-158` 提到的两类降级标注目前在库中不触发**——校验时不要假设存在。
5. **`media.url` 规范形**：CI 用正则 `^\./media/[a-z0-9-]+\.(mp4|gif)(\?v=\d+)?$` 强制校验（`pr-checks.yml:74`），并逐一核对 release 资产存在（`:60-97`）。
6. **生成/同步链**：编辑卡片后 `python3 gallery/sync-from-cards.py`（刷新 `gallery/source/*.md` 副本 + `library.json` 文本字段 + `stats` + 排序）再 `python3 gallery/build-seo.py`；两步产物必须 commit，否则 CI 的「Generated artifacts are in sync with cards」gate 失败（`pr-checks.yml:45-58`）。
7. **卡片→索引字段映射**（`sync-from-cards.py:82-101`）：`一句话`→`summary`、`适用`→`use`、`时长`→`duration`、`能量`→`energy`、`## 意图` 小节正文→`intention`、目录名→`category`、`标签:`→`tags`（首项为主类别）、`source` 由 `category`+`name` 拼出。
8. **离线校验便利**：`cards[]` 按 `name` 字母序排序，是「All 视图」排序的唯一权威（`sync-from-cards.py:116-117`）。
9. **本地样例缺失**：`gallery/media/` 目录存在但**为空**（mp4 不入 git）——要本地看样片先跑 `gallery/fetch-media.sh`（`SKILL.md:261-264`）。

---

## C. 可复用资产

### C8. `assets/lib/` 每个组件的用途、props 接口、依赖

**总览**（`SKILL.md:224-232`）：`assets/lib/` 组件 **copy 进新项目**后自由修改（**不 import 本库**）。PageCam 是一切「真实页面」镜头的地基；FlatPanel 与 helpers/camera 需要 `three` + `@react-three/fiber` + `@remotion/three`，其余仅需 remotion。

| 文件 | 行数 | 用途 | 依赖 |
|---|---|---|---|
| `PageCam.tsx` | 151 | 2.5D 页面相机（整页截图 + 关键帧运镜 + 3D 倾斜 + 伪 DoF） | `remotion` |
| `ClipCard.tsx` | 200 | 把外部视频 mp4 包成可被镜头卡运镜骨架驱动的「卡片主角」（含交叉淡化循环） | `remotion` |
| `DigitRoll.tsx` | 45 | 里程表式等宽数字纵列滚动 | `remotion` |
| `FlashCut.tsx` | 20 | 暖白闪光硬切遮罩 | `remotion` |
| `Caption.tsx` | 54 | 屏幕空间底部通栏解说字幕 | `remotion` |
| `FlatPanel.tsx` | 65 | three.js 场景里平躺的纸质卡面板 + 接触阴影 | `three`（+ 使用处需 `@react-three/fiber` / `@remotion/three`） |
| `VerticalTicker.tsx` | 129 | 3D 透视多列无限纵向滚动墙 | `remotion` |
| `helpers/rand.ts` | 11 | mulberry32 确定性 PRNG | 无 |
| `helpers/shake.ts` | 10 | 确定性手持相机噪声 | 无 |
| `helpers/motion.ts` | 40 | `velocityAt` / `lagged` / `dampedSettle` | 无 |
| `helpers/camera.tsx` | 75 | three.js 相机关键帧 `Rig` | `@react-three/fiber` + `remotion` + `three` |
| `helpers/__tests__/helpers.test.ts` | 181 | 纯函数单测（vitest） | `vitest` |

#### `PageCam.tsx`

来源注释：`// origin: template/src/aifl/live/PageCam.tsx（模板片同源组件）`（`:1`）。

导出类型 `CamKey`（`:4-13`）：

```ts
export type CamKey = {
  frame: number;
  cx: number;
  cy: number;
  zoom: number;
  rotX?: number; // deg, tilt about the horizontal axis (positive = top leans away, like looking at a table)
  rotY?: number; // deg, tilt about the vertical axis (positive = right edge recedes, i.e. seen from the LEFT)
  rotZ?: number; // deg, in-plane roll
  persp?: number; // px, perspective strength (default 1400; smaller = stronger)
};
```

组件 props（`:29-42`，含行内注释）：

```tsx
export const PageCam: React.FC<{
  src: string;          // staticFile path under textures/live/
  pageH: number;        // CSS page height
  keys: CamKey[];
  children?: React.ReactNode;  // page-space overlays (positioned in CSS px)
  blur?: number;
  saturate?: number;
  ease?: (t: number) => number;
  dof?: { focusY: number; strength: number };
  // Optional absolute-frame override: when PageCam is rendered inside a
  // <Sequence> (which rebases useCurrentFrame), the parent can pass the
  // restored absolute comp frame so CAM_KEYS keep their absolute frame refs.
  frame?: number;
}> = ({ src, pageH, keys, children, blur = 0, saturate = 1, ease = Easing.bezier(0.33, 0, 0.15, 1), dof, frame: frameProp }) => {
```

- 坐标语义（`:18-24`）：`(cx, cy)` 是被居中到 1920×1080 视口的**页面空间 CSS 点**；`zoom` 是缩放（1 = 1 CSS px → 1 输出 px）；页面纹理是 2x，通过 `width` 以 CSS 尺寸渲染。
- 3D 降级（`:22-24`、`:61-80`）：**当没有任何 key 声明 3D 字段时**，退化为原始平面 pan/zoom 且渲染像素级一致。
- `dof` 实现（`:133-148`）：屏幕空间顶部渐变模糊带（`backdropFilter: blur(strength px)` + 线性 mask），近似倾斜页面的焦平面。
- **文字锐利度的命门**（`:99-115` 长篇注释）：3D 模式**不用 `transform: scale(zoom)`**（Chromium 会按 1920 布局宽栅格化 3D 合成层再 GPU 放大 → 内容先降采样后放大必糊），改用 CSS `zoom` 属性（布局级缩放），坐标换算 `Tx = 960/zoom − cx`、`Ty = 540/zoom − cy`，旋转以 `transform-origin: cx px cy px` 为轴以保持焦点屏幕位置不变。
- `frame` prop 的用途（`:38-44` + `deck-deal-flyin.md:42`）：`<Sequence>` 会 rebase `useCurrentFrame`，而 `CameraMotionBlur` 内部 Freeze 会让 PageCam 采样错帧——绝对帧编排的镜头必须传 `frame` 还原绝对帧。

#### `ClipCard.tsx`

用途（`:11-28`）：把外部 mp4 包进圆角「卡片」，让为矩形卡元素调校过的运镜骨架（`spotlight-hero-card` / `magician-card-flourish` / `neon-frame-orbit-drop` / `quad-split-parallel-scenes`）原样驱动**真实 footage**。实测于一支已交付 39s 宣传片（512×512 clip 上 zoom 1.7 的 spotlight push-in；3-up quad-split 32px 字幕）。

**关键限制**（`:21-28`）：`OffthreadVideo`（截至 4.0.484）**没有 `loop` prop**，播完会冻结——传 `loopDurationInFrames` 开启无缝 dissolve 循环，每遍在上一遍尾部淡入。有效步长 `loopDurationInFrames - startFrom`；层数由**包围 shot 的时长**（非 Composition 时长）派生。音频与透明度共用同一包络互补交叉淡化。

Props（`:83-108`）：

```tsx
export const ClipCard: React.FC<{
  src: string;            // path under public/
  caption?: string;       // monospace caption bar under the clip
  size?: number;          // card edge (square clips)  default 560
  radius?: number;        // default 20
  muted?: boolean;        // default true
  captionSize?: number;   // default 17 — raise on small/far cards to keep ≥32px on-screen text
  startFrom?: number;     // trim: play the clip from this frame  default 0
  style?: React.CSSProperties;
  loopDurationInFrames?: number;   // playable clip length in comp frames → enables crossfade loop
  loopCrossfadeInFrames?: number;  // default 8
  durationInFrames?: number;       // enclosing shot duration — loop layer count is derived from this
}> = ({ ... })
```

- 循环守卫（`:118-124`）：`step = loopDurationInFrames - startFrom - loopCrossfadeInFrames`；`canLoop` 要求 `loopDurationInFrames > loopCrossfadeInFrames && step >= loopCrossfadeInFrames`，否则回退单层播放（避免层瞬间淡到 0 或 3 层以上重叠破包络）。
- 层数（`:126-127`）：`n = Math.max(1, Math.ceil(shotFrames / step))`。
- 包络函数（`:50-63`）：

```tsx
let envelope: number;
if (frame <= fadeIn) {
  envelope = fadeIn === 0 ? 1 : interpolate(frame, [0, fadeIn], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
} else if (frame <= step) {
  envelope = 1;
} else {
  envelope = interpolate(frame, [step, step + fadeOut], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
}
const opacity = Math.max(0, Math.min(1, envelope));
const volume = muted ? 1 : opacity;
```

- 卡片外观常量（`:170-177`）：`background: '#111116'`、`border: '1px solid rgba(255,255,255,0.10)'`、`boxShadow: '0 24px 80px rgba(0,0,0,0.55)'`；`capH = caption ? Math.round(captionSize * 2.6) : 0`（`:110`）。
- 已知坑（`demos/README.md:92-95`）：`durationInFrames` 不传时层数按 Composition 总时长算（短 shot 长工程问题）；`startFrom ≥ 可播放长度` 或 `step < crossfade` 自动回退单层；循环素材建议 30fps、**方形**（运镜骨架按方形卡片标定）。
- 参考 demo：`demos/ui-entrance/clipcard-looping/ClipCardLooping.tsx`（回归三场景：muted=false 循环、startFrom>0+循环、短 Sequence 长 Composition；`demos/README.md:97-98`）。

#### `DigitRoll.tsx`

来源注释：`// origin: template/src/aifl/DigitRoll.tsx（模板片同源组件）`（`:1`）。

```tsx
export const DigitRoll: React.FC<{
  value: string;
  delay?: number;      // default 0
  fontSize?: number;   // default 30
  color?: string;      // default 'oklch(52% 0.115 65)'
}> = ({ value, delay = 0, fontSize = 30, color = 'oklch(52% 0.115 65)' }) => {
```

- 机制（`:14-38`）：`lineH = fontSize * 1.15`；每位 strip 是 `DIGITS + DIGITS`（"01234567890123456789"）两轮，`translateY(-offset px)`；`offset = (10 + target) * t * lineH`（先滚满一整条 strip 再落到目标位）。
- 逐位错峰（`:24-28`）：位 i 的窗口 `[delay + i*4, delay + i*4 + 22]`，easing `Easing.bezier(0.25, 0.8, 0.25, 1)`。
- 非数字字符（如 `.` / `%`）直接静态渲染（`:19-23`）。
- 等宽：每位都带 `fontVariantNumeric: 'tabular-nums'`（`:35`）。

#### `FlashCut.tsx`

来源注释 `:1`。**亮场硬切用的暖白 bloom**（`:4`）。

```tsx
export const FlashCut: React.FC<{ duration?: number }> = ({ duration = 10 }) => {
  const frame = useCurrentFrame();
  const o = interpolate(frame, [0, duration * 0.4, duration], [0, 0.85, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  // AbsoluteFill, pointerEvents: 'none',
  // background: radial-gradient(ellipse at 50% 45%,
  //   rgba(255,248,235,0.98), rgba(255,244,224,0.55) 55%, transparent 80%)
};
```

用法约定：只盖硬切两侧（模板片 `FLASH_CUTS` 的 `from = cut − 5`，10f 长；`template/src/aifl/Main.tsx:48-49`、`:184-189`、`TEMPLATE.md:35`）。**不当装饰光效**（`TEMPLATE.md:46`）。

#### `Caption.tsx`

来源注释 `:1`。屏幕空间解说字幕：等宽 UI 信息条，前置小琥珀方块（`:7-13`）。

```tsx
export const Caption: React.FC<{ text: string; duration: number; bottom?: number }> = ({
  text, duration, bottom = 72,
}) => { ... }
```

- 动效（`:19-27`）：入场 8f（`[0, 8] → [0, 1]`），出场末 8f（`[duration - 8, duration] → [1, 0]`），入场同时 `translateY((1 - inT) * 8px)`。
- 样式常量（`:4-5`、`:40-47`）：`fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace'`、`fontSize: 22`、`letterSpacing: '0.14em'`、`textTransform: 'uppercase'`、`color: 'oklch(45% 0.006 82)'`、方点 `AMBER = 'oklch(52% 0.115 65)'`。
- **重要合规提示（源码注释 `:11-13`）**：

```text
注意：22px 属"信息条"风格（大字距全大写作补偿），低于审美准则 Q11 的
字幕线（≥56px）。作为叙事主字幕使用时应提到 56–60px 档或改用大字幕组件；
沿用 22px 信息条风格属于 Q11 允许的有意识违反，需在项目说明中注明。
```

#### `FlatPanel.tsx`

来源注释 `:1`：`// origin: 模板片源仓库（本库模板未包含 3D 版，需 three + @react-three/fiber + @remotion/three）`。

```tsx
/** A paper card lying flat on the desk. Plane with the UI texture facing up
 * (texture top edge points toward world -z), soft contact shadow beneath. */
export const FlatPanel: React.FC<{
  texture: THREE.Texture | null;
  width: number;
  height: number;
  position?: [number, number, number];  // default [0, 0.02, 0]
  yaw?: number;                          // default 0
  opacity?: number;                      // default 1
  glow?: number;                         // default 0.3
  shadow?: boolean;                      // default true
}> = ({ texture, width, height, position = [0, 0.02, 0], yaw = 0, opacity = 1, glow = 0.3, shadow = true }) => {
```

- 材质（`:36-50`）：`MeshStandardMaterial({ color: '#fdfcfa', roughness: 0.62, metalness: 0, transparent: true })`；`map` 与 `emissiveMap` 同纹理，`emissiveIntensity = glow`，每帧写 `opacity` 并 `needsUpdate = true`。
- 接触阴影（`:6-19`、`:54-58`）：模块级 `useShadowTexture()` 生成 128×128 径向渐变 `CanvasTexture`（中心 `rgba(58,51,42,0.32)` → 边缘透明）；阴影 mesh 比面板大 1.3 倍，`opacity: 0.85 * opacity`、`depthWrite: false`。
- 结构（`:52-64`）：`<group position rotation={[0, yaw, 0]}>` 内先阴影后面板，面板 `planeGeometry args={[width, height]}` 且 `rotation={[-Math.PI/2, 0, 0]}`（平躺）。

#### `VerticalTicker.tsx`

来源注释 `:1-3`：移植自 `vibe-motion/skills remotion-3d-ticker`，改动为 items 泛化为 ReactNode、遮罩高度/透视角/scale/列宽/间距提为 props。

```tsx
export interface TickerColumn {
  items: React.ReactNode[];      // any ReactNode (screenshot-slice divs, <Img>, text cards…)
  durationInSeconds: number;     // seconds for one full loop
  direction: -1 | 1;             // -1 scrolls up, 1 scrolls down
}

export interface VerticalTickerProps {
  columns: TickerColumn[];
  backgroundColor?: string;   // default '#000'
  maskHeight?: number;        // default 200
  tiltDeg?: number;           // default 20
  perspective?: number;       // default 1000
  scale?: number;             // default 1.2
  columnWidth?: number;       // default 400
  gap?: number;               // default 30
}
```

- 无缝循环机制（`:34-41` 注释 + `:106-109`）：每列 `[...items, ...items]` 翻倍 + `progress = (frame % loopFrames) / loopFrames` 取模 `translateY`：up 方向 `0 → -50%`，down 方向 `-50% → 0`。
- **接缝命门**（`:38-40`）：`-50%` 必须恰等于单副本周期（内容高 + n 个 gap）；源实现用 flex `gap`（翻倍后只有 `2n-1` 个 gap）会差 `gap/2` px 跳一下——本实现改为每项 `marginBottom = gap`，容器高恰为周期两倍。
- 遮罩（`:69-91`）：上下两条 `zIndex: 10` 的线性渐变（`backgroundColor` → transparent）。
- 整墙变换（`:61`）：`perspective(${perspective}px) rotateX(${tiltDeg}deg) scale(${scale})`，`transformOrigin: 'center center'`。

#### `helpers/rand.ts`

```ts
// origin: 模板片源仓库 helpers
/** Deterministic PRNG — same seed always yields the same sequence. */
export const mulberry32 = (seed: number) => {
  let a = seed | 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
};
```

#### `helpers/shake.ts`

```ts
// origin: 模板片源仓库 helpers
/**
 * Deterministic hand-held camera noise. Layered sines at incommensurate
 * frequencies read as organic drift; amplitude in world units.
 */
export const handheld = (frame: number, amp = 0.012): [number, number, number] => [
  amp * (Math.sin(frame * 0.31) + 0.6 * Math.sin(frame * 0.83 + 1.7)),
  amp * (Math.sin(frame * 0.47 + 0.9) + 0.5 * Math.sin(frame * 1.13 + 3.1)),
  0,
];
```

#### `helpers/motion.ts`

来源 `:1`：移植自 `disney-animation-rule-skill implementation-patterns`。

```ts
export const velocityAt = (
  posAt: (f: number) => { x: number; y: number },
  frame: number,
  dt = 0.5,
): { vx: number; vy: number; speed: number; direction: number } => { ... }

export const lagged = <T>(stateAt: (f: number) => T, frame: number, delayFrames: number): T =>
  stateAt(frame - delayFrames);

export const dampedSettle = (t: number, freq: number, damping: number): number =>
  t <= 0 ? 0 : Math.exp(-damping * t) * Math.sin(2 * Math.PI * freq * t);
```

- `velocityAt`（`:9-19`）：中心差分（`frame ± dt`）求速度/速率/朝向；用于驱动 stretch / smear / blur / shake 强度，按主体尺寸归一化幅度。**对任何纯 `posAt` 生效，无逐帧状态**。
- `lagged`（`:21-32`）：**无状态**的 follow-through——滞后层只是把主状态在 `frame − delayFrames` 采样；拖拽层级给每个附件更大 delay 与更小幅度（shadow 2f、ghost 4f…）。**绝不跨帧累积状态**。
- `dampedSettle`（`:34-40`）：闭式阻尼振荡，`t` 为距冲击的帧数，返回衰减到 0 的有符号偏移因子；`freq` 单位 cycles/frame（~0.1），`damping` 每帧（~0.15）。

#### `helpers/camera.tsx`

来源 `:1`。three.js 默认相机关键帧动画。

```tsx
export type CamKeyframe = {
  frame: number;
  pos: [number, number, number];
  look: [number, number, number];
  fov?: number;
};

const easeInOut = Easing.bezier(0.4, 0.0, 0.2, 1.0);

/**
 * Animates the default camera through keyframes (frames relative to the
 * enclosing Sequence). Position/look are eased segment by segment.
 * `shake` adds deterministic hand-held drift (world units).
 */
export const Rig: React.FC<{
  keyframes: CamKeyframe[];
  easing?: (t: number) => number;  // default easeInOut
  shake?: number;                  // default 0
}> = ({ keyframes, easing = easeInOut, shake = 0 }) => { ... }
```

- 分段插值（`:29-56`）：找到包含当前帧的段，`interpolate(frame, [a.frame, b.frame], [0, 1], { clamp, clamp, easing })`，对 `pos`/`look` 做 3 维 lerp，`fov` 默认 36 线性插值。
- `useFrame` 内（`:58-72`）：`shake > 0` 时用 `handheld(frame, shake)` 加 `dx/dy`，`look` 加 `dx*0.6 / dy*0.6`；然后 `camera.position.copy(pos)`、`camera.lookAt(look)`，`PerspectiveCamera` 时写 `camera.fov` 并 `updateProjectionMatrix()`。
- 注意：`keyframes[].frame` 是**相对包围 Sequence** 的帧（`:17-18` 注释）。

#### 组件清单的来源与依赖速查（`SKILL.md:224-246`）

- `assets/scripts/capture-template.mjs`：复制后改顶部 `CONFIG`（BASE/路由/选择器）。
- `demos/` 各卡实现源码：多数为自包含灰阶 demo（部分 import `demos/_fixtures/Fixtures.tsx` 的假 UI 场景件，个别 import `demos/_textures/` 的真实页面纹理），copy 进 Remotion 项目即可跑。
- 个别 demo 用到 `@remotion/motion-blur`（`CameraMotionBlur`），需 `npm i @remotion/motion-blur`，**8 个文件 / 6 张卡**名单（`demos/README.md:25-33`）：
  1. `camera/crash-zoom-punch/CrashZoomReal.tsx`
  2. `camera/crash-zoom-punch/CrashImpactReal.tsx`
  3. `camera/space-camera-moves/DroneDiveLanding.tsx`
  4. `opening/magician-card-flourish/MagicianCardFlourish.tsx`
  5. `rhythm/speed-ramp-freeze/SpeedRampReal.tsx`
  6. `transition/shot-transitions/WhipPanReal.tsx`
  7. `transition/shot-transitions/WhipBrakeReal.tsx`
  8. `transition/transition-hidden-cut/InvisibleCut.tsx`

#### demo 的两套共享依赖（`demos/README.md:8-23`、`:35-45`）

- `_fixtures/Fixtures.tsx`：灰阶假 UI 场景件（`FakeDashboard` / `Card` / `TitleBlock` / `G` 调色板）。多数 demo import 它；copy 时改 import 路径。
- `_fixtures/PageCam2D.tsx`：2.5D 页面相机（与 template 的 `PageCam` 同款坐标数学，**self-contained，仅依赖 remotion**）。给「真实纹理」类 demo 复用——名单：`spotlight-hero-card` / `type-and-filter` / `deck-deal-flyin` / `row-embed` / `list-stack-press` / `document-typewriter-reveal` / `outro-group-photo-launch`。
- `_textures/`：少数「真实素材版」demo 的整页截图与 `live-layout.json`；`staticFile('textures/live/xxx.png')` 要求把同名文件复制到项目 `public/textures/live/`（`page-waterfall-wall` 例外，写的是 `textures/xxx.png` → `public/textures/`）。
- **Motion 系 demo（2026-08 并入的 48 张卡）**（`demos/README.md:35-45`）：共享依赖是 `_fixtures/Motion.tsx`（`E` 缓动表 / `seg` / `lerp` / 确定性 rand / `useT` / `DesignStage`）；画面用 `<DesignStage>` 的 **480×270 设计坐标**作画、等比放大到合成分辨率，**改合成分辨率不需要动参数**；文字密集的 demo 用 `raster="zoom"`（布局期放大，小字号字形按目标尺寸光栅化，更清晰），默认 `transform scale` 是合成期放大，两者 API 相同。
- 每个组件同时 `export const <卡名大写蛇形>_DURATION`（30fps 帧数）：

```tsx
import { BlurSlide, BLUR_SLIDE_DURATION } from './blur-slide/BlurSlide';
<Composition id="BlurSlide" component={BlurSlide}
  durationInFrames={BLUR_SLIDE_DURATION} fps={30} width={1920} height={1080} />
```

- 三个文字密集组件例外（`glass-pill-dictation-typing` / `chip-grid-single-select-blackout` / `pill-chip-slot-cycle-handled`）：挂载时用 `useLayoutEffect` 实测一次文字宽度（之后恒定，单次渲染内仍逐帧确定），因此布局随渲染环境字体而变——**跨平台若字体回退不同，宽度会整体漂移**；组件内备有兜底估算值，介意可把实测值写死（`:57-62`）。
- 每个 Motion 系组件都经过与原样片 mp4 的全帧 SSIM 比对验收（`mean≥0.97 / min≥0.93` 或有注释说明的编码噪声豁免；`demos/README.md:61-62`）。

---

### C9. `assets/audio/` 目录结构、BGM 清单、SFX 类别、授权结论

#### 目录结构

```
assets/audio/
  ATTRIBUTION.md            授权与 URL 记录（193 行）
  AUDITION-2026-07-27.md    逐文件时长/峰值/建议钉点（36,903 字节）
  bgm/                      5 首 BGM 备选
  sfx/<类别>/               16 个类别目录
```

（`sound-design.md:62-66` 给出同一结构；`ATTRIBUTION.md:5` 复述。）

#### BGM 全部文件名 + 时长（实测 ffprobe）

| 文件名 | 时长（ffprobe 实测） | 原曲名 | 艺术家 | 风格 | BPM | URL |
|---|---|---|---|---|---|---|
| `bgm-tech-house.mp3` | **288.692290s** | （首批沿用，无法逐曲反查） | — | Tech House | ~124 | Mixkit，商用前复核 |
| `cat-walk.mp3` | **123.990385s** | Cat Walk | Arulo | House | ~129 | `https://assets.mixkit.co/music/371/371.mp3` |
| `g-eazy-nba-type.mp3` | **104.312494s** | G Eazy NBA type | Arulo | Hip Hop | ~86 | `https://assets.mixkit.co/music/403/403.mp3` |
| `house-vibez.mp3` | **111.464450s** | House Vibez | Lily J | House | ~123 | `https://assets.mixkit.co/music/745/745.mp3` |
| `tonight-hiphop.mp3` | **113.475906s** | Tonight | Michael Ramir C. | Hip Hop | ~103 | `https://assets.mixkit.co/music/841/841.mp3` |

（曲名/艺术家/风格/BPM/URL 来源：`ATTRIBUTION.md:183-193`；BPM 为 librosa 实测，beat grid 最小二乘拟合法；时长为本手册实测 ffprobe。`sound-design.md:64` 记作「5 首」；模板片用的 `bgm-tech-house.mp3` 时长在 `sound-design.md:107` 记作 288.7s，与实测一致。）

#### SFX 的 16 个类别名与各自数量

目录 `assets/audio/sfx/` 下有 **16 个类别目录**（实测），逐类文件数：

| 类别 | 数量 | 装什么（`sound-design.md:78-95`） | 什么时候进这个目录 |
|---|---|---|---|
| `transition/` | **23** | whoosh / sweep / swoosh / 风 | 运镜、场景切换、元素飞入飞走 |
| `impact/` | **14** | impact / thud / stomp / bass hit | 落地钉点、重拍、slam |
| `riser/` | **1** | 上升铺垫 | 进 finale / 大镜头前的能量铺垫 |
| `camera/` | **10** | 快门、镜头、变焦 | 拍照感、crash zoom、对焦、iris |
| `ui/` | **18** | 点击、开关、通知、pop | UI 反馈、主题切换、列表落入 |
| `text/` | **13** | 打字机、键盘、书写 | 打字揭示、描线、下划线 |
| `paper/` | **10** | 纸、翻页、印刷 | 翻页转场、撕裂、纸艺、riso |
| `film/` | **8** | 放映机、胶片、磁带、黑胶 | 预告片语法、胶片串、回带变速 |
| `light/` | **10** | sparkle、光效 | 扫光、点亮、余韵闪光 |
| `data/` | **13** | glitch、电流、数据 | HUD、流式输出、骨架屏、故障 |
| `scifi/` | **5** | 科技、太空、底噪 | 太空运镜、系统底噪（长样本铺底） |
| `mech/` | **8** | 机械、工业、锁 | 部件组装、锁定、形变 |
| `glass/` | **4** | 玻璃、碎裂 | 碎裂转场、硬切冲击 |
| `fluid/` | **5** | 墨水、水、流体、颗粒 | 墨开场、颗粒填充、气泡 |
| `crowd/` | **3** | 人群、掌声、呼吸、心跳 | 合影收尾、发布会感、张力 |
| `counter/` | **4** | 计数器、仪表、钟、倒计时 | 数字滚动、读数、时间轴 |
| **合计** | **151**（实测文件数） | — | — |

> **文档口径：【已证实】目录实测 149 个，与仓库文档一致（原文「151」为误计，见开篇校正 1）。** `SKILL.md:235-236`、`sound-design.md:65`、`ATTRIBUTION.md:5` 记作「**149 个**音效，16 类」；主上下文用 `Get-ChildItem -Recurse -File` 独立复核为 **149 个 .mp3 / 16 类 / 无嵌套子目录**，逐类相加 = 149。`AUDITION-2026-07-27.md` 与 `ATTRIBUTION.md` 记录的是分批入库过程（第二批「下载 165 个 → md5 去重删 3 → 试听筛选删 38 → 留用 124」，`ATTRIBUTION.md:54`），期间删除过 `impact-cine.mp3`、`typewriter.mp3`（`sound-design.md:124-127`）——**删除动作已体现在 149 这个最终数里，文档无滞后**。

**词汇表 → 目录映射**（`sound-design.md:70-74`；这是最易踩的坑）：

| 词汇表 | whoosh | impact | riser | sparkle | transition |
|---|---|---|---|---|---|
| 目录 | `transition/` | `impact/` | `riser/` | **`light/`** | `transition/` |

**`sparkle` 的目录名是 `light/`，库里没有 `sparkle/` 目录**（`SKILL.md:238`、`sound-design.md:70`）。whoosh 与 transition 同在 `transition/`（音色本就重叠）；其余 11 个类别是词汇表之外的**拟音层**（S4 的「贴画面定制」槽位）。

#### `ATTRIBUTION.md` 的授权结论

**能否免费商用：能，但有逐文件保留项。**

- **规矩**（`ATTRIBUTION.md:3`）：下载音频素材时当场记录曲名/URL，事后无法反查。
- **Mixkit Sound Effects Free License**（免署名可商用）：
  - 基础 SFX（首批沿用）标为 `Mixkit SFX Free License` 或 `Mixkit License`（`:19-29`）。
  - 扩充第一批全部为 `Mixkit Sound Effects Free License（免署名可商用）`（`:33`）。
  - 扩充第二批同样全部为 `Mixkit Sound Effects Free License（免署名可商用）`（`:54`）。
- **BGM**：`Mixkit Stock Music Free License 免署名可商用`（`ATTRIBUTION.md:183`）。
- **保留项（商用前须自行确认）**：
  - 基础 SFX 首批 11 个中，`keyboard.mp3`、`riser-cine.mp3`、`sparkle.mp3`、`whoosh-big.mp3` 标为「**无法反查**，商用前须确认」；`pop.mp3` 标为「**来源待考**，商用前须确认」（`:21-29`）。
  - `bgm-tech-house.mp3` 标为「首批沿用，无法逐曲反查…**商用前复核**」（`:187`；`sound-design.md:52` 同）。
- **已删文件与等价替换**（`sound-design.md:124-127`）：`impact-cine.mp3` 已从 `assets/audio/` 删除，但**模板片照常渲染**——Remotion 读的是 `template/public/audio/` 的独立副本（`staticFile('audio/...')`），那份仍在。复刻 outro 三拍句式时用 `sfx/impact/impact-deep-whoosh.mp3` 代替：**它与原 `impact-cine.mp3` 字节完全相同**（md5 `ce27fd2f`）。`typewriter.mp3` 已删（本就是死资产）；要单击拟音改用 `sfx/text/typewriter-hit-single.mp3` 或 `typewriter-hit-hard.mp3`。
- **同素材重名 4 对（字节完全相同）**（`sound-design.md:129-141`）：

```text
transition/transition-soft     = transition/air-zoom-vacuum      （Air zoom vacuum）
transition/swoosh-quick        = transition/sweep-fast-small     （Fast small sweep transition）
impact/impact-transition       = impact/impact-epic-trailer      （Movie trailer epic impact）
impact/impact-cine             = impact/impact-deep-whoosh       （Cinematic whoosh deep impact；cine 已删）
```
  → **这几对不能用来做「双样本交替」**——字节相同，交替等于没换音。真要双样本，从同类别挑音色近但不同的（如 `text/typewriter-hit-hard` + `text/typewriter-hit-soft`）。新增音效入库时先跑 md5 去重：

```bash
find assets/audio -name '*.mp3' -exec md5 -r {} \; | sort | awk '{print $1}' | uniq -d
```

#### 「禁音名单」细节（SKILL.md 特别提到的两点）

**① `sfx/ui/` 必须逐个试听，不能整目录放行**（`SKILL.md:239-241`、`sound-design.md:150-180`）。`ui/` 是全库唯一**内部质感分裂**的类别。18 个文件的质感分档（`sound-design.md:154-173` 原表）：

| 文件 | Mixkit 原名 | 质感 |
|---|---|---|
| `switch-light` | Light switch sound | ✅ 真实电灯开关 |
| `switch-tap` | On or off light switch tap | ✅ 真实电灯开关 |
| `switch-click-quick` | Quick switch click | ✅ 真实开关 |
| `pop` | （来源待考） | ✅ 模板片定稿用过 |
| `hitech-touch-magnet` | Hi-tech touch with magnet | ⚠️ 磁吸质感，偏合成但有物理感，按片子调性定 |
| `chime-crystal` | Crystal chime | ⚠️ 水晶风铃，属光效/装饰音而非 UI 反馈，也可归 `light/` 用法 |
| `pop-electric` | Electric pop | ⚠️ 电子 pop，连发场景可用，单发略合成 |
| `ui-select-click` | Select click | ⚠️ 界面点击，比下面几个干净 |
| `ui-click-tone` | Cool interface click tone | ❌ 合成 tone |
| `ui-confirm-bleep` | High tech bleep confirmation | ❌ 合成 bleep |
| `ui-confirm-tone` | Confirmation tone | ❌ 合成 tone |
| `ui-tone-quick` | Digital quick tone | ❌ 合成 tone |
| `ui-success-soft` | Success software tone | ❌ 合成 tone |
| `ui-notify-tech` | Technology notification | ❌ 通知音 |
| `ui-message-pop` | Message pop alert | ❌ 通知音 |
| `ui-popup-dry` | Dry pop up notification alert | ❌ 通知音 |
| `ui-option-select` | Interface option select | ❌ 合成界面音 |
| `ui-select-modern` | Modern technology select | ❌ 合成界面音 |

用法（`sound-design.md:175-178`）：✅ 一档可直接用作交互动作拟音；⚠️ 一档**必须在成片语境里试听**再决定；❌ 一档默认不用于产品宣传片——**例外**：片子刻意要「系统在说话」的叙事（HUD 播报、AI 确认回执、报错演示），此时它是有意的风格选择，按 `aesthetic-rules` 须写进项目说明文档。同样的逐个试听纪律适用于 `data/` 与 `scifi/`（合成音天然多），只是那两类用途本就是数字/科技质感。

**② `glass/` 不在禁列**：`sfx/glass/` 是真实碎裂材质音（4 个）（`SKILL.md:240`、`aesthetic-rules.md:119`）。

**③ 模板片自己用 `click-camera.mp3` 且给了全片最高 SFX 响度 0.6**——真实快门声，不是 UI 提示音（`aesthetic-rules.md:117`）。

#### 两份特殊名单（钉帧必查）

**长样本（>5s，21 个，必须显式给 `durationInFrames`）**（`sound-design.md:190-213`）：`scifi/scifi-computer-ambience` 23.5s、`film/projector-spin-antique` 21.7s、`text/keyboard` 19.6s、`text/write-blackboard` 13.9s、`mech/mech-robotic-futuristic` 9.6s、`camera/camera-autofocus` 9.6s、`paper/paper-book-browse-fast` 9.3s、`scifi/space-intro-futuristic` 8.1s、`light/light-spell` 8.0s、`impact/impact-cine-big` 7.9s、`scifi/tech-hum-futuristic` 6.0s、`transition/wing-flutter`+`swoosh-slow`+`wind-pass-vibrate` 5.0–5.7s、`paper/paper-wind-blow` 5.5s、`mech/metal-drop-scifi-small` 5.5s、`light/light-aura`+`light-transition-magic` 5.1–5.5s、`impact/impact-movie-epic` 5.1s、`data/power-up-electronic` 5.0s、`crowd/applause-rhythmic-loop` 5.0s。判据：底噪/循环类按镜头时长铺；动作类按动作时长截；带长尾混响的 impact（`impact-cine-big` `impact-movie-epic` `metal-drop-scifi-small`）让尾音自然衰减，硬截会显得干。

**本身录得轻的文件（峰值 <-12dB，7 个）**（`sound-design.md:215-227`）：

| 文件 | 峰值 | 比 BGM(-9.4dB) 低 | 要压过 BGM（约 -6dB）需 |
|---|---|---|---|
| `data/data-load-os` | -24.6dB | -15.2dB | ~8.5x |
| `text/pencil-write-short` | -22.7dB | -13.3dB | ~6.8x |
| `text/write-fast` | -20.0dB | -10.6dB | ~5.0x |
| `transition/wing-flutter` | -17.9dB | -8.5dB | ~3.9x |
| `camera/ui-zoom-in` | -14.3dB | -4.9dB | ~2.6x |
| `counter/clock-knob-spin` | -14.0dB | -4.6dB | ~2.5x |
| `counter/clock-tick-single` | -13.9dB | -4.5dB | ~2.5x |

三条出路（`sound-design.md:229-236`）：① 换素材（首选）；② 预归一化 `ffmpeg -i in.mp3 -af "loudnorm=I=-16:TP=-1.5" out.mp3`；③ `volume` 给 >1 的增益（Remotion 允许，实测 `data-load-os` 给 4 输出 -12.7dB、给 16 输出 -0.7dB；`validateMediaProps` 只拦 `volume<0`，Web Audio 路径直接写 `gainNode.gain` 不钳制——**但预览会钳到 1.0**，必须以渲染产物验峰）。

**模板片实际使用的 14 个基础层**（`sound-design.md:101-122`）：12/14 在片中实际发声；2 个死资产（`impact-transition.mp3` 保留库中未引用、`typewriter.mp3` 已删）；来源待考的 `pop.mp3` 仍在库中。

---

### C10. `template/` 完整可渲染工程

#### 目录结构（实测，已剔除 node_modules）

```
template/
├── package.json
├── package-lock.json          （lockfileVersion 3）
├── remotion.config.ts
├── tsconfig.json
├── TEMPLATE.md                （99 行：换产品复现指南）
├── THEMES.md                  （44 行：主题/调色板编辑）
├── .gitignore
├── public/
│   ├── audio/                 11 个 SFX mp3
│   │   click-camera.mp3 / impact-cine.mp3 / keyboard.mp3 / pop.mp3 / riser-cine.mp3 /
│   │   sparkle.mp3 / swoosh-quick.mp3 / transition-snap.mp3 / transition-soft.mp3 /
│   │   whoosh-big.mp3 / whoosh-fast.mp3
│   └── textures/live/         32 个 png
│       card1.png … card10.png（含 card4-hires.png）/
│       detail-experiments.png / detail-full.png /
│       float-filter.png / float-search.png / float-section.png / float-stats.png /
│       nav.png / paper1.png … paper5.png / papers-full.png /
│       projects-empty.png / projects-full.png / wbr-full.png
├── scripts/
│   └── build-palette-assets.cjs
├── themes/                    （构建期主题资源目录）
└── src/
    ├── index.ts               registerRoot(Root)
    ├── Root.tsx               <Composition id="AiflPromo">
    ├── workbench.ts           213 行：动效工作台清单
    ├── aifl/
    │   ├── Main.tsx           192 行：AIFL_SHOTS / TITLE_CARDS / CAPTIONS / SFX / AiflMain
    │   ├── PaperTitleCard.tsx 111 行
    │   ├── Caption.tsx        65 行
    │   ├── DigitRoll.tsx      48 行
    │   ├── FlashCut.tsx       24 行
    │   ├── live-layout.json   389 行：页面元素坐标表
    │   └── live/
    │       ├── PageCam.tsx        150 行
    │       ├── SceneOpen.tsx      552 行
    │       ├── SceneFlyIn.tsx     468 行
    │       ├── SceneDetail.tsx    158 行
    │       ├── ScenePapers.tsx    200 行
    │       ├── SceneWbr.tsx       324 行
    │       └── SceneOutroLive.tsx 411 行
    └── themes/
        ├── manifest.tsx / visual-theme.tsx / ThemedFilm.tsx
        ├── palettes.json（74 行）/ palette-assets.json（1 行）/ palette-assets.ts（24 行）
```

（`template/TEMPLATE.md:41-49` 给出共用地基组件表；`README.md` 的仓库结构章节亦列出 `template/`。）

#### `template/package.json` 依赖清单与版本（原样）

```json
{
  "name": "promo-template",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "remotion studio src/index.ts",
    "render": "remotion render src/index.ts AiflPromo out/promo.mp4",
    "still": "remotion still src/index.ts AiflPromo"
  },
  "dependencies": {
    "@remotion/cli": "4.0.484",
    "react": "19.2.7",
    "react-dom": "19.2.7",
    "remotion": "4.0.484"
  },
  "devDependencies": {
    "@types/react": "19.2.17",
    "typescript": "6.0.3"
  }
}
```

`package-lock.json` 头部（实测，`lockfileVersion: 3`）与 `package.json` 一致。

#### 可用 npm scripts（`template/package.json:5-9`）

| script | 命令 |
|---|---|
| `npm run dev` | `remotion studio src/index.ts` |
| `npm run render` | `remotion render src/index.ts AiflPromo out/promo.mp4` |
| `npm run still` | `remotion still src/index.ts AiflPromo` |

**注意**：`template/` **没有** `npm test`；测试在仓库根 `package.json`（`npm test` = `vitest run`，`package.json:6`）与 `workbench/`。

#### `remotion.config.ts`（全文 6 行）

```ts
import { Config } from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
Config.setChromiumOpenGlRenderer('angle');
Config.setConcurrency(4);
```

（`workbench/remotion.config.ts` 与 template 同口径：jpeg 帧、ANGLE GL、并发 4；`workbench.md:133`。）

#### `tsconfig.json`（全文 15 行）

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "jsx": "react-jsx",
    "strict": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "resolveJsonModule": true,
    "noEmit": true,
    "lib": ["DOM", "ES2022"]
  },
  "include": ["src"]
}
```

#### Composition 定义（`template/src/Root.tsx` 全文 17 行）

```tsx
import { Composition } from 'remotion';
import { AIFL_TOTAL } from './aifl/Main';
import { ThemedFilm } from './themes/ThemedFilm';

export const Root: React.FC = () => {
  return (
    <Composition
      id="AiflPromo"
      component={ThemedFilm}
      defaultProps={{theme: 'ink-press'}}
      durationInFrames={AIFL_TOTAL}
      fps={30}
      width={1920}
      height={1080}
    />
  );
};
```

`template/src/index.ts`：

```ts
import { registerRoot } from 'remotion';
import { Root } from './Root';

registerRoot(Root);
```

#### `TEMPLATE.md` 的模板替换流程（6 步，`TEMPLATE.md:61-84`）

规格（`TEMPLATE.md:6`）：1920×1080 @ 30fps，**1085 帧（36.2s）**，SFX-only（无 BGM 版）。风格：纸墨琥珀（纸底 `#f2eee6`，墨字，衬线大标题，琥珀强调色）。

1. **采集素材**（`:63-67`）：复制 `../assets/scripts/capture-template.mjs` 进目标产品项目，改 `BASE_URL` 与选择器，产出三件套——整页 2x 截图、元素透明底切片、`layout.json`。素材命名对齐本模板（`projects-full`/`detail-full`/…），可直接覆盖 `public/`。
2. **换 layout 坐标**（`:68-69`）：用新 `layout.json` 替换 `src/aifl/live-layout.json`。场景代码里所有飞行目标位/遮罩位/悬浮件位置都从它读。
3. **逐镜头适配**（`:70-75`）：每镜头**先读对应镜头卡全文 + 场景源码**；必改项 = PageCam 的 `keys`（cx/cy/zoom 按新页面构图重定）、元素切片文件名、卡片数量/槽位循环、文案；**不要动** = 缓动曲线、时长配比、hold 帧预算、SFX 钉帧结构。
4. **文案**（`:76-78`）：改 `TITLE_CARDS`（`*词*` 标强调）、`CAPTIONS`、outro 品牌名/tagline；镜头结构变了同步改 `src/workbench.ts`（新镜头加一行 `scene(...)`；字卡照 `title(...)`），然后 `cd ../workbench && npm run parity`。
5. **验收**（`:79-81`）：每改完一镜头 `npx remotion still` 出静帧自检（每镜头至少入场中/动作峰值/落定后三帧）；全改完整片渲染 + ffmpeg 抽帧回看；最后对照 `../references/aesthetic-rules.md` 过 checklist。
6. **时长伸缩**（`:82-84`）：加/删镜头时整体平移 `AIFL_SHOTS` 的 `from`（单一事实源），`CAPTIONS`/`SFX`/`FlashCut` 的绝对帧号表跟着平移——建议先把新时间线定稿再动 SFX 表。

#### 模板片结构（`TEMPLATE.md:12-37`，10 镜 / 1085f）

```text
| # | 帧区间 | 时长 | 场景文件 | 内容 | 对应镜头卡 |
|---|--------|------|----------|------|-----------|
| 1 | 0–220 | 7.3s | live/SceneOpen.tsx | 墨线描画+字标压印开场 → dashboard 全景 → 聚光主角卡 | brand-ink-open / spotlight-hero-card |
| 2 | 220–275 | 1.8s | PaperTitleCard.tsx | 字卡①"All your team's research, one place to go." | paper-title-card |
| 3 | 275–465 | 6.3s | live/SceneFlyIn.tsx | 牌堆特写环绕 → 发牌飞入网格 → 滚动 → 搜索打字 → 筛选 → 点击推近 | deck-deal-flyin / type-and-filter |
| 4 | 465–565 | 3.3s | live/SceneDetail.tsx | 详情页宏观特写，行元素逐条嵌入 | row-embed |
| 5 | 565–620 | 1.8s | PaperTitleCard.tsx | 字卡②"Paper Radar…"（含 DigitRoll 数字子标） | paper-title-card |
| 6 | 620–725 | 3.5s | live/ScenePapers.tsx | 论文雷达列表堆叠压入 + 计数器落定 | list-stack-press |
| 7 | 725–775 | 1.7s | PaperTitleCard.tsx | 字卡③"Every project, linked to your weekly report." | paper-title-card |
| 8 | 775–885 | 3.7s | live/SceneWbr.tsx | 周报页"自己写自己"打字机揭示 + 历史周报逐条 pop 入侧栏 | document-typewriter-reveal |
| 9 | 885–940 | 1.8s | PaperTitleCard.tsx | 字卡④"The whole team, on the same page." | paper-title-card |
| 10 | 940–1085 | 4.8s | live/SceneOutroLive.tsx | 虚焦 → 元素合影组装 → 铅印字标砸落（riser→impact→sparkle）→ 1s hold | outro-group-photo-launch |
```

对应代码常量（`template/src/aifl/Main.tsx:15-28`）：

```ts
export const AIFL_SHOTS = {
  morning: { from: 0, duration: 220 },  // 0–7.3s  brand ~46f + 30f hold + 138f macro
  card1: { from: 220, duration: 55 },   // 7.3–9.2s
  table: { from: 275, duration: 190 },  // 9.2–15.5s pile → deal → scroll → search → filter → click
  macro: { from: 465, duration: 100 },  // 15.5–18.8s macro card detail, rows reveal
  card2: { from: 565, duration: 55 },   // 18.8–20.7s
  chart: { from: 620, duration: 105 },  // 20.7–24.2s papers stack radar
  cardWbr: { from: 725, duration: 50 }, // 24.2–25.8s
  wbr: { from: 775, duration: 110 },    // 25.8–29.5s weekly report
  card3: { from: 885, duration: 55 },   // 29.5–31.3s
  outro: { from: 940, duration: 145 },  // 31.3–36.2s
} as const; // sum = 1085

export const AIFL_TOTAL = 1085;
```

**字卡文案 DSL**（`Main.tsx:30-46`）：`TITLE_CARDS` 用**空格分词**，`*word*` = 琥珀斜体强调词，由 `parseWords` 解析：

```ts
export const parseWords = (text: string): { text: string; accent?: boolean }[] =>
  text
    .split(/\s+/)
    .filter(Boolean)
    .map((w) => {
      const m = w.match(/^\*(.+)\*$/);
      return m ? { text: m[1], accent: true } : { text: w };
    });
```

**叠加载荷（全部在 `Main.tsx` 声明式管理且全部 `export`）**（`TEMPLATE.md:30-37`）：`TITLE_CARDS`（4 张字卡文案表，card2 带副标 + 滚动数字）、`CAPTIONS`（底部通栏解说 6 条，绝对帧号表）、`FLASH_CUTS`/`FlashCut`（暖白闪 4 处，`from = 切点 − 5`，两侧各 5f 跨骑接缝）、`SFX`（30+ 条 `{from, src, volume}`，逐条注释；`keyboard` 长样本用 `sfxDuration` 截断 24f/44f）。

`FLASH_CUTS` 与 `sfxDuration`（`Main.tsx:48-54`）：

```ts
export const FLASH_CUTS = [AIFL_SHOTS.table.from, AIFL_SHOTS.macro.from, AIFL_SHOTS.chart.from, AIFL_SHOTS.wbr.from];

export const sfxDuration = (s: { from: number; src: string }) =>
  s.src === 'keyboard.mp3' ? (s.from > 700 ? 44 : 24) : 90;
```

#### 主题系统（`template/THEMES.md`）

- 9 个预设：Ink Press、Modern Light、Midnight、Sage、Coral、Iris、Deep Ocean、Obsidian Violet、Vintage Kraft（`THEMES.md:5`）；旧 ID（`solar-pop`、`coral-burst`、`color-play`）保持兼容（`:5`）。
- **Ink Press 保留原始栅格截图，没有调色板编辑器**；要重新着色须选其他预设（`:9`）。
- 单一调色板源：`src/themes/palettes.json` 定义每个可编辑预设的 7 个语义色，场景适配器与 `themes/ui.cjs` 共同读取（`:16`）。
- 直接渲染时 `AiflPromo` 接受 `theme` 与可选 `colors`（`:26-32`）：

```json
{"theme":"coral-burst","colors":{"accent":"#2459ad","surface":"#e1ecff"}}
```
  存为 props JSON 后 `npm run render -- --props=<file>`；缺省或未知预设回退 Ink Press。Workbench 导出则携带 `project.themeId` / `project.themeColors`。
- props 解析优先级（`:22`）：schema defaults → preset defaults → project palette → explicit clip edits。

---

### C11. Remotion 相关关键依赖版本

| 包 | 版本 | 来源 |
|---|---|---|
| `remotion` | **4.0.484** | `template/package.json:14`、`template/package-lock.json:12`、`workbench/package.json` deps |
| `@remotion/cli` | **4.0.484** | `template/package.json:11` |
| `@remotion/motion-blur` | **4.0.484** | `workbench/package.json` deps；template **故意不装**，demos 需要时 `npm i --no-save "@remotion/motion-blur@$(node -p "require('./package.json').dependencies.remotion")"`（`pr-checks.yml:110-112`） |
| `@remotion/player` | **4.0.484** | `workbench/package.json` |
| `@remotion/three` | **4.0.484** | `workbench/package.json` |
| `@remotion/google-fonts` | **4.0.484** | `workbench/package.json` |
| `@remotion/zod-types` | **4.0.484** | `workbench/package.json` |
| `react` | **19.2.7** | `template/package.json:12`、`workbench/package.json` |
| `react-dom` | **19.2.7** | `template/package.json:13` |
| `@types/react` | **19.2.17**（template）/ `19.2.17`（workbench） | `template/package.json:17` |
| `@types/react-dom` | `19.2.3` | `workbench/package.json` |
| `typescript` | **6.0.3**（template）/ `~5.9.0`（workbench） | `template/package.json:18`、`workbench/package.json` |
| `three` | **0.185.1**（`@types/three` `^0.185.0`） | `workbench/package.json` |
| `@react-three/fiber` | **9.6.1** | `workbench/package.json` |
| `zod` | **4.3.6** | `workbench/package.json` |
| `zustand` | `^5.0.0` | `workbench/package.json` |
| `vite` | `^6.0.0`（+ `@vitejs/plugin-react ^4.3.0`） | `workbench/package.json` |
| `vitest` | `^3.2.4` | 根 `package.json:10` |

**Node 版本要求**：
- 仓库**未在 `package.json` 中声明 `engines` 字段**（`template/package.json` 全文 20 行、根 `package.json` 全文 12 行均无）——**未找到显式的 Node 版本下限声明**。
- 从 CI 与文档可推出的实际要求：**Node 22**（`pr-checks.yml:32`、`:101`、`:139`、`:162` 均为 `node-version: 22`）；README「Headless / CI notes」记作「tested: 2 cores, **Node 22**」（`README.md:159`）。
- `workbench.md:153-155` 记录工作台把工程 `src/` 以符号链接打包进 `workbench/node_modules`，其中是 **remotion 4.0.484 / React 19**；工程若用了 `@remotion/three`、`three`、`@remotion/motion-blur`、`@remotion/google-fonts` 以外的包，需先在 `workbench/` 里装同版本。

---

## D. 工程化要点

### D12. `references/workbench.md` §2–3：`src/workbench.ts` 清单怎么写

**清单的作用**（`workbench.md:20-35`、`:37-41`）：工作台把片子拆成 clip（Project → Track → Clip）；「拆解导入」层要求成片工程提供 `src/workbench.ts` 清单，**时间表与 `Main.tsx` 同源**，导入后不改任何东西渲出来就是原片。TypeScript 类型在 `workbench/src/cards/manifest.ts`，**工程文件不需要 import，结构兼容即可**（`workbench.md:39-40`）。

**`workbench.md:42-67` 给出的结构范例（原样）**：

```ts
export const WORKBENCH = {
  name: 'Ink Press · AIFL promo',
  fps: 30, width: 1920, height: 1080,
  total: AIFL_TOTAL,                 // 成片总帧数
  background: '#f2eee6',             // Main 最外层 AbsoluteFill 的底色
  revision: undefined,               // 可选版本号；不给则按清单内容哈希判「是不是同一版成片」
  shots: [                           // 镜头：from/duration 与 <Sequence> 一一对应（绝对帧）
    { id: 'morning', label: 'S1 墨线开场', from: 0, duration: 220, component: SceneOpen },
    { id: 'card1', label: '字卡①', from: 220, duration: 55,
      component: TitleCardUnit,                     // 吃 props 的组件
      props: { text: 'All your team’s research, *one* place to go.' },  // 成片里的实际值
      schema: [{ type: 'textarea', key: 'text', label: '文案', default: '' }],
      durationProp: 'duration',                     // 把 clip 时长注入这个 prop（尾部淡出跟着走）
      cardId: 'title-card', cardName: '字卡' },     // 四张字卡共用一张卡
    …
  ],
  transitions: [...],                // 转场层（闪白 / 光条），结构同上
  captions: [...],                   // 字幕 / 解说条
  overlays: [...],                   // 全片常驻叠加层（网格 / 暗角）
  sfx: SFX.map(s => ({ from: s.from, duration: 90, src: `audio/${s.src}`, volume: s.volume })),
  bgm: [{ from: 0, duration: TOTAL, src: 'audio/bgm.mp3', volume: 0.34 }],
  order: ['transitions', 'captions', 'overlays'],   // 叠加层 z 序（上→下），缺省即此
  original: AiflMain,                // 原合成，供 parity 对照
};
```

**最小范例（本手册据 `workbench.md:42-67` 与 `template/src/workbench.ts` 提炼，可直接抄）**：

```ts
// src/workbench.ts —— 最小可用清单（3 个镜头 + 1 条转场 + 1 条字幕 + 1 条 SFX）
import { createElement, type FC } from 'react';
import { SHOTS, TOTAL, Caption, FlashCut, MySceneA, MySceneB, AiflMain } from './timeline';

// 1) 带默认值的 props 适配器（工作台属性面板改的就是这里的值）
type TitleProps = { text?: string; duration?: number };
export const TitleUnit: FC<TitleProps> = ({ text = '', duration = 55 }) =>
  createElement(PaperTitleCard, { duration, words: parseWords(text) });
TitleUnit.displayName = 'PaperTitleCard';

// 2) schema 字段助手（形状 = workbench PropField）
const text = (key: string, label: string, def: string) =>
  ({ type: 'text', key, label, default: def });

export const WORKBENCH = {
  name: 'My promo',
  fps: 30, width: 1920, height: 1080,
  total: TOTAL,
  background: '#f2eee6',
  shots: [
    { id: 'open',  label: 'S1 开场', from: SHOTS.open.from,  duration: SHOTS.open.duration,
      component: MySceneA },
    { id: 'card1', label: '字卡①',  from: SHOTS.card1.from, duration: SHOTS.card1.duration,
      component: TitleUnit, props: { text: 'One *place* to go.' },
      schema: [text('text', '文案', '')], durationProp: 'duration',
      cardId: 'title-card', cardName: '字卡' },
    { id: 'feat',  label: 'S3 功能', from: SHOTS.feat.from,  duration: SHOTS.feat.duration,
      component: MySceneB },
  ],
  transitions: SHOTS.cuts.map((cut, i) => ({
    id: `flash-${i + 1}`, label: `闪白 @${cut}f`, from: cut - 5, duration: 10,
    component: FlashUnit as FC<Record<string, unknown>>, durationProp: 'duration',
    cardId: 'flash-cut', cardName: '暖白闪转场',
  })),
  captions: CAPTIONS.map((c, i) => ({
    id: `caption-${i + 1}`, label: c.text, from: c.from, duration: c.duration,
    component: CaptionUnit as FC<Record<string, unknown>>,
    props: { text: c.text }, schema: [text('text', '解说文案', '')],
    durationProp: 'duration', cardId: 'caption', cardName: '解说字幕条',
  })),
  sfx: SFX.map((s) => ({ from: s.from, duration: 90, src: `audio/${s.src}`, volume: s.volume })),
  order: ['transitions', 'captions', 'overlays'] as const,
  original: AiflMain as FC<Record<string, unknown>>,
};
```

**§2 的硬性要求**（`workbench.md:69-89`）：
1. **参数化程度**：模板六个场景 + 字卡 + 解说条全部导出 `*_DEFAULTS`（文案/字号/色板）并以带默认值的 props 读取，清单 `schema` 直接引用同一对象——属性面板里改的就是屏幕上的值，**缓动/时值/相机键不暴露**（`:69-70`）。demo 里的场景常量（`CONFIG`/顶部 `const`）照这个模式提成 `DEFAULTS + Partial<typeof DEFAULTS>` 即可接入（`:71`）。
2. **同源原则**：清单里的每张表都从 `Main.tsx` **import**（`SHOTS`/`CAPTIONS`/`SFX`/字卡文案表），**不要手抄第二份**（`:73-76`）。范例：`template/src/workbench.ts` + `template/src/aifl/Main.tsx`（`AIFL_SHOTS` / `TITLE_CARDS` / `CAPTIONS` / `SFX` / `FLASH_CUTS` / `sfxDuration` 全部 `export`）。
3. **版本判据**（`:78-80`）：`?import=project` 打开时，存档的 `source` 与 `manifestKey(清单)` 不同才重新导入。`key = 名字 + 总帧数 + revision`；未写 `revision` 时用清单内容哈希（时间表/label/props/单元→卡的分组拓扑/组件 `displayName`/音效表）——改镜头位置、文案、音效或换组件即视为新版本；旧存档压进撤销栈，⌘Z 可找回。
4. **分组规则**（`:82-85`）：同一 `cardId`（或同一 `component` 引用）的单元共用一张「成片单元卡」，素材库里只出现一次；`label` 是时间轨显示名（中英文都行，工作台默认英文界面，按 `workbench/src/i18n.ts` 词典翻译成当前界面语言，查不到原样显示）。卡 id 为 `proj:<kind>:<cardId|首个单元 id>`；显式 `cardId` 与另一组首个单元 id 撞名（或单元 id 重复）时，后出现的组加 `~2` 后缀并在控制台警告——**请给单元换 id 或写显式 `cardId`，别依赖后缀**。
5. **素材路径**（`:87-89`）：`sfx[].src` 等一律相对工程 `public/`（工作台把工程 `public/*` 链接进自己的 `public/`）。字幕/字卡文案里的 `*词*` 记法是 Ink Press 字卡的强调词 DSL（`parseWords`）；其他工程可以自定 DSL，只要 props 是字符串/数字/布尔就能进属性面板。

**§3 制作新片时怎么写镜头（让它"未来可编辑"）**（`workbench.md:91-113`，6 条）：
1. **语境级参数 → props（带默认值）**：文案、颜色、字号、位置、开关、数据（多条用逐行文本 DSL）。**节奏命门保持常量**（弹入时长、错峰间隔、缓动曲线、相机路径）——它们决定动效品相，暴露出去反而容易调坏。
2. **`duration`/`dur` 类 prop 要真的用**（出场淡出按它算），清单里声明 `durationProp`，clip 拉长后淡出会跟着挪而不是定格在原时长处。
3. **时间表只写一份**：`timeline.ts`/`Main.tsx` 里的 `SHOTS` 是唯一事实源，SFX 钉帧、字幕表、转场点都从它派生并 `export`；`workbench.ts` 只 import + 补 `component`/`schema`。
4. **纯函数、确定性**：不读 `useVideoConfig().durationInFrames` 做绝对时间假设（motion-lab 系 `useT()` 归一化是例外且被工作台正确处理：clip 拉长 = 动画放慢）。
5. 交付前跑一次 `npm run parity` 确认拆解无损。
6. **实时预览得跑得动**：Player 是实时合成，不像渲染那样每帧等栅格化完成再截图。铺满巨型平面（几千 px 见方）的程序渐变 / `backdrop-filter` 放在 PageCam 这类每帧改 `zoom` 的 3D 层里，Chrome 栅格化跟不上就整块时有时无（Ink Press 模板 S3 的金属桌面曾因此在预览里疯狂闪）。这类纯装饰的重绘内容用 `getRemotionEnvironment().isRendering` 分流：渲染走原效果，预览用纯色/更轻的替身，几何与时序不变（`SceneFlyIn.tsx` 的 `METAL_PREVIEW` 是范例）。parity 只比渲染结果，所以仍成立。

**schema 字段类型**（`workbench.md:112-113`）：`text` / `textarea` / `number`（min/max/step/unit）/ `slider` / `color` / `select`（options）/ `boolean`，定义在 `workbench/src/cards/types.ts`。

**模板实际实现参考**（`template/src/workbench.ts`，213 行）：字段助手 `text`/`textarea`/`color`/`size`（`:32-37`），适配器 `TitleCardUnit`/`CaptionUnit`/`FlashUnit`（`:39-57`），`SCHEMAS`（`:71-130`），`scene()`/`title()` 构造器（`:132-159`），`PAPER_WORKBENCH`（`:161-212`），最后 `export const WORKBENCH = withThemes(PAPER_WORKBENCH);`（`:213`）。

**工作台的其余关键能力**（供交付后使用）：
- 打开命令（`workbench.md:11-18`；`SKILL.md:175`）：

```bash
node workbench/scripts/open.mjs <成片工程目录>
# → 链接工程 src/ 与 public/ → 生成索引 → 起 dev server（5198）→ 浏览器打开并自动导入成片
```
  首次自动 `npm install`（一次性，约 1 分钟）；dev server 后台常驻，`kill $(cat workbench/.dev.pid)` 停；shotcraft 端口 5198 / talkcraft 5199（`:17-18`）。
- **三层可编辑度**（`:22-28`）：时间与图层（所有 clip；要求组件是 `useCurrentFrame()` 的纯函数、tween 全部 clamp、无 `Date.now`/`Math.random`）、内容与样式（属性面板）、拆解导入（`src/workbench.ts`）。
- **无限损校验**（`:136-138`）：`npm run parity -- --frames 150,240,470,1000` 渲 `ProjImported` 与 `ProjOriginal` 同帧 PNG 逐像素比对（需 python3 + Pillow），差异像素 < 0.1% 视为一致；退出码 0 一致 / 1 有差异 / 2 无法得出结论（缺 Pillow、比对未执行）——不会假绿。
- **已知边界**（`:140-157`）：同轨允许 clip 重叠；变速为匀速重映射（无曲线变速）；卡片库按 30fps 编排（`CARD_FPS`），工程 fps 不同时拖卡上轨按 `clipDefaultsFor` 换算时长并反向变速；媒体卡（`timing: "realtime"`）只换算时长不变速；Freeze 不改 `useVideoConfig().fps`，卡内若用 `spring({fps})` 在非 30fps 工程里节奏会偏移；`open.mjs` 只重启自己启动的 dev server（`.dev.pid` + 进程命令行核实），端口被手动起的 server 占着时报错退出（因为 `@proj` 别名在 vite 启动时定死、刷新不会换工程）；音频 clip 导入时截到成片总长；demo 卡需要的灰阶纹理（`textures/live/*.png`）工程自带 `public/textures` 时以工程为准，否则兜底链接 `demos/_textures`。

---

### D13. 确定性渲染与伪随机固定种子

**硬规则来源**：`SKILL.md:158-159`（核心理念第 9 条）、`pipeline.md:232-234`（阶段 5 铁律）、`aesthetic-rules.md` 间接（A9/A6 与 Q 组均要求逐帧可复现）、`workbench.md:26`（时间与图层层的代码要求）。

**禁止项（原文）**：

```text
**确定性渲染铁律**：禁 `Date.now()` / `Math.random()` / 无参 `new Date()`。
一切伪随机用固定种子（mulberry32/哈希函数，seed 从 index 派生），
保证逐帧可复现、渲染间零抖动。
```
（`pipeline.md:232-234`；`SKILL.md:158-159` 同）

**工作台侧的等价表述**（`workbench.md:26`）：组件是 `useCurrentFrame()` 的纯函数、tween 全部 clamp、无 `Date.now`/`Math.random`——本 skill 第 9 条铁律已保证；**现有 demo（218 个里 216 个自动接入）与全部成片镜头无需改动即可上轨**。

**`mulberry32` 的签名与用法**（`assets/lib/helpers/rand.ts:1-11`）：

```ts
// origin: 模板片源仓库 helpers
/** Deterministic PRNG — same seed always yields the same sequence. */
export const mulberry32 = (seed: number) => {
  let a = seed | 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
};
```

- **签名**：`mulberry32(seed: number) => () => number`，返回一个无参取数函数，值域 `[0, 1)`。
- **seed 派生约定**：`seed 从 index 派生`（`pipeline.md:233`、`SKILL.md:159`）。库内实例如 `outro-group-photo-launch` 的「金尘 20 颗 2–3px、opacity 0.15–0.35、**全参数 index 派生确定性**」（`outro-group-photo-launch.md:27` 参数表「氛围三件套」行），以及 `deck-deal-flyin` 的姿态抖动公式 `(((k*7)%9)−4)*2`（`deck-deal-flyin.md:22`，「抖动必须确定性伪随机（硬规则：渲染必须可复现），真随机会渲染间抖动」）。
- **典型用法**：

```ts
import { mulberry32 } from './helpers/rand';

// 每个粒子用 index 派生独立种子 → 粒子参数互不相关但完全可复现
const particles = Array.from({ length: 20 }, (_, i) => {
  const r = mulberry32(i * 9973 + 17);   // seed 从 index 派生
  return { x: r() * 1920, y: r() * 1080, s: 2 + r() * 1, o: 0.15 + r() * 0.2 };
});
```

- **另一类确定性函数（非 PRNG，闭式）**（`assets/lib/helpers/shake.ts:6-10`、`assets/lib/helpers/motion.ts:39-40`）：`handheld(frame, amp)` 用不可通约频率的叠加正弦读作有机漂移；`dampedSettle(t, freq, damping)` 是闭式阻尼振荡，无逐帧状态累积（`motion.ts:21-26` 明确「Never accumulate state across rendered frames — every layer stays a pure function of the frame number」）。
- **纯帧位置函数的写法规范**（`demos/data/odometer-digit-roll/OdometerDigitRoll.tsx:20-21`、`:83`）：`posAt(f, i)` 只依赖帧号与 index；残影门控用 `Math.abs(pos - posAt(frame - 1, i))` 一阶差分——**不留状态**。
- **确定性被测试覆盖**（`assets/lib/helpers/__tests__/helpers.test.ts`）：见 D17。
- **图像/滤镜侧的确定性**：`print-texture-transitions.md:24` 明确 SVG `feTurbulence` 的 `seed` **必须写死**（确定性）。
- **与工作台的兼容边界**（`workbench.md:102-103`）：不读 `useVideoConfig().durationInFrames` 做绝对时间假设；motion-lab 系 `useT()` 归一化是例外且被工作台正确处理。

---

### D14. `references/music-beat-sync.md`：BGM 卡点完整方法论

**何时启用**（`music-beat-sync.md:18-27`）：阶段 0 先检查用户是否已指定音乐。已选好 → 先分析节奏再让分镜每个切点锚到拍号；未选 → BGM 选型放到阶段 6，动效时间线按内容节奏排，不强行卡点。
**铁律：音乐先行。** 网格没验收通过之前不设计分镜；时长对不上时改时间参数，**不删改用户文案**；分析全程用**浮点秒**记录时刻，**换算成帧只发生在进 Remotion 的最后一步**（提前取整会让误差在管线里滚雪球，`:25-27`）。

**实测结论**（`:4-5`）：一支 70s、18 镜、131.97 BPM 的强鼓点宣传片按此法制作，渲后回测全部切点误差 ≤2.2f（感知阈值约 3f）。

#### 步骤 1：节拍网格测定（不要相信 `beat_track` 的 tempo 标量）（`:29-61`）

```python
import numpy as np, librosa

y, sr = librosa.load("bgm.mp3", sr=None, mono=True)
tempo, beats = librosa.beat.beat_track(y=y, sr=sr, tightness=400, units="time")

# 关键一步：对 beat 序列做最小二乘等距网格拟合，求真实 BPM 与相位。
i = np.arange(len(beats))
A = np.vstack([i, np.ones_like(i)]).T
(T, t0), *_ = np.linalg.lstsq(A, beats, rcond=None)
bpm = 60.0 / T
residual = beats - (t0 + i * T)
print(f"BPM={bpm:.2f}  t0={t0:.4f}s  T={T:.5f}s  残差±{np.abs(residual).max()*1000:.0f}ms")
```

- 运行方式：`uv run --with librosa --with scipy --python 3.11`（`:31`、`:248`）。
- **`beat_track` 的 tempo 标量可能偏差 2%+（实测 129.2 vs 真值 131.97）**，但它输出的 beat 时刻序列本身是好的——所以用整个序列拟合直线 `t_i = t0 + i*T`（`:39-41`）。
- **验收标准**：残差 ≤ ±15ms（半帧内）说明是机器鼓点、网格可信；残差大说明有变速段，需分段拟合（`:50-51`）。
- **半倍/双倍歧义必查**（`:53-56`）：判据不是听感，是鼓点数据——正确网格下 kick 应主要落在整数拍；拿 0.5x/1x/2x 三个候选各算一遍分数（§3 指标），选覆盖率最高的。
- **复杂曲先分离鼓 stem**（`:58-61`）：`librosa.effects.hpss` 取打击成分；重方案 Demucs（见 §6）；之后所有鼓点检测都在鼓 stem 上做。

#### 步骤 2：鼓点分类与能量结构（`:63-112`）

**2a 三分类瞬态检测**（`:65-97`）：

| 类别 | 频段 | 驱动的动效 |
|---|---|---|
| kick | 40–160 Hz | 冲击 / slam / 骤缩——画面「被砸」的一拍 |
| snare | 150–500 Hz 体 + 1–3 kHz 打击面（两者都要有） | 替换 / 闪切 / 构图切换——「换一件事」的一拍 |
| hihat | 6–14 kHz | 微动密度——hihat 密的段落微动效可以密，稀的段落必须收 |

```python
from scipy.signal import butter, sosfilt
def band_env(y, sr, lo, hi):
    sos = butter(4, [lo, hi], btype="band", fs=sr, output="sos")
    env = librosa.onset.onset_strength(y=sosfilt(sos, y), sr=sr)
    return env, librosa.times_like(env, sr=sr)

kick_env, times = band_env(y, sr, 40, 160)
# 把每个整数拍位置的 env 能量列出来，排序找最强 hit：
for n in range(int((times[-1]-t0)/T)):
    t = t0 + n*T
    e = kick_env[np.argmin(np.abs(times - t))]
    # 记录 (拍号 n, 能量 e)，取 top 若干作为"大 slam 候选拍"
```

命中记成 `{t 秒, s 强度, k 类别}` 的列表存档（`:91`）。
**命中表是候选池，不是触发器**（`:93-97`）：强鼓点曲（tech-house 类）kick 几乎每拍都有，逐拍执行「被砸」就是「镜头随节奏抖动」（用户投诉，见 R4）。kick→冲击的映射**只用于从候选池里选出 §2b 的最强 hit（全片 2–3 处）**；其余 kick 只作为切点和元素级动效的**时机**参照，不驱动画面幅度。

**2b RMS 能量曲线与结构表**（`:99-112`）：`librosa.feature.rms` 拉全曲能量曲线，配合鼓点密度切出段落边界，产出两样进设计 spec——**音乐结构表**（能量从第几拍起满、breakdown/静默段在第几拍；breakdown 处放品牌呼吸位是天然结构）与**最强 hit 拍号清单**（全片 2–3 个最大 slam：开题/高潮/收尾）。
**易错点（实测踩过）**：最大 slam 钉在 b52.5（两拍之间）而最强 kick 在整数拍 b52 上，渲后回测偏差 **+5.75f**——强鼓点曲的重音几乎总在整数拍上，**半拍钉点必须有 env 数据支持，不能凭听感**（`:110-112`）。

#### 步骤 3：网格验收与产物（先验收，后分镜）（`:114-139`）

拿候选网格（含 0.5x/1x/2x）逐一对齐最近的真实鼓点瞬态，算**四个指标**：

| 指标 | 含义 | 门槛 |
|---|---|---|
| match | 网格拍命中真实瞬态的比例 | **≥98%** |
| mean_abs_ms | 平均绝对对齐误差 | **<10ms** |
| drift | 残差对时间做线性回归的斜率（漂移） | **全曲累计 <5ms** |
| 首拍有效性 | 网格第 0 拍是否落在真实的音乐攻击上 | **必须** |

（`:118-124`）按分数选出获胜网格，把**所有候选和获胜理由**写进分析产物留档；拿不准时给候选网格各合成一条 click 轨叠回原曲听一遍，**但最终以指标定夺，不以听感定夺**（`:125-127`）。

**分析产物随项目留档（每一个切点的审计链）**（`:129-139`）：

```text
analysis/
  beat_data.json    # bpm, t0, T, beats[], hits[{t,s,k}], rms[], sections[]
  grid_drift.json   # 各候选网格的 match/误差/漂移 与获胜理由
  click_*.wav       # 候选 click 轨（可选，听感复核用）
```
`beat_data.json` 里的时刻**永远是浮点秒、不预取整**；下游只依赖 `bpm / beats / hits / rms / sections` 这几个字段名。

#### 步骤 4：时间线用拍号写，不用帧号写（`:141-194`）

```ts
export const FPS = 30;
export const SOURCE_BEAT0 = 0.2244;  // 源音乐分析 t0，秒，与 beat_data.json 一致
export const BEAT_INT = 0.45465;     // T，秒
export const OUTPUT_AUDIO_OFFSET_SEC = 0; // 渲后回测确认有输出音轨偏移时填实测值（§5b）
export const beatT = (n: number) =>
  SOURCE_BEAT0 + OUTPUT_AUDIO_OFFSET_SEC + n * BEAT_INT;           // 拍→秒
export const beatF = (n: number) => Math.round(beatT(n) * FPS);    // 拍→帧

export const SHOTS = {
  s0_open:  { from: 0,        to: beatF(8) },
  s1_slam:  { from: beatF(8), to: beatF(16) },
  // …每个镜头边界都是 beatF(整数拍)；镜头内部动效用局部拍：
};
export const localBeat = (shot: {from: number}, n: number) => beatF(n) - shot.from;
```

好处（`:162-164`）：换曲/换段落时改两个常量全片重排；SFX 钉帧表也写 `beatF(n)`，与画面共用同一事实源，永不错位。**源分析值与渲染偏移分开记账**：`SOURCE_BEAT0` 是审计真值永不改，输出偏移只进 `OUTPUT_AUDIO_OFFSET_SEC`。

**锚点绑定规则（哪些用网格、哪些用真实瞬态）**（`:166-174`）：
- 密集规则切点（每拍/每两拍一切）→ 用获胜网格的 `beatF(n)`；
- 稀疏重音、孤立定格 → **钉真实瞬态**，不用网格插值点；
- 结尾定格 → 最后一个真实瞬态 + RMS 静默确认（防止钉在余韵尾巴上）；
- 视频素材/SFX 按**内部峰值**对齐，不按文件头对齐：`素材起始 = 目标拍时刻 − (峰值时刻 − 裁剪偏移)`；峰值用音频能量包络或 FFmpeg 帧差定位。

**设计规矩**（`:176-194`）：
- 镜头时长以拍为单位（4/8 拍一镜），加速段可用半拍/四分之一拍阶梯（如 `CUT_BEATS = [48, 49.5, 50.5, 51, 51.25]` 的收敛逼近）；
- 每拍一动作的步进类镜头（清单逐项、马赛克逐格）直接 map 拍号；
- BGM 鼓点已密时 SFX 克制：只钉画面独有动作、大 slam 只给 2–3 处；
- **全画面级冲击有硬上限**：全片 ≤3 处、与 §2b 最强 hit 清单一一对应、相邻两处间隔 ≥16 拍；节拍泵类连打单次 ≤4 拍且全片 ≤1 次，打完接足 hold；**计数单位是一次手法使用**；
- **卡点动效默认落在主角元素层**，整画面与相机层默认不参与逐拍运动；「每拍一动作」指内容步进，不是画面幅度脉冲；
- 结构性运动（形变/运镜/位姿）用连续帧函数；冲击事件（出现/替换/闪/骤缩）在选定的那一帧上开关；多层动效同帧命中构成重音，**要错开只错 1–2 帧且必须是设计意图**，不允许来自取整的意外错位。

#### 步骤 5：渲后回测（闭环，必做）（`:196-244`）

**5a 两种误差分开报，不混为一谈**（`:198-207`）：
- **音频真值误差**：设计切点秒值 vs 真实瞬态秒值的距离，验的是分析管线；门槛：平均 <5ms，全部 ±33ms 内，90% 在 ±15ms 内。
- **视觉量化误差**：秒值换算到最近可渲染帧引入的取整误差，验的是帧率够不够；`beatF()` 取整那一步的误差就是它，逐锚点记录。
- 最近帧取整误差上限由 FPS 决定：**30fps ±16.7ms、60fps ±8.3ms、120fps ±4.2ms**。**30fps 交付不要声称 <5ms 的视觉精度**；量化误差超容忍时**升帧率**，而不是去改音频分析。

**5b 渲出成片抽音轨回测**（`:209-244`）：

```bash
ffmpeg -i out/promo.mp4 -vn -acodec pcm_s16le /tmp/render-audio.wav
```

对渲出音轨重跑第 1 步的网格拟合（**BGM 从视频里量，不从源文件量**——这样连音频编码/对齐偏移一起验），然后逐一对比「设计切点帧号 vs 最近测得拍的帧号」，输出误差表。

| 判定 | 误差 |
|---|---|
| 合格 | ≤3f（感知阈值） |
| 理想 | ≤1.5f |
| 必修 | >3f 的任何切点 |

误差超标的钉点回第 4 步改拍号或帧偏移，重渲再测，直到全表合格。
**系统性同向偏移先查输出音轨偏移，不逐点手改**（`:227-244`）：误差表若呈同向等量偏移（所有切点一致 +N 帧），根因几乎总是渲染输出链路的音轨偏移（AAC encoder priming 等，48kHz 典型 ≈1.28f，见 `sound-design §4.6`）。诊断：拿 BGM 原文件与渲出音轨做归一化交叉相关量出偏移量。修复：**输出偏移单设常量，不写回源分析值**：

```ts
export const SOURCE_BEAT0 = 0.2244;        // 源音乐分析 t0，与 beat_data.json 一致，永不掺入渲染偏移
export const OUTPUT_AUDIO_OFFSET_SEC = 0.0427; // 输出音轨偏移，按渲染管线实测（sound-design §4.6）
export const beatT = (n: number) => SOURCE_BEAT0 + OUTPUT_AUDIO_OFFSET_SEC + n * BEAT_INT;
```
全片切点随 `beatT` 一次归位，**不要逐锚点手改拍号**；SFX 侧补偿走 `sound-design §4.6` 的同一常量。观感危害不止「不准」：冲击画面差 2–3 帧听不出是跟着鼓的，合理的卡点动效会被读作无端抖动。

#### 步骤 6：工具备忘（`:246-257`）
- librosa 不在系统 python：`uv run --with librosa --with scipy --python 3.11 script.py`；
- 只有人声/复杂编曲的曲子 `beat_track` 会漂：先用 `librosa.effects.hpss`，仍不干净时上 Demucs：`uvx --from demucs demucs --two-stems=drums -n htdemucs bgm.mp3 -o analysis/`，之后 §1/§2 全部在 `drums.wav` 上跑；
- BPM 拿不稳时 madmom 的 RNN+DBN 与 Essentia 的 RhythmExtractor2013 可作第二、第三票；三者对不齐时**回 §3 用瞬态覆盖率投票，不猜**；
- 变速曲（DJ 转场、accelerando）：先用 librosa 局部 tempogram（约 5s 窗）确认变速点，再按能量段分段拟合，各段各自 `t0`/`T`。

---

### D15. `references/sound-design.md`：音效使用的核心规则与目录清单

**方法（顺序）**（`sound-design.md:16-26`）：**画面结构基本锁定 → 先铺 BGM 定能量骨架 → 逐拍钉 SFX。**

1. **BGM 先行，定能量骨架**（`:20`）：一条 BGM 全片铺底，音量包络用 `interpolate` 做首尾淡入淡出（模板片 `[0, 30, TOTAL-50, TOTAL] → [0, 0.34, 0.34, 0]`，即 1s 淡入、1.7s 淡出）；BGM 音量压在 **0.34** 左右给 SFX 留 headroom；能量曲线要和分镜表能量曲线对得上（低开 → 中段推进 → outro 峰值）；候选曲必须垫进成片试听。BGM 的 `<Audio>` 用布尔 inputProp（如 `bgm`，默认 `true`）包住挂载，SFX 不受该开关影响——终渲固定出两版，无 BGM 版从同一时间线渲出：`npx remotion render … --props=props-nobgm.json`（文件内容 `{"bgm":false}`；**Windows shell 会剥掉内联 JSON 的双引号，走文件最稳**，macOS/Linux 也可内联 `--props='{"bgm":false}'`）。
2. **词汇表按「片种」选，不按「事件」选（S1）**（`:21-22`）：词汇 = whoosh(运镜) / impact(落地) / riser(铺垫) / sparkle(光效，目录 `light/`) / transition(转场)，禁用游戏音包**音色**。模板片第一版按 UI 事件语义选音（click/drop/confirmation），用户一耳朵判死刑「太像游戏了」。**禁的是音色不是动作**；`sfx/ui/` 需逐个试听；`sfx/glass/` 是真实碎裂材质音。
3. **SFX 逐拍钉帧、声明式表集中管理（S2）**（`:23`）：SFX 是 `{ from, src, volume }[]` 数组，逐条注释对应的画面动作，渲染时每条包一个 `<Sequence from={s.from}>`。
4. **通用音之外留「贴画面定制」槽位**（`:24`）：有辨识度的画面动作仍要专属拟音（打字揭示配键盘声、逐周落入配 pop）；泛用 swoosh 盖不住（S4）。

时机教训（`:26`）：模板片的音频工作直到画面改了约 30 轮之后才开始；有一次把换 BGM 和画面重做混在同一轮改动里，画面随后继续改，SFX 全表报废重钉。**声音永远排在画面锁定之后（S3）**。

**模板片 SFX 表位置**（`:5`）：全部集中在一个文件里管理（`template/src/aifl/Main.tsx`：`SFX[]` 钉帧表），**场景组件不含任何音频代码——声音是时间线级资产，不是镜头级资产**。

#### BGM 选型（`:30-54`）

三易其稿（34 分钟，`:32-40`）：

| 稿 | 曲目 | 来源/授权 | 被换原因 |
|---|---|---|---|
| v1 | Kevin MacLeod – *Inspired*（暖色 ambient 钢琴底） | incompetech，CC-BY | 用户：「BGM换个更有节奏感，更激情欢快的」 |
| v2 | Kevin MacLeod – *Life of Riley*（欢快 folk-pop） | incompetech，CC-BY | 用户：「这个配乐和音效都太像游戏了…鼓点强的，节奏感强的」 |
| v3（定稿） | Mixkit tech-house 鼓底（`bgm-tech-house.mp3`），音量升至 0.34 | Mixkit license | 未再被换 |

**v1→v2 只隔 22 分钟就又被否**——说明选曲时根本没在成片语境里听。**候选曲必须垫进成片试听后再定**（`:40`）。

选型判据（`:42-46`）：鼓点强、节奏感强，优先电子底（tech-house 类）；「好听/欢快」不是判据；气质基准是「典型的产品宣传视频」——闭眼只听音轨应像产品发布会预告，不像手机游戏（S1）；能量曲线能托住全片结构（平稳鼓底适合叠 SFX 层次，旋律太抢的曲子会和拟音打架）。

免费授权来源清单（`:48-54`）：

| 来源 | 授权 | 适用 | 备注 |
|---|---|---|---|
| Mixkit | Mixkit License（免费商用、免署名） | BGM + 电影系 SFX（whoosh/impact/riser/sparkle）+ 各类拟音 | 模板片定稿主力来源；批量下载后 metadata 常被抹掉，**下载时就记录曲名/URL** |
| incompetech（Kevin MacLeod） | CC-BY 4.0（**需署名**） | BGM，曲库大、按情绪筛选 | 模板片 v1/v2 出处 |
| Kenney（音包） | CC0 | 游戏类项目 | **产品宣传片禁用**（S1）——模板片引入后整批删除 |

#### SFX 目录清单（`:58-99`）

见 C9 的 16 类别表。补两条纪律：
- **类别是找音的索引，不是配音的判据**（`:99`）：`glass/` `crowd/` `fluid/` 这类材质音是「贴画面定制」槽位（S4），泛用转场仍优先 `transition/` `impact/`。
- 逐文件的时长/峰值/建议钉点见 `assets/audio/AUDITION-2026-07-27.md`；授权与 URL 见 `assets/audio/ATTRIBUTION.md`（`:97`）。

#### 模板片实际使用的 14 个（唯一有实战帧号的声音数据）（`:101-122`）

| 文件 | 所在目录 | 时长 | 用途场景 | 典型钉帧位置（模板片，30fps/全片 1085f） | 来源与授权 |
|---|---|---|---|---|---|
| `bgm-tech-house.mp3` | `bgm/` | 288.7s | 整片鼓底 BGM，tech-house 电子 | 全片铺底，音量包络 0→0.34→0.34→0 | Mixkit（无法逐曲反查，商用前复核） |
| `transition-soft.mp3` | `sfx/transition/` | 1.27s | 柔转场：品牌落定、场景切入 | f12 / f277 / f475 / f623 / f779（每次进新场景一发） | Mixkit |
| `whoosh-fast.mp3` | `sfx/transition/` | 1.76s | 快速运镜、批量元素飞走 | f78 brand→dashboard、f340/356 发牌加速、f435 筛选网格飞走 | Mixkit |
| `whoosh-big.mp3` | `sfx/transition/` | 2.32s | 大幅度运镜：弹起、拉远、回摆 | f127 hero 卡弹起、f308 orbit 拉远、f388 swoosh 回搜索栏 | Mixkit |
| `sparkle.mp3` | `sfx/light/` | 4.55s | 光效 reveal：扫描光束、收尾闪光 | f141 hero 卡光束、f1005 结尾 rule 闪光 | Mixkit |
| `transition-snap.mp3` | `sfx/transition/` | 0.57s | 短促落定/贴回原位的 snap | f204 hero 卡 impact reseat | Mixkit |
| `swoosh-quick.mp3` | `sfx/transition/` | 0.78s | 字卡出场统一音、轻推镜 | f220/565/725/885 四张 title card、f455 点击后 push-in | Mixkit |
| `keyboard.mp3` | `sfx/text/` | 19.6s | 真实键盘打字拟音（长样本，按段落裁剪用） | f401 搜索框输入（截 24f）、f781 周报页「自己写出来」（截 44f） | Mixkit |
| `click-camera.mp3` | `sfx/camera/` | 0.35s | 点击确认/快门感（全片最响 vol 0.6） | f451 点击卡片进详情、f648 papers 计数落定 | Mixkit |
| `riser-cine.mp3` | `sfx/riser/` | 4.81s | 电影系上升铺垫，进 finale | f945 outro 合影组装段起 | Mixkit |
| `impact-cine.mp3` | **已从库中删除** | 4.06s | 电影系重音钉点（vol 0.55 全片 SFX 峰值） | f980 字标 stamp 落地 | Mixkit |
| `pop.mp3` | `sfx/ui/` | 0.48s | 列表条目逐个落入的短促 pop | f840–865 周报周列表 6 连发，每 5f 一发、音量 0.40→0.25 阶梯递减 | **来源待考** |
| `impact-transition.mp3` | `sfx/impact/` | 4.87s | **死资产：全片未被引用** | 无 | Mixkit（同批），未接线 |
| `typewriter.mp3` | **已从库中删除** | 0.22s | **死资产：全片未被引用** | 无 | **来源待考** |

小结（`:122`）：12/14 在片中实际发声；2 个死资产；来源待考的 `pop.mp3` 仍在库中。复用时**取其相对语义而非绝对数值**（`:103`）。

#### 对齐技巧（`:182-357`）

**4.1 钉帧方法**（`:184-248`）：
- **声明式中央注册表**：`SFX: { from, src, volume }[]`，每条注释对应画面动作；渲染层遍历数组，每条包 `<Sequence from={s.from}>`；帧号表与分镜表（`AIFL_SHOTS`）放同一文件对照（S2）。
- **长样本靠 Sequence 截断，不剪音频文件**：`keyboard.mp3`（19.6s 原素材）按语境给 `durationInFrames` 24f 或 44f；**其余统一 90f** 让 ≤3s 素材自然播完；音频时长与画面动作严格等长（S4）。库里 **21 个文件长于 5s，必须显式给 `durationInFrames`**，照 90f 默认值会拖到动作结束后还在响。
- **音量分层**：BGM 0.34 打底，SFX 常规区间 0.2–0.6（点击确认 0.6 最响、pop 连发尾音 0.25 最轻）；**但 0.2–0.6 的前提是素材峰值接近 0dB**——`volume` 是乘法系数不是目标音量；库里 7 个本身录得轻的文件（峰值 <-12dB）即便给到 1.0 仍可能被 BGM 盖住，首选换素材或预归一化，必要时可给 >1 的增益（**预览会钳到 1.0，须以渲染产物验峰**）。钉完以渲染产物试听，不要只信数字。
- 实测命令（`:246-247`、`:240-242`）：

```bash
ffmpeg -hide_banner -i <file>.mp3 -af volumedetect -f null /dev/null 2>&1 | grep max_volume
ffmpeg -hide_banner -i out.mp4 -af volumedetect -f null /dev/null 2>&1 | grep max_volume
```

**4.2 变调与防机枪感**（`:250-258`）：**本仓库实证无 playbackRate 变调**（模板片全仓 `grep playbackRate` 零命中）。防机枪感靠三招组合：
1. **双样本交替**：连发用两个近似样本轮流（模板片 deck-deal 8 连发 pluck_002/pluck_001 交替）；
2. **音量阶梯递减**：沿序列线性衰减做「距离感」——定稿 pop 6 连发 `0.40/0.37/0.34/0.31/0.28/0.25`；
3. **间隔跟随动画曲线加速**：连发间隔贴画面加速节拍收缩（8f→3f）；密到糊成一片时**主动让声音淡出成一条 swoosh**。
   目标听感：连发段落是「数得出来的节奏」，不是机械复读（S2）。

**4.3 riser→impact：镜头收束句式**（`:260-268`）：

```text
riser-cine（组装/铺垫段起） → 约 35f 后 impact-deep-whoosh（主体 stamp 落地，全片响度峰值） → 25f 后 sparkle（余韵光效）
```
模板片 f945→f980→f1005，是**定稿声音方向确立后唯一从未改动的段落句式**。其它可复用小句式：场景切换 = `transition-soft` 一发；字卡出场 = `swoosh-quick` 统一音；点击确认 = `click-camera`（给全片最高 SFX 响度）。

**4.4 返工教训：三次重钉的顺序账**（`:270-280`）：第 1 次音色方向错误（游戏音包→电影系词汇）属声音自身返工；第 2 次画面时间线变更（总长 1020→1085）全表 `from` 平移；第 3 次周报段画面加动画该段 SFX 重写——**两次纯属画面返工的连带成本**。规则化：声音在画面锁定后做；任何改变镜头时长/顺序的修改，收尾动作固定包含「全表 SFX 帧号重对」。

**4.5 钉帧一律相对 shot 起点，而非绝对帧（硬规则）**（`:282-286`）：模板片钉绝对帧号，单文件数组便于整表平移，但绝对帧意味着**零结构复用**——任何一个镜头改时长，其后所有条目全部失效。做法：`SHOTS.<shot>.from + offset`（卡点片写 `beatF(n)`）；新项目起手即按相对钉帧写，**绝不写裸数字帧号**。

**4.6 音画对齐补两项偏移（硬规则）**（`:288-357`）：
设计意图是「音源峰值落在目标拍帧上」，从意图到成片隔着**两项偏移**，都不补时本仓库实测最重一击晚了 **0.27s**。统一公式（浮点计算，最后一步取整）：

```text
Sequence.from = 目标峰值帧 − 音源峰值滞后帧 − 输出音轨偏移帧
```

**偏移一：最终输出音轨偏移（逐渲染管线实测）**（`:299-325`）。根因在**输出编码/封装链路**，不是 `<Audio>` 或 `Sequence.from` 的行为：AAC 编码器有 encoder priming，48kHz 下典型 2048 samples = 1.28f@30fps。本仓库 AiflPromo 实测 click 滞后 **2032 samples**、impact **2066 samples**（≈1.27–1.29f），与 priming 指纹吻合；渲染品（`aifl-ref.mp4`）音轨的 edit list（`elst media time=0`）未声明裁剪这段垫头。Remotion 官方跟踪同族问题：`remotion-dev/remotion#7099`。
- **按管线记录，不按「片」**：偏移由 Remotion 版本 + 音频 codec + sample rate + 容器四要素决定；四要素不变可复用，换任何一样必须重测。priming 量级依编码器而异（ffmpeg 内置 aac ≈1024、fdk-aac 2048、Apple ≈2112 samples），**不能预设常数**。
- **promo-ink 时代实测过 4f**（≈133ms/6400 samples），量级远超 priming 所能解释、根因未验证——仅作为「旧常数不可跨管线搬运」的警示数据。
- 实测方法（渲后做，同管线量准一次通用）：

```bash
ffmpeg -i out/promo.mp4 -vn -acodec pcm_s16le /tmp/render-audio.wav
```
  拿 2–3 个尖锐 SFX 的**原文件**对渲出音轨做归一化交叉相关（numpy `np.correlate`），峰值位置减去设计帧号就是偏移量；**多个探针残差一致才算量准**。

**偏移二：音源自身的峰值滞后（逐文件量）**（`:327-332`）。很多素材的能量峰不在文件头（渐强攻击、前置气口），按文件头对齐等于晚到。实测例：`brush-write 2f`、`paper-slide 10f`、`ink-char 深达 24f`。峰值位置用音频能量包络定位，**新音效入库时随 max_volume 一并记录**。

渲染层实现（SFX 表保持 `{ from, src, volume }` schema 不变，三项拆分发生在 `from` 的计算表达式里——审计链完整，**绝不逐条手改帧号**）（`:334-344`）：

```tsx
// 本管线实测：Remotion 4.x + AAC 48kHz mp4，2026-08-23，click/impact 双探针交叉相关
const OUTPUT_AUDIO_OFFSET_F = 1.28;
const PEAK_F: Record<string, number> = { 'impact-deep-whoosh.mp3': 2 /* 逐文件实测 */ };
const sfxFrom = (targetPeakF: number, src: string) =>
  Math.max(0, Math.round(targetPeakF - (PEAK_F[src] ?? 0) - OUTPUT_AUDIO_OFFSET_F));
// 表内写法：{ from: sfxFrom(SHOTS.outro.from + 35, 'impact-deep-whoosh.mp3'), src: …, volume: 0.55 }
```

两个边界（`:346-351`）：
- **`durationInFrames` 不加偏移**：窗口整体前移后起止点在听感上一起归位；给截断型音效加长窗口会多播出本该裁掉的内容。
- `Math.max(0, …)` 兜底意味着**片头约 2f 内的钉点无法完成全部补偿**，残差记进验收表；片头重音尽量不要设计在前 2 帧。

BGM 侧同理但记账位置不同：`SOURCE_BEAT0` 保持分析真值不动，输出偏移单独设常量参与 `beatT` 换算，见 `music-beat-sync.md §5b`——两处共用同一套交叉相关实测法。**验收：补偿后重渲，对 2–3 个探针重跑交叉相关，残差 ≤0.5f 为合格**（`:357`）。

---

## E. 渲染与输出

### E16. 从 `template/` 渲染一支视频的完整命令序列

#### 最小命令序列（模板原样）

```bash
# 0) 进入模板工程
cd template

# 1) 安装依赖
npm install          # 或 npm ci（有 package-lock.json 时推荐）
# 首次约需下载 Remotion CLI + Chromium Headless Shell

# 2) 预览（Remotion Studio）
npx remotion studio src/index.ts
# 或 npm run dev

# 3) 验收静帧（阶段 5 最高频动作；每镜头至少入场中/动作峰值/落定后三帧）
npx remotion still src/index.ts AiflPromo out/qa/f150.png --frame=150
# 或 npm run still -- --frame=150 out/qa/f150.png

# 4) 整片渲染
npx remotion render src/index.ts AiflPromo out/promo.mp4
# 或 npm run render

# 5) 从成片抽关键帧回看（每轮修改后必做）
ffmpeg -i out/promo.mp4 -vf "select=eq(n\,150)" -vframes 1 out/qa/from-render-f150.png
```

来源：`TEMPLATE.md:8-10`（跑起来 + 验收静帧）、`SKILL.md:247-248`（`npm install && npx remotion render src/index.ts AiflPromo out/promo.mp4`）、`pipeline.md:222-229`（still / render / ffmpeg 抽帧）、`pipeline.md:32-33`（静帧产物按版本归档 `out/qa/`）。

**渲染配置在工程级固定**（`template/remotion.config.ts`）：`setVideoImageFormat('jpeg')`、`setOverwriteOutput(true)`、`setChromiumOpenGlRenderer('angle')`、`setConcurrency(4)`。

#### 带 BGM / 无 BGM 双版本渲染（固定交付动作）

`pipeline.md:347-354`（阶段 7 步骤 1）：

```bash
# 写一个 props 文件（内容就是 {"bgm":false}）
echo '{"bgm":false}' > props-nobgm.json      # Windows PowerShell: '{"bgm":false}' | Set-Content props-nobgm.json -Encoding utf8

# 从同一时间线渲出无 BGM 版（保留 SFX）
npx remotion render src/index.ts AiflPromo out/promo-nobgm.mp4 --props=props-nobgm.json

# 带 BGM 版
npx remotion render src/index.ts AiflPromo out/promo.mp4
```

- **跨平台可靠性**：`--props=<file>` 最稳；**Windows shell 会剥掉内联 JSON 的双引号，必须走文件**（`pipeline.md:351-353`、`sound-design.md:20`、`TEMPLATE.md:96-98`）。
- 实现要求：BGM 的 `<Audio>` 用布尔 inputProp（如 `bgm`，默认 `true`）单独包住，与 SFX 解耦（`pipeline.md:291-292`、`sound-design.md:20`）。
- 命名区分：`promo.mp4` / `promo-nobgm.mp4`（`pipeline.md:354`）。
- 注意：**`template/` 当前版本未实现 `bgm` inputProp**——`template/src/Root.tsx` 只有 `defaultProps={{theme: 'ink-press'}}`（`:10`），`Main.tsx` 无 `<Audio>` BGM（`Main.tsx:124-133` 只有 SFX）；`TEMPLATE.md:95-98` 把它写成「复现片若加了 BGM」的条件动作。全仓 grep `bgm` 在 `.tsx` 中仅命中 `workbench/src/panels/LibraryPanel.tsx:366`（工作台素材库的 BGM 分组），即**模板本身是 SFX-only 版**（`TEMPLATE.md:6` 明确「SFX-only（无 BGM 版）」）。要出双版本需自行给目标工程加 `bgm` prop。

#### 多分辨率 / 多比例的推荐做法

**仓库内实现的机制（3 条，均有源码依据）：**

1. **Composition 尺寸即输出尺寸**。`template/src/Root.tsx:7-15` 的 `<Composition id="AiflPromo" … width={1920} height={1080} />` 就是 1920×1080；Remotion 另可用 `--scale` 输出缩放副本（**仓库文档与脚本中均未出现 `--scale` 用法——未找到本仓库的推荐值**）。
2. **设计坐标系隔离（新 demo 系）**：Motion 系 demo 用 `<DesignStage>` 的 **480×270 设计坐标**作画、等比放大到合成分辨率；**「卡片参数表数值都在此坐标系下标定，改合成分辨率不需要动参数」**（`demos/README.md:42-43`）。老 demo 用手写逻辑坐标系 + 整体 `scale(min(W/420, H/250))`（`ui-entrance/research-card-stack-scroll.md:41`）或 `scale(252/330)`（`ui-entrance/floating-glossy-label-pills.md:55`）。**这是本仓库推荐的多分辨率做法**：把像素值写死在逻辑坐标系里，输出尺寸只改一处。
3. **多比例（如 9:16 竖版）需要改 Composition 的 `width`/`height` 并复核构图**。仓库内**没有竖版工程或竖版配方卡**；`gallery` 与 `template` 全部以 1920×1080 标定。相关可复用依据：`workbench.md:143-147` 明确「卡片库按 30fps 编排（`CARD_FPS`）；工程 fps 不同时，拖卡上轨按 `clipDefaultsFor` 换算时长并反向变速；媒体卡（`timing: "realtime"`）只换算时长、不变速」，以及「卡内若用 `spring({fps})` 等按秒计时，非 30fps 工程里节奏会偏移」。

**`--props` 的其他实际用法（仓库内有据可查的三种）**：

```bash
# ① 主题/调色板（template 直接渲染）
#    先写 props 文件：{"theme":"coral-burst","colors":{"accent":"#2459ad","surface":"#e1ecff"}}
npm run render -- --props=<file>

# ② 无 BGM 版
npx remotion render src/index.ts AiflPromo out/promo-nobgm.mp4 --props=props-nobgm.json

# ③ 剪映导出用的「平板」渲染（jianying-export.md:48-49）
npx remotion render src/index.ts <CompId> out/plate.mp4 --props='{"bgm":false,"plate":true}'
```
来源：`THEMES.md:26-32`、`pipeline.md:347-354`、`references/jianying-export.md:48-49`。

**渲染耗时的量化提示（仓库内唯一数值）**：`deck-deal-flyin.md:30` 记「`samples` 按渲染预算调（**每 +1 约 +1 倍渲染时间**）」——指 `@remotion/motion-blur` 的 `<CameraMotionBlur samples={10}>`。其余耗时数据仓库未给出。

#### 无头 / CI 环境渲染（README「Headless / CI notes」）

`README.md:157-171`（中文版 `README_CN.md:142-148`）记录三个已知墙：

1. **并发上限** —— 低核机器上 `remotion still/render` 会报 `"Maximum for --concurrency is 2"`。**修复：加 `--concurrency=1`**。
2. **Old Headless 移除** —— 近期 Chrome/Chromium 移除了 old headless 模式，把 Remotion 指向系统 chromium 会启动失败。**修复：改用 `chrome-headless-shell` 二进制而不是完整 Chrome**。
3. **CDN 被墙** —— 若 `remotion.media` 不可达，自动下载 headless-shell 会被拒绝。**修复：`--browser-executable=<path-to-local chrome-headless-shell>`**。

加上这三个 flag 后，模板的逐帧渲染可以跑通（`:171`）。

---

### E17. 仓库自带的测试与验证手段

#### ① `npm test`（vitest）覆盖什么

`package.json`（仓库根，全文 12 行）：

```json
{
  "name": "video-shotcraft-tests",
  "private": true,
  "description": "Unit tests for assets/lib/helpers pure functions",
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "devDependencies": {
    "vitest": "^3.2.4"
  }
}
```

**唯一测试文件**：`assets/lib/helpers/__tests__/helpers.test.ts`（181 行）。文件头注释（`:1-3`）：**纯函数、无状态，每条断言都是确定性的，不需要 mock**。

覆盖的 `describe` 块与被测函数（`:5-9`）：

| describe | 被测函数 | 断言数 | 覆盖点（行号） |
|---|---|---|---|
| `mulberry32` | `helpers/rand.ts` | 5 | 值域 `[0,1)`（`:11-18`）；同种子同序列（`:20-26`）；不同种子不同序列（`:28-34`）；**跨实例可复现、无隐藏状态泄漏**（交错调用不影响，`:36-45`）；边界种子 0 / -1 / 3.7 / 2147483647 / -2147483648 不抛（`:47-54`） |
| `velocityAt` | `helpers/motion.ts` | 5 | 匀速直线恢复速度（`:61-66`）；`direction === atan2(vy,vx)`（`:68-71`）；静止主体返回 0（`:73-79`）；**中心差分对二次轨迹是二阶精度**（`x=f²` 在 f=4 给 8，`:81-86`）；缩放随 `dt` 不变（`:88-92`） |
| `lagged` | `helpers/motion.ts` | 3 | 在 `frame − delay` 采样（`:96-100`）；负帧原样返回（由调用方 clamp，`:102-105`）；泛型类型透传（`:107-110`） |
| `dampedSettle` | `helpers/motion.ts` | 6 | `t ≤ 0` 时为 0（`:114-117`）；首个峰值正向（`:119-123`）；每半周期符号翻转（`:125-131`）；幅度包络随时间衰减（`:133-139`）；更高 damping 衰减更快（`:141-148`）；同参数确定性（`:150-152`） |
| `handheld` | `helpers/shake.ts` | 4 | 返回 3 元组且 `z === 0`（`:156-161`）；同帧同输出（`:163-165`）；幅度与 `amp` 线性（`:167-172`）；**始终在包络内**（`|x| ≤ 1.6·amp`、`|y| ≤ 1.5·amp`，遍历 500 帧，`:174-180`） |

`SKILL.md:249-251` 对 `npm test` 的表述：「纯函数单测：`npm test`（仓库根 vitest，覆盖 `assets/lib/helpers` 的 **mulberry32 / velocityAt / lagged / dampedSettle / handheld**，确定性断言）」——与实测一致。

#### ② `assets/scripts/smoke-render-demos.py` 做什么

文件头 docstring（`:1-20`）：

```text
"""smoke-render-demos.py — demo 渲染冒烟测试。

堵住"能编译不能运行"的漏洞：现有 CI 只做 tsc 编译，不验证 demo 能否
真的渲染。本脚本扫描所有带时长导出（`_DURATION` / `_DUR`）的 demo，
自动生成一个临时 Root 注册全部，然后逐个渲染首帧，断言输出文件非空、
渲染不崩。
```

- **用法**（`:9-10`）：`python3 assets/scripts/smoke-render-demos.py [--subset a,b,c] [--list]`（从仓库根）。
- **前置条件**（`:12-18`）：`template/` 已 `npm install`（remotion 4.0.484）；demos 用到的 `@remotion/motion-blur` 已装到 template（CI 里临时装）；需要纹理的 demo 的 `demos/_textures/` 文件已复制到 `template/public/textures/live/`（脚本会自动复制缺失的）；需要素材 mp4 的 demo（如 `clipcard-looping`）跳过并报告，**不失败**。
- **退出码**（`:19`）：全通过 0；任一 demo 渲染失败 1（列出失败清单）。

**实现要点**：
- 扫描根 `ROOT = Path(__file__).resolve().parent.parent.parent`、`TEMPLATE = ROOT / 'template'`（`:31-35`）。
- 时长导出正则（`:36`）：`DUR_PAT = re.compile(r'export const (\w+_DURATION|\w*_DUR)\s*=')`。
- 跳过名单（`:39`）：`MATERIAL_REQUIRED = {'ClipCardLooping'}`。
- `find_demos()`（`:42-57`）：遍历 `demos/**/*.tsx`（按路径排序），要求同时命中时长导出**且**存在 `export const <stem>: React.FC =`（精确正则，避免文件名出现在注释/字符串里造成误判）。
- `write_smoke_root()`（`:60-76`）：生成 `template/src/smoke-root.tsx`，为每个 demo 生成

```tsx
import { <Stem>, <DURNAME> } from '<relpath>';
<Composition id="<Stem>" component={<Stem>} durationInFrames={<DURNAME>} fps={30} width={1920} height={1080} />
```
  并 `registerRoot(Root)`。
- `ensure_textures()`（`:79-92`）：把 `demos/_textures/` 下的 `.png/.jpg/.jpeg/.webp` **复制**（不覆盖已存在）到 `template/public/textures/live/`；跳过 `layout.json` 等数据文件（它们是被 import 进 TS 的，不是运行时纹理）。
- `render_one()`（`:95-109`）：在 `TEMPLATE` 目录下执行

```bash
npx remotion still src/smoke-root.tsx <Stem> --frame=0 <out.png> --log=error
```
  失败条件：`returncode != 0`（取 `stderr[-400:]` 作为错误信息），或输出不存在/大小为 0（`'rendered but empty output'`）。
- 清理（`:156-157`）：跑完删除生成的 `smoke-root.tsx`。
- `--list` 只列出可渲染 demo 名（`:119-122`）；`--subset` 含未找到的 demo 时**退出码 1**（`:124-131`）。

`demos/README.md:110-120` 给出本地全量跑法：

```bash
cd template && npm ci && npm i --no-save "@remotion/motion-blur@$(node -p "require('./package.json').dependencies.remotion")"
cd .. && python3 assets/scripts/smoke-render-demos.py                    # 全量
python3 assets/scripts/smoke-render-demos.py --subset BlurSlide,Scramble # 子集
python3 assets/scripts/smoke-render-demos.py --list                      # 列出可渲染 demo
```

#### ③ CI 跑什么（`.github/workflows/pr-checks.yml`，175 行）

**触发**（`:7-20`）：`pull_request` → `main`，paths 过滤 `references/shots/**`、`gallery/**`、`demos/**`、`assets/lib/**`、`assets/scripts/**`、`template/src/**`、`workbench/**`、`package.json`、`package-lock.json`、该 workflow 自身。

**4 个 job**：

| job | 运行环境 | 步骤 | 依据 |
|---|---|---|---|
| **`unit-tests`** | ubuntu-latest，Node 22，cache `package-lock.json` | `npm ci` + `npm test`（「Helpers pure functions unit tests」） | `:26-38` |
| **`verify`** | ubuntu-latest，Python3 + Node 22 | ① **生成产物与卡片同步 gate**：跑 `python3 gallery/sync-from-cards.py` + `python3 gallery/build-seo.py`，然后 `git status --porcelain -- gallery` 非空即失败（用 porcelain 而非 `diff --exit-code`，因为**新卡重新生成的 source 副本是 UNTRACKED**，diff 看不到）；② **每条 `library.json` 预览必须存在于 `gallery-media` release**：拉 release 资产名，正则强制 `media.url` 形如 `^\./media/[a-z0-9-]+\.(mp4\|gif)(\?v=\d+)?$`（因为 `app.js` 把它插进 `innerHTML` 未转义），并核对每个文件名在 release 里存在；③ **demo 严格编译**：`cd template && npm ci`，`npm i --no-save "@remotion/motion-blur@$(node -p "require('./package.json').dependencies.remotion")"`（**pinned 到 template 的 remotion 版本**——裸装 latest 会嵌套第二份 remotion 并触发 `checkMultipleRemotionVersions`），`ln -s template/node_modules node_modules` 给 tsc 一个仓库顶级 module-resolution root，`find demos -name '*.tsx'` 全部 + `assets/lib/` 中 9 个**只依赖 remotion 的组件**（`ClipCard.tsx` `Caption.tsx` `DigitRoll.tsx` `FlashCut.tsx` `PageCam.tsx` `VerticalTicker.tsx` `helpers/motion.ts` `helpers/rand.ts` `helpers/shake.ts`）走 `tsc --noEmit --strict --skipLibCheck …`；**three 相关的 `FlatPanel` 与 `helpers/camera` 被排除**（template 不装 three） | `:40-132` |
| **`workbench-build`** | ubuntu-latest，Node 22，cache `workbench/package-lock.json` | ① `cd workbench && npm ci && npx tsc -b && npx vite build`（`prepare` hook 跑 `scripts/gen-index.mjs`：218 demos + gallery metadata → static index）；② template（含 workbench manifest）编译：`ln -s ../workbench/node_modules template/node_modules` 后 `cd template && ../workbench/node_modules/.bin/tsc --noEmit -p tsconfig.json`；③ `npm --prefix workbench run test:themes`（主题与调色板回归） | `:134-156` |
| **`demo-smoke`** | ubuntu-latest，Node 22，cache `template/package-lock.json` | `cd template && npm ci` → 装 motion-blur → `ln -s template/node_modules node_modules` → `python3 assets/scripts/smoke-render-demos.py`（渲染每个可跑 demo 的首帧） | `:158-175` |

`SKILL.md:252-255` 对 CI 的表述：「CI（`pr-checks.yml`）已自动跑：**tsc 严格编译全部 demo + vitest + 冒烟渲染**」——与实测一致（另有 workbench build 与主题回归两个 job）。

**其他 workflow**：`.github/workflows/deploy-pages.yml`（部署 gallery 到 GitHub Pages）、`.github/workflows/showcase-publish.yml`（作品展示页发布，配 `.github/scripts/showcase-publish.py`）。`.github/ISSUE_TEMPLATE/showcase.yml` 是投稿表单。

#### ④ 工作台侧的两项验证（交付前必跑）

| 命令 | 作用 | 依据 |
|---|---|---|
| `cd workbench && npm run parity -- --frames 150,240,470,1000` | 渲 `ProjImported` 与 `ProjOriginal` 同帧 PNG 逐像素比对（需 python3 + Pillow），**差异像素 < 0.1% 视为一致**；退出码 0 一致 / 1 有差异 / **2 无法得出结论（缺 Pillow、比对未执行）——不会假绿** | `workbench.md:136-138`；脚本 `workbench/scripts/parity.mjs:4`（用法注释）、`:21`（默认帧表）、`:30-32`（缺 Pillow 时报错）、`:79-85`（逐帧比对） |
| `cd workbench && npm run test:themes` | 主题/调色板状态与 props 适配器的纯函数回归（用 Node `node:test` + `assert/strict`，通过 `require.extensions` 用项目自带 TypeScript 转译 `src/theme.ts`） | `workbench/package.json` scripts；`workbench/scripts/test-themes.mjs:1-25` |

`workbench/scripts/test-themes.mjs:11-18` 被断言的适配器函数：`switchTheme`、`themedProps`、`inheritedProps`、`selectedTheme`、`themedBackground`、`upgradeLegacyTheme`；`THEMES.md:36` 列出测试覆盖范围：「custom palette validation and precedence, reset, edit preservation, legacy saves, unthemed projects, palette history, preserved weekly copy, caption defaults, and separate light/accent/shadow roles」。

#### ⑤ 无自动化的手工验收（流程强制）

- 每镜头 `npx remotion still` 静帧肉眼验收，产物按版本归档 `out/qa/`（`pipeline.md:32-33`、`:222-225`）。
- 每轮修改后整片渲染 + ffmpeg 抽帧回看（`pipeline.md:226-229`）。
- 交付前**独立 subagent 终检**（干净上下文）+ `final-review.md` + `aesthetic-rules.md` 逐条报告（`pipeline.md:355-368`、`final-review.md:1-5`）。

---

## 附录 A：调研方法与可复现命令

本手册的全部「实测」结论来自下列只读操作（均在仓库根执行）：

```powershell
# 1) 卡片总数与分布
Get-ChildItem -LiteralPath 'references\shots' -Recurse -File -Filter *.md |
  Where-Object { $_.Name -ne 'ATTRIBUTION.md' } | Measure-Object   # → 157
Get-ChildItem -LiteralPath 'references\shots' -Directory | ForEach-Object {
  "$($_.Name)`t$((Get-ChildItem -LiteralPath $_.FullName -File -Filter *.md).Count)" }

# 2) 全量 frontmatter 抽取（写入 UTF-8 文件避免控制台编码问题）
$root = '<repo>'
foreach ($f in Get-ChildItem "$root\references\shots" -Recurse -File -Filter *.md) {
  $lines = Get-Content -LiteralPath $f.FullName -Encoding UTF8
  # 取第一个 --- ... --- 区间并输出
}

# 3) BGM 时长
Get-ChildItem 'assets\audio\bgm' -File | ForEach-Object {
  & ffprobe -v error -show_entries format=duration -of csv=p=0 $_.FullName }

# 4) SFX 分类计数
Get-ChildItem 'assets\audio\sfx' -Directory | ForEach-Object {
  "$($_.Name)`t$((Get-ChildItem -LiteralPath $_.FullName -File).Count)" }

# 5) library.json 结构
$j = Get-Content 'gallery\api\library.json' -Raw -Encoding UTF8 | ConvertFrom-Json
$j.PSObject.Properties.Name; $j.stats; $j.cards.Count
```

**重要环境提示**：本手册撰写期间，仓库目录从
`C:\Users\75203\Downloads\xkd\VideoGenResearch-minimax\video-shotcraft`
**移动**到
`C:\Users\75203\Downloads\xkd\video-shotcraft`
（由父 agent 通知确认）。所有相对路径以仓库根为基准，不受此移动影响。

---

## 已知坑与注意事项

### 1. 平台差异（Windows / macOS / Linux）

| 问题 | 表现 | 正确做法 | 依据 |
|---|---|---|---|
| **`--props` 内联 JSON 在 Windows 被 shell 剥引号** | `--props='{"bgm":false}'` 在 Windows 上失效 | **写成文件走 `--props=props-nobgm.json`**（内容 `{"bgm":false}`）；macOS/Linux 可内联 | `pipeline.md:351-353`、`sound-design.md:20`、`TEMPLATE.md:96-98` |
| 工作台打开的 dev server 端口冲突 | 端口被手动起的 server 占着时 `open.mjs` 报错退出 | 因为 `@proj` 别名在 vite 启动时定死、刷新不会换工程；只能停掉手动 server | `workbench.md:148-149` |
| 工作台停服 | 后台常驻 | `kill $(cat workbench/.dev.pid)`；工作台只重启**自己启动的** dev server（`.dev.pid` + 进程命令行核实） | `workbench.md:17`、`:148-149` |
| 剪映导出 | `mac_draft.py` 在 Mac 剪映 11.2 实测通过；`windows_draft.py` **按上游支持路径实现，未真机验证** | Windows 路径需自行验证；新环境先跑 `smoke_test.py` | `SKILL.md:256-260` |
| **无头 Linux / CI 三堵墙** | ① `Maximum for --concurrency is 2`（低核机器）；② 指向系统 chromium 启动失败（old headless 被移除）；③ `remotion.media` 不可达时 headless-shell 自动下载被拒 | ① `--concurrency=1`；② 用 `chrome-headless-shell` 二进制而非完整 Chrome；③ `--browser-executable=<本地 chrome-headless-shell 路径>` | `README.md:157-171`、`README_CN.md:142-148` |
| MD5 命令的平台差异 | `sound-design.md:145` 给的是 macOS 的 `md5 -r` | Linux 用 `md5sum`，Windows 用 `certutil -hashfile` 或 PowerShell `Get-FileHash` | 文档原文 `sound-design.md:144-146` |
| `ffmpeg … -f null /dev/null` | 文档命令用 `/dev/null` | Windows 改 `-f null NUL` 或用 `2>&1 \| Select-String max_volume` | `sound-design.md:241`、`:247` |
| Playwright/Puppeteer 截图脚本 | `capture-template.mjs` 里 `puppeteer.launch()` 无参（用自带 Chromium） | 目标工程需先 `npm i puppeteer`（唯一依赖） | `capture-template.mjs:14`、`:108` |
| `template/scripts/build-palette-assets.cjs` | 需要 Playwright（开发环境） | `SHOTCRAFT_PLAYWRIGHT` / `SHOTCRAFT_BROWSER` 可指定已有模块与 Chromium 可执行文件；编译产物已 commit，**终端用户不需要这些工具** | `THEMES.md:20` |

### 2. 依赖要求

| 项 | 要求 | 依据 |
|---|---|---|
| Remotion | **4.0.484**（`remotion`、`@remotion/cli`、`@remotion/motion-blur`、`@remotion/player`、`@remotion/three`、`@remotion/google-fonts`、`@remotion/zod-types` 全部同版本） | `template/package.json:11-14`、`workbench/package.json` |
| React / React-DOM | **19.2.7** | `template/package.json:12-13` |
| `@remotion/motion-blur` | **template 故意不装**；8 个 demo / 6 张卡需要。**必须 pinned 到 template 的 remotion 版本**：裸装 latest 会嵌套第二份 remotion 并触发 `checkMultipleRemotionVersions` | `pr-checks.yml:108-112`、`demos/README.md:25-33` |
| three 栈 | `helpers/camera.tsx` 与 `FlatPanel.tsx` 需要 `three` + `@react-three/fiber` + `@remotion/three`；其余 lib 组件只需要 remotion。CI 因此**排除这两个文件**的 tsc | `SKILL.md:229-232`、`FlatPanel.tsx:1`、`pr-checks.yml:117-119` |
| Node | **未在 `package.json` 声明 `engines`**；CI 与文档统一用 **Node 22** | `pr-checks.yml:32`/`:101`/`:139`/`:162`、`README.md:159` |
| Python | 冒烟渲染脚本与 gallery 脚本需要 **python3**；`npm run parity` 需要 **python3 + Pillow** | `demos/README.md:110-116`、`workbench.md:136-138`、`parity.mjs:30-32` |
| librosa / scipy | 不在系统 python 时用 `uv run --with librosa --with scipy --python 3.11` | `music-beat-sync.md:31`、`:248` |
| Demucs（可选） | `uvx --from demucs demucs --two-stems=drums -n htdemucs bgm.mp3 -o analysis/` | `music-beat-sync.md:250-252` |
| 剪映导出 | 需 venv + `pip install pyJianYingDraft` | `SKILL.md:259-260` |
| ffmpeg / ffprobe | 抽帧回看、音量探测、音轨提取、交叉相关探针 | `pipeline.md:227-228`、`sound-design.md:212`、`:240-242`、`:320-322` |

### 3. 确定性与可复现

- 禁 `Date.now()` / `Math.random()` / 无参 `new Date()`；伪随机一律固定种子（`mulberry32`，seed 从 index 派生）（`pipeline.md:232-234`、`SKILL.md:158-159`）。
- 抖动/粒子等「随机感」参数必须**确定性派生**（如 `deck-deal-flyin` 用 `(((k*7)%9)−4)*2`；`outro-group-photo-launch` 金尘全参数 index 派生）。真随机会渲染间抖动（`deck-deal-flyin.md:22`、`outro-group-photo-launch.md:27`）。
- SVG `feTurbulence` 的 `seed` **必须写死**（`print-texture-transitions.md:24`）。
- **不跨帧累积状态**：拖拽层级用 `lagged()` 采样 `frame − delayFrames`，而非有状态模拟（`helpers/motion.ts:21-32`）。
- **工作台兼容**：不读 `useVideoConfig().durationInFrames` 做绝对时间假设（`workbench.md:102-103`）。
- `<Sequence>` 会 rebase `useCurrentFrame`；配合 `CameraMotionBlur` 内部 Freeze 会让 PageCam 采样错帧 → **绝对帧编排的镜头给 PageCam 传 `frame` prop**（`deck-deal-flyin.md:42`、`PageCam.tsx:38-44`）。
- 三个 Motion 系 demo（`glass-pill-dictation-typing` / `chip-grid-single-select-blackout` / `pill-chip-slot-cycle-handled`）挂载时用 `useLayoutEffect` 实测文字宽度：**跨平台字体回退不同会导致宽度整体漂移**，介意可把实测值写死（`demos/README.md:57-62`）。

### 4. 画质与可读性（最常返工的点）

| 症状 | 根因 | 先查什么 |
|---|---|---|
| 3D 推进下文字发糊 / 有像素方块 | Chromium 对 3D 合成层按 1920 布局宽栅格化再 GPU 放大（先降采样后放大必糊） | **先查纹理源分辨率链路**（截图倍率 → 栅格化路径 → 缩放方式），最后才考虑相机。DoF 只做氛围，**永远不是清晰度的解法**（实证无效）。解法 = 全页 2x + CSS `zoom`（布局级放大）+ hero 元素单独 4x 截图，三件缺一不可（`aesthetic-rules.md:52-61`、`PageCam.tsx:99-115`、`TEMPLATE.md:88-89`） |
| 有效字高不足（手机小窗读不清） | 只按代码 `fontSize` 判断，忽略祖先 `scale` 与透视压缩 | 逐帧量**渲染帧上的实际像素**：字幕 ≥56px（推荐 60 档）、辅助 ≥32px；有效字高 = `fontSize × 全部祖先 scale × cos(rotY)`。文字只有「纹理」或「要读」两态（`aesthetic-rules.md:103-106`） |
| `Caption.tsx` 作为主字幕太小 | 组件默认 `fontSize: 22` 属「信息条」风格 | 作叙事主字幕须提到 56–60px 档；沿用 22px 属 Q11 的有意识违反，**必须写进项目说明**（`Caption.tsx:11-13`） |
| 光效廉价感 | glint/泛光群发；光溢出圆角 | 单点、给主角、每镜最多一次；必须被 `border-radius`/`overflow` 裁剪。**批量元素入场靠运动本身，不靠逐个发光**（`aesthetic-rules.md:68-71`） |
| 飞入元素悬空看着假 | 终点不是页面布局真实槽位 | 元素必须落进真实槽位（嵌入、归位、排进滚动流）；用 `layout.json` 坐标（`aesthetic-rules.md:93-96`、`pipeline.md:265-266`） |
| 相机抖动 | 默认加了 handheld shake | 亮场 UI 宣传片**禁用** handheld shake；相机噪声只在暗场氛围片明确追求纪实感时用极小值（暗场片保留 0.02 未被投诉）（`aesthetic-rules.md:63-66`、`pipeline.md:260`） |
| 节拍性抖动（镜头随音乐抖） | 把 kick→冲击映射执行成逐拍全画面泵 | R4：全画面/相机层冲击**全片 ≤3 处**、相邻 ≥16 拍、钉最强 hit 清单；节拍泵单次 ≤4 拍且全片 ≤1 次；**计数单位是一次手法/set-piece 使用，不按内部子事件数**（`aesthetic-rules.md:38-41`、`music-beat-sync.md:93-97`、`:182-191`） |
| 收尾保守 | 初版几乎总是偏保守 | Q8：起稿就按「像一个产品发布」的规格给足 crane/舞台光/粒子（`outro-group-photo-launch.md:34`） |
| 开场平庸 | 多卡群舞撑不起第一印象 | Q5：单主角 + 完整动作弧（聚光→推近→悬浮→描边光→归位），锁定→落地 ≈3.3s（`spotlight-hero-card.md:27`、`:35`） |
| 节奏过快 | 首版几乎总是偏快 | R3：初版默认放慢一档；**排时间线时先划走 hold/rest 帧再排动效**（品牌字标 ≥30f、批量收尾 ≥15f、开场主体动作 ≥3s）（`aesthetic-rules.md:33-36`、`promo-energy-arc.md:31-32`） |
| 参考图被全局套用 | 把一张参考图当全片风格令 | P2：先逐帧拆解成手法清单（「手法｜参考片实现｜取舍」三列表），逐镜头判断适配性（`aesthetic-rules.md:174-177`、`pipeline.md:74-78`） |
| 纹理里烤入的排版细节穿帮 | 遮罩没多盖圆点等细节 | `li` 圆点需遮罩向左多盖 28px（`::marker` 在文本左 ~22px）（`document-typewriter-reveal.md:25`） |
| 白底上「提亮」不可见 | 白卡上 brightness 提亮等于没做 | **加深才可感**——改深色叠层脉冲；同理亮线在浅色区靠黑描边、深色区靠白核（`crane-rise-reveal.md:25-26`、`wipe-transitions.md:37-38`） |
| 演示版参数当定稿 | demo 在灰阶/占位素材上调校通过 | 多张卡的「已知坑」首条即此：**参数是调校起点非实战定稿，首次实战须以真实素材回验**（`crane-rise-reveal.md:37`、`gauge-readout-moves.md:34`、`wipe-transitions.md:35`、`odometer-digit-roll.md:42`） |

### 5. 声音与音画对齐

- **声音必须排在画面锁定之后**；任何改变镜头时长/顺序的修改，收尾动作固定包含「全表 SFX 帧号重对」（S3）。模板片三次重钉中**两次纯属画面返工的连带成本**（`sound-design.md:270-280`）。
- **钉帧一律相对 shot 起点**（`SHOTS.x.from + offset` 或 `beatF(n)`），绝不写裸数字帧号（`sound-design.md:282-286`）。
- **长样本（>5s，21 个）必须显式给 `durationInFrames`**，否则照 90f 默认值会拖到动作结束后还在响；带长尾混响的 impact 例外，让尾音自然衰减（`sound-design.md:187-213`）。
- **`volume` 是乘法系数不是目标音量**：常规 0.2–0.6 的前提是素材峰值贴近 0dB；7 个轻音素材（峰值 <-12dB，最轻 -24.6dB）给到 1.0 仍会被 BGM 盖住（`sound-design.md:215-236`）。
- **预览会把 `volume` 钳到 1.0**（`Math.min(volume, 1)` 只出现在传统 `<audio>.volume` 回退路径）——**预览听到的可能比成片轻，必须以渲染产物为准判断**，并查 `max_volume` 防削波（`sound-design.md:238-242`）。
- **音画对齐两项偏移必须都补**：输出音轨偏移（AAC priming，48kHz 典型 ≈1.28f，实测 click 2032 / impact 2066 samples）+ 音源峰值滞后（逐文件量）。都不补时最重一击晚 **0.27s**；卡点片差 2–3 帧就足以让合理卡点动效被读作无端抖动（`sound-design.md:288-357`、`aesthetic-rules.md:141-144`）。
- **偏移常数不可跨管线搬运**：由 Remotion 版本 + codec + sample rate + 容器四要素决定（`sound-design.md:308-315`）。
- **`SOURCE_BEAT0` 永不掺入渲染偏移**——源分析值是审计真值与审计基准，混入渲染偏移会在换 codec/重新分析时造成二次补偿（`music-beat-sync.md:227-244`）。
- **计数误差与视觉量化误差分开报**；30fps 交付不要声称 <5ms 的视觉精度（30fps 取整上限 ±16.7ms）（`music-beat-sync.md:198-207`）。
- **`sfx/ui/` 逐个试听、不能整目录放行**；`sparkle` 的目录名是 `light/`；`glass/` 不在禁列（见 C9）。
- **4 对同素材重名文件（字节相同）不能用来做「双样本交替」**——交替等于没换音，机枪感照旧（`sound-design.md:129-141`）。

### 6. 性能与耗时

| 项 | 数据/提示 | 依据 |
|---|---|---|
| `@remotion/motion-blur` 的 `samples` | **每 +1 约 +1 倍渲染时间**；`shutterAngle > 270` 发糊 | `deck-deal-flyin.md:30` |
| CameraMotionBlur 的包裹范围 | **只包快速段**（≥30px/f）；慢速特写段（<10px/f）包了会把 1px 级细纹理（拉丝金属）采样抹软；30fps 下相机每帧跳 50–70px 会频闪 | `deck-deal-flyin.md:30` |
| 并发 | `remotion.config.ts` 设 `setConcurrency(4)`；低核无头机需 `--concurrency=1` | `template/remotion.config.ts:6`、`README.md:162-163` |
| 首帧冒烟渲染 | 脚本逐个 `remotion still --frame=0`，全量遍历所有带时长导出的 demo | `smoke-render-demos.py:95-109`、`:145-154` |
| 工作台首次启动 | 自动 `npm install`（一次性，约 1 分钟） | `workbench.md:17` |
| 工作台 3D 层实时预览 | Player 是实时合成，巨型平面程序渐变/`backdrop-filter` 放在每帧改 `zoom` 的 3D 层里，Chrome 栅格化跟不上会整块时有时无（Ink Press 模板 S3 金属桌面曾疯狂闪）→ 用 `getRemotionEnvironment().isRendering` 分流，预览用更轻替身，几何与时序不变 | `workbench.md:105-110` |
| 3D 纹理内存 | `card4-hires.png` 123KB、`detail-experiments.png` 3.26MB、`projects-full.png` 618KB、`wbr-full.png` 488KB（2x 整页纹理）；大页纹理与 4x 元素特写同时驻留会增加内存与栅格化压力 | 实测 `template/public/textures/live/` 文件大小 |
| 渲染成本策略 | 「静帧足够定调」——阶段 1 明确**不渲染视频做风格提案，太贵**；实际形态是「改哪个镜头就 still 哪几帧，然后整片重渲，成本可接受且杜绝接缝意外」 | `pipeline.md:109-110`、`:226-229` |
| 音效工作的时间成本 | 模板片音频工作直到画面改了约 30 轮之后才开始；三次重钉中两次是画面返工连带成本 | `sound-design.md:26`、`:270-280` |

### 7. 数据安全与合规（硬门槛）

- **公开演示数据只有在产品简报明确确认后才可保留**；客户、个人、内部、密钥、实时或其他敏感数据**必须先虚构、脱敏或冻结**，且在采集前冻结（`SKILL.md:97-100`、`aesthetic-rules.md:47-50`、`pipeline.md:51-52`）。
- **复刻既有页面必须用真实截图**；手搓 UI 限非复刻场景，且质量（出版级）与表达明确性是硬门槛，达不到就回截图路线（`aesthetic-rules.md:47-50`，2026-07-13 用户裁决把判例收窄为「不用手搓复刻既有页面」）。
- **文档/报告类镜头的 mock 必须出版级**：产品原生排版、文字铺满、侧栏/评论栏完整入镜；mock 内容里**绝不出现客户/成员真名**（Q10、`document-typewriter-reveal.md:35-36`）。
- **截图前必须先注入假数据**（`capture-template.mjs:15-17` 标为【红线】）：空库 / lorem ipsum 截出来的图直接废片；真实客户数据则不能出片。
- 模板的截图素材来自一个内部研究管理工具（数据为虚构演示数据）——**对外分发成片前务必整套替换为目标产品自己的截图**（`TEMPLATE.md:58-59`）。
- 终检 D 组专门查这条（D1–D5），且**未经确认的数据属于终检失败**（`final-review.md:73-80`、`pipeline.md:400-401`）。

### 8. 资产使用与工程组织

- `assets/lib/` 组件 **copy 进新项目后自由修改（不 import 本库）**（`SKILL.md:226`）。
- **必须读准确 demo 源码**：配方卡给的是语义和参数表，demo 才是调校过的参数真相（缓动、时值配比、摘罩时机、已知坑的规避写法）；**凭卡名和理解新写＝放弃全部调校积累，实测质感差一档**（`SKILL.md:136-142`、`pipeline.md:216-219`）。
- 卡上「已知坑/命门」标注的参数**不得降档**——质量标准只升不降（`pipeline.md:217-218`）。
- **`gallery/media/` 目录为空**（mp4 不入 git）——本地看样片先跑 `gallery/fetch-media.sh`，或直接用在线版 `https://vincentwei1021.github.io/video-shotcraft/library.html`（`SKILL.md:261-264`）。
- **`implementationStatus` 当前全库为空**：`sync-from-cards.py:17-20` 的 `STYLE_STATUS = {}`，注释明确「every style has demo source」——`pipeline.md:214-215` / `guided-free-creation.md:156-158` 描述的「仅供参考」「缺少预览」两类标注**当前不触发**，校验时不要假设存在。
- **卡片文件数与文档口径**：`references/shots/**/*.md` 实测 157 张（与 `library.json.stats.cardCount`、`SKILL.md:8`、`README.md:177` 一致）；`assets/audio/sfx/` 实测 **149** 个（`-Recurse -File`，与文档一致；原文「151」为把类别目录计入的误计，见开篇校正 1）。
- 改动卡片后必须重跑 `gallery/sync-from-cards.py` + `gallery/build-seo.py` 并 commit，否则 PR 的 artifact gate 失败（`pr-checks.yml:45-58`）。
- `标签:` 字段的值必须是 `CATEGORIES` 的键，否则 `sync-from-cards.py` 硬失败（`:96-99`）。
- 每个改动保持独立 commit 以便干净回滚；改错立即整 commit revert，不在错误版本上打补丁（P3、`pipeline.md:238-240`）。

### 9. 本仓库未找到 / 未验证的事项（如实列出）

| 事项 | 状态 |
|---|---|
| `--scale` 的推荐用法与推荐值 | **未找到**——仓库文档与脚本中均无 `--scale` 出现 |
| 竖版（9:16）或其他非 1920×1080 的工程、配方卡、示例 | **未找到**——`gallery` 与 `template` 全部以 1920×1080 标定 |
| `package.json` 中的 Node `engines` 声明 | **未找到**——仅 CI 与 README 用 Node 22 |
| 模板工程内的 `bgm` inputProp 实现 | **未找到**——`template/src/Root.tsx` 只有 `theme` 默认 props，`Main.tsx` 无 BGM `<Audio>`；模板为 SFX-only 版 |
| `references/sequences/` 的其他桥段模板 | **未找到**——该目录只有 `promo-energy-arc.md` 与 `.gitkeep` |
| 逐文件时长/峰值的完整原始清单 | 存在但未逐条誊抄——见 `assets/audio/AUDITION-2026-07-27.md`（36,903 字节） |
| `impact-cine.mp3` 在 `assets/audio/` 中的存在性 | **已删除**；`template/public/audio/impact-cine.mp3` 的独立副本仍在（模板照常渲染）；等价文件是字节相同的 `sfx/impact/impact-deep-whoosh.mp3`（md5 `ce27fd2f`） |
| 渲染单支视频的实测耗时数字 | **未找到**——仓库仅给出 motion-blur `samples` 的倍数关系 |
| `windows_draft.py`（剪映导出）的真机验证 | **未验证**——`SKILL.md:257-258` 明确「按上游支持路径实现，未真机验证」 |

---

*手册结束。所有行号引用基于撰写时的仓库快照；若文件被后续编辑，行号可能漂移。*

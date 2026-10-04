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
   git log --oneline -15        # 逐条核对上一批的 commit 是否都在
   git status --short           # 工作区干净（除 .env）
   ```
2. 确认后，**用新的指令组替换全文**，而不是在末尾追加。
3. **不要累积历史指令组** —— 已执行的指令没有留存价值（`git log` 才是历史）。

> 本项目历史上曾累积到 **34 组 / 700+ 行**，其中 33 组早已执行完。
> 这条机制的完整说明在 [guides/00_dev_principles.md](guides/00_dev_principles.md) §5.1。

## ⚠️ 分组时最容易踩的坑：`git add <file>` 是**文件级原子**

```
git add src/x.py   →  提交 src/x.py 的**全部**改动
```

**后果**：如果一个文件在**多个功能组**里都被改过，按文件 add 会把**后面的改动连带提交**进前一组。

**实测踩过**：第 44 步（中文数字规范化）的 `git add` 列表里有 `src/videogen/validate.py`，
而该文件后来又被加进了「多样性兜底 `_enforce_variety`」——
结果 `_enforce_variety` 被**连带提交进了数字规范化的 commit**（`b7a5863`），
commit message 与实际内容不符，事后无法拆开。

**规避办法（二选一）**：

| 办法 | 做法 | 代价 |
|---|---|---|
| **按文件边界切组**（推荐） | 一个文件**只出现在一组**里；同一文件的多处改动**合并成一组**提交 | 组会变大一点 |
| 用 `git add -p` | 交互式挑选 hunks | 人工成本高，且本项目的指令是给自动化执行用的 |

> **所以写指令前先问自己**：这个文件在别的组里也出现过吗？
> 出现过 → 要么合并成一组，要么等前一组提交完再改这个文件。

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
git diff --cached --name-only                                          # 反查有没有漏项 / 误加
git diff --cached --name-only | Select-String '\.(png|wav|mp3|ttf|mp4|jpg)$'   # 应为空
git diff --cached --stat | Select-Object -Last 1
```

> ⚠️ **素材入库原则**：大文件不入库，索引与元数据入库。
> `.gitignore` 的 `*` **不跨目录** —— 新增素材目录结构时必须单独补规则。
> 本项目已有规则：`assets/sets/*/images/*.{png,jpg,jpeg,webp}` 与
> `assets/sets/*/audio/*.{wav,mp3}`。可用 `git add --dry-run <目录>` 先验证。

---

## 待执行（4 组）

### 第 49 步：镜头类型 13 → 21（扩动效选择空间）

```powershell
git add src/videogen/spec.py
git add src/videogen/compile.py
git add remotion/src/shots/ShotRenderer.tsx
git add remotion/src/shots/IconGrid.tsx remotion/src/shots/QuoteCard.tsx
git add remotion/src/shots/StepsList.tsx remotion/src/shots/ComparisonTable.tsx
git add remotion/src/shots/LayerStack.tsx remotion/src/shots/ProgressMeter.tsx
git add remotion/src/shots/KeywordHighlight.tsx remotion/src/shots/ImagePair.tsx
git add tests/test_plan.py
git commit -m "feat(shots): 镜头类型 13 → 21，补 8 个内容形态

用户反馈「两个视频里由视频文案生成的分镜类型相同」。

**根因（实测数据）**：卡库 157 张与可落地 type 21 个**只有 1 个同名交集**
（只有 timeline-travel）。也就是说 brand-ink-open 这类卡名不是合法 type 值，
把 157 张卡名列给模型看，等于递一份「看得见、选不了」的清单。
模型的选择空间实际只有几个 type，其中图文类原本只有 3 个
（figure-panel / stat-compare / flow-diagram）——
所以任何文章的图文镜头组合都必然雷同。

补的 8 个各自对应一种**内容形态**（不是「再多几个好看的动效」）：

  icon-grid          并列枚举（无序多项）
  quote-card         单句论断 / 结论
  steps-list         有序步骤（带编号）
  layer-stack        分层架构（自下而上）
  comparison-table   多方案逐项对比（3 项以上）
  progress-meter     部分 vs 总体（覆盖率）
  keyword-highlight  长句里的关键词逐个点亮
  image-pair         两图并排（素材类缺口）

字段一律**复用**现有结构（bullets / nodes / sides / metric / eyebrow / footer），
只有 image-pair 需要一个新字段 image2。

**顺带修掉一个会让 image-pair 静默失效的 bug**：
compile.py::compile_shot 是逐字段手写的，加了 image2 到 spec.py 和 to_dict
却漏了它 —— 后果是 spec 校验能过（REQUIRED_FIELDS 有 image2）、
但传到 Remotion 的 props 里没有 image2，镜头退化成单图。
现已按 image 的同一套路径口径补上。

test_plan.py 同步：catalog 的断言从「含卡元数据表格」改为
「列可落地 type、且**不含卡名**」——这条断言专门守住不再列卡名。

验证：pytest 142 passed；tsc --noEmit 0 错误；
remotion compositions 打包成功（整个模块图含 8 个新组件可被打包）。"
```

### 第 50 步：补上「被引用却不存在」的跨语言契约测试

```powershell
git add tests/test_spec_parity.py
git commit -m "test(contract): 补上 spec.py 注释引用了却不存在的契约测试

spec.py 第 24 行的注释从很早就写着「一致性由 tests/test_spec_parity.py 强制」，
但该文件**实际不存在**（全工作区搜索无果）。注释与仓库现状不符比没有注释更危险 ——
它让人以为有一道防线，其实没有。

它守的是一个**真实踩过的坑**：TS 端加过 3 个图文类型却忘了同步 Python 侧，
于是脚本一生成 figure-panel 就被校验器拒绝（见 docs/issues/006）。

做法是**直接解析 TypeScript 源文件**（不跑 node），把两侧权威定义摆在一起比：

1. TS 的 ShotType 联合 == Python 的 SHOT_TYPES（**含顺序**）
2. REQUIRED_FIELDS 的键集 == SHOT_TYPES
3. 两侧都无重复项
4. REQUIRED_FIELDS 用到的字段名都能在 TS ShotSpec 接口里找到
5. TS ShotSpec 有 image2（image-pair 依赖）
6. ShotRenderer 为每个 type 都有分支（少一个 case 不是编译错，而是运行时画不出来）
7. 每个 type 都有对应组件文件（kebab-case → PascalCase）
8. 素材类类型必须要求 image

为什么解析源码而不是比对生成物：生成物会过期，源码不会 ——
两边**同时**改才可能一致，这正是要守的东西。

验证：该文件 14 passed；全量 142 passed。"
```

### 第 51 步：素材集索引与字幕更新

```powershell
git add assets/sets/omni-io-skills/images/index.json
git add assets/sets/omni-io-skills/audio/omni-io-skills.asr.srt
git add assets/sets/h3-world
git add assets/sets/spark-x2
git commit -m "chore(assets): 素材集索引与字幕更新；新增两套素材集

- omni-io-skills/images/index.json：改用视觉模型自动标注重生成
  （提示词策略是实测出来的：**问「描述这张图」会泛泛而谈甚至编造，
   问「照抄图里最显眼的文字标签」则准确得多** —— 所以要求先抄录再判断用途。
   03 图抄到 9 个标签全对；专有名词也从误读的 Omni-10 修正为 Omni-IO）
- omni-io-skills.asr.srt：数字规范化 + 逐字母缩写保护后重切
  （「百分之四十六」→「46%」；「W A S D」不再被切成三段）
- 新增 assets/sets/h3-world 与 assets/sets/spark-x2 两套素材集
  （只入库 set.json / images/index.json / *.srt / asr_*.json）

**大文件不入库**：png/jpg/wav 由 .gitignore 挡住
（assets/sets/*/images/* 与 assets/sets/*/audio/*，已用 git add --dry-run 验证）。

顺带删除遗留的临时文件 assets/sets/omni-io-skills/images/index.manual.bak.json。"
```

### 第 52 步：闭环技术路线（下一阶段的路线图）

```powershell
git add docs/plan/02_closed_loop_roadmap.md memory/project.md
git add docs/git_commands.md
git commit -m "docs(plan): 闭环视频生成路线图（下一阶段）

用户问：「为什么你直接生成的视频效果就很好，通用性也很高，
但是通过脚本生成的质量就差很多呢？」

**根因**：不是模型好坏，而是**闭环 vs 开环**。
- 手工做时有视觉反馈闭环（渲染 → 看图 → 改 → 再渲染，3–8 轮），每轮都有像素级反馈；
- 现有脚本是开环（LLM 纯文本规划 → 渲染 → 直接交付），**没有人看过结果**。

文档拆解了六个技术维度差距，并给出最尖锐的证据 ——
spark-x2 的 scan-annotate 标注框是 LLM **闭着眼睛猜**的：
x=0.05 w=0.9（占满宽）+ y=0.2/0.55/0.75（等距三行），连 y 顺序都是乱的。
这是「文本模型想象一张图」的典型形状 —— 根子在**模态不匹配**：
让语言模型输出像素坐标，等于让它闭着眼睛画地图。

五条技术线路（按投产比排序）：
① 渲染后自动视觉质检闭环（核心，结构性地复制「看」的能力）
② VLM 规划（让规划器能看图）
③ 坐标交给 VLM（别让文本 LLM 猜 bbox）
④ 组件参数暴露给 LLM（现有 11 个 TUNE 旋钮对 LLM 不可见）
⑤ 扩模板（边际收益最低 —— 没人看渲染结果，模板再多也是闭眼画）

文档含：独立实现的目录结构建议、**最小可验证路径（5 步顺序）**、
环境与硬约定（含 TMP/TEMP 与 MiniMax base_resp 两个会白费半天的坑）、
验收标准、测试用文章路径。

memory/project.md 在「Round 11 续」之前插入「下一步」章节指向该文档，
保证新对话读 memory 第一眼就能接上。"
```

---

## 当前状态

| 项 | 值 |
|---|---|
| 已提交 commit 数 | 45 |
| 分支 | `opt_deliver` |
| 待执行的指令组 | **4 组（第 49–52 步，见上）** |
| 工作区待提交 | 6 个已跟踪文件改动 + 12 个新文件（含 2 个素材集目录） |
| 已执行完毕 | 第 35–48 步（14 组，已全部落库，本文件已清空它们） |

### 一处历史遗留，仅记录不改写

`b7a5863`（"中文数字规范化"）的提交内容里**混进了** `validate.py` 的
`_enforce_variety`（多样性兜底）—— 那是同一文件在**后续功能组**里的改动，
被下一步的 `git add src/videogen/validate.py` 连带提交了。

**不要求改写历史**（已推送/已建立的 commit 改写风险大于收益）。
把这条记在这里是为了提醒：**分组时注意「文件级原子」这个坑**（见上文）。

### 下一步（不在本文件的提交范围）

按 [docs/plan/02_closed_loop_roadmap.md](plan/02_closed_loop_roadmap.md) 做**独立的闭环实现**。
**新对话从这里开始**。

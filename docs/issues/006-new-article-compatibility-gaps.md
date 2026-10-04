# 006 — 换一篇文章暴露的 6 个兼容性缺陷

> **这份文档是一次"易用性验证"的产物。** 任务是用现有的脚本，拿一篇**从未见过**
> 的新素材（`20261004` Omni-IO Skills）生成短视频，检验程序能否直接复用。
>
> 结论：**主干能跑通，但暴露出 6 个真实缺陷**，其中 4 个是「改了 A 没改 B」型不一致
> 或「为单一素材写死」型假设。逐条记录，因为这类缺陷**单元测试全绿也照样存在**。

## 缺陷 1（严重）：TS 加了镜头类型，Python 契约没同步

**现象**：脚本生成 `figure-panel` 时校验器直接抛错：

```
SpecValidationError: 镜头 2 的类型不在封闭集合内 / unknown shot type: 'figure-panel'
可用类型 / available: title-reveal, page-spotlight, ... outro-lockup
```

**根因**：前一轮我在 `remotion/src/compositions/types.ts` 的 `ShotType` 联合里加了
`figure-panel` / `stat-compare` / `flow-diagram` 三个类型，还写了三个组件、
注册了分发 —— 但 `src/videogen/spec.py` 的 `SHOT_TYPES`、`REQUIRED_FIELDS`、
`ShotSpec` 字段、`compile_shot`、`to_dict`/`from_dict`、system prompt **全没动**。

于是「Remotion 端认识这三个类型」而「规划端不认识」，链路中间断了一截。

**为什么单元测试没发现**：`tests/` 里的 spec 全部用旧类型构造；
新类型的测试根本没写。**测试只覆盖它自己声明的东西** —— 新功能没测试，
就等于没验证过它与旧契约的一致性。

**修法**：
1. `spec.py`：补 `SHOT_TYPES`、`REQUIRED_FIELDS`、`ShotType`、`ShotSpec` 的
   `eyebrow`/`footer`/`bullets`/`nodes`/`sides`/`metric` 字段，以及
   `ShotNode` / `ShotSide` 两个 dataclass
2. `compile.py`：`compile_shot` 输出这些字段，否则渲染出来是空壳
3. `to_dict` / `from_dict`：手写序列化必须逐个字段补 —— **漏一个就静默丢数据**
4. `system.md`：字段表、JSON 模板、篇幅约束
5. `tests/test_pipeline.py`：补 `test_compile_shot_emits_figure_fields`

**预防**：TS 与 Python 的类型定义是**同一份契约的两个副本**，靠人记必然漏。
后续应加一条测试直接解析 `types.ts` 的 `ShotType` 联合，与 `SHOT_TYPES` 比对 ——
这是唯一能真正锁住一致性的办法。

## 缺陷 2（中等）：写死的帧数只对老素材成立

**现象**：`Root.tsx` 的 4 个 Composition 把 `durationInFrames` 写死成
1490（短视频）/ 4665（中视频）。新素材音频是 **48.16s = 1445 帧** ——
用写死的 1490 会多出 45 帧，片尾是黑屏。

**根因**：帧数写死在 Composition 上。它只在「本项目最早两套素材」这个前提下成立，
一旦换文章就不成立。

**修法**：新增两个**通用 Composition**（`SetLandscape` / `SetPortrait`），
用 `calculateMetadata` 从 props 读 `durationInFrames` 与 `fps`；
`compile_props` 输出这两个字段。这样**一个 Composition id 服务任意素材集**，
不必每篇文章都新增注册项 —— 这是脚本化量产的关键。

`FilmProps` 同步加 `durationInFrames?` / `fps?` 两个可选字段。

## 缺陷 3（轻）：脚本硬编码素材名 + 重复导入

**现象 A**：`scripts/plan.py` 的 `SOURCES` 把素材文件名与标题写死，
换文章必须改代码。

**现象 B**：`import_article.py` 不传 `--name` 时，素材集名由目录名推导；
`slugify(max_len=32)` 把中文长名截断，推导出
`Omni-IO-Skills开源-Harness让Agent兼容`，而首次是用 `--name omni-io-skills` 导入的 ——
**同一个素材目录产生了两个名字**，于是静默导入出两套素材。

**修法**：
1. 新增 `videogen/sources.py`：素材集抽象（`AssetSet` / `load_set` /
   `import_from_article` / `list_sets`），素材**按目录发现**而不是写死
2. `slugify` 的 `max_len` 提到 64（中文信息密度高，32 太短）
3. `find_set_by_source()`：按 `set.json` 里记录的来源路径去重 ——
   同一篇文章**永不重复导入**
4. `plan.py` / `asr_subtitles.py` / 新增 `render_set.py` 全部支持 `--set`

**顺带修的接口不一致**：`LegacySource.images_index` 一开始写成了方法，
而 `AssetSet.images_index` 是属性 → `TypeError: 'WindowsPath' object is not callable`。
两个类实现了同一个协议，**同名成员的类型必须一致**。

## 缺陷 4（轻）：`_relayout` 引入的收敛顺序坑（已在前一轮修）

不属于本轮新发现，但本轮又被验证了一次：5s 上限的切分与卡数收敛会互相打架，
`_converge_shot_count` 甚至会把刚切好的镜头合并回超 5s。
现在的顺序是 `迭代{relayout ⇄ split} → converge → resequence`，
且**合并只在结果仍 ≤5s 时才做**，否则主动放弃并留痕。

## 缺陷 5（中）：来源标注写死在共享组件里

**现象**：新素材的成片右上角仍显示 **上一篇文章** 的来源
`Science Robotics · Tsinghua × ByteDance Seed`。

**根因**：`FilmShell.tsx` 把来源标注写死在 JSX 里。所有视频都共用这个 shell，
所以换素材后它照旧显示旧来源 —— **画面在说"这是清华那篇"，而旁白在讲 Omni-IO**。

**为什么难发现**：它不是崩溃，也不是类型错误，只是一个**静默的错误信息**。
只有把新素材的成片抽帧出来看才会注意到。

**修法**：
1. `FilmProps` 新增 `source?`
2. `FilmShell` 从 props 取，为空则不渲染（不编造）
3. `AssetSet` 新增 `source_label`（**给观众看的短标注**，与 `source`
   这个"素材来源目录"是两回事），从 `set.json` 读
4. `compile_props` 依次回退：`asset_set.source_label` → 分镜里的 `source` → 空
5. 导入时用 `_derive_source_label()` 从 `meta.json` 的 URL 推导
   （arXiv 链接 → `arXiv:2609.31847`）
6. 单测 `test_compile_props_source_label_prefers_asset_set`

## 缺陷 6（严重）：镜数不足 → 镜头被切分 → 同一画面重复播

**现象**：新素材第一版成片里，同一个画面**重复出现两到三次**：

```
[3] figure-panel  三层技能，七种模态      ← 同一文案
[4] figure-panel  三层技能，七种模态      ← 重复
[5] figure-panel  三层技能，七种模态      ← 重复
[6] flow-diagram  四层解耦，按依赖分波跑   ← 同一文案
[7] flow-diagram  四层解耦，按依赖分波跑   ← 重复
[8] flow-diagram  四层解耦，按依赖分波跑   ← 重复
```

8 个镜头里有 5 个被切成多段，13 镜里只有 8 个是"新内容"。

**根因链**：
1. 音频 48.16s = **1445 帧**
2. 单镜上限 150 帧 → **至少需要 10 镜**（⌈1445 ÷ 150⌉）
3. 但旧 prompt 的 `constraints` 把 `shot_count` 告诉成 **5–6 镜**（来自素材集体系之前的常量）
4. 模型遵守 5–6 镜的"建议"（实际给了 8 镜，已算配合）
5. `_relayout` 必须把这 8 镜撑满 1445 帧 → **每镜 ≈180 帧**
6. 超过 150 帧 → `_split_long_shots` **切分**
7. 切分是**复制内容**（有意设计：总时长由音频锁定，多出的时间只能变成更多镜头）
   → 于是同一画面播多遍

**这是一个规格冲突，不是编码错误。** 修复必须让**规划端**知道节奏下限：

**修法**：
1. `planner.build_user_prompt`：算 `min_for_pacing = ceil(total_frames / 150)`，
   `shot_lo = max(区间下限, min_for_pacing)`，`shot_hi = max(区间上限, shot_lo + 3)`
   —— **留 3 镜余量**，因为总帧数不可能整除，均摊总会把某些镜推高一点
2. `constraints["shot_duration_max_frames"]` 从 **700 改成 150**（与
   `validate.MAX_SHOT_FRAMES` 对齐 —— 之前两边不一致，模型以为可以给 700）
3. `system.md`：加自检公式 `镜数 ≥ ceil(total_frames / 150)`，
   并明确写清"镜数不足会导致同一画面重复播"

**效果对比（同一素材、同一模型）**：

| | 修复前 | 修复后 |
|---|---|---|
| 模型规划镜数 | 8 镜 | **11 镜** |
| 被迫切分 | 5 镜被切 → 13 镜 | **0 切分** |
| 同一画面重复 | 有（8 镜里 5 镜重复） | **无** |
| 用到的镜头类型 | 3 种 | **7 种** |
| 修复记录 | 6 条 | 2 条（均不涉及切分） |

**这条最有价值的地方**：它说明**「切分」这个兜底机制会把「规划错误」转译成「观感缺陷」**。
兜底保住了时长与节奏，但代价是内容重复 —— 所以**兜底不能替代正确的规划**，
必须把约束前移到 prompt。

## 验证结论

| 检查项 | 结果 |
|---|---|
| 素材导入（一篇全新文章） | ✅ 一行命令；标题/副标/口播/图片自动提取 |
| 图片语义索引 | ⚠️ 需人工补（抓取元数据 caption 全为 null，无法自动） |
| ASR 重切字幕 | ✅ 48.16s → 22 条，平均 1.89s / 12.5 字 |
| LLM 规划 | ✅ 一次通过，4.6s，**用上了全部 3 个新图文类型** |
| 校验与节奏约束 | ✅ 8 镜 → 13 镜（5s 上限），总帧 1445 精确 |
| 渲染 | ✅ 两个方向均出片 |

**净结论**：主干可复用，但「加新镜头类型」这个动作**跨了 3 个语言/5 个文件**，
是最容易漏的地方。见缺陷 1 的预防措施。

## 复发预防清单

| 触发动作 | 必须同步的地方 |
|---|---|
| 新增一个镜头类型 | `types.ts`（TS 联合）· `spec.py`（`ShotType`/`SHOT_TYPES`/`REQUIRED_FIELDS`/`ShotSpec`）· `ShotRenderer.tsx` · `compile_shot` · `to_dict`/`from_dict` · `system.md` · 单测 |
| 改动输出尺寸/帧数 | `compile_props`（从时间轴取）· Composition（用 `calculateMetadata`，**不要写死**） |
| 支持新素材 | 只放 `assets/sets/<name>/`，**不要往代码里加分支** |
| 改单镜时长约束 | `validate.py` 常量 · `spec_schema.md` §5 · `system.md` · `SHOT_COUNT_RANGE` 三处 |

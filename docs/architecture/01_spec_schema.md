# VideoSpec — LLM 输出契约 / The LLM output contract

> **什么时候加载**：写 LLM prompt、改 spec 结构、实现校验与编译时。
> 上游：[00_pipeline.md](00_pipeline.md) 阶段 2–3。本文件是 spec 字段的**唯一权威处**。

## 1. 为什么是这份形状

三条设计约束（都来自 [00_pipeline.md](00_pipeline.md) §1 的硬规则）：

1. **镜头类型封闭** → `shots[].type` 是枚举，不接受自由文本
2. **可校验** → 每个字段都能用纯 Python 判断合法与否，无需渲染
3. **可复现** → spec 落盘后，同 spec + 同素材必得同一支视频

## 2. 结构

```jsonc
{
  "version": 1,                       // 契约版本；结构变更必须递增
  "kind": "short",                    // "short" | "mid"
  "fps": 30,
  "durationInFrames": 1490,           // 由音频时长算出，LLM **不得**自己写
  "theme": "cyan-noir",
  "title": "清华团队登 Science Robotics",
  "subtitle": "视觉足球技能 · 误差降 46%",
  "total_seconds": 49.66,             // 冗余字段，供人工核对
  "shots": [ /* 见 §3 */ ],
  "repair_log": []                    // 阶段 3 写入；LLM 输出时必须为空
}
```

## 3. 镜头 / shots[]

```jsonc
{
  "type": "number-roll",              // 必填，枚举见 §4
  "from": 289,                        // 必填，本片内起始帧
  "durationInFrames": 349,            // 必填
  "caption_segments": [2],            // 必填，绑定的字幕段号（审计用）
  "text": "统一感知-运动强化学习框架",
  "subtext": "50 帧观测 → 64 维隐藏状态",
  "tagline": null,
  "metrics": [                        // number-roll / counter-burst 用
    { "label": "历史观测", "value": "50 帧" }
  ],
  "image": "05_mmbiz-qpic-cn.png",    // 相对 assets/images
  "targets": [                        // scan-annotate 用，归一化坐标 0–1
    { "x": 0.32, "y": 0.10, "w": 0.20, "h": 0.34, "label": "POLICY" }
  ],
  "stops": [                          // timeline-travel 用
    { "label": "2025", "note": "RoboCup 成人组冠军" }
  ],
  "source": "Science Robotics · RESEARCH"
}
```

### 3.1 各字段的硬约束

| 字段 | 约束 | 违反时的修复 |
|---|---|---|
| `from` | ≥ 0；与前后镜**不重叠**；首镜为 0 | 重排 `from`（按顺序累加） |
| `durationInFrames` | ≥ 最低时长（见 §5 表） | 裁剪/补足到合法区间 |
| `Σ durationInFrames` | 必须 == `durationInFrames` | 按比例微调末镜 |
| `caption_segments` | 段号必须存在于 Timeline | 丢弃该引用并记 repair |
| `image` | 必须存在于 `assets/images/index.json` | **降级为纯文字卡**（保留 type） |
| `targets[].x/y/w/h` | ∈ [0,1]；`x+w ≤ 1`、`y+h ≤ 1` | 钳制到边界 |
| `metrics` | `number-roll` 需 1–3 项；每项 `value` ≤ 8 字符 | 截断或丢弃多余项 |
| `stops` | `timeline-travel` 需 2–4 项 | 补/删到区间内 |
| `text` | ≤ 40 字（会渲成一行标题） | 截断 |

## 4. 镜头类型枚举与所需字段

| type | 必填字段 | 对应镜头卡 |
|---|---|---|
| `title-reveal` | `text`；可选 `subtext` | `letterspace-materialize` |
| `page-spotlight` | `image`；可选 `text` / `source` | `spotlight-hero-card` |
| `number-roll` | `text` + `metrics`(1–3) | `odometer-digit-roll` |
| `scan-annotate` | `image` + `targets`(1–4)；可选 `text` / `subtext` | `scanline-annotate-focus` |
| `radar-reveal` | `image`；可选 `text` / `subtext` | `spotlight-sweep-moves` C 式 |
| `counter-burst` | `metrics`(1)；可选 `text` / `subtext` | `counter-confetti` |
| `before-after` | `image`；可选 `text` / `subtext` / `metrics` | `before-after-slider-scrub` |
| `slow-push` | `image`；可选 `text` | `tension-camera-moves` C 式 |
| `timeline-travel` | `stops`(2–4)；可选 `text` / `metrics` | `timeline-travel` |
| `outro-lockup` | `text`；可选 `tagline` | `logo-shrink-wordmark-lockup` |

> 枚举的代码真源是 `remotion/src/compositions/types.ts` 的 `ShotType`。
> **两处必须同步** —— 加了新组件就要同时改这里和那份类型。

## 5. 卡的时长与卡数约束

| 项 | 约束 | 依据 | 校验器实现 |
|---|---|---|---|
| 短视频卡数 | **5–6** | 用户指定 | ⚠️ 见下 |
| 中视频卡数 | **8–10** | 用户指定 | ⚠️ 见下 |
| **单卡最小时长** | **45 帧（1.5s）** | 低于此读作闪切 | ✅ `_repair_duration` |
| **单卡最大时长** | **150 帧（5s）** | **用户明确反馈**：超过 5 秒节奏就明显变慢 | ✅ `_split_long_shots` |
| 首镜 `title-reveal` | 必须 | 片头字标 | ✅ 合并时受保护 |
| 末镜 `outro-lockup` | 必须 | 收尾 lockup | ✅ 合并时受保护 |
| 品牌字标 hold | ≥ 30 帧（1s） | 审美准则 R1 | ❌ 由分镜设计保证 |
| 批量动效收尾静止 | ≥ 15 帧（0.5s） | 审美准则 R2 | ❌ 由分镜设计保证 |
| 开场主体动作 | ≥ 90 帧（3s） | 审美准则 R3 | ❌ 由分镜设计保证 |

> ⚠️ **卡数区间的地位已下降。** 短视频分镜从 6 镜改到 **12 镜**（每镜 ≈4.1s），
> 因为「单镜 ≤5s」是硬约束而总时长由音频锁定 —— 只能靠增加镜数消化。
> 卡数区间现在只作为「LLM 规划时的建议目标」，**不再由校验器强制执行**；
> 校验器只在「合并后仍 ≤5s」时才合并（见 `_converge_shot_count`）。
> 内置分镜（`ShortFilm.tsx`）不走校验器，其镜数由分镜作者决定。

### 5.0 五秒上限优先于卡数上限

冲突时的处理优先级：

1. **总帧数 = 音频时长**（最高优先，否则音画不同步）
2. **每镜 ≤ 150 帧**：超了就**切分**成等长若干段（复制内容，不丢信息）
3. **卡数区间**：只在不违反第 2 条时才合并；否则**主动放弃**并留痕

```python
MIN_SHOT_FRAMES = 45            # 1.5s
MAX_SHOT_FRAMES = 150           # 5.0s ← 节奏旋钮
ABSOLUTE_MAX_SHOT_FRAMES = 700  # 硬护栏
SHOT_COUNT_RANGE = {"short": (5, 6), "mid": (8, 10)}   # 仅作规划建议
```

**收敛顺序（不可调换）**：

```
逐镜修复 → 迭代{ _relayout ⇄ _split_long_shots } → _converge_shot_count → _resequence
```

`_relayout` 会把余数**均摊**到所有镜头（不是塞给末镜 —— 那会造出 1000+ 帧的巨物），
`_split_long_shots` 负责切分，`_resequence` 在合并后做收尾对齐（**不再切分**，
否则镜数会立刻反弹）。

### 5.1 卡数超限怎么修（`_converge_shot_count`）

**合并相邻最短的一对，绝不丢镜头** —— 丢镜头等于丢旁白覆盖。策略：

1. 优先合并**内部相邻对**（不碰首末镜），因为首末镜有结构语义
2. 内部无可选对时才允许碰首末镜（卡数 ≤2 就超限的极端情况）
3. 合并时：
   - 时长相加
   - `caption_segments` 取**并集**（审计链完整：两段旁白由同一镜承载）
   - 文案用 `·` **拼接**，不静默丢弃（合并的代价是"两句挤一镜"，不是"一句消失"）
   - 缺的 `image`/`subtext` 从被并方继承，避免合并后画面变空
4. 合并只留痕、不重排帧号 —— 之后由 `_relayout` 统一归位

**卡数不足不硬凑**：凑镜头需要创作，不该由校验器瞎编。只记警告性修复，
否则「片子比预期短/空」会无从追查。

> ⚠️ **实测教训（这条规则就是这么发现的）**：卡数区间在本文档写了、
> system prompt 也告诉了模型，但校验器**漏了实现** —— 中视频真实调用
> 给出 **11 镜**（超出 8–10）却直接通过。
> **契约写了就必须有代码兜底**，否则文档只是愿望。

## 6. 阶段 3 的修复策略（按顺序尝试）

```
1. 时长越界      → 裁剪/补足到合法区间，并重排后续 from
2. 未知镜头 type → 报错（枚举错误不可猜测修复）
3. 素材不存在    → 该镜降级为纯文字卡（保留原 type 的版式退化为标题）
4. metrics 超量  → 截断到 3 项
5. 总帧数不符    → 按比例缩放各镜 duration，末镜吸收余数
6. 仍失败        → 退回内置兜底 spec（保证能出片），整条记入 repair_log
```

**每次修复必须写 `repair_log`**，格式：
```jsonc
{ "shot_index": 3, "field": "image", "problem": "素材不存在: 99_x.png",
  "action": "降级为纯文字卡" }
```

理由：成片能出来但和预期不符时，`repair_log` 是**唯一**能查明原因的东西。
没有它，这类问题会变成无法追查的谜。

## 7. LLM prompt 组织

```
plan/prompts/
  system.md      角色与硬规则（封闭镜头集、时间轴对齐、禁止编造数字）
  catalog.md     由代码从 shot_catalog 生成（不手写，避免与实现漂移）
  user.j2        把阶段 1 的结构化数据填进模板
```

**prompt 不在代码里拼字符串** —— prompt 需要人工反复迭代，
且要能对比不同版本的产出差异。

给 LLM 的输入（**不塞原始长文**）：

1. 口播分段的 `start/end/text` 列表（分镜的骨架）
2. 可用镜头卡清单（枚举 + 每卡参数 schema + 适用场景）
3. 可用图片清单（文件名 + 尺寸 + **人工语义标签**）
4. 视频参数：目标时长、方向、主题 id、fps
5. 硬约束：安全区、卡数上下限、每卡时长区间、禁止事项

**关键数字由阶段 1 抽好作为白名单**给 LLM，**禁止 LLM 自己从文本里「读」数字** ——
这是防数字错最有效的一条。

## 8. 校验实现位置

| 阶段 | 模块 | 状态 |
|---|---|---|
| spec 数据结构 | `src/videogen/spec.py` | ⬜ 待实现（B2） |
| 校验与修复 | `src/videogen/validate.py` | ⬜ 待实现（B2） |
| Python 侧类型镜像 | `remotion/src/compositions/types.ts` | ✅ 已有 |

实现时**两侧类型必须逐字段对齐**；不一致会导致「Python 校验通过但渲染缺字段」。

# 架构 — 生成流程 / prompt / script / workflow

> **什么时候加载**：工程化实现、接 LLM、改 spec 结构、排查「为什么生成结果不对」时。
> 本文档是**生成架构的唯一权威处**。`spec schema` 的字段级定义见
> [01_spec_schema.md](01_spec_schema.md)。

## 1. 为什么需要架构，而不是「让 LLM 直接写 Remotion 代码」

对照 `VideoGenResearch-minimax` 的失败模式：

| 做法 | 后果 |
|---|---|
| LLM 自由生成 Remotion TSX | 每次结构都不同，无法复用；出问题无法定位；改一个字要重生成整段 |
| LLM 输出一个「黑盒 spec」，渲染端解释它 | spec 无契约、无校验，坏数据直接渲成坏画面；失败没有降级路径 |
| 一次性脚本直接 `render` | 没有可调用的稳定入口，`Agent_VideoGen_Module` 接不进去 |

**本项目的解法有三条硬规则：**

> **规则 1 — 镜头类型是封闭集合。** LLM **只能从预置镜头卡中选择**（`shot type` 枚举），
> 并对每张卡的**已声明参数**赋值。LLM **绝不产出 JSX / TSX / 任意代码**。
>
> **规则 2 — spec 是可校验的数据契约。** Python 侧用 Pydantic 校验；校验失败按固定策略
> 修复或降级，**绝不让坏 spec 进入渲染**。
>
> **规则 3 — 产物必须可复现。** spec 落盘为 JSON，任何人拿同一份 spec + 素材
> 必得同一支视频（渲染端禁 `Date.now()` / `Math.random()`，见开发守则 §4）。

## 2. 五阶段流水线

```
┌─ 阶段 1 ────────────┐   ┌─ 阶段 2 ──────┐   ┌─ 阶段 3 ─────────┐
│ 素材理解             │   │ LLM 规划       │   │ 校验与编译        │
│ SUBTITLE→TIMELINE   │──▶│ DeepSeek       │──▶│ Pydantic 校验     │
│ 纯 Python，无 LLM    │   │ → VideoSpec    │   │ → 渲染 props      │
└─────────────────────┘   └───────────────┘   └──────────────────┘
        │                        │                      │
   srt/wav/图片清单          spec.json              props_*.json
        │                        │                      │
        └────────────────────────┴──────────────────────┘
                                 ▼
                    ┌─ 阶段 4 ──────────┐   ┌─ 阶段 5 ────────┐
                    │ 渲染（Node 薄壳）  │   │ 产物与归档       │
                    │ remotion render   │──▶│ mp4 + 日志       │
                    └───────────────────┘   └─────────────────┘
```

### 阶段 1 — 素材理解（`videogen/analyze/`，**无 LLM**）

纯确定性 Python，**不花一分钱**：

| 步骤 | 输入 | 输出 | 实现 |
|---|---|---|---|
| 解析字幕 | `*.srt` | `list[Segment]`（start/end/text） | `pysubs2` 或自写解析 |
| 音频时长 | `*.wav` | `duration`（秒） | `wave` / `soundfile` |
| 时间轴归一 | 上两者 | `Timeline`：总帧数 = `round(音频时长 × fps)` | 纯计算 |
| 素材盘点 | `images/` | `list[Asset]`（路径/宽高/方向） | `Pillow` |

**关键约束**：时间轴由**音频时长**决定，不由字幕最后一条决定
（本次素材字幕止于 155.480s，音频 155.48s，一致；但两者可能不等，取音频为准）。
总帧数 `durationInFrames` 由阶段 3 写入 Composition props，Remotion 侧用
`calculateMetadata` 读取。

### 阶段 2 — LLM 规划（`videogen/plan/`，**唯一花钱处**）

**一次调用**产出整份 `VideoSpec`（不做多轮对话，不做逐镜头调用 —— 那会把成本乘 N）。

输入给 LLM 的内容（全部来自阶段 1 的结构化结果，**不塞原始长文**）：

1. 口播分段的 `start/end/text` 列表（这是分镜的**骨架**）；
2. 可用镜头卡清单（**枚举 + 每卡的参数 schema + 适用场景**，从 `shot_catalog` 生成）；
3. 可用图片素材清单（文件名 + 尺寸 + **人工填写的语义标签**）；
4. 视频参数：目标时长、方向（横/竖）、主题 id、fps；
5. 硬约束：安全区、卡数上限、每张卡的最小/最大时长、禁止事项。

**输出**：严格 JSON（DeepSeek 的 `response_format: json_object` 或 function calling），
结构见 [01_spec_schema.md](01_spec_schema.md)。

**Prompt 组织**（`videogen/plan/prompts/`，纯文本文件，便于人工迭代）：

```
system.md      角色与硬规则（封闭镜头集、时间轴对齐、禁止编造数字）
catalog.md     由代码从 shot_catalog 生成，不手写（避免与实现漂移）
user.j2        把阶段 1 的结构化数据填进模板
```

> prompt **不在代码里拼字符串**。理由：prompt 需要人工反复迭代，
> 且要能对比不同版本的产出差异。

### 阶段 3 — 校验与编译（`videogen/compile/`，**无 LLM**）

```
spec.json ──▶ Pydantic 校验 ──┬─ 通过 ─▶ 编译成 Remotion props
                              │
                              └─ 失败 ─▶ 修复策略（有限次）：
                                          1. 时长越界 → 裁剪/补足到合法区间
                                          2. 未知镜头卡 → 替换为最接近的合法卡
                                          3. 素材引用不存在 → 该镜头降级为纯文字卡
                                          4. 仍失败 → 退回内置兜底 spec（保证能出片）
```

**降级必须留痕**：每次修复写入 `spec.repair_log[]`，渲染日志与产物一并归档，
否则「片出来了但和预期不符」会变成无法追查的谜。

**编译产出**：每个 `(video_kind, aspect)` 一份 props JSON
—— `props_short_landscape.json` / `props_short_portrait.json` / …

### 阶段 4 — 渲染（`videogen/render/`，Node 薄壳）

Python 通过 `subprocess` 调 `npx remotion render`（或 `@remotion/renderer` 的 Node 脚本）。

**为什么是薄壳**：渲染是确定性工程，业务逻辑（排到什么镜头、什么文案）
已在 spec 里定死。Node 侧**只做三件事**：把 props 注入 Composition、调 Remotion、报错回传。

| 关注点 | 做法 |
|---|---|
| Composition 注册 | 横竖屏各注册一个（`ShortLandscape` / `ShortPortrait`…），共用镜头组件 |
| 版式差异 | 组件内读 `useVideoConfig()` 的 `width/height` 分支，**不是等比缩放** |
| 时长 | props 里的 `durationInFrames`，经 `calculateMetadata` 生效 |
| 字体 | `delayRender()` 等 `NotoSansSC-VF.ttf` 就绪（见 [issues/002](../issues/002-cjk-font-ttc-face-ambiguity.md)） |
| 确定性 | 禁 `Date.now()` / `Math.random()`；伪随机用固定种子（`assets/lib/helpers` 的 `mulberry32`） |

### 阶段 5 — 产物与归档（`videogen/pipeline.py`）

```
out/
  <run_id>/                     # run_id = 时间戳 + spec 哈希前缀
    spec.json                   # 实际用于渲染的 spec（含 repair_log）
    props_short_landscape.json
    props_short_portrait.json
    short_landscape_1080p.mp4
    short_portrait_1080x1920.mp4
    render.log
    manifest.json               # 本次运行的输入哈希、耗时、算力开销
```

**spec 必须与成片同目录归档** —— 这是「可复现」的唯一保证。
`manifest.json` 记录 LLM token 用量与渲染耗时，供成本核算（开发守则 §2 要求记录开销）。

## 3. 与 `Agent_VideoGen_Module` 的对接面

只暴露**一个函数**作为稳定入口（其余皆为内部实现）：

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
    确定性：同一组输入必得同一支视频（LLM 温度固定为 0）。
    """
```

`VideoResult` 携带：成片路径列表、`spec` 对象、`repair_log`、耗时与 token 用量。
**调用方不需要知道 Remotion 存在。**

## 4. Prompt 设计要点

| 要点 | 做法 |
|---|---|
| 时间轴对齐 | 把分段 srt 的**真实时间**给 LLM，要求镜头起止吸附到分段边界；**不让 LLM 自己算时长** |
| 数字准确 | 关键数字由阶段 1 抽好（正则 + 人工确认）后**作为白名单**给 LLM，禁止 LLM 自己从文本里"读"数字 |
| 封闭镜头集 | catalog 里明确写「只能选下列 type」，并给出每卡参数范围 |
| 卡数约束 | 直接在 prompt 里给上下限（短 5–6 / 中 8–10），并在阶段 3 硬校验 |
| 温度 | 固定 `temperature=0`，保证可复现 |
| 失败重试 | 最多 1 次重试，把 Pydantic 的错误信息**原文回灌**给 LLM 让它自己修；再失败就走兜底 spec |

## 5. 成本模型（已实测，2026-10-02）

| 项 | 实测 |
|---|---|
| LLM（DeepSeek `deepseek-chat`） | **每支视频 1 次调用**；prompt **17,959** token（catalog 占大头）+ completion **628–902** token |
| LLM 耗时 | **3.0–3.5 s**（`attempts=1`，无重试） |
| 校验修复 | 真实输出**一次通过，0 条修复**（`from` 由服务端重排，模型不需要算帧号） |
| 单次调用费用 | 约 **$0.006**（按 DeepSeek 输入 ¥1/M、输出 ¥7/M 量级折算；以官方当前价为准） |
| 单帧自检 | 秒级 |
| 整片渲染 | 短视频 ≈ 1490 帧 / 方向、中视频 ≈ 4665 帧 / 方向（需沙箱外执行） |
| 调优成本 | 主要来自**反复渲染** → 纪律：先 `still` 单帧，确认后再整片 |

> 实测值归档在 `out/<kind>/spec.json` 与终端日志；本表由
> `scripts/plan.py` 的真实运行结果回填。

**钱花在哪**：真实调用只在 `scripts/plan.py` 不带 `--dry-run` 时发生，以及
`pytest -m live` 时。其余全部路径零成本。

## 6. 待定（随调研结论收敛）

- **镜头卡清单**：需从 `video-shotcraft/references/shots/` 的卡片中筛出本项目
  `shot_catalog` 的 v1 集合（等调研子代理结果）。当前预置意图：
  PageCam 页面卡、数字翻转、雷达/图表入场、图片卡、字幕条、wordmark 片头、CTA 收尾。
- **BGM 与卡点**：是否加 BGM、是否走 `music-beat-sync`（等调研结论）。
- **图片语义标签**：7 张图的标签已人工判读完成，见
  [research/03_article_materials.md](../research/03_article_materials.md) §5，
  需落成 `assets/images/index.json` 供阶段 1 读取。

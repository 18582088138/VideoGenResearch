# 闭环视频生成 · 技术路线与交接 / Closed-loop video generation

> **这份文档的用途**：新对话接手时先读它，就能知道「为什么做闭环」「要做什么」「已知问题是什么」。
> 配套读：[memory/project.md](../../memory/project.md)（项目级事实）、[docs/plan/01_delivery_optimization.md](01_delivery_optimization.md)（上一轮交付优化）。

---

## 0. 一句话任务

**独立实现一个「闭环」的视频生成系统**（不要求兼容现有框架），
把 5 条技术线路落地，做出一个能自检、能自修的生成器。

产出物要能证明：**「有闭环」比「开环」在画面上差多少**。

---

## 1. 为什么要做闭环：质量差距的根因

### 1.1 现象

用户的原话：

> 「为什么你直接生成的视频效果就很好，通用性也很高，但是通过脚本生成的质量就差很多呢？」

### 1.2 根因：闭环 vs 开环

**链路 A —— AI 手工做（效果好）**

```
看素材图（read_image）        ← 真的"看"到了
   ↓
写代码 / 改参数
   ↓
渲染单帧（remotion still，秒级）
   ↓
看图（read_image）            ← 判断"素材被裁了/文案压住了"
   ↓
改代码 → 再渲染 → 确认
   ↓
（循环 3–8 轮）→ 成片
```

**每一轮都有像素级反馈。**

**链路 B —— 现有脚本（效果差）**

```
文章文本 + 旁白 + 素材的 60 字文字描述
   ↓
LLM 在文本空间规划            ← 看不到图
   ↓
输出 spec（含**猜的**坐标）
   ↓
组件用**写死的参数**渲染
   ↓
成片（第一次看到效果 = 最终效果）
```

**没有任何反馈。**

### 1.3 六个技术维度差距

| # | 维度 | 手工做 | 现有脚本 | 差距本质 |
|---|---|---|---|---|
| 1 | **视觉反馈** | 渲染→看图→改，3–8 轮 | 一次成型 | **最根本** |
| 2 | **素材理解** | 读过原图，知道布局 | 只有 VLM 压出的 60–120 字 | **信息带宽** |
| 3 | **空间坐标** | 能量出框的位置 | 纯文本**瞎猜** | **模态不匹配** |
| 4 | **动效定制** | 能为一个镜头写 200 行 TSX | 从固定模板里选 + 填空 | **定制 vs 填空** |
| 5 | **参数调优** | 看到问题就改 | 组件参数是编译期常数 | **静态 vs 动态** |
| 6 | **返工粒度** | 只重做第 3 镜 | 一次性生成全部，无逐镜检查 | **粒度** |

### 1.4 最尖锐的证据：表示鸿沟

实测 `spark-x2` 的 `scan-annotate` 标注框（**LLM 从没看过这张图**）：

```
img=05  target: x=0.05 y=0.55 w=0.9 h=0.18   label='Gaokao 2026'
        target: x=0.05 y=0.2  w=0.9 h=0.18   label='BFCL-V4'
        target: x=0.05 y=0.75 w=0.9 h=0.18   label='tau2-bench'
```

特征：`x=0.05 w=0.9`（占满宽度）+ `y=0.2/0.55/0.75`（等距三行），
**连 y 的顺序都是乱的** —— 这是「文本模型想象一张图」的典型形状，
不是这张图真实的形状。

> 同源现象：VLM 标注也把 `Omni-IO` 读成了 `Omni-10`。
> **文字都能读错，更别说推理空间布局。**

---

## 2. 五条技术线路（要落地的内容）

### ① 渲染后自动视觉质检闭环 ★ 核心

```
渲染 → 抽帧 → VLM 评审（"素材被裁了吗？文案压住了吗？标注框对得上吗？"）
     → 反馈给 LLM 修正 spec → 重渲 → 再审
     → 达标 or 达迭代上限 → 输出
```

**这是结构性地复制"手工做"的闭环**，投产比最高。
成本：每轮 1 次 VLM + 1 次 LLM + 1 次渲染。

### ② 让规划器能看图（VLM 规划）

现有规划是**纯文本 LLM**。改成 VLM（或带上图），素材选择与内容贴合度会跃升。
成本：每镜 1 次 VLM 调用。

### ③ 坐标交给 VLM（bounding box）

**不要让文本 LLM 猜坐标。** 用 VLM 输出 bbox，或接专用检测模型。
这是 `scan-annotate` 类镜头能不能看的关键。

### ④ 组件参数暴露给 LLM

让每个组件声明「可调参数 + 取值域」，LLM 能微调（如"这镜素材占比 0.7"）。
现有系统的 11 个 `TUNE` 旋钮**对 LLM 是不可见的**。

### ⑤ 扩模板覆盖度

现有系统已从 13 → 21 个镜头类型。但这条**边际收益最低** ——
模板再多，只要没人看渲染结果，还是"闭眼画"。

---

## 3. 已知问题清单（实测，按严重度）

### 3.1 高：坐标靠猜（见 §1.4）

- 影响：所有带 `targets` 的镜头（`scan-annotate`）
- 根因：文本 LLM 在符号空间推理像素坐标
- 修法：技术线路 ③

### 3.2 高：没有视觉质检

- 影响：**所有**镜头 —— 渲染出来什么样，没人看过
- 修法：技术线路 ①

### 3.3 中：规划器看不到图

- 现象：素材选择靠 60 字描述，可能选错图配错话
- 修法：技术线路 ②

### 3.4 中：VLM 标注会误读专有名词

- 实测：`Omni-IO` → `Omni-10`（已通过"先照抄标签再判断用途"的提示词策略缓解）
- 残留：`narrative_use` 曾出现 4 张图全写"适合放在开头"的同质化

### 3.5 中：图文镜头类型雷同（已部分修复）

- 现象：不同文章的图文镜头都是 `figure-panel`/`flow-diagram`/`stat-compare`
- 根因（已定位）：**卡库 157 张与可落地 type 只有 1 个同名交集**
  （只有 `timeline-travel`）→ 模型的选择空间实际只有几个 type
- 已做：type 13 → 21；`build_catalog` 不再列卡名；加 `_enforce_variety` 兜底
- **待验证**：新对话跑一次看图文类型是否真的多样化了

### 3.6 中：素材过度复用

- 现象：模型把同一张图**连续用了 3 镜**
- 已做：prompt 加「同一素材不连续使用」
- 待验证

### 3.7 低：组件参数写死

- 见技术线路 ④

---

## 4. 实施建议：独立实现

用户明确要求：**「独立实现就好，不用兼容现有框架」**。

建议新建 `loop/` 目录，**不依赖** `src/videogen/` 的数据契约，自己定：

```
loop/
├── README.md           怎么跑
├── config.py           模型/阈值/迭代上限
├── vision.py           VLM 三能力：annotate（标注）/ locate（定位 bbox）/ review（质检）
├── planner.py          带图规划（技术线路 ②）
├── composer.py         spec → 渲染（可复用 remotion 作为渲染后端）
├── reviewer.py         视觉质检 + 问题→修正建议（技术线路 ①）
├── loop.py             闭环主控（生成→渲染→评审→修正→重渲）
└── run.py              入口
```

### 渲染后端的选择

| 方案 | 优点 | 缺点 |
|---|---|---|
| **复用 remotion**（推荐） | 动效成熟、已有 21 个组件 | 需要 TS props 契约 |
| Python + PIL/ffmpeg | 完全独立、参数化容易 | 动效弱 |

**建议复用 remotion 做渲染**，但**组件 props 重新设计**为「参数可调」（技术线路 ④），
不要迁就旧 spec 格式。

### 最小可验证路径（建议顺序）

1. **先做 ① 的骨架**：渲染 → 抽帧 → VLM 评审 → 输出问题清单。
   **先不做自动修正**，人工看清单准不准。
2. 接 ③：`locate()` 让 VLM 给 bbox，替换"猜坐标"。
3. 接 ④：给组件加 `tune` 参数块，让 LLM 能调。
4. 接 ②：规划阶段带图。
5. 最后加自动修正（把 VLM 的问题转成 spec 修改）。

---

## 5. 环境与硬约定（照抄，别踩）

| 项 | 值 |
|---|---|
| 项目根 | `C:\Users\75203\Downloads\xkd\VideoGenResearch-deepseek` |
| Python | `C:\Users\75203\miniforge3\envs\ov_env_py312\python.exe`（3.12.14） |
| Node | v22.16.0；remotion v4.0.484 |
| 控制台 | **GBK** —— 输出别用 emoji（`✅` 会 `UnicodeEncodeError`） |
| 写非 ASCII 文件 | **不要用 PowerShell**（PS 5.1 会写成 GBK）；用 Python `write_text(encoding='utf-8')` |

### 必须设的环境变量

```powershell
$env:npm_config_cache = 'C:\Users\75203\Downloads\xkd\.npm-cache'
$env:npm_config_tmp   = 'C:\Users\75203\Downloads\xkd\.npm-tmp'
$env:TMP              = 'C:\Users\75203\Downloads\xkd\.render-tmp'   # 必须！见下
$env:TEMP             = $env:TMP
$env:PYTHONIOENCODING = 'utf-8'
```

**`TMP`/`TEMP` 必须在工作区内**：Remotion 会把 pre-encode 的 mp4 写进 `%TEMP%`，
指向系统临时目录会 `Permission denied`，报成看不懂的 `write EOF`。

### 模型（`VideoGenResearch-deepseek/.env`）

| 用途 | 模型 | 备注 |
|---|---|---|
| 文本规划 | `deepseek-chat` | DeepSeek，便宜 |
| **视觉（看图）** | **`MiniMax-Text-01`** | 实测最佳：能照抄英文原标签 |
| 视觉备选 | `abab7-chat-preview` | 同样准确 |
| ASR | MiniMax `asr-1.0` | 字级时间戳 |

#### ⚠️ 两个必须记住的坑

**1. MiniMax 的业务错误藏在 `base_resp`，HTTP 状态是 200**

```json
HTTP 200 但 {"base_resp": {"status_code": 2013, "status_msg": "unknown model"}}
```

**只看 HTTP 码会把失败当成功**（`content` 是 `None`）。
判据一律用 `base_resp.status_code == 0`。

**2. 这几个"模型名"是不存在的 / 不能用**

| 名称 | 实际情况 |
|---|---|
| `MiniMax-VL-01` | ❌ **该模型不存在** |
| `MiniMax-M1` / `abab6.5-chat` | ❌ 明确 `not support img` |
| `MiniMax-M2` | ⚠️ 能读但答非所问 |
| `abab6.5s-chat` | ⚠️ 会把标签意译错（`Asset Registry` → 资产管理设计） |
| OpenRouter 的 `nvidia/nemotron-3-super-120b-a12b:free` | ❌ 不支持图像输入 |

### 视觉调用的提示词策略（实测有效）

> **问「描述这张图」会得到泛泛而谈甚至编造；
> 问「照抄图里最显眼的几个文字标签」则准确得多。**

所以要求模型**先做可验证的抄录，再做用途判断**。
效果：03 图抄到 9 个标签全对。

### 抽帧品检的固定套路

```powershell
cd remotion
npx remotion still src/index.ts SetLandscape `
  "..\out\<set>\short\qa\probe.png" `
  --props="<绝对路径>\props_short_landscape.json" --frame=190
```

- `--props` **必须绝对路径**（子进程 cwd 是 `remotion/`）
- 从 Python 调 Remotion **不要用 `npx`**（它是 `.cmd` shim，`CreateProcess` 不解析）→ 直调 `node <remotion-cli.js>`
- ⚠️ **Remotion 校验 `--frames` 用的是 Composition 的静态 `durationInFrames`，不是 `calculateMetadata` 算出的值** —— 静态值要设成足够大的上限（现有代码用 30000）

---

## 6. 验收标准

新对话做完后，应能回答：

1. **闭环是否真的跑起来了** —— 至少 1 轮「渲染 → VLM 评审 → 修正 → 重渲」
2. **质检准不准** —— VLM 说的问题，人看了是否同意（抽 5 帧人工核对）
3. **坐标是否变准** —— `locate()` 给的 bbox 与实际图元是否对齐
4. **参数是否被用上** —— LLM 生成的 `tune` 参数是否真的影响了画面
5. **对比开环差多少** —— 同一个文章，开环 vs 闭环的效果对照

### 建议用的测试文章

```
C:\Users\75203\Downloads\xkd\DailyNewsAssistant\outputs\articles\20260919\Spark-X2-5开源4B-1-7B-智能体模型-探索端侧大模型的智能体能力上__d49afa69
```

（5 张图；开环版本已跑过，见 `out/spark-x2/`，可直接对照）

---

## 7. 现有系统的关键数据（供对照）

| 项 | 值 |
|---|---|
| 镜头类型 | 21 个（`src/videogen/spec.py` 的 `SHOT_TYPES`） |
| 测试 | 142 passed（`pytest`） |
| TS | `tsc` 0 错误 |
| 一键入口 | `scripts/make_video.py --article <目录> --kind short [--name <短名>]` |
| 一键重渲 | 同上加 `--rerender`（不重新规划、不花 LLM 钱） |
| 交付目录 | `out/<素材集>/<kind>/{video,shots,subtitles,storyboard,qa,logs}` |
| 人可读镜头表 | `out/<素材集>/<kind>/storyboard/shots.txt` ← **验收看这个最直观** |

---

## 8. 一条重要提醒

**这个项目的每一次质量提升，都来自"有人真的看了渲染结果"。**
所有"配置写了没人消费""卡库 157 张落不了地""坐标靠猜"的问题，
本质都是**链路上有一段是"通"的假象**。

做闭环的价值就在这：**让系统自己成为那个"看的人"。**

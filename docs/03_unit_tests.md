# 单元测试总览 — VideoGenResearch-deepseek

> **什么时候加载**：想知道「改了什么该跑哪个测试」时。**不要为了跑测试而通读本文档。**
> 开发守则 §2：默认**只跑本次改动对应的节点**，不做全量测试。

## 复测总入口

```powershell
cd C:\Users\75203\Downloads\xkd\VideoGenResearch-deepseek
$py = "C:\Users\75203\miniforge3\envs\ov_env_py312\python.exe"

# 只跑某个文件的全部节点（推荐日常用法）
& $py -m pytest tests/test_timeline.py -v

# 只跑单个节点（最省）
& $py -m pytest tests/test_timeline.py::test_build_timeline_mid_frames -v
```

`pyproject.toml` 里 `addopts = "-m 'not live and not slow'"` —— **默认不会跑花钱/耗时的用例**。
这是成本护栏，请勿为了「跑全一点」而加 `-m ''`。

## 测试节点清单

| 文件 | 覆盖什么 | 费用 | 何时必须跑 |
|---|---|---|---|
| `tests/test_timeline.py` | SRT 解析容错、秒↔帧换算、时间轴构建、真实素材时长/帧数 | 零 | 改 `src/videogen/timeline.py` 或换素材后 |
| `tests/test_assets.py` | 镜头卡索引加载（157 张 / 10 类）、图片语义索引、尺寸核对 | 零 | 改 `assets/*/index.json`、`scripts/build_shot_catalog.py` 或 `src/videogen/assets.py`・`shot_catalog.py` 后 |
| `tests/test_validate.py` | spec 字段约束、逐项降级修复、时间轴对齐、序列化往返 | 零 | 改 `src/videogen/spec.py`・`validate.py`，或改 `remotion/src/compositions/types.ts` 后（两侧必须对齐） |
| `tests/test_plan.py` | 密钥打码、`.env` 装载、JSON 容错、prompt 组装、数字白名单抽取、**服务端字段覆盖** | 零（网络全 mock） | 改 `src/videogen/llm_config.py`・`llm.py`・`plan/**` 或 prompt 后 |
| `tests/test_pipeline.py` | spec→props 编译、Composition 解析、端到端编排（渲染被替换）、manifest 台账、**CLI 命令构造** | 零（渲染被替换） | 改 `src/videogen/compile.py`・`pipeline.py`・`render/**` 后 |
| `tests/test_plan.py::test_live_plan_short_video` | **真实 DeepSeek 调用**（`.live` 标记，默认排除） | ✅ **约 1 次调用** | 只在「LLM 链路可行性验证」时手动跑 |

## 按改动定位测试（速查）

| 我改了什么 | 跑哪个 |
|---|---|
| `src/videogen/timeline.py` | `pytest tests/test_timeline.py -v` |
| `src/videogen/assets.py` | `pytest tests/test_assets.py -v` |
| `src/videogen/shot_catalog.py` | `pytest tests/test_assets.py -v` |
| `src/videogen/spec.py` / `validate.py` | `pytest tests/test_validate.py -v` |
| `remotion/src/compositions/types.ts` | `pytest tests/test_validate.py -v`（校验镜像是否漏字段） |
| `src/videogen/llm_config.py` / `llm.py` | `pytest tests/test_plan.py -v`（网络全 mock，零费用） |
| `src/videogen/plan/**` 或 `plan/prompts/*.md` | `pytest tests/test_plan.py -v`；改 prompt 后建议再跑一次 `scripts/plan.py --kind short` 做真实对照 |
| `src/videogen/compile.py` / `pipeline.py` | `pytest tests/test_pipeline.py -v` |
| `src/videogen/render/**` | `pytest tests/test_pipeline.py -v`；再出一次静帧验证真的能渲 |
| `scripts/plan.py` | `python scripts/plan.py --kind short --dry-run`（零费用演练） |
| `scripts/build_shot_catalog.py` | 先重跑脚本，再 `pytest tests/test_assets.py -v` |
| `assets/images/index.json` | `pytest tests/test_assets.py -v` |
| 换文章素材（新 srt/wav） | `pytest tests/test_timeline.py -v`（真实素材断言会红，需同步更新期望值） |
| Remotion 工程 / 镜头组件 | 见下文「Remotion 侧验证」 |

## Remotion 侧验证（不是 pytest）

Remotion 是 Node 侧，用**单帧渲染自检**代替单测 —— 秒级出图，比整片渲染便宜两个数量级。

```powershell
cd C:\Users\75203\Downloads\xkd\video-shotcraft\template
$env:npm_config_cache='C:\Users\75203\Downloads\xkd\.npm-cache'
$env:npm_config_tmp='C:\Users\75203\Downloads\xkd\.npm-tmp'

# 1) 列出 Composition，确认注册成功
npx remotion compositions src/index.ts

# 2) 出单帧自检（改任何镜头组件后先做这一步，不要直接整片渲）
npx remotion still src/index.ts <CompositionId> out/check.png --frame 60
```

**纪律**：整片渲染（`remotion render`）只在「功能可行性验证」时做，
且开销必须记入 [research/04_bgm_and_audio.md](research/04_bgm_and_audio.md) 或对应 issue。

## 标记约定

| 标记 | 含义 | 是否默认跑 |
|---|---|---|
| （无标记） | 纯逻辑、离线、零成本 | ✅ 是 |
| `@pytest.mark.slow` | 秒级以上（整片渲染、大批量） | ❌ 否 |
| `@pytest.mark.live` | 真实调用 LLM / 付费服务 | ❌ 否 |

## 每个测试文件都自带复测指令

按开发守则要求，**每个测试文件的模块 docstring 里都有**：

1. 测试说明文档指针（即本文档）；
2. **完整可复制的复测命令**；
3. 预期结果；
4. 费用说明。

所以在终端里 `Get-Content tests/test_xxx.py -TotalCount 30` 就能拿到复测指令，
不必回来翻本文档。

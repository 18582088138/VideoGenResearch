# VideoGenResearch-deepseek

用 **Remotion + video-shotcraft** 把中文科技新闻稿（含现成配音 wav + srt 字幕 + 配图）
生成**横屏 / 竖屏**视频的技术验证与调研项目。

**最终目标是沉淀一个可复用的 Python 模块**，作为后续 `Agent_VideoGen_Module` 的地基，
并可挂到 `DailyNewsAssistant` 上作为一个功能拓展 —— 而不是只渲出几支样片。

## 这是什么（以及不是什么）

| 是 | 不是 |
|---|---|
| 「代码即渲染」路线的技术验证 | 纯 AI 文生视频（Sora / 可灵等）—— 本期不做 |
| Remotion + video-shotcraft 的能力与用法梳理 | 一次性宣传片脚本堆 |
| 可复用 Python 模块 + 生成流程/prompt/workflow 架构 | 一次性渲完就丢的 demo |

## 快速开始

```powershell
# 1) 环境（Windows / conda）
$py = "C:\Users\75203\miniforge3\envs\ov_env_py312\python.exe"

# 2) 跑测试（只跑相关节点，勿全量 —— 见开发守则）
& $py -m pytest tests/test_timeline.py -v

# 3) 重新生成镜头卡索引（源仓库更新后）
& $py scripts\build_shot_catalog.py

# 4) Remotion 工程（在 video-shotcraft/template 或本项目 remotion/ 下）
$env:npm_config_cache='C:\Users\75203\Downloads\xkd\.npm-cache'
$env:npm_config_tmp='C:\Users\75203\Downloads\xkd\.npm-tmp'
npx remotion compositions src/index.ts        # 列 Composition
npx remotion still src/index.ts <Id> out/check.png --frame 60   # 单帧自检
```

> ⚠️ npm 必须带上 `npm_config_cache` / `npm_config_tmp` 两个环境变量，
> 否则会撞 DSH 沙箱的文件访问限制，见 [docs/issues/001](docs/issues/001-npm-cache-blocked-by-sandbox.md)。

## 先读什么

1. **[memory/project.md](memory/project.md)** —— 跨会话记忆（决策 + 硬事实）
2. **[docs/00_INDEX.md](docs/00_INDEX.md)** —— 文档索引，标了每份文档「什么时候加载」
3. **[docs/guides/00_dev_principles.md](docs/guides/00_dev_principles.md)** —— 开发守则

**不要**一次性读完 `docs/`。文档按需加载是本项目最重要的成本纪律。

## 目录

```
assets/    素材（图片 / 音频 / 字体 / 语义索引）—— 只放素材
docs/      全部文档，00_INDEX.md 是唯一入口
memory/    跨会话记忆
out/       渲染产物（只放产物；脚本绝不进这里）
scripts/   薄壳脚本（零业务逻辑）
skill/     项目专属 skill（video-shotcraft + Remotion 调用协议）
src/       可复用 Python 包 videogen/
tests/     单元测试（每文件自带复测指令）
```

## 外部依赖

| 依赖 | 位置 / 版本 |
|---|---|
| Remotion | `video-shotcraft/template` 内锁定 **v4.0.484**（非 v3） |
| video-shotcraft | 工作区根 `../video-shotcraft`（`Vincentwei1021/video-shotcraft` @ `5ddbf52`） |
| 中文旁白与配图 | `DailyNewsAssistant/outputs/articles/20260919/…清华团队…踢足…` |
| Node | v22.16.0（实测可用） |

## 许可注意

- **字体**：Noto Sans SC（SIL OFL 1.1），免署名可商用。
- **SFX / BGM**：Mixkit Free License，免署名可商用（个别文件来源待考，见源仓库 `ATTRIBUTION.md`）。
- **Remotion**：个人与小团队免费，公司使用可能需付费许可 —— 对外发布前自行确认。
- **新闻配图**：来自微信公众号原文，本仓库仅内部验证使用，不随代码分发。

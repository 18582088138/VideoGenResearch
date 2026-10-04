# Remotion 文档 + BGM 生成能力 技术调研

> 目标场景：用 Remotion（React 写视频）+ video-shotcraft 镜头卡体系，把中文科技新闻稿件（现成配音 `.wav` + `.srt` 字幕）渲染成横屏 `1920x1080` 与竖屏 `1080x1920` 两个版本；运行环境 Windows + Node.js（另有 Python 3.12 conda 环境做工程化封装）。
>
> 调研时间基线：本文的 v3 结论以 **`v3.remotion.dev` 文档站 + Remotion 仓库 `v3.3.96` tag 的文档源文件** 为准；v4/v5 结论以 **`www.remotion.dev` 当前文档** 为准。
>
> 标注约定：**【官方】** = 官方文档/官方页面直接写明；**【社区】** = 第三方文章、GitHub issue、经验值；**【推断】** = 基于官方文档的合理推论，未在官方原文中出现。

---

## ⚠️ 使用前必读：本项目落定的结论（2026-10-02 复核）

本文件由调研子代理产出（约 2000 行，超出任务书建议篇幅 —— 因为它选择保完整性而非删掉
用户明确要求的 flag 表与 API 签名）。以下 **5 条**已由主上下文复核并落定为项目决策：

### 结论 1（重要）：任务书给的 **Remotion v3 文档站是错的**，本项目已用 v4

用户给的链接是 `https://v3.remotion.dev/docs/`，但需求清单里 5 个关键特性
**全部是 v4.0 才引入的**，在 v3 文档站实测 **404**：

| 特性 | v3 | v4 | 本项目是否需要 |
|---|---|---|---|
| `<Composition schema>` + `@remotion/zod-types` | ❌ 404 | ✅ | 需要（spec 校验） |
| `calculateMetadata()` | ❌ | ✅ | 需要（音频决定动态时长） |
| `@remotion/captions`（`parseSrt` 等） | ❌ 404 | ✅ | 可不用（字幕已自行解析） |
| `@remotion/fonts` 的 `loadFont()` | ❌ | ✅ | 可用 FontFace 手工替代 |
| `selectComposition()`（Node API） | ❌ | ✅ | 需要（工程化调用） |

**主上下文独立验证**：`video-shotcraft/template/package.json` 锁定 `remotion@4.0.484`，
且本机实测 `remotion compositions` / `remotion still` 均通过（见
[plan/00_dev_plan.md](../plan/00_dev_plan.md) §3）。

→ **本项目直接采用 v4.0.484**，memory 决策 **D11** 已记录。文档里 v3 的等价实现段落
保留作为背景资料，但**不作为实现依据**。

### 结论 2（商用红线）：**MusicGen 权重是 CC-BY-NC，禁止商用**

代码 MIT，但**权重 CC-BY-NC 4.0** → **不可商用**。**这是本次调研最重要的许可红线**，
本项目直接排除该方案，不引入。

同理排除：Stable Audio Open（许可阈值未确证，需 GPU）、Magenta（Python 3.12 + Windows 装不上）、
Suno/Udio（无稳定 API、条款多变、结果不可复现）。

### 结论 3（BGM 答案）：Remotion **没有**音频合成 API，但本项目也不需要生成

- `@remotion/media-utils` 官方定位只有「获取信息 + 可视化」，**无任何合成函数**。
- 官方给过用 `OfflineAudioContext` 离屏合成正弦音的示例 → 证明「渲染期生成音频」可行，
  但受 `delayRender` 30s 超时与内存约束，且 Data URL 体积是 PCM 的 1.33 倍。
- **程序化合成（numpy + `scipy.signal.lfilter`）**：1–3 分钟 BGM 在普通 CPU 上
  **1–10 秒**，零许可风险、确定性可复现 → 这是「要生成时」的最佳路线。
- **但本项目连生成都不需要**：`video-shotcraft/assets/audio/bgm/` **自带 5 首免版权 BGM**
  （Mixkit Free License，BPM 实测 124/129/86/123/103），**零算力开销**。

→ **回答用户的原问题**：项目自带 BGM 素材，**生成 BGM 的算力开销为 0**；
若将来要"每条视频独一无二"的 BGM，走**程序化合成**（1–10 秒/条），
**不要**走 AI 音乐模型（许可与算力都不划算）。memory 决策 **D10** 与此一致（BGM 默认关闭）。

### 结论 4（Remotion 许可，工程化前必须评估）

免费范围：**个人 / ≤3 名员工的营利组织 / 非营利 / 评估期**。
当前定价（子代理抓取，**商用前需自行复核**）：

| 档位 | 价格 | 备注 |
|---|---|---|
| Automators（自动化批量渲染） | **$0.01 / 次渲染，$100/月保底** | ⚠️ 直接影响 `Agent_VideoGen_Module` 的成本模型 |
| Creators | $25 / 月 / Seat | |
| Enterprise | $500 / 月起 | |

**注意**：`@remotion/*` 子包标注 MIT，但**核心包是 Remotion License**（非 MIT）。

→ **风险登记**：若 `Agent_VideoGen_Module` 要做**批量自动化渲染**，需走 Automators 档，
`$0.01/次 + $100/月` 是**必须计入的业务成本**。已记入 [plan/00_dev_plan.md](../plan/00_dev_plan.md) §7。

### 结论 5（Windows 两个实操坑，直接影响命令写法）

1. **Windows 上 `--props` 不能传内联 JSON，必须传文件路径**（官方警告）
   → 我们的架构本来就落盘 props JSON（`props_<kind>_<aspect>.json`），天然合规。
2. **自动下载的 Chromium 不含 MP3/MP4 编解码器**，可能导致超时；
   离线/内网可用 `--browser-executable` 指向已装 Chrome。
   → 本项目旁白是 **WAV**（PCM），且已实测渲染通过，暂不受影响；
   但**素材里 5 首 BGM 是 MP3**，若启用 BGM 需留意此限制。

### ⚠️ 校正：SFX 文件数是 **149**，不是 151（本文档正文的 151 是错的）

本文档正文（§C9 与「已知坑」§8）记 `assets/audio/sfx/` 实测 **151** 个文件，
**这是误计**。主上下文用 `Get-ChildItem -LiteralPath <sfx> -Recurse -File` 复核：

```
总文件数: 149      扩展名分布: .mp3 = 149（无其它类型）
camera 10 · counter 4 · crowd 3 · data 13 · film 8 · fluid 5 · glass 4
impact 14 · light 10 · mech 8 · paper 10 · riser 1 · scifi 5 · text 13
transition 23 · ui 18          逐类相加 = 149
```

误差来源可复现：`-Recurse` 再叠加 `-Directory` 或把目录项计入时，
会多出 **16 个**类别目录（149 + 16 = 165）或 **+2**（`sfx/` 自身与另一层）→ 151。

→ **149 是正确的，且与仓库自身文档口径一致**（`SKILL.md:235`、`sound-design.md:65`、
`ATTRIBUTION.md:5`）；反而是本文档的「文档 149 未同步、实际 151」这一说法不成立。
`tests/test_assets.py` 不依赖该数字；`memory/project.md` 与
[02_video_shotcraft_usage.md](02_video_shotcraft_usage.md) 的「校正 1」均按 **149** 记录。

> 注：02 手册的「校正 1」曾推断「仓库文档 149 是对的、手册 151 是错的」——
> 该推断**本次得到独立证实**，两份子代理产物里那一处 151 已按此更正。

### 其它要点速查

| 主题 | 结论 |
|---|---|
| 多分辨率 | **`--scale` 只能同比例放大，无法做 16:9↔9:16**（官方原文：仅对文字/SVG/图片有效，对 video/Canvas 无效）→ 与 [design/00_platform_output_spec.md](../design/00_platform_output_spec.md) §2.1 **结论一致**，进一步坐实「两个 Composition」方案 |
| `--concurrency` | 默认 = CPU 线程一半；过高会导致 Chrome 不加载 `<Video>` → delayRender 超时。用 `npx remotion benchmark` 实测 |
| `--gl` | 本地默认 `null`，**不要盲目用 `angle`**（历史版本有内存泄漏崩溃） |
| 中文字体 | 建议 **woff2 + 子集化**（完整中文 TTF 10–20MB → 数十 KB）。本项目用 17MB 的 `NotoSansSC-VF.ttf`，**渲染可用但打包偏慢**，记入待优化 |
| 并发渲染 | 官方原话：嵌入视频是 Remotion 的显著瓶颈，鼓励与 FFmpeg 组合搭流水线 |
| 平台规范 | 抖音/小红书**官方规范原文在登录态后台，未能取得权威数值**（已明确标注「未证实」），安全区数值来自第三方创作者工具文章 |
| 安全区细节 | 居中字幕要**左右取同值**，否则抖音 `60/120` 非对称边距会让字幕整体左偏 30px —— 本项目 `layout.ts` 已按对称处理 |

### 本文件的边界（子代理自述）

- 列出 **16 项未确证** 与 **10 项必须本机实测**（中文字体回退、concurrency 最优值、
  `--gl` 最优值、横竖屏耗时比、ducking 听感、OfflineAudioContext 实测、SRT 边界、
  平台二次转码画质、props JSON 体积等）。
- 沙箱禁止 shell 出网，全部抓取通过 `web_fetch` 完成；
  `raw.githubusercontent.com` 多次限流，改用文档站 HTML 与 tag 源文件交叉验证。

---

## 0. 结论摘要（先看这一节）

### 0.1 最重要的一条：你要的四个特性在 v3 里都不存在

你的需求清单里有 5 个关键特性，**它们全部是 Remotion v4.0 才引入的，v3 官方文档站上对应页面返回 404**。如果你坚持 v3，就必须自己实现这些能力。

| 特性 | v3 是否可用 | 证据 |
|---|---|---|
| `<Composition schema={...}>` + `@remotion/zod-types` | ❌ 不可用（v4.0 起） | `https://v3.remotion.dev/docs/schemas` → **404**；v4 迁移文档写明 `TComposition` 类型在 v4 才加入 `AnyZodObject` 泛型 |
| `calculateMetadata()` | ❌ 不可用（v4.0 起） | v4 文档页标注 `[v4.0.0]`；v3 文档对应方案是 `/docs/dynamic-metadata` |
| `@remotion/captions`（`parseSrt` / `createTikTokStyleCaptions`） | ❌ 不可用（v4.0 起） | `https://v3.remotion.dev/docs/captions` → **404**；captions 出现在 v4 文档导航 |
| `@remotion/fonts` 的 `loadFont()` | ❌ 不可用（v4.0 起） | v3 只有 `/docs/fonts`（FontFace API 手工加载）；`@remotion/fonts` 在 v4 导航下 |
| `selectComposition()`（Node API） | ❌ 不可用（v4.0 起） | v4 文档页标注 `[v4.0.0]`；v3 用 `getCompositions()` + `.find()` |

**建议**：新项目直接上 **Remotion v4（或 v5）**，并在工程化封装里锁定精确版本。坚持 v3 只有在「已有 v3 代码库、不想迁移」时才合理，且需要接受上面 5 项全部手工实现。

### 0.2 其余核心结论速览

1. **v3 的动态时长**靠 `getInputProps()` 在 `<Composition durationInFrames={...}>` 里算，或靠 `delayRender()/continueRender()` 异步算；**v4** 用 `calculateMetadata()`（更干净、只调用一次、可返回 `defaultCodec` 等）。【官方】
2. **多分辨率/多比例**官方只提供 `--scale`（等比缩放，仅对文字/SVG/图片有效，对 video/canvas 无效）。**横屏+竖屏这种「不同宽高比」不能靠 `--scale`**，必须走「同一 Component + 传入 `orientation` prop + 注册两个 Composition」或「程序化传 `width/height` 覆盖」。【官方 + 推断】
3. **音频方面 Remotion 官方没有「音频合成 API」**：`@remotion/media-utils` 只做「读取/可视化/格式转换」（`getAudioDurationInSeconds`、`getAudioData`、`visualizeAudio`、`audioBufferToDataUrl` 等），**没有振荡器/合成器/音符生成能力**。【官方】
4. **但 Remotion 官方文档给出了用 `OfflineAudioContext` 离屏合成音频、再交给 `<Audio>` 的完整官方示例（渲染正弦音）**。这意味着「用 Web Audio API 在渲染期生成音频」是**官方认可的可行路径**，Tone.js 的 `Tone.Offline()` 同理可用。关键限制：必须 `await offlineContext.startRendering()` 并用 `delayRender()/continueRender()` 卡住当前帧，且**不能用 Tone.Transport 的实时时钟**。【官方 + 推断】
5. **BGM 最省算力、最可控的排序**（针对「科技感/电影感」中文科技新闻视频）：
   **现成免版权素材（0 算力，分钟级）> Python/NumPy 程序化合成（CPU，秒级~分钟级）> 浏览器端 Web Audio 离屏合成（CPU/NPU 无关，随渲染并行）> MusicGen-small / Stable Audio Open / ACE-Step（需要 GPU 或用 CPU 跑数十分钟）> Suno/Udio（云端，但自动化与版权条款有风险）**。
6. **平台输出参数**：竖屏 `1080x1920`、横屏 `1920x1080`，H.264 + `yuv420p`、`fps=30`、CRF 建议 `18~21`（Remotion H.264 默认 18）、音频 AAC `192k~320k`。【官方 + 社区】

---

## 1. 环境与版本基线

### 1.1 版本事实

- v3 文档站：<https://v3.remotion.dev/docs/>（本文引用的全部 v3 页面均在此站下）
- 本文核对的 v3 文档源码 tag：`v3.3.96`（仓库路径 `packages/docs/docs/*.md`）
- v3 配置文件格式在 **v3.3.39** 被拍平（`Config.setConcurrency()` 取代 `Config.Bundling.*`），旧写法仍兼容但已废弃。【官方：<https://v3.remotion.dev/docs/config>】
- 当前主线已是 v4/v5（存在 `5-0-migration` 文档页面）。【官方：<https://www.remotion.dev/docs/5-0-migration>】

### 1.2 Windows + Node 环境注意

- **v3 需要单独安装 FFmpeg**（`ffmpeg` / `ffprobe` 必须在 `PATH`，或用 `--ffmpeg-executable` / `--ffprobe-executable` 指定）。v4 起 FFmpeg 被打包进 `@remotion/renderer`，`ffmpegExecutable` 选项被移除。【官方：v3 <https://v3.remotion.dev/docs/config#setffmpegexecutable>；v4 <https://www.remotion.dev/docs/4-0-migration>】
- **Windows 上 `--props` 不能传内联 JSON 字符串**（因为 PowerShell/cmd 会吃掉 `"` 字符），必须写临时 JSON 文件再传路径。这是官方明确写的警告，对本项目（大量 props 参数化）非常重要。【官方：<https://v3.remotion.dev/docs/cli/render#--props>】

```
# ✗ Windows 上会被破坏
npx remotion render src/index.ts News out/video.mp4 --props={"orientation":"portrait"}

# ✓ 官方推荐：写文件
python -c "import json;json.dump({...},open('props.json','w',encoding='utf-8'),ensure_ascii=False)"
npx remotion render src/index.ts News out/video.mp4 --props=./props.json
```

- **H.264 编码器**：Remotion 默认下载的 Chromium 不含专有编解码器，官方建议在需要 H.264/MP4 支持时使用**系统安装的 Chrome**（`--browser-executable` / `Config.setBrowserExecutable()`）。【官方：<https://v3.remotion.dev/docs/config#setbrowserexecutable>、<https://v3.remotion.dev/docs/timeout>（"Importing MP4 videos in Chromium" 一节）】

---

## 2. A 部分：Remotion v3 核心概念

### A1. Composition / registerRoot / Root 的写法与 props

#### A1.1 `registerRoot()` 【官方：<https://v3.remotion.dev/docs/register-root>】

```tsx
// src/index.ts
import { registerRoot } from "remotion";
import { RemotionRoot } from "./Root";
registerRoot(RemotionRoot);
```

官方明确要求：**`registerRoot()` 必须放在与「组合列表」不同的文件里**，因为 React Fast Refresh 会重新执行被刷新文件中的所有代码，而这个函数只能被调用一次。【官方】

需要延迟注册（动态 import / 加载 WASM）时：

```tsx
import { continueRender, delayRender, registerRoot } from "remotion";
import { RemotionRoot } from "./Root";

const wait = delayRender();
loadWebAssembly().then(() => {
  registerRoot(RemotionRoot);
  continueRender(wait);
});
```

#### A1.2 `<Composition>` 完整参数表 【官方：<https://v3.remotion.dev/docs/composition>】

| Prop | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | `string` | ✅ | 唯一 ID，**只允许字母、数字和 `-`**；渲染时用它选择组合 |
| `fps` | `number` | ✅ | 帧率 |
| `durationInFrames` | `number` | ✅ | 总帧数 |
| `width` | `number` | ✅ | 像素宽 |
| `height` | `number` | ✅ | 像素高 |
| `component` **或** `lazyComponent` | `React.FC` / `() => Promise<{default: React.FC}>` | ✅（二选一） | 两者都不传或都传都会报错；用 `lazyComponent` 时组件必须是 default export（React Suspense 限制） |
| `defaultProps` | `object` | ❌ | 预览用默认 props；渲染时可用 CLI flag 覆盖 |

官方补充：
- 用 `<Folder name="...">` 可以把组合分组到 Studio 侧边栏。【官方】
- **`defaultProps` 传超大对象会变慢**，官方有专门页面讨论规避方式。【官方：<https://v3.remotion.dev/docs/troubleshooting/defaultprops-too-big>】
- `defaultProps` 与 props 的类型安全靠 `React.FC<{}>` 泛型，**v3 没有任何运行时校验**。

#### A1.3 v3 下如何做 props 校验（zod）——必须自己实现

v3 没有 `schema` prop，所以：

```ts
// src/schema.ts —— 用 zod 定义，但校验要自己做
import { z } from "zod";

export const shotPropsSchema = z.object({
  title: z.string(),
  orientation: z.enum(["landscape", "portrait"]),
  voiceover: z.string(),        // public/ 下的 wav 文件名
  srt: z.string(),              // public/ 下的 srt 文件名
  cards: z.array(
    z.object({
      id: z.string(),
      kind: z.enum(["title", "bullets", "quote", "chart", "outro"]),
      startMs: z.number(),
      endMs: z.number(),
      text: z.string().optional(),
      bullets: z.array(z.string()).optional(),
    })
  ),
});

export type ShotProps = z.infer<typeof shotPropsSchema>;
```

```tsx
// src/Root.tsx
import { Composition, Folder } from "remotion";
import { NewsVideo } from "./NewsVideo";
import { shotPropsSchema, type ShotProps } from "./schema";

const defaultProps: ShotProps = shotPropsSchema.parse({
  title: "示例新闻",
  orientation: "landscape",
  voiceover: "voice.wav",
  srt: "voice.srt",
  cards: [],
});

export const RemotionRoot = () => (
  <>
    <Folder name="News">
      <Composition<ShotProps>
        id="News-Landscape"
        component={NewsVideo}
        width={1920}
        height={1080}
        fps={30}
        durationInFrames={30 * 30}
        defaultProps={defaultProps}
      />
      <Composition<ShotProps>
        id="News-Portrait"
        component={NewsVideo}
        width={1080}
        height={1920}
        fps={30}
        durationInFrames={30 * 30}
        defaultProps={{ ...defaultProps, orientation: "portrait" }}
      />
    </Folder>
  </>
);
```

**在 Pipeline 里做真正的校验**（推荐做法）：

```ts
// scripts/validate-props.ts —— 在渲染前用 Node 校验 Python 生成的 props.json
import { readFileSync } from "node:fs";
import { shotPropsSchema } from "../src/schema";

const raw = JSON.parse(readFileSync(process.argv[2], "utf8"));
const parsed = shotPropsSchema.parse(raw);        // 校验失败直接抛错，渲染不会开始
console.log(JSON.stringify(parsed));
```

> **v4 的写法（供迁移参考）**【官方：<https://www.remotion.dev/docs/zod-types/>、<https://www.remotion.dev/docs/4-0-migration>】
> - v4 起 `<Composition>` 接受 `schema` prop，类型为 `TComposition<Schema extends AnyZodObject, Props>`；
> - `@remotion/zod-types` 提供 Remotion 专用 Zod 类型：`zColor()`（取色器）、`zTextarea()`（多行文本，Studio 里显示为 textarea）、`zMatrix()`；
> - 自 v4.0.426 起 `@remotion/zod-types` 基于 **Zod v4**；若要继续用 Zod 3.22.3，需改用 `@remotion/zod-types-v3`。
> - 校验失败时 Studio 会直接给出可视化错误，比手工 parse 体验好很多。

---

### A2. 动画 API：签名、参数表与可运行代码

#### A2.1 `useCurrentFrame()` 【官方：<https://v3.remotion.dev/docs/use-current-frame>】

```tsx
import { useCurrentFrame } from "remotion";

const frame = useCurrentFrame(); // 从 0 开始的整数
```

关键语义（官方在 Sequence 页明确写出）：**`<Sequence>` 内所有子组件的 `useCurrentFrame()` 值会被 `from` 偏移**。例如外层 `from={30}`，视频第 30 帧时子组件看到的是 `0`；`from={-15}` 表示内容已经被"提前播放"了 15 帧（用于裁剪开头）。【官方：<https://v3.remotion.dev/docs/sequence>】

#### A2.2 `useVideoConfig()` 【官方：<https://v3.remotion.dev/docs/use-video-config>】

返回对象包含：`width`、`height`、`fps`、`durationInFrames`、`id`、`defaultProps`。

```tsx
import { useVideoConfig } from "remotion";

const { width, height, fps, durationInFrames, id, defaultProps } = useVideoConfig();
```

#### A2.3 `interpolate()` 【官方：<https://v3.remotion.dev/docs/interpolate>】

```ts
interpolate(
  input: number,
  inputRange: number[],   // 支持多点，如 [0, 20, durationInFrames - 20, durationInFrames]
  outputRange: number[],  // 与 inputRange 等长
  options?: {
    extrapolateLeft?: "extend" | "clamp" | "identity";   // 默认 "extend"
    extrapolateRight?: "extend" | "clamp" | "identity";  // 默认 "extend"
    easing?: (input: number) => number;                  // 默认恒等（线性）
  }
): number
```

自 **v3.3.77** 起导出类型 `ExtrapolateType` 与 `InterpolateOptions`：

```tsx
import { ExtrapolateType, InterpolateOptions } from "remotion";
const extrapolate: ExtrapolateType = "clamp";
const option: InterpolateOptions = { extrapolateLeft: extrapolate };
```

可运行示例（淡入淡出 + 弹簧驱动 + 夹紧）：

```tsx
import React from "react";
import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export const FadeAndSlide: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const opacity = interpolate(
    frame,
    [0, 20, durationInFrames - 20, durationInFrames],
    [0, 1, 1, 0]
  );

  const driver = spring({ frame, fps });
  const translateY = interpolate(driver, [0, 1], [60, 0]);

  const scale = interpolate(frame, [0, 20], [0.9, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.8, 0.22, 0.96, 0.65),
  });

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <div
        style={{
          opacity,
          transform: `translateY(${translateY}px) scale(${scale})`,
          color: "#fff",
          fontSize: 64,
        }}
      >
        中文科技新闻标题
      </div>
    </AbsoluteFill>
  );
};
```

补充：`interpolate(1.5, [0,1], [0,2], { extrapolateRight: "extend" }) === 3`，`"clamp"` 得 `2`，`"identity"` 得 `1.5`。【官方】

#### A2.4 `spring()` 【官方：<https://v3.remotion.dev/docs/spring>】

参数表：

| 参数 | 默认值 | 版本 | 说明 |
|---|---|---|---|
| `frame` | — | — | 当前帧；延迟动画可传 `frame - 20` |
| `from` | `0` | — | 起始值 |
| `to` | `1` | — | 结束值（可能过冲） |
| `fps` | — | — | 必须是 `useVideoConfig().fps` |
| `reverse` | `false` | v3.3.92 | 反向播放 |
| `config.mass` | `1` | — | 质量，减小则更快 |
| `config.damping` | `10` | — | 阻尼 |
| `config.stiffness` | `100` | — | 刚度（越大越弹） |
| `config.overshootClamping` | `false` | — | 是否禁止过冲 |
| `durationInFrames` | — | v3.0.27 | 把曲线拉伸到指定帧数 |
| `durationRestThreshold` | — | v3.0.27 | 判定"结束"的接近程度，仅在给了 `durationInFrames` 时生效 |
| `delay` | — | v3.3.90 | 延迟帧数 |

**执行顺序**（官方明确）：① 先按 `durationInFrames` 拉伸 → ② 再按 `reverse` 反向 → ③ 最后按 `delay` 延迟。【官方】

```tsx
import React from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";

export const SpringDemo: React.FC<{ delay?: number; stiffness?: number }> = ({
  delay = 0,
  stiffness = 100,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const scale = spring({
    frame,
    fps,
    from: 0.6,
    to: 1,
    config: { stiffness, damping: 12, mass: 1, overshootClamping: false },
    durationInFrames: 30,
    delay,
  });

  return <div style={{ transform: `scale(${scale})` }}>镜头卡入场</div>;
};
```

#### A2.5 `<Sequence>` 【官方：<https://v3.remotion.dev/docs/sequence>】

| Prop | 类型 | 默认 | 版本 | 说明 |
|---|---|---|---|---|
| `from` | `number` | `0` | v3.2.36 起可选（之前必填） | 子组件"视频开始"的帧；负值=裁掉开头 |
| `durationInFrames` | `number` | `Infinity` | — | 超出范围子组件会被 unmount |
| `name` | `string` | — | — | 仅用于 Studio 时间轴标签 |
| `layout` | `"absolute-fill" \| "none"` | `"absolute-fill"` | v1.4 | 默认包一层 `<AbsoluteFill>`；`"none"` 时不能设置 `style`/`className` |
| `style` | `React.CSSProperties` | — | v3.0.27 | 应用在容器上 |
| `className` | `string` | — | v3.3.45 | 应用在容器上 |
| `ref` | `React.Ref<HTMLDivElement>` | — | v3.2.13 | — |

嵌套会级联（`from={30}` 里再套 `from={60}`，孙组件在 90 帧开始）。裁剪开头 + 延迟需要两层嵌套：

```tsx
<Sequence from={30}>
  <Sequence from={-15}>
    <BlueSquare />
  </Sequence>
</Sequence>
```

> `@remotion/three` 的 `<ThreeCanvas>` 内使用 `<Sequence>` 必须传 `layout="none"`，否则默认的 `<div>` 会报错。【官方】

#### A2.6 `<Series>` / `<Series.Sequence>` 【官方：<https://v3.remotion.dev/docs/series>】

`<Series>` 自身不接 props，只能包含 `<Series.Sequence>`；`<Series.Sequence>` 的 props：

| Prop | 说明 | 版本 |
|---|---|---|
| `durationInFrames` | 必填；**只有最后一个可以是 `Infinity`**，其余必须为正整数 | — |
| `offset` | 正数=延迟并留白；负数=提前开始并与前一个重叠；偏移会顺延影响后面的序列 | — |
| `layout` | `"absolute-fill"`（默认）/ `"none"` | — |
| `style` | 容器样式 | v3.3.4 |
| `className` | 容器类名 | v3.3.45 |
| `ref` | `React.Ref<HTMLDivElement>` | v3.3.4 |

```tsx
import React from "react";
import { Series } from "remotion";
import { TitleCard, BulletsCard, OutroCard } from "./cards";

export const NewsVideo: React.FC = () => (
  <Series>
    <Series.Sequence durationInFrames={40}>
      <TitleCard />
    </Series.Sequence>
    <Series.Sequence durationInFrames={60} offset={-5}>
      <BulletsCard />
    </Series.Sequence>
    <Series.Sequence durationInFrames={90}>
      <OutroCard />
    </Series.Sequence>
  </Series>
);
```

> 对本项目更实用的模式：**用画面卡（shot）的毫秒时间轴驱动 `Sequence from/durationInFrames`**，而不是用 `Series` 的固定帧数——因为配音长度是变动的。见 A3.4。

#### A2.7 `<AbsoluteFill>` 【官方：<https://v3.remotion.dev/docs/absolute-fill>】

```ts
const style: React.CSSProperties = {
  position: "absolute",
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  width: "100%",
  height: "100%",
  display: "flex",
  flexDirection: "column",
};
```

支持 `ref`（v3.2.13 起，类型 `HTMLDivElement`）。【官方】

#### A2.8 `Easing` 【官方：<https://v3.remotion.dev/docs/easing>】

API 与 React Native 的 `Easing` 完全一致（官方原话）。方法表：

| 方法 | 签名 | 说明 |
|---|---|---|
| `step0` | `static step0(n)` | 任意正值返回 1 |
| `step1` | `static step1(n)` | n >= 1 返回 1 |
| `linear` | `static linear(t)` | `f(t)=t` |
| `ease` | `static ease(t)` | 基本惯性（cubic-bezier(.42,0,1,1)） |
| `quad` | `static quad(t)` | `t*t` |
| `cubic` | `static cubic(t)` | `t*t*t` |
| `poly` | `static poly(n)` | 返回 `t^n` 的缓动 |
| `sin` | `static sin(t)` | 正弦 |
| `circle` | `static circle(t)` | 圆形 |
| `exp` | `static exp(t)` | 指数 |
| `elastic` | `static elastic(bounciness)` | 默认 bounciness=1 |
| `back` | `static back(s)` | 回拉 |
| `bounce` | `static bounce(t)` | 弹跳 |
| `bezier` | `static bezier(x1,y1,x2,y2)` | 三次贝塞尔，等价 CSS `transition-timing-function` |
| `in` / `out` / `inOut` | `static in(easing)` … | 包装器：正向 / 反向 / 对称 |

```tsx
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";

export const EasingDemo: React.FC = () => {
  const frame = useCurrentFrame();
  const scale = interpolate(frame, [0, 100], [0, 1], {
    easing: Easing.bezier(0.8, 0.22, 0.96, 0.65),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return <AbsoluteFill style={{ transform: `scale(${scale})`, backgroundColor: "red" }} />;
};
```

---

### A3. 音频 / 视频 / staticFile / 动态时长

#### A3.1 `<Audio>` 【官方：<https://v3.remotion.dev/docs/audio>】

| Prop | 类型 | 版本 | 说明 |
|---|---|---|---|
| `src` | `string` | — | 用 `staticFile("voice.wav")` 指向 `public/`，或直接填 URL |
| `volume` | `number \| (frame: number) => number` | — | 回调版里"音频开始播放的第一帧"编号为 `0`（与 `useCurrentFrame()` 无关）；**官方推荐用回调**，可绘制音量曲线且性能更好 |
| `startFrom` | `number`（帧） | — | 裁掉音频开头 |
| `endAt` | `number`（帧） | — | 裁掉音频结尾 |
| `playbackRate` | `number` | v2.2.0 | 0.5=变慢一倍；Chrome 对 <0.0625 或 >16 会抛错 |
| `muted` | `boolean` | v2.0.0 | 可随时间变化 |
| `loop` | `boolean` | v3.2.29 | 循环 |
| `acceptableTimeShiftInSeconds` | `number` | v3.2.42 | 默认 `0.45`，超出则 seek |
| `allowAmplificationDuringRender` | `boolean` | v3.3.17 | 允许 `volume > 1` 在渲染时真正放大（预览时被限制为 1） |

配音 + BGM 的实战写法（包含 BGM 淡入淡出与"配音期间压低 BGM"）：

```tsx
import React from "react";
import { AbsoluteFill, Audio, Sequence, interpolate, staticFile, useVideoConfig } from "remotion";

export const AudioMix: React.FC<{
  voiceover: string;
  bgm: string;
  voiceDurationInFrames: number; // 配音占的帧数
  fps: number;
}> = ({ voiceover, bgm, voiceDurationInFrames, fps }) => {
  const { durationInFrames } = useVideoConfig();
  const FADE = Math.round(0.5 * fps); // 0.5s 淡入淡出

  return (
    <AbsoluteFill>
      {/* 配音：从 0 帧开始 */}
      <Audio src={staticFile(voiceover)} volume={1} />

      {/* BGM：全程，但配音期间自动压低到 0.12 */}
      <Audio
        loop
        src={staticFile(bgm)}
        volume={(f) => {
          const fadeIn = interpolate(f, [0, FADE], [0, 1], { extrapolateRight: "clamp" });
          const fadeOut = interpolate(
            f,
            [durationInFrames - FADE, durationInFrames],
            [1, 0],
            { extrapolateLeft: "clamp" }
          );
          const duck = f < voiceDurationInFrames ? 0.12 : 0.55;
          return Math.max(0, Math.min(1, 0.55 * fadeIn * fadeOut * (duck / 0.55)));
        }}
      />
    </AbsoluteFill>
  );
};
```

> 更精确的"ducking"应按 `srt` 的时间轴判断当前帧是否在说话，可用 `Sequence` 分段或用上面的帧区间判断。

#### A3.2 `<Video>` 【官方：<https://v3.remotion.dev/docs/video>】

- 包装原生 `HTMLVideoElement`，**除 `autoplay` 和 `controls` 外**原生 props 都会透传；可用任意 CSS。
- 支持 `startFrom` / `endAt` / `style` / `volume`（含逐帧函数）/ `playbackRate`（v2.2.0）/ `muted` / `loop`（v3.2.29）/ `acceptableTimeShiftInSeconds`（v3.2.42）/ `allowAmplificationDuringRender`（v3.3.17）/ `onError`。
- `<Video>` 的音频也会进入输出。

#### A3.3 `<OffthreadVideo>` 【官方：<https://v3.remotion.dev/docs/offthreadvideo>】

**渲染时用 FFmpeg 在浏览器之外抽帧，然后放进 `<Img>` 里显示；预览时仍是 `<video>`。** 自 v3.0.11 起可用。官方推荐在渲染时优先使用它而不是 `<Video>`。【官方：<https://v3.remotion.dev/docs/performance> "Videos" 一节】

- 支持 `volume` / `playbackRate` / `muted` / `acceptableTimeShiftInSeconds` / `onError` / `className` / `style`。
- `imageFormat`（v3.0.22）：`"jpeg"`（默认）或 `"png"`；`png` 可显示透明视频（VP8/VP9/ProRes），但慢约 40%（VP8 会慢得多）。**v4 起该 prop 被移除，改为 `transparent`。**
- **不支持 `loop`**，官方给了用 `getVideoMetadata()` + `<Loop>` 自己实现的示例。
- 性能陷阱：**不要在超出视频长度后继续嵌入该视频**（例如 5 秒素材放进 10 秒组合）；最后一帧的抽取代价显著高于已知时间戳的帧。【官方】

#### A3.4 `staticFile()` 与 `public/` 规则 【官方：<https://v3.remotion.dev/docs/staticfile>】

- `staticFile()` 自 **v2.5.7** 起可用，把 `public/` 里的文件转成 URL，例如 `staticFile("/my-image.png")` → `"/static-32e8nd/my-image.png"`。
- **`public/` 必须和「包含 `remotion` 依赖的 `package.json`」在同一个目录**，即使 Remotion 代码在子目录里也一样。【官方原话】
- 为什么不直接写字符串路径：避免部署到子目录时断裂、避免与组合名冲突、保持框架无关。
- 可用 `getStaticFiles()` 列出 `public/` 全部文件。
- 自定义 public 目录：`Config.setPublicDir()`（v3.2.13）/ CLI `--public-dir` / `bundle({ publicDir })`。
- 典型目录结构：

```txt
my-video/
├─ node_modules/
├─ public/
│  ├─ voiceover.wav          # 现成配音
│  ├─ voiceover.srt          # 现成字幕
│  ├─ bgm-tech-pulse.mp3     # BGM
│  ├─ Noto_Sans_SC_Bold.woff2 # 中文字体
├─ src/
│  ├─ Root.tsx
│  ├─ index.ts
├─ package.json
```

#### A3.5 `@remotion/media-utils` 【官方：<https://v3.remotion.dev/docs/media-utils/>】

官方定位原话：**"a package providing utility functions for getting information about video and audio, and for visualizing audio"**；除 `useAudioData()` 外所有函数也可在 Remotion 之外使用。**包里没有任何合成/生成函数。**

v3/v4 文档中列出的函数：

| 函数 | 用途 |
|---|---|
| `getAudioDurationInSeconds(src)` | 返回 `Promise<number>`，音频时长（秒）。**v3 之前叫 `getAudioDuration()`**；内部会创建一个隐藏 `<audio>` 标签加载音频【官方：<https://v3.remotion.dev/docs/get-audio-duration-in-seconds>】 |
| `getVideoMetadata(src)` | 视频元数据（`durationInSeconds` 等） |
| `getAudioData(src)` | 解码为音频数据（可视化用） |
| `useAudioData(src)` | 上面函数的 hook 版本 |
| `useWindowedAudioData(src)` | 只解码窗口内的音频数据 |
| `visualizeAudio(...)` | 把音频数据转成频谱柱 |
| `visualizeAudioWaveform(...)` | 波形 |
| `getWaveformPortion(...)` | 取波形片段 |
| `createSmoothSvgPath(...)` | 平滑 SVG 路径 |
| `audioBufferToDataUrl(audioBuffer)` | **把 `AudioBuffer` 转成 Base64 Data URL**，可喂给 `<Audio src=...>` |
| `getImageDimensions(src)` | 图片尺寸 |

`audioBufferToDataUrl()` 是从「读」跨越到「写」的唯一桥梁——它是 BGM/音效在浏览器内生成为音频轨的关键函数。【官方：<https://www.remotion.dev/docs/audio-buffer-to-data-url>】

#### A3.6 动态时长

**(a) v3 官方做法 1：基于 input props** 【官方：<https://v3.remotion.dev/docs/dynamic-metadata>】

```tsx
// src/Root.tsx
import { Composition, getInputProps } from "remotion";

const inputProps = getInputProps();

export const Index = () => (
  <Composition
    id="MyComposition"
    component={MyComponent}
    width={1920}
    height={1080}
    fps={30}
    durationInFrames={inputProps?.duration ?? 20} // 预览时用 fallback
  />
);
```

**(b) v3 官方做法 2：异步信息（例如用 `getAudioDurationInSeconds` 探测配音长度）** 【官方：<https://v3.remotion.dev/docs/dynamic-metadata>】

```tsx
// src/Root.tsx
import React, { useEffect, useState } from "react";
import { Composition, continueRender, delayRender, staticFile } from "remotion";
import { getAudioDurationInSeconds } from "@remotion/media-utils";
import { NewsVideo } from "./NewsVideo";

const FPS = 30;

export const Index: React.FC = () => {
  const [handle] = useState(() => delayRender());
  const [duration, setDuration] = useState(1);

  useEffect(() => {
    getAudioDurationInSeconds(staticFile("voiceover.wav"))
      .then((seconds) => {
        setDuration(Math.ceil(seconds * FPS) + 15); // 尾巴留 0.5s
        continueRender(handle);
      })
      .catch((err) => {
        console.error(`Error fetching metadata: ${err}`);
      });
  }, [handle]);

  return (
    <Composition
      id="News-Landscape"
      component={NewsVideo}
      width={1920}
      height={1080}
      fps={FPS}
      durationInFrames={duration}
    />
  );
};
```

**(c) v3 SSR 侧的配套要求**（很容易踩坑）：`getCompositions()` 与 `renderFrames()` / `renderMedia()` **都要传同一个 `inputProps`**，否则动态时长在两阶段算出来不一致。【官方：<https://v3.remotion.dev/docs/dynamic-metadata>】

```ts
const comps = await getCompositions(bundled, { inputProps });
// ...
await renderMedia({ composition, serveUrl: bundled, inputProps, codec: "h264", outputLocation });
```

**(d) v4 做法：`calculateMetadata()`** 【官方：<https://www.remotion.dev/docs/calculate-metadata>，标注 `[v4.0.0]`】

```tsx
import React from "react";
import { CalculateMetadataFunction, Composition } from "remotion";
import { MyComponent, MyComponentProps } from "./MyComp";

const calculateMetadata: CalculateMetadataFunction<MyComponentProps> = ({
  props, defaultProps, abortSignal, compositionId, isRendering,
}) => {
  return {
    durationInFrames: props.duration,
    props,
    defaultCodec: "h264",
    defaultVideoImageFormat: "png",
    defaultPixelFormat: "yuv420p",
    defaultProResProfile: "hq",
    defaultSampleRate: 44100,
  };
};

export const Root: React.FC = () => (
  <Composition
    id="MyComp"
    component={MyComponent}
    durationInFrames={300}
    fps={30}
    width={1920}
    height={1080}
    defaultProps={{ text: "Hello World", duration: 1 }}
    calculateMetadata={calculateMetadata}
  />
);
```

要点（官方）：
- `calculateMetadata` **只被调用一次**，与渲染并发度无关，运行在单独的标签页里，由 `selectComposition()` 触发；
- 可以 async，但必须在 `delayRender` 的超时时间内 resolve；
- 返回的 `defaultCodec` 优先级：低于显式传给 `renderMedia()` 的选项、高于配置文件；
- **Studio 里每次改 props 都会重新执行**——所以别在里面做昂贵操作。

---

### A4. 字幕：v3 没有官方 captions 支持

**核实结论：`@remotion/captions`、`parseSrt()`、`createTikTokStyleCaptions()` 全部是 v4.0 引入的，v3 官方文档站无此页面。**
- `https://v3.remotion.dev/docs/captions` → **HTTP 404**（实测）
- `https://www.remotion.dev/docs/captions/` → 存在，含 Importing from .srt / Transcribing / Displaying / Exporting 四个子页 + `@remotion/captions` API reference

#### A4.1 v3 下解析 SRT 的正确姿势（自己写解析器）

SRT 格式简单，v3 下用正则解析即可。下面是一个可直接用的实现（含中文/`\r\n`/多余空行容错）：

```ts
// src/parseSrt.ts —— v3 自研 SRT 解析（v4 可直接用 @remotion/captions 的 parseSrt）

export type Caption = {
  text: string;
  startMs: number;
  endMs: number;
  timestampMs: number | null;
  confidence: number | null;
};

const TIME_RE = /(\d{2}):(\d{2}):(\d{2})[,.](\d{3})/;

function toMs(h: string, m: string, s: string, ms: string) {
  return (+h * 3600 + +m * 60 + +s) * 1000 + +ms;
}

export function parseSrt(input: string): { captions: Caption[] } {
  const normalized = input.replace(/\r\n/g, "\n").replace(/\r/g, "\n").trim();
  const blocks = normalized.split(/\n{2,}/);
  const captions: Caption[] = [];

  for (const block of blocks) {
    const lines = block.split("\n").filter((l) => l.trim() !== "");
    if (lines.length === 0) continue;

    const arrowIndex = lines.findIndex((l) => l.includes("-->"));
    if (arrowIndex === -1) continue;

    const times = lines[arrowIndex].match(
      new RegExp(`${TIME_RE.source}\\s*-->\\s*${TIME_RE.source}`)
    );
    if (!times) continue;

    const startMs = toMs(times[1], times[2], times[3], times[4]);
    const endMs = toMs(times[5], times[6], times[7], times[8]);
    const text = lines.slice(arrowIndex + 1).join("\n").trim();
    if (!text) continue;

    captions.push({ text, startMs, endMs, timestampMs: startMs, confidence: null });
  }

  return { captions };
}
```

#### A4.2 v3 下显示字幕（按 srt 时间轴切 Sequence）

```tsx
// src/Captions.tsx
import React, { useEffect, useState } from "react";
import {
  AbsoluteFill, Sequence, continueRender, delayRender, staticFile, useVideoConfig,
} from "remotion";
import { parseSrt, type Caption } from "./parseSrt";

const SAFE_BOTTOM_PX = 320; // 竖屏避让底部信息栏，见 B11
const SAFE_TOP_PX = 108;

export const Captions: React.FC<{ srt: string; portrait: boolean; fontSize?: number }> = ({
  srt, portrait, fontSize = 54,
}) => {
  const { fps } = useVideoConfig();
  const [captions, setCaptions] = useState<Caption[] | null>(null);
  const [handle] = useState(() => delayRender("load srt"));

  useEffect(() => {
    fetch(staticFile(srt))
      .then((r) => r.text())
      .then((text) => {
        setCaptions(parseSrt(text).captions);
        continueRender(handle);
      })
      .catch((e) => console.error(e));
  }, [srt, handle]);

  if (!captions) return null;

  return (
    <AbsoluteFill>
      {captions.map((c, i) => {
        const from = Math.round((c.startMs / 1000) * fps);
        const durationInFrames = Math.max(
          1,
          Math.round(((c.endMs - c.startMs) / 1000) * fps)
        );
        return (
          <Sequence key={i} from={from} durationInFrames={durationInFrames}>
            <AbsoluteFill
              style={{
                justifyContent: "flex-end",
                alignItems: "center",
                paddingBottom: portrait ? SAFE_BOTTOM_PX : 120,
                paddingTop: portrait ? SAFE_TOP_PX : 60,
                paddingLeft: portrait ? 120 : 160,
                paddingRight: portrait ? 180 : 160,
              }}
            >
              <div
                style={{
                  fontSize,
                  lineHeight: 1.35,
                  fontWeight: 800,
                  color: "#fff",
                  whiteSpace: "pre",
                  textAlign: "center",
                  textShadow: "0 4px 24px rgba(0,0,0,0.85)",
                  fontFamily: "Noto Sans SC",
                }}
              >
                {c.text}
              </div>
            </AbsoluteFill>
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
```

#### A4.3 v4 官方 captions 用法与版本要求

以下片段来自 v4 官方文档（**v3 用户不可直接用**）：

```tsx
// 读取并解析 .srt 【官方：https://www.remotion.dev/docs/captions/importing】
import { useState, useEffect, useCallback } from "react";
import { AbsoluteFill, staticFile, useDelayRender } from "remotion";
import { parseSrt } from "@remotion/captions";
import type { Caption } from "@remotion/captions";

export const MyComponent: React.FC = () => {
  const [captions, setCaptions] = useState<Caption[] | null>(null);
  const { delayRender, continueRender, cancelRender } = useDelayRender();
  const [handle] = useState(() => delayRender());

  const fetchCaptions = useCallback(async () => {
    try {
      const response = await fetch(staticFile("subtitles.srt"));
      const text = await response.text();
      const { captions: parsed } = parseSrt({ input: text });
      setCaptions(parsed);
      continueRender(handle);
    } catch (e) {
      cancelRender(e);
    }
  }, [continueRender, cancelRender, handle]);

  useEffect(() => {
    fetchCaptions();
  }, [fetchCaptions]);

  if (!captions) return null;
  return <AbsoluteFill>{/* Use captions here */}</AbsoluteFill>;
};
```

```tsx
// 分页成"抖音样式"字幕 【官方：https://www.remotion.dev/docs/captions/displaying】
import { createTikTokStyleCaptions } from "@remotion/captions";

const { pages } = useMemo(() => {
  return createTikTokStyleCaptions({
    captions,
    combineTokensWithinMilliseconds: SWITCH_CAPTIONS_EVERY_MS,
  });
}, [captions]);
```

```tsx
// 逐词高亮 【官方：https://www.remotion.dev/docs/captions/displaying】
const CaptionPage: React.FC<{ page: TikTokPage }> = ({ page }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentTimeMs = (frame / fps) * 1000;
  const absoluteTimeMs = page.startMs + currentTimeMs;

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <div style={{ fontSize: 80, fontWeight: "bold", textAlign: "center", whiteSpace: "pre" }}>
        {page.tokens.map((token, tokenIndex) => {
          const isActive = token.fromMs <= absoluteTimeMs && token.toMs > absoluteTimeMs;
          return (
            <span key={`${token.fromMs}-${tokenIndex}`} style={{ color: isActive ? "#39E508" : "white" }}>
              {token.text}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
```

**版本要求小结**：
- `@remotion/captions`：**v4.0+**（v3 无）
- `useDelayRender()` 这个 hook：**v4**（v3 用 `delayRender()` / `continueRender()` / `cancelRender()` 顶层函数）
- `Caption` / `TikTokPage` 类型：v4
- 另有 `@remotion/install-whisper-cpp`、`@remotion/openai-whisper`、`@remotion/whisper-web`、`@remotion/whisper-webgpu` 用于**从音频转写**生成字幕（v4 生态）。本项目已有现成 srt，不需要这部分。

---

### A5. 渲染：CLI 参数完整列表与 Node API

#### A5.1 `npx remotion render` 参数表 【官方：<https://v3.remotion.dev/docs/cli/render>】

```
npx remotion render <entry-file> [<composition-id>] [<output-location>]
```

入口文件探测优先级：① `Config.setEntryPoint()` → ② `src/index.ts` / `src/index.tsx` / `src/index.js` / `remotion/index.ts` / `app/remotion/index.ts` → ③ 失败。不传 `output-location` 则输出到 `out/`。

| Flag | 取值 / 说明 | 版本 |
|---|---|---|
| `--props` | 序列化 JSON 字符串 **或 JSON 文件路径**；`getInputProps()` 读取。**Windows 不支持内联 JSON** | — |
| `--height` | 覆盖组合高度 | v3.2.40 |
| `--width` | 覆盖组合宽度 | v3.2.40 |
| `--concurrency` | CPU 线程数，最小 1，最大 `os.cpus().length`，也支持百分比（如 `50%`） | — |
| `--pixel-format` | 自定义像素格式（如 `yuv420p`、`yuv444p`） | — |
| `--image-format` | `jpeg`（默认，更快，不支持透明）/ `png` | v1.4.0 |
| `--config` | 指定配置文件位置 | v1.2.0 |
| `--env-file` | dotenv 文件位置，默认 `.env` | v2.2.0 |
| `--quality` | JPEG 质量 0–100（PNG 时无效）。**v4 改名为 `--jpeg-quality`** | v1.4.0 |
| `--overwrite` | 默认开启；用 `--overwrite=false` 关闭 | — |
| `--sequence` | 输出图片序列而非视频 | v1.4.0 |
| `--codec` | `h264`(默认) / `h265` / `png` / `vp8` / `vp9` / `mp3` / `aac` / `wav` / `prores` / `h264-mkv` | v1.4.0 |
| `--audio-codec` | `pcm-16` / `aac` / `mp3` / `opus` | v3.3.42 |
| `--audio-bitrate` | FFmpeg `-b:a` 语法，如 `128K`、`1M`；默认 `320k` | v3.2.32 |
| `--video-bitrate` | FFmpeg `-b:v` 语法；**与 `--crf` 互斥** | v3.2.32 |
| `--prores-profile` | `4444-xq`/`4444`/`hq`/`standard`/`light`/`proxy`，默认 `hq`，仅 prores 有效 | v2.1.6 |
| `--crf` | 最小 0（v2.1.3 起禁止为 0，建议 ≥1）；**与 `--video-bitrate` 互斥** | v1.4.0 |
| `--browser-executable` | Chrome 路径；不指定且找不到会自动下载 | v1.5.0 |
| `--scale` | 输出缩放系数，`0 < scale <= 16`，默认 1 | — |
| `--frames` | 渲染子集，如 `--frames=0-9` | v2.0.0 |
| `--every-nth-frame` | 只渲染每第 n 帧，**仅 GIF 有效** | v3.1.0 |
| `--muted` | 关闭音频输出，仅视频渲染可用 | v3.2.1 |
| `--enforce-audio-track` | 即使没有音频也渲染一条静音轨 | v3.2.1 |
| `--number-of-gif-loops` | GIF 循环次数，仅 GIF | v3.1.0 |
| `--bundle-cache` | Webpack 缓存，默认开启；`--bundle-cache=false` 关闭 | v2.0.0 |
| `--log` | `error` / `warn` / `info`（默认）/ `verbose` | — |
| `--port` | 自定义 HTTP 端口 | — |
| `--public-dir` | `public/` 目录位置 | v3.2.13 |
| `--ffmpeg-executable` | 自定义 ffmpeg（**v4 已移除**） | — |
| `--ffprobe-executable` | 自定义 ffprobe（**v4 已移除**） | v3.0.17 |
| `--timeout` | 单帧 `delayRender()` 超时，默认 `30000` ms | — |
| `--ignore-certificate-errors` | 忽略无效 SSL 证书 | v2.6.5 |
| `--disable-web-security` | 关闭 CORS 等安全特性 | v2.6.5 |
| `--disable-headless` | 打开真实浏览器窗口观察渲染 | v2.6.5 |
| `--gl` | `angle` / `egl` / `swiftshader` / `swangle` / `null`；**本地默认 `null`**，Lambda 默认 `swangle` | — |
| `--user-agent` | 自定义 UA | v3.3.83 |

**不存在的 flag（避免误用）**：`--pixel-format` 以外的像素格式 flag、`--parallelism`（v3.2.17 起改名为 `concurrency`）、`--entry`（入口是位置参数）。

#### A5.2 `npx remotion still` 【官方：<https://v3.remotion.dev/docs/cli/still>】

```
npx remotion still <entry-file> [<composition-id>] [<output-location>]
```

独有 flag：`--frame`（默认 `0`；**v3.2.27 起支持负值，`-1` 为最后一帧**）。其余 flags 与 `render` 基本一致（`--props` / `--image-format` / `--config` / `--env-file` / `--quality` / `--overwrite` / `--browser-executable` / `--scale` / `--bundle-cache` / `--log` / `--port` / `--public-dir` / `--ffmpeg-executable` / `--ffprobe-executable` / `--timeout` / `--ignore-certificate-errors` / `--disable-web-security` / `--disable-headless` / `--gl` / `--user-agent`）。

实用场景：**用 still 快速验证"竖屏安全区是否被挡住"**。

```bash
npx remotion still src/index.ts News-Portrait out/check-safe-area.png --frame=90 --props=./props.json
```

#### A5.3 `npx remotion studio`（v3 叫 preview）【官方：<https://v3.remotion.dev/docs/cli/preview>】

- v3 的命令是 `npx remotion preview`；`npx remotion studio` 是 v4 的命令名（v3 文档站的 CLI 列表里只有 `preview`）。
- 提供时间轴、props 编辑、逐帧预览。
- 相关 flag：`--disable-keyboard-shortcuts`、`--webpack-poll`。

#### A5.4 `npx remotion compositions` 【官方：<https://v3.remotion.dev/docs/cli/compositions>】

列出项目中所有可渲染组合（ID、尺寸、fps、时长）。这是 Python 侧"探测有哪些可用组合"的轻量入口：

```bash
npx remotion compositions src/index.ts
```

#### A5.5 `npx remotion benchmark` 【官方：<https://v3.remotion.dev/docs/cli/benchmark>】

官方推荐用它来**寻找最优 `--concurrency`**。【官方：<https://v3.remotion.dev/docs/performance>】

```bash
npx remotion benchmark src/index.ts News-Landscape --concurrency=1,2,4,8
```

#### A5.6 编程式渲染（Node API）—— 工程化调用的关键

**完整流水线示例**（v3 官方 SSR 示例的可运行版）【官方：<https://v3.remotion.dev/docs/ssr>】：

```ts
// render.ts
import { bundle } from "@remotion/bundler";
import { getCompositions, renderMedia, renderStill } from "@remotion/renderer";
import path from "node:path";

const start = async () => {
  const compositionId = "News-Landscape";
  const entry = "./src/index";

  // ① 打包（只需一次，可复用）
  console.log("Creating a Webpack bundle of the video");
  const bundleLocation = await bundle(path.resolve(entry), () => undefined, {
    webpackOverride: (config) => config,
  });

  // ② 参数化输入
  const inputProps = { foo: "bar" };

  // ③ 取出所有组合
  const comps = await getCompositions(bundleLocation, { inputProps });
  const composition = comps.find((c) => c.id === compositionId);
  if (!composition) {
    throw new Error(`No composition with the ID ${compositionId} found. Review "${entry}" for the correct ID.`);
  }

  // ④ 渲染视频
  const outputLocation = `out/${compositionId}.mp4`;
  console.log("Attempting to render:", outputLocation);
  await renderMedia({
    composition,
    serveUrl: bundleLocation,
    codec: "h264",
    outputLocation,
    inputProps,
  });
  console.log("Render done!");
};

start();
```

**各函数签名（v3）**

`bundle()` —— 自 **v3.2.17** 起为新签名（旧的 `(entryPoint, onProgress, options)` 仍兼容）【官方：<https://v3.remotion.dev/docs/bundle>】：

```ts
const bundle: (options?: {
  entryPoint: string;                  // 入口文件的绝对路径
  onProgress?: (progress: number) => void;
  webpackOverride?: WebpackOverrideFn;
  outDir?: string;                     // 不传则用临时目录
  enableCaching?: boolean;             // 默认 true
  publicPath?: string;
  rootDir?: string;                    // 含 package.json 的 Remotion 根目录，默认 cwd
  publicDir?: string | null;
  onPublicDirCopyProgress?: (bytes: number) => void;
  onSymlinkDetected?: (path: string) => void;
}) => Promise<string>;                  // 解析为 bundle 输出目录
```

`getCompositions()`【官方：<https://v3.remotion.dev/docs/renderer/get-compositions>】：

```ts
const getCompositions: (
  bundleOrServeUrl: string,
  options: {
    inputProps?: object | null;
    envVariables?: Record<string, string>;
    puppeteerInstance?: PuppeteerBrowser;
    onBrowserLog?: (log: BrowserLog) => void;
    browserExecutable?: BrowserExecutable;
    ffmpegExecutable?: FfmpegExecutable;
    ffprobeExecutable?: FfmpegExecutable;
    timeoutInMilliseconds?: number;     // 默认 30000
    chromiumOptions?: { disableWebSecurity?: boolean; ignoreCertificateErrors?: boolean; headless?: boolean; gl?: string; userAgent?: string };
  }
) => Promise<TComposition[]>;
```

返回值示例（`defaultProps` 自 v2.5.7 起返回）：

```ts
[
  { id: "HelloWorld", width: 1920, height: 1080, fps: 30, durationInFrames: 120, defaultProps: { title: "Hello World" } },
  { id: "Title", width: 1080, height: 1080, fps: 30, durationInFrames: 90, defaultProps: undefined },
]
```

`renderMedia()`【官方：<https://v3.remotion.dev/docs/renderer/render-media>】关键参数：

| 参数 | 类型 / 默认 | 说明 |
|---|---|---|
| `serveUrl` | `string` | `bundle()` 的产物路径或托管 URL |
| `composition` | `TCompMetadata` | 含 `id/width/height/fps/durationInFrames`，来自 `getCompositions()` |
| `codec` | `"h264"`(默认)/`h265`/`vp8`/`vp9`/`mp3`/`aac`/`wav`/`prores`/`h264-mkv`/`gif` | — |
| `audioCodec` | `"pcm-16"`/`"aac"`/`"mp3"`/`"opus"`（v3.3.41+） | 与 `codec` 同时指定音频时以此为准 |
| `audioBitrate` | `string`，默认 `320k`（v3.2.32） | 与 `crf` 互斥 |
| `videoBitrate` | `string`（v3.2.32） | 与 `crf` 互斥 |
| `inputProps` | `object` | 传给组合，`getInputProps()` 读取 |
| `concurrency` | `number \| string \| null`，默认 CPU 线程的一半（v3.2.17 从 `parallelism` 改名） | — |
| `crf` | `number \| null` | — |
| `imageFormat` | `"jpeg"`(默认)/`"png"`/`"none"`（v3.2.27+） | 渲染纯音频时用 `"none"` |
| `quality` | `number` 0–100，默认交给浏览器（当前 80） | 仅 jpeg |
| `frameRange` | `number \| [number, number] \| null` | 单帧或区间 |
| `muted` / `enforceAudioTrack` | `boolean`（v3.2.1） | — |
| `scale` | `number` | — |
| `outputLocation` | `string`，可选（v3.0.26+）；不传则返回内存 Buffer | 必须是文件路径 |
| `puppeteerInstance` | `puppeteer.Browser` | 复用浏览器可提速；用 `openBrowser()` 创建 |
| `onStart` | `({ frameCount }) => void` | — |
| `onProgress` | `({ progress, renderedFrames, encodedFrames, stitchStage, ... }) => void` | `progress` 自 v3.2.17 起可用 |
| `onDownload` | `(src) => ({ percent, downloaded, totalSize }) => void` | 音频/视频下载进度 |
| `onBrowserLog` | `(log: BrowserLog) => void` | — |
| `timeoutInMilliseconds` | `number`，默认 `30000` | — |
| `cancelSignal` | `CancelSignal`（v3.0.15） | 来自 `makeCancelSignal()` |
| `verbose` / `dumpBrowserLogs` | `boolean` | **v4 起被 `logLevel: "verbose"` 取代** |
| `chromiumOptions.gl` | `"angle"`/`"egl"`/`"swiftshader"`/`"swangle"`/`null` | 本地默认 `null` |
| `chromiumOptions.headless` | `boolean`，默认 `true` | — |
| `ffmpegOverride` | `({ type, args }) => string[]`（v3.2.22） | **官方明确不鼓励**；可能随 patch 版本失效，且在 Lambda 上不可用 |

`renderStill()`【官方：<https://v3.remotion.dev/docs/renderer/render-still>，v2.3+】：

```ts
await renderStill({
  composition,
  serveUrl: bundleLocation,
  output: "/tmp/still.png",     // 绝对路径
  inputProps: { custom: "data" },
  frame: 0,                     // 默认 0；v3.2.27 起支持负值
  imageFormat: "png",           // 默认 "png"（注意与 render 的默认 jpeg 不同）
  scale: 1,
  quality: undefined,           // 仅 jpeg
  overwrite: true,              // 默认 true
  puppeteerInstance: null,
  envVariables: {},
  dumpBrowserLogs: false,
  timeoutInMilliseconds: 30000,
  cancelSignal,                 // v3.0.15
  chromiumOptions: {},
});
```

返回值（v3.3.9+）：`{ buffer }` —— 只在**没有**提供 `output` 选项时返回 Buffer，否则为 `null`。

其他 v3 renderer API：`renderFrames()`（输出图片序列）、`stitchFramesToVideo()`（把图片序列编码成视频）、`openBrowser()`（跨调用共享浏览器实例，显著提速）、`makeCancelSignal()`、`ensureFfmpeg()`、`ensureFfprobe()`、`getCanExtractFramesFast()`。【官方：<https://v3.remotion.dev/docs/renderer>】

**v4 的重要变化**：
- 新增 `selectComposition({ serveUrl, id, inputProps })`，直接按 ID 取组合并执行 `calculateMetadata()`；找不到 ID 会抛错。这比 `getCompositions().find()` 更直接。【官方：<https://www.remotion.dev/docs/renderer/select-composition>】
- `ensureFfmpeg()` / `ensureFfprobe()` / `ffmpegExecutable` / `ffprobeExecutable` 被移除（FFmpeg 内置）。【官方：<https://www.remotion.dev/docs/4-0-migration>】
- `selectComposition()` 增加了 `mediaCacheSizeInBytes`、`offthreadVideoCacheSizeInBytes`、`offthreadVideoThreads`、`chromeMode`、`onBrowserDownload` 等选项（v4.0.x）。【官方】

---

### A6. 多分辨率 / 多比例输出：方案对比

**先明确一个事实**：Remotion 的 `--scale` 是**等比缩放**（`Config.setScale`，v2.6.7+），文档原话是 "useful if you would like to render the video in **multiple resolutions in the same aspect ratio**"。**横屏 16:9 与竖屏 9:16 不是同一宽高比，`--scale` 无法完成。**【官方：<https://v3.remotion.dev/docs/scaling>】

`--scale` 的能力边界（官方原文）：
- 可被放大并真正提升细节的：**文字、SVG、图片**（图片需原始分辨率足够）
- **不能**被放大提升分辨率的：**视频、Canvas/WebGL**
- 取值约束：`0 < scale <= 16`；结果必须是整数像素；MP4 要求两个维度都能被 2 整除；从 1920 降到 1280 建议传 `2/3` 避免舍入误差（**这不能作为 CLI flag 使用**）

#### 方案 1：注册两个 Composition（推荐）⭐

```tsx
<Composition id="News-Landscape" component={NewsVideo}
  width={1920} height={1080} fps={30} durationInFrames={d}
  defaultProps={{ ...props, orientation: "landscape" }} />

<Composition id="News-Portrait" component={NewsVideo}
  width={1080} height={1920} fps={30} durationInFrames={d}
  defaultProps={{ ...props, orientation: "portrait" }} />
```

- ✅ **优点**：`getCompositions()` 能直接列出两个组合，Studio 里可分别预览；布局差异（字号、边距、卡片排布、安全区）可以用 `orientation` prop 走不同分支；时长可以各自独立（竖屏文案有时需要重排导致时长微调）；错误隔离好。
- ❌ **缺点**：如果 `durationInFrames` 是运行时算出来的，两个 `<Composition>` 都要拿到同一个值（v3 里要么在 Root 用一次 `delayRender` 算好，要么 SSR 传 `inputProps`）；组合数量翻倍。
- 对本项目：**推荐**。竖屏与横屏的排版差异（安全区、字号、一行字数）本来就大，一个 `orientation` 分支比统一布局好看得多。

#### 方案 2：同一 Composition + CLI `--width/--height` 覆盖（v3.2.40+）

```bash
npx remotion render src/index.ts News-Landscape out/h.mp4 --props=./props.json
npx remotion render src/index.ts News-Landscape out/v.mp4 --width=1080 --height=1920 --props=./props-portrait.json
```

- ✅ **优点**：只注册一个组合，注册逻辑简单；CLI 层面完全参数化，适合 Python 批量调度。
- ❌ **缺点**：`width/height` 覆盖不会改变你自己的布局代码——你必须从 `useVideoConfig()` 读 `width/height` 来判断横竖屏，或从 `inputProps` 读 `orientation`（**这是一个隐式依赖，容易漏**）；Studio 预览看不到覆盖后的效果（只能看到默认的 1920x1080）；Node API 里 `renderMedia()` 用的是 `getCompositions()` 返回的 `composition` 对象，覆盖宽高需要自己改这个对象或另走 CLI。
- 对本项目：**可用**，但要求布局代码严格以 `useVideoConfig()` 为准，禁止硬编码 `1920`/`1080`。

#### 方案 3：同一 Composition + `--scale` 做"同比例多分辨率"（4K 交付）

```bash
# 1920x1080 的工程渲染成 3840x2160
npx remotion render src/index.ts News-Landscape out/4k.mp4 --scale=2
```

- ✅ **优点**：零布局改动，文字/SVG 真正更高清。
- ❌ **缺点**：只能同比例；对 `<OffthreadVideo>` 嵌入的视频素材**不会**提升细节（源素材分辨率是上限）；渲染成本约随像素数线性上升。
- 用途：**只用于"横屏出 1080p 和 4K 两版"这类同比例需求。**

#### 方案 4：两层（推荐组合）

```
竖屏 1080x1920  → Composition "News-Portrait"（默认尺寸）
横屏 1920x1080  → Composition "News-Landscape"（默认尺寸）
横屏 4K         → "News-Landscape" + --scale=2（可选）
```

用 Python 调度时，一条流水线两端：

```bash
# 横屏
npx remotion render src/index.ts News-Landscape out/news-1920x1080.mp4 \
  --props=./build/props-landscape.json --codec=h264 --crf=18 \
  --audio-codec=aac --audio-bitrate=256K --concurrency=6 --log=info

# 竖屏
npx remotion render src/index.ts News-Portrait out/news-1080x1920.mp4 \
  --props=./build/props-portrait.json --codec=h264 --crf=18 \
  --audio-codec=aac --audio-bitrate=256K --concurrency=6 --log=info
```

---

### A7. 字体：Google Fonts / 本地字体 / 中文字体在 Windows 的注意事项

#### A7.1 `@remotion/google-fonts`（v3.2.40+）【官方：<https://v3.remotion.dev/docs/google-fonts>】

```tsx
import { loadFont } from "@remotion/google-fonts/TitanOne";
const { fontFamily } = loadFont(); // "Titan One"

// 限定 style / weights / subsets（类型安全）
import * as Montserrat from "@remotion/google-fonts/Montserrat";
Montserrat.loadFont("normal", {
  weights: ["400", "600", "800"],
  subsets: ["latin", "latin-ext"],
});
```

注意：**默认会加载所有 style、weight 和 subset**——对 CJK 字体（如 Noto Sans SC）这可能是几十个 woff2 分片文件，会明显拖慢打包与渲染启动。**务必显式指定 `weights` 和 `subsets`。**【官方 + 推断】

`getInfo()` 可以拿到字体的 `unicodeRanges` 与每个子集的具体 woff2 URL，便于排查"某个字没渲染出来"的问题。【官方】

```tsx
import { getInfo } from "@remotion/google-fonts/Montserrat";
console.log(getInfo());
```

#### A7.2 v3 加载本地/中文字体：FontFace API（官方推荐写法）

```tsx
// src/load-fonts.ts —— 放在会被执行到的地方
import { continueRender, delayRender, staticFile } from "remotion";

const waitForFont = delayRender("load Noto Sans SC");

const font = new FontFace(
  `Noto Sans SC`,
  `url('${staticFile("NotoSansSC-Bold.woff2")}') format('woff2')`
);

font
  .load()
  .then(() => {
    document.fonts.add(font);
    continueRender(waitForFont);
  })
  .catch((err) => console.log("Error loading font", err));
```

官方注意事项：
- **URL 必须加引号**（否则会报 "could not be parsed as a value list"）。
- `format` 取值：`woff2` / `woff` / `opentype`（OTF）/ `truetype`（TTF）。
- 之后用 `style={{ fontFamily: "Noto Sans SC" }}` 引用。
- 若 TypeScript 报类型错，安装最新 `@types/web`。

#### A7.3 v4 的 `@remotion/fonts` 的 `loadFont()`（更简洁）

官方描述：**"provides an API for loading local fonts or remote fonts from a URL into a Remotion component."** 只有 `loadFont()` 一个 API。【官方：<https://www.remotion.dev/docs/fonts-api/>】

```tsx
// v4 only
import { loadFont } from "@remotion/fonts";
import { staticFile } from "remotion";

loadFont({
  family: "Noto Sans SC",
  url: staticFile("NotoSansSC-Bold.woff2"),
  weight: "700",
}).then(() => console.log("Font loaded"));
```

v3 只能用 A7.2 的 FontFace 写法（`@remotion/fonts` 在 v3 不存在）。**【官方 + 实测 404 推断】**

#### A7.4 中文字体在 Windows 下的注意事项（重点）

1. **优先用 `woff2` 而不是 `ttf`/`otf`。** 一个完整中文字体 TTF 动辄 10–20 MB，woff2 通常能压到 3–8 MB；而 Chromium 每渲染一个页面实例都要加载字体文件。**【推断，基于文件体积与加载机制】**

2. **考虑子集化（subsetting）**：如果视频里只用到的字符有限（新闻稿+字幕），用 Python 的 `fonttools` 做子集，可以压到几十 KB：

```python
# 用 Python 3.12 做字体子集化（配合 fonttools）
# pip install fonttools brotli
from fontTools import subset

def make_subset(src_ttf: str, text: str, out_woff2: str) -> None:
    opts = subset.Options()
    opts.flavor = "woff2"          # 输出 woff2
    opts.desubroutinize = True
    opts.layout_features = ["*"]
    font = subset.load_font(src_ttf, opts)
    subsetter = subset.Subsetter(options=opts)
    subsetter.populate(text=text)  # 只保留用到的字符
    subsetter.subset(font)
    subset.save_font(font, out_woff2, opts)

if __name__ == "__main__":
    text = open("script.txt", encoding="utf-8").read()
    make_subset("C:/Windows/Fonts/msyh.ttc", text, "public/subset-sc.woff2")
```

3. **不要在 `fontFamily` 里依赖"系统已安装的字体"。** 渲染时是**无头 Chromium**加载的页面环境，虽然它通常能读到系统字体（Windows 上 `C:\Windows\Fonts`），但**官方从未承诺这一行为**，而且 Linux 渲染机上必然不一致。跨机一致性要求下必须用 `staticFile()` + `FontFace` 显式加载。**【推断】**

4. **`document.fonts.add()` 必须在 `continueRender()` 之前完成**，否则会渲染出回退字体（表现为"部分帧字宽不同、排版跳动"）。这是 Remotion 里中文字体最常见的 bug。**【推断，基于官方 FontFace 示例的顺序】**

5. **Windows 系统中文字体路径参考**（仅用于取源文件、做子集化，不要直接引用路径）：`C:\Windows\Fonts\msyh.ttc`（微软雅黑）、`msyhbd.ttc`、`simhei.ttf`（黑体）、`simsun.ttc`（宋体）、`Deng.ttf`（等线）。**注意 `.ttc` 是字体集合，`fonttools` 需要指定 index，且商用授权需要单独确认**（微软雅黑的商用授权受微软许可约束，视频分发属于"内容输出"场景，存在风险）。**【社区/常识，需法务确认】**

6. **推荐用于科技新闻的可商用中文字体**（需自行核对最新许可）：思源黑体/Noto Sans SC、思源宋体/Noto Serif SC（SIL OFL）、霞鹜文楷 LXGW WenKai（SIL OFL）、得意黑 Smiley Sans（SIL OFL）。Google Fonts 上可直接通过 `@remotion/google-fonts/NotoSansSC` 加载。**【社区/推断，许可证请以字体官方页为准】**

7. **渲染时长提示**：CJK 字体分片多，`loadFont()` 若不限 subset，**打包阶段会显著变慢**（几十个 woff2 被打进 bundle / 或运行期大量请求）。建议固定 `subsets: ["chinese-simplified"]` 并只加载实际用到的 2–3 个字重。**【推断】**

---

### A8. 性能与稳定性

#### A8.1 `--concurrency` 调优 【官方：<https://v3.remotion.dev/docs/performance>、<https://v3.remotion.dev/docs/config#setconcurrency>】

- 默认值 `null` = **CPU 线程数的一半**。
- 官方原话：**"A concurrency too high and a concurrency too low can both be counterproductive."**
- 官方建议用 `npx remotion benchmark` 实测最优值；也可以试 `os.cpus().length`（用满所有线程，代价是系统会变卡）。
- **内存压力是主要风险**：官方在 timeout 页明确写着 "When setting the concurrency too high, Chrome might decide to not load some `<Video />`s which can lead to a timeout error"，并把它列为 Remotion 的已知 bug，**规避办法就是降低 concurrency**。
- 实战建议（**【推断】**）：竖屏 1080x1920 素材简单时可用 `cpus-1`；横屏带多个 `<OffthreadVideo>` 时先从中位数（如 4–6）开始压测；16GB 内存机器上，`--concurrency` 超过 8 且含多个视频时很容易触发问题。

#### A8.2 `--gl`（OpenGL 后端）在 Windows 的选择 【官方：<https://v3.remotion.dev/docs/cli/render#--gl>】

取值：`angle` / `egl` / `swiftshader` / `swangle` / `null`。
- **本地渲染默认 `null`**（即 Chromium 默认，Windows 上通常是 D3D11/ANGLE 路径）。
- Lambda 默认 `swangle`（Swiftshader on Angle，Chrome 101 起支持）。
- 历史教训（官方 changelog 注释）：v2.4.3–v2.6.6 默认 `angle`，但**有小的内存泄漏，会让长时间渲染崩溃**——所以不要盲目指定 `angle`。
- 受 GPU 影响的元素：WebGL（Three.js/Skia/P5.js/Mapbox）、2D Canvas、GPU 加速 CSS（`box-shadow`、`filter: blur()`、`filter: drop-shadow()`）。【官方：<https://v3.remotion.dev/docs/performance>】
- **推荐做法（【推断】）**：本项目主要是文字/图形/图片，**保持默认 `null` 不动**；如果遇到"某些帧渲染出黑块/花屏"，再依次尝试 `--gl=angle` 和 `--gl=swangle`；只有在 CI/无 GPU 的 Windows Server 上才考虑显式 `swiftshader`（纯 CPU，最慢但最稳定）。

#### A8.3 Chromium 下载与离线渲染

- **默认行为**：Remotion 会先尝试探测系统已有的 Chrome/Chromium，**找不到就自动下载一个**。【官方：<https://v3.remotion.dev/docs/config#setbrowserexecutable>、<https://v3.remotion.dev/docs/renderer/render-media#browserexecutable>】
- **内网/离线环境**：官方没有"离线包"式的显式说明，但可用 `--browser-executable`（CLI）/ `browserExecutable`（Node API）/ `Config.setBrowserExecutable()` 指向已安装的 Chrome，从而完全不触发下载。v4 还提供 `ensureBrowser()` 与 `onBrowserDownload` 回调来显式控制/观测下载。**【官方 + 推断】**
- **重要陷阱**：官方 timeout 页明确写道——**Linux 上如果没装 Chrome，Remotion 下载的那个 Chromium 不含 MP3/MP4 编解码器**，加载 MP4 或不受支持的音频编码会直接超时。**规避：转成 WebM，或使用真正的 Chrome。** Windows 上同理，建议统一安装 Chrome 并用 `--browser-executable` 指定。**【官方：<https://v3.remotion.dev/docs/timeout>】**

#### A8.4 常见报错与对策

**(1) `A delayRender() was called but not cleared after 28000ms`**【官方：<https://v3.remotion.dev/docs/timeout>】

官方列出的可能原因与对策：

| 原因 | 对策 |
|---|---|
| 调了 `delayRender()` 但从没调 `continueRender()` | 检查代码路径，确保所有分支都会 `continueRender()` |
| 没有网络 / 防火墙拦截（字体、图片、音视频） | 确保所有网络资源可达；云端渲染注意 VPC 出网 |
| 在 Chromium 里加载 MP4 / 不支持的音频编码 | 转 WebM，或改用真 Chrome |
| 内存压力（concurrency 过高导致 Chrome 不加载 `<Video>`） | **降低 concurrency** |
| Remotion 版本太旧 | 升级 |
| 确实需要更长时间（昂贵 WebGL、大量预处理） | 提高超时 |

提高超时的三种方式：CLI `--timeout=<ms>`；Node API 的 `timeoutInMilliseconds`；`Config.setDelayRenderTimeoutInMilliseconds()`（v2.6.3+）。默认 `30000`。

加标签便于定位（v2.6.13+）：

```tsx
delayRender("Fetching data from API...");
// 报错信息会变成：A delayRender() "Fetching data from API..." was called but not cleared after 28000ms.
```

**(2) `Composition not found`**

- 症状：`getCompositions().find(c => c.id === X)` 返回 `undefined`；或 CLI 找不到组合 ID。
- 官方示例里的错误文案就是：
  ```ts
  throw new Error(`No composition with the ID ${compositionId} found. Review "${entry}" for the correct ID.`);
  ```
  【官方：<https://v3.remotion.dev/docs/ssr>】
- 常见根因（【推断】）：
  1. **ID 拼写/大小写**不一致；ID 只允许字母、数字和 `-`（有下划线或中文会直接不合法）。【官方：<https://v3.remotion.dev/docs/composition>】
  2. **`<Composition>` 被条件渲染或放在错误的组件里**——官方有专门页面 "Wrongly mounted `<Composition>`"。【官方：<https://v3.remotion.dev/docs/wrong-composition-mount>】
  3. **浏览器缓存了旧 bundle**：加 `--bundle-cache=false` 排查。
  4. **`props`/`inputProps` 里含非 JSON 可序列化值**（如 Date、函数、Map），导致 Root 抛错、组合列表为空。官方另有 "defaultProps too big" 页面提示大对象会拖慢甚至失败。
  5. **动态时长依赖 `delayRender` 却没 resolve**：`getCompositions()` 会挂到超时。这也是为什么 `inputProps` 必须**同时**传给 `getCompositions()` 和 `renderMedia()`。【官方：<https://v3.remotion.dev/docs/dynamic-metadata>】

**(3) 内存不足 / 渲染中途崩溃**

- 直接对策：降低 `--concurrency`；把 `--image-format` 保持 `jpeg`（`png` 更慢更占内存）；避免超长单镜头；把视频素材换成 `<OffthreadVideo>`；分片渲染（`--frames=0-899` / `900-1799`）再用 FFmpeg 拼接。**【推断 + 官方 performance 页】**
- 官方在 performance 页坦承：**"Embedded videos can be a significant bottleneck in Remotion at the moment regardless of which component is being used. We are aware of this constraint and are encouraging users to combine Remotion with other tools such as FFmpeg to build efficient pipelines."** 这句话对本项目（新闻视频，可能含大量素材片段）非常重要——**官方自己建议把重活交给 FFmpeg**。

**(4) 其他官方 troubleshooting 页面**【官方：<https://v3.remotion.dev/docs/troubleshooting/debug-failed-render>】

- `Target closed`、`Media playback error`、`Non-seekable media`、`Flickering`、`Version mismatch`、`ENAMETOOLONG`、`Slow method to extract frame`、`staticFile() relative paths`、`staticFile() remote URLs`、`Root component Timeout`、`defaultProps too big`、`Source could not be parsed`、`Fast Refresh not working`。
- 排查利器：`--log=verbose` 会打印**最慢的帧**；用 `console.time` 计时；用 `npx remotion benchmark` 扫 concurrency。【官方：<https://v3.remotion.dev/docs/performance>】

---

### A9. 许可证

#### A9.1 免费使用的边界 【官方：<https://v3.remotion.dev/docs/license>】

Remotion 官方原文（v3 文档站）列出的**免费**情形：

- 个人（an individual）
- **员工不超过 3 人的营利组织**（a for-profit organisation with up to 3 employees）
- 非营利 / 非盈利组织
- 正在评估是否合适、且尚未用于商业用途

**不符合以上任一条件 → 需要购买公司许可证。** 官方建议同时阅读 LICENSE 文件与 Company License FAQ，并在有疑问时发邮件询问。

- LICENSE 文件：<https://github.com/remotion-dev/remotion/blob/main/LICENSE.md>
- License FAQ：<https://www.remotion.dev/docs/license/faq>
- 购买入口：<https://companies.remotion.dev>、<https://remotion.pro/dashboard>

#### A9.2 当前实际条款与价格（v4 时期，2026 年页面）

**【官方：<https://www.remotion.dev/docs/license/pricing>】**

| 档位 | 适用范围 | 价格结构 |
|---|---|---|
| **Free License** | 个人、**≤3 人的公司** | 免费；**组织变大后必须升级**；无需注册 |
| **Company License / Remotion for Automators** | 构建视频生成工具（视频编辑器、prompt-to-video 应用、嵌入 Remotion Player） | **$0.01 / 次渲染，最低 $100/月**；自动化项目的开发者不需要 Seat |
| **Company License / Remotion for Creators** | 为组织内部制作视频（低产量手工创作、用 AI agent 和 Studio 构建动效设计系统） | **$25/月/Seat**，每个用户 1 Seat |
| **Company License（含两者）** | 混合场景 | 示例：10,000 次渲染 + 3 Seats = $100/月 |
| **Enterprise** | 高级需求 | **$500/月起**，含私有 Slack/Discord、月度咨询、自定义条款与合规表单、Editor Starter |

#### A9.3 对本项目的直接结论

- 如果**只有你一个人 / ≤3 人团队**在做这个新闻视频流水线：**免费**。
- 一旦**团队 ≥4 人**，或者**把渲染能力做成对外服务/批量化产品**（Python 封装、批量跑稿件的服务化封装）：**需要 Company License**。
- "自动化"档位是按**渲染次数**计费（$0.01/次，$100/月保底），而"创作者"档位按**Seat**计费（$25/月/人）——**批量生产视频的自动化流水线应归入 Automators 档**。这个判断需要和 Remotion 官方确认，因为"自动化项目"的定义写着 "batch rendering and automated video products"。**【官方条款 + 推断】**
- 注意：`@remotion/bundler`、`@remotion/sfx`（NPM 包部分）、`@remotion/google-fonts`、`@remotion/media-utils` 这几项在各自文档页标注 **MIT**，但**核心 `remotion` 包与 `@remotion/renderer` 等是 Remotion License**——不能只看子包的 MIT 就认为整体可自由商用。

---

## 3. B 部分：分辨率与平台规范

### B10. 抖音 / 小红书 的视频参数

> **重要声明**：抖音、小红书的官方规范大多在**登录态**的创作者后台/帮助中心里，公开可抓取的权威页面很少。以下数据来源分三类，已逐条标注。

#### B10.1 小红书

| 项目 | 要求 | 来源等级 |
|---|---|---|
| 笔记视频比例 / 尺寸 | **9:16 竖屏（1080×1920）** | 【社区，含引用的第三方规范整理】 |
| 时长上限 | **≤ 15 分钟** | 【社区】 |
| 容器 / 编码 | MP4 / MOV | 【社区】 |
| 文件大小 | **≤ 500 MB** | 【社区】 |
| 笔记配图比例 | 竖版 3:4（推荐 1080×1440）、1:1（1080×1080）、横版 4:3（1080×810）；**同一篇笔记只能用一种比例** | 【社区】 |
| 图文上限 | 18 张（2024 年从 9 张扩容），单张 ≤ 20 MB，JPG/PNG | 【社区】 |
| 店铺商品视频 | 支持 1:1、3:4、16:9；时长 15–60 秒（建议 30 秒内）；MP4；≤ 50 MB | 【社区】 |

来源：<https://www.biaojixia.com/specs/xiaohongshu>（第三方聚合页，页面本身注明"平台官方后台多为登录态，故采用具名、可访问的权威电商规范资料并交叉核对"）

**横屏在小红书**：小红书以竖版为主，横屏视频（16:9）可以发但信息流占屏面积小、推荐权重通常更低。**如果必须同时出横屏，横屏版更适合同步到 B 站/视频号/YouTube。****【社区/推断】**

#### B10.2 抖音

| 项目 | 要求 | 来源等级 |
|---|---|---|
| 竖屏比例 / 分辨率 | **9:16，建议 1080×1920**（"不低于 1080×1920 像素"） | 【社区，引自抖店规范整理】 |
| 主图视频 | 推荐 9:16 竖屏、1080×1920、MP4、建议 15 秒内 | 【社区】 |
| 编码格式 | H.264（H.265 支持度差，兼容性风险） | 【推断，基于通用播放兼容性】 |
| 容器 | MP4 | 【社区】 |
| 帧率 | 30 fps（60 fps 亦可，但会显著提高码率与渲染成本） | 【推断】 |
| 时长上限 | **未找到权威公开数值**；普通账号历史上为 15 分钟档，实际以创作者后台的最新提示为准 | **【未证实】** |
| 文件大小上限 | **未找到权威公开数值** | **【未证实】** |

来源：<https://www.biaojixia.com/specs/douyin>（同上，第三方聚合）

**横屏在抖音**：可直接上传 16:9，但会被居中加黑边或以"横屏模式"展示，上下信息栏仍会遮挡画面。**建议横屏内容单独做一版竖屏（重排版），而不是把横屏直接压进竖屏画布。****【推断】**

#### B10.3 推荐输出参数（本项目）

| 参数 | 竖屏 | 横屏 | 依据 |
|---|---|---|---|
| 分辨率 | `1080x1920` | `1920x1080` | 平台主流【社区】 |
| 容器 / 视频编码 | MP4 / H.264 (`h264`) | 同 | 兼容性最好【官方 codec 表：H.264 "Very good" 浏览器兼容性】 |
| 像素格式 | `yuv420p` | `yuv420p` | 最广泛兼容【推断】 |
| CRF | **18–21**（Remotion H.264 默认 18，范围 1–51） | 同 | 【官方：<https://v3.remotion.dev/docs/encoding>】 |
| 帧率 | 30 fps（科技新闻无需 60） | 30 fps | 【推断】 |
| 音频编码 | AAC | AAC | 【官方 audio codec 表】 |
| 音频码率 | `192K`–`256K` | 同 | Remotion 默认 `320k`；语音类内容 192K 已足够【官方默认值 + 推断】 |
| GOP / profile | 未暴露（Remotion 未开放） | — | 【官方】Remotion 只用 FFmpeg 的默认值 |

**CRF 取值建议（官方数据 + 经验）**：

| 编码 | 最小(最好) | 最大(最小体积) | **官方默认** |
|---|---|---|---|
| H264 | 1 | 51 | **18** |
| H265 | 0 | 51 | 23 |
| VP8 | 4 | 63 | 9 |
| VP9 | 0 | 63 | 28 |

官方警告：**"每个编码器有各自的可接受范围和不同默认值。`23` 在 H264 上看起来很好，在 WebM 上会非常糟糕。"** 另外 **v2.1.3 起 CRF 不允许为 0**（会在 macOS/iOS 上出问题），请用 ≥1。【官方：<https://v3.remotion.dev/docs/encoding>】

**给本项目的具体命令**：

```bash
# 竖屏（平台主发布版）
npx remotion render src/index.ts News-Portrait out/xhs-1080x1920.mp4 \
  --props=./build/props-portrait.json \
  --codec=h264 --crf=19 --pixel-format=yuv420p \
  --audio-codec=aac --audio-bitrate=192K \
  --concurrency=6 --log=info

# 横屏（B站/视频号/YouTube 主发布版）
npx remotion render src/index.ts News-Landscape out/yt-1920x1080.mp4 \
  --props=./build/props-landscape.json \
  --codec=h264 --crf=18 --pixel-format=yuv420p \
  --audio-codec=aac --audio-bitrate=256K \
  --concurrency=6 --log=info
```

#### B10.4 AI 生成内容标注要求

- 《**人工智能生成合成内容标识办法**》由四部门联合发布，**2025 年 9 月 1 日起施行**：AI 生成合成内容必须进行标识（显式标识 + 隐式/文件元数据标识），不得"隐身"传播。来源：光明网 <https://m.gmw.cn/2025-03/14/content_1303991368.htm>、<https://m.gmw.cn/2025-03/14/content_1303991405.htm>；司法网转载 <http://news.jcrb.com/shxw/202509/t20250901_7117645.html>
- 2025 年 12 月，8 家电商平台签订规范应用承诺书，直播间违规使用 AI 将被屏蔽。来源：<http://bj.people.com.cn/n2/2025/1205/c14540-41432994.html>、<https://scjgj.beijing.gov.cn/zwxx/mtjj/202512/t20251231_4382400.html>
- **对本项目的实务建议**【推断】：即使视频画面是模板化渲染（非 AI 生成），只要**配音/AI 主播/BGM 是 AI 生成的**，就应考虑在简介或画面角标中做显式标识，并在容器元数据中保留隐式标识。**具体合规口径请咨询法务。**

---

### B11. 竖屏 / 横屏安全区

**核心事实：抖音官方没有公开发布"安全区"规范文档。** 官方对外发布的只有广告位相关的《避让区域详细描述》（TopView / 信息流），这些是 **ByteDance 飞书文档，需要登录，抓取会跳转到 `accounts.larkoffice.com`**，我无法读取内容：
- 抖音 TopView 避让区域详细描述（对外版）：<https://bytedance.larkoffice.com/docx/H7fvdd7cmoSrqOx23GwcRaX0nCg>
- 抖音信息流避让区域详细描述（对外版）：<https://bytedance.larkoffice.com/docx/AHJqdO0MpokNEyx7Fgxc6dEinkc>

因此下面的像素值来自**创作者工具类文章的一致口径**，**属于社区经验值，必须本机实测确认**。

#### B11.1 三平台安全区数值（1080x1920 画布）

| 平台 | 顶部 | 底部 | 左侧 | 右侧 |
|---|---|---|---|---|
| TikTok / 抖音 | **108 px** | **320 px** | 60 px | **120 px** |
| Instagram Reels | 220 px | 420 px | 60 px | 180 px |
| YouTube Shorts | 150 px | 320 px | 60 px | 180 px |

来源：【社区】<https://www.ffmpeg-micro.com/blog/tiktok-safe-zone-margins-aren-t-ffmpeg-pixels-convert-them>（原文注明这些是"创作者工具页面持续公布的区间"，是 app chrome 的测量值而非格式规范）

**跨平台统一（取各边最大值）**：顶部 **220 px**、底部 **420 px**、左 **60 px**、右 **180 px** → 1080x1920 上剩 **840x1280** 可用区（占画布 53%）。

**换成百分比（推荐，分辨率无关）**：顶部 **11.5%**、底部 **22%**、左 **5.6%**、右 **16.7%**。

> 原文的一个重要细节：**ASS 字幕使用 `Alignment=2` 时，libass 会在 `MarginL` 和 `MarginR` 之间居中**，所以抖音那种 60/120 的非对称边距会让居中字幕**整体左偏 30 px**。**做法：左右都取较大的值（都设 120 或都设 180）。**

#### B11.2 落地到 Remotion 的安全区常量

```ts
// src/safeArea.ts
export type SafeArea = {
  top: number;
  bottom: number;
  left: number;
  right: number;
};

/** 竖屏：取抖音/小红书/Reels/Shorts 各边最大值的保守并集 */
export const SAFE_PORTRAIT: SafeArea = {
  top: 220,
  bottom: 420,
  left: 180,   // 左右取同值，避免居中偏移
  right: 180,
};

/** 竖屏精简版：只发抖音/小红书时可用（更省空间，推荐先测） */
export const SAFE_PORTRAIT_TIGHT: SafeArea = {
  top: 108,
  bottom: 320,
  left: 120,
  right: 120,
};

/** 横屏：无右侧按钮轨，主要是顶部/底部留白 */
export const SAFE_LANDSCAPE: SafeArea = {
  top: 60,
  bottom: 90,
  left: 96,
  right: 96,
};

export const safeStyle = (a: SafeArea): React.CSSProperties => ({
  position: "absolute",
  top: a.top,
  bottom: a.bottom,
  left: a.left,
  right: a.right,
});
```

配套的 `<SafeArea>` 组件（把镜头卡内容塞进安全区，而不是让每张卡自己算边距）：

```tsx
import React from "react";
import { AbsoluteFill, useVideoConfig } from "remotion";
import { SAFE_LANDSCAPE, SAFE_PORTRAIT_TIGHT, safeStyle } from "./safeArea";

export const SafeArea: React.FC<{ children: React.ReactNode; tight?: boolean }> = ({
  children,
  tight = true,
}) => {
  const { width, height } = useVideoConfig();
  const portrait = height > width;
  const area = portrait
    ? tight
      ? SAFE_PORTRAIT_TIGHT
      : SAFE_PORTRAIT
    : SAFE_LANDSCAPE;

  return (
    <AbsoluteFill>
      <div style={safeStyle(area)}>{children}</div>
    </AbsoluteFill>
  );
};
```

#### B11.3 自检方法

```bash
# 渲染关键帧静帧，肉眼检查安全区
npx remotion still src/index.ts News-Portrait out/safe-check.png --frame=90 --props=./build/props-portrait.json
```

在 Studio 里临时叠一层虚线"禁区框"（`border: 2px dashed red`，分别用 `top/height`、`bottom/height`、`left/width`、`right/width` 四个绝对定位 div 表示），改完删掉即可。

#### B11.4 字幕字号建议（【推断】）

- 竖屏 1080 宽：安全区宽 = `1080 - 120 - 120 = 840` px；中文正文 **52–60 px**，一行约 **13–14 个字**；建议单屏最多 2 行。
- 横屏 1920 宽：安全区宽 ≈ `1920 - 96 - 96 = 1728` px；中文正文 **48–56 px**，一行约 **30 个字**；建议单屏最多 2 行。
- 竖屏字幕的 `bottom` 从 320 起算（用 tight 集），横屏 90 起算。

---

## 4. C 部分：BGM 生成能力（重点）

### C12. 逐项核实

#### C12.1 Remotion 自身有没有音频合成/生成能力？

**结论：没有专门的"音频生成 API"，但官方文档明确承认「用 Web Audio API 离屏渲染音频」这条路径，并给出了完整示例。**

证据一：`@remotion/media-utils` 的官方定位是 **"utility functions for getting information about video and audio, and for visualizing audio"**——只有"获取信息"和"可视化"，**没有任何合成函数**。函数清单：`getAudioDurationInSeconds`、`getVideoMetadata`、`getAudioData`、`useAudioData`、`useWindowedAudioData`、`visualizeAudio`、`visualizeAudioWaveform`、`getWaveformPortion`、`createSmoothSvgPath`、`audioBufferToDataUrl`、`getImageDimensions`。【官方：<https://v3.remotion.dev/docs/media-utils/>】

证据二：`audioBufferToDataUrl()` 页面上有官方示例 **"Example: Rendering a sine tone"**——用 `OfflineAudioContext` 生成 C4 正弦音，转成 Data URL 后交给 `<Audio>`。这**证明浏览器端离屏音频合成在 Remotion 渲染中是官方支持的做法**。【官方：<https://www.remotion.dev/docs/audio-buffer-to-data-url>】

证据三：Remotion 有一个 `@remotion/sfx` 包（**v4.0.429 起**），提供 32 个**现成音效 URL**（whip、whoosh、pageTurn、uiSwitch、mouseClick、ding、vineBoom、recordScratch 等）。官方描述：可作包引入或直接 URL 加载，峰值统一归一化到 **-3dB**，"All files can be used without attribution, but the attribution is available on the detail page of a sound."；NPM 包 MIT，各音效各自许可。【官方：<https://www.remotion.dev/docs/sfx/>】
**注意：`@remotion/sfx` 是音效库，不是 BGM 库，也没有生成能力。**

**结论表**：

| 问题 | 结论 |
|---|---|
| Remotion 有音频合成 API 吗？ | ❌ 没有。核心包与 `@remotion/media-utils` 都不提供振荡器/合成器/音符/和弦 API【官方】 |
| `<Audio>` 能播放什么？ | Chromium 支持的所有音频格式；也可播放 `audioBufferToDataUrl()` 产出的 Base64 Data URL【官方】 |
| 有没有官方认可的"渲染期生成音频"路径？ | ✅ 有：`OfflineAudioContext` + `audioBufferToDataUrl()` + `<Audio src={dataUrl}>`【官方示例】 |
| `@remotion/media-utils` 支持音频合成吗？ | ❌ 不支持。仅读取/可视化/格式转换【官方】 |

#### C12.2 Tone.js / Web Audio API 能否在 Remotion 里离线渲染生成音乐？

**结论：能，但必须用 `Tone.Offline()` / `OfflineAudioContext` 这条"离屏渲染"路径，绝对不能用 `Tone.Transport` 的实时播放时钟。**

**(a) 可行路径（确定性输出）**

```tsx
// src/SynthBgm.tsx —— 用 OfflineAudioContext 在渲染期合成一段"科技感"BGM
import React, { useCallback, useEffect, useState } from "react";
import { Audio, cancelRender, continueRender, delayRender, staticFile, useVideoConfig } from "remotion";
import { audioBufferToDataUrl } from "@remotion/media-utils";

export const SynthBgm: React.FC<{ volume?: number }> = ({ volume = 0.25 }) => {
  const [handle] = useState(() => delayRender("synthesize bgm"));
  const [dataUrl, setDataUrl] = useState<string | null>(null);
  const { fps, durationInFrames } = useVideoConfig();
  const lengthInSeconds = durationInFrames / fps;
  const sampleRate = 44100;

  const renderAudio = useCallback(async () => {
    const ctx = new OfflineAudioContext({
      numberOfChannels: 2,
      length: Math.ceil(sampleRate * lengthInSeconds),
      sampleRate,
    });

    const master = ctx.createGain();
    master.gain.setValueAtTime(0.0001, 0);
    master.gain.exponentialRampToValueAtTime(1, 1.5);                       // 淡入
    master.gain.setValueAtTime(1, lengthInSeconds - 2);
    master.gain.exponentialRampToValueAtTime(0.0001, lengthInSeconds);      // 淡出
    master.connect(ctx.destination);

    // 低频 pad：两个失谐锯齿波 + 低通，营造"科技感"底噪
    const lp = ctx.createBiquadFilter();
    lp.type = "lowpass";
    lp.frequency.setValueAtTime(400, 0);
    lp.frequency.linearRampToValueAtTime(2200, lengthInSeconds);
    lp.Q.value = 6;
    lp.connect(master);

    for (const freq of [55, 55.3, 82.4]) {
      const osc = ctx.createOscillator();
      osc.type = "sawtooth";
      osc.frequency.value = freq;
      const g = ctx.createGain();
      g.gain.value = 0.18;
      osc.connect(g).connect(lp);
      osc.start(0);
      osc.stop(lengthInSeconds);
    }

    // 4 拍脉冲（每 2 秒一次）—— 节拍器式的"科技脉动"
    const beat = 2;
    for (let t = 0; t < lengthInSeconds; t += beat) {
      const osc = ctx.createOscillator();
      osc.type = "sine";
      osc.frequency.setValueAtTime(180, t);
      osc.frequency.exponentialRampToValueAtTime(45, t + 0.35);
      const g = ctx.createGain();
      g.gain.setValueAtTime(0.9, t);
      g.gain.exponentialRampToValueAtTime(0.001, t + 0.4);
      osc.connect(g).connect(master);
      osc.start(t);
      osc.stop(t + 0.45);
    }

    const buffer = await ctx.startRendering();   // ← 关键：离线渲染，确定性
    setDataUrl(audioBufferToDataUrl(buffer));
    continueRender(handle);
  }, [handle, lengthInSeconds]);

  useEffect(() => {
    renderAudio().catch((err) => cancelRender(err));
  }, [renderAudio]);

  if (!dataUrl) return null;
  return <Audio src={dataUrl} volume={volume} />;
};
```

> **v3 注意**：上面用的是 v4 的 `@remotion/media` 的 `<Audio>`。**v3 里请从 `remotion` 导入 `<Audio>`**，`audioBufferToDataUrl()` 则从 `@remotion/media-utils` 导入（v3/v4 都有）。`dataUrl` 字符串可能很长（几分钟的 44.1kHz 立体声 WAV 的 Base64 会达到几十 MB），**这是这条路径最大的工程风险**，见下面 (c)。

Tone.js 版本：

```tsx
import * as Tone from "tone";

const buffer: Tone.ToneAudioBuffer = await Tone.Offline(() => {
  const synth = new Tone.PolySynth(Tone.Synth).toDestination();
  synth.triggerAttackRelease(["A2", "E3"], "2n", 0);
  const noise = new Tone.Noise("brown").toDestination();
  noise.start(0).stop(4);
}, 8); // 8 秒
// buffer.get() 拿到 AudioBuffer
```

`Tone.Offline(callback, duration)` 官方文档：<https://tonejs.github.io/docs/15.1.22/functions/Offline.html>（另有 `OfflineContext` 类：<https://tonejs.github.io/docs/14.7.39/OfflineContext>）

**(b) 关键限制（这是最容易踩坑的部分）**

1. **帧时钟 ≠ 音频时钟。** Remotion 渲染是**逐帧截图**（每帧一个 Chromium 截图），页面并没有在"实时播放"。任何依赖 `AudioContext.currentTime` 真实流逝、或依赖 `setTimeout`/`requestAnimationFrame` 推进的音乐逻辑都会产生**非确定性**结果（不同帧截图时状态不同）。
   → **必须**把整段音乐一次性在 `OfflineAudioContext` 里算完，得到确定性的 `AudioBuffer`，再当成普通音频资源播放。
   → **绝对不要**用 `Tone.Transport.start()` / `Tone.now()` 这类实时时钟 API。**【官方示例的写法 + 推断】**

2. **`delayRender()` 超时。** 合成耗时算在单帧的 `delayRender` 超时里，默认只有 **30 秒**。复杂合成（大量音符/卷积混响）很容易超时。**对策**：提高 `--timeout`，或**把 BGM 生成挪出渲染进程**（预生成 wav 文件 → `staticFile()` 加载），这也是官方"先用工具生成资源"思路的延伸。**【官方 timeout 页 + 推断】**

3. **Data URL 体积与内存。** `audioBufferToDataUrl()` 产出 Base64，体积约为原始 PCM 的 1.33 倍。44.1kHz/16bit/立体声 = 176.4 KB/s → 3 分钟 ≈ 31.7 MB → Base64 ≈ 42 MB 的字符串。**在 6 个并发渲染进程里各持一份，内存会爆。**
   → **务实的 workaround**：合成一次 → 用 Node/Python 落盘成 `.wav`（或用 `OfflineAudioContext` 渲染后转码）→ 下次渲染直接 `staticFile("bgm.wav")`。**即"程序化生成 + 缓存复用"**。**【推断，但基于官方 data URL 机制 + 体积计算】**

4. **Tone.js 在离线渲染里的已知性能问题**：Tone.js 仓库有 "Poor offline rendering performance" 的 issue（<https://github.com/Tonejs/Tone.js/issues/436>）。如果合成规模大，建议直接用原生 Web Audio API。**【社区】**

5. **`@remotion/media-utils` 的兼容性表**：`audioBufferToDataUrl()` 页面的浏览器/环境兼容表在抓取结果中显示为空（未标出支持的单元格）。考虑到它被用于官方示例且运行在 Chromium 中，**在实际渲染环境（Chromium/Chrome）里是可用的**；但**在 Studio 的某些环境下未经验证**。【官方页面表格为空 + 推断，**建议本地实测**】

**(c) 结论**

- ✅ **技术上可行且官方认可**（有官方示例）。
- ⚠️ **工程上不推荐直接在渲染时合成 BGM**，原因是超时风险 + Data URL 内存爆炸。
- ✅ **推荐形态**：**用 Node/Web Audio 或 Python 预生成一次 BGM → 落盘成 wav/mp3 → Remotion 用 `staticFile()` 加载。** 这样得到的是"确定性 + 可缓存 + 零渲染开销"。

#### C12.3 Python 侧 AI 音乐生成方案

##### (1) Meta AudioCraft / MusicGen

| 维度 | 情况 |
|---|---|
| 模型 | `facebook/musicgen-small`（约 300M）、`musicgen-medium`（约 1.5B）、`musicgen-large`（约 3.3B）、`musicgen-melody`、`musicgen-stereo-*` |
| 架构 | 单阶段自回归 Transformer，基于 32kHz EnCodec 分词器，4 个 codebook、50 Hz 采样；**每秒音频只需 50 个自回归步**（codebook 间引入小延迟并行预测） |
| 训练数据 | **20K 小时"授权音乐"**：10K 首内部高质量曲目 + ShutterStock + Pond5 |
| **代码许可** | **MIT**（audiocraft 仓库 `LICENSE`） |
| **权重许可** | **CC-BY-NC 4.0**（`LICENSE_weights`）→ **禁止商业用途** |
| CPU 可行性 | 可跑，但 small 已是"分钟级生成数十秒音频"的量级；medium/large 在 CPU 上基本不实用。**具体速度未找到权威基准，属"需实测"项** |

来源（含逐字引用）：
- 许可原文（**这段是本次调研中拿到的关键逐字证据**）：<https://replicate.com/pphu/musicgen-small/readme> 原话——"All code in this repository is licensed under the Apache License 2.0 license. The code in the Audiocraft repository is released under the MIT license as found in the LICENSE file. The weights in the Audiocraft repository are released under the CC-BY-NC 4.0 license as found in the LICENSE_weights file."
- 权重许可文件：<https://github.com/facebookresearch/audiocraft/blob/main/LICENSE_weights>
- 官方模型卡：<https://facebookresearch.github.io/audiocraft/model_cards/MUSICGEN_STYLE_MODEL_CARD.html>
- HF 模型页（license 标签 `cc-by-nc-4.0`）：<https://huggingface.co/facebook/musicgen-small>
- 论文：<https://arxiv.org/abs/2306.05284>

> **对本项目的致命结论**：**MusicGen 的权重是 CC-BY-NC 4.0，不能用于商业用途的视频。** 如果这个新闻视频流水线有任何商业化可能（广告、带货、企业号、付费内容），**MusicGen 直接出局**——除非只用于内部原型验证。
> 补充：`musicgen-small` 的 HF 页面上 license 标签即 `cc-by-nc-4.0`，与权重许可文件一致。【官方页面；HF 页面本次抓取多次失败，标签信息来自搜索索引，**建议自行打开确认**】

##### (2) Stability AI `stable-audio-open-1.0`

| 维度 | 情况 |
|---|---|
| 定位 | 开放权重的**文本到音频**模型（音乐 + 音效），约 1.1B 参数 |
| 许可 | **Stability AI Community License**——通常允许商业使用，但**年收入超过某阈值（常见口径为 100 万美元）的组织需要企业许可**；**具体阈值与条款本次未能从官方页面取到原文，属"必须自行核实"项** |
| 硬件 | 官方与社区口径为需要 GPU（显存需求常见口径 8–12GB 级别）；**CPU 上可跑但极慢** |
| 生成时长 | 单次生成上限通常为 47 秒级别（需按段拼接） |

来源（**均未能成功抓取到原文，标记为待核实**）：
- 官方模型页：<https://huggingface.co/stabilityai/stable-audio-open-1.0>
- 官方论文公告：<https://stability.ai/news-updates/stable-audio-open-research-paper>（页面可访问但正文未返回）
- 许可证页：<https://stability.ai/license>
- 第三方自托管说明（含 VRAM 讨论）：<https://gigagpu.com/stable-audio-open-self-hosted/>

> **对本项目的结论**：**商用许可比 MusicGen 宽松**（社区许可通常允许 <100 万美元年收入的组织商用），但**需要 GPU**，在纯 Windows CPU 环境下不实用。**必须自行核实当年的收入阈值与条款。**

##### (3) Google Magenta

| 维度 | 情况 |
|---|---|
| 内容 | `magenta`（Python，TF 版 MusicVAE / Performance RNN / MelodyRNN / DrumsRNN 等）、`magenta-js`（浏览器端）、Magenta RealTime（较新） |
| 维护状态 | 仓库仍在 GitHub 上（<https://github.com/magenta/magenta>），但**长期处于低活跃/维护模式**；TensorFlow 依赖与 Python 3.12 的兼容性是最大障碍（TF 版本停在较早的 2.x 系列） |
| CPU 可行性 | MusicVAE / MelodyRNN 这类小模型**可以 CPU 跑**（这是 Magenta 相对 MusicGen 的最大优势） |
| 许可 | Apache 2.0（代码）；**模型 checkpoint 的许可需逐个核对** |

来源：<https://github.com/magenta/magenta>（本次抓取只拿到 GitHub 页面导航，README 正文未返回）；学术评估参见 <https://roserbatlleroca.github.io/MusGO_framework/models/magenta-realtime/>

> **对本项目的结论**：**技术上能在 CPU 跑，但 TF 依赖在 Python 3.12 + Windows 上安装困难**（TensorFlow 对 Python 3.12 的官方支持是较新版本才有，而 Magenta 依赖老 TF API）。**性价比低于"程序化合成"路线。**【推断，需实测】

##### (4) Suno / Udio（云端 AI 音乐）

| 维度 | 情况 |
|---|---|
| 是否有公开 API | **没有面向公众的稳定官方 API**（Suno 有合作伙伴/企业通道，第三方逆向 API 不受支持且不稳定）。社区有非官方 API 封装（如 <https://raw.githubusercontent.com/api-evangelist/suno/refs/heads/main/apis.yml>），**不建议用于生产** |
| 版权归属 | Suno 官方帮助中心的表述需要以其最新条款为准：<https://help.suno.com/en/articles/2746945-do-i-have-the-copyrights-to-songs-i-made>（本次抓取失败，**必须自行阅读**） |
| 商业条款动态 | Suno 与 Warner Music 的合作使其条款在 2025–2026 年发生变动，第三方报道：<https://www.digitalmusicnews.com/2025/12/22/suno-warner-music-deal-changes/>、<https://tophit.com/news/pro/14283> |
| 自动化适用性 | ❌ 不适合"批量稿件自动出片"：无稳定 API、额度限制、条款变动、生成结果不可复现（每次生成不同） |

> **对本项目的结论**：**Suno/Udio 不适合作为流水线的自动化 BGM 来源。** 可以作为人工偶尔补充，但不进入工程链路。

##### (5) 其他开源音乐生成模型（2025 前后）

| 模型 | 说明 | 许可 / 硬件 |
|---|---|---|
| **ACE-Step** | 开源音乐生成基础模型，GitHub 活跃（<https://github.com/ace-step/ACE-Step>），有 1.5 版本与 XL 权重（<https://huggingface.co/ACE-Step/acestep-v15-xl-base>）；已在 HuggingFace `diffusers` 中有官方 pipeline 文档（<https://raw.githubusercontent.com/huggingface/diffusers/main/docs/source/en/api/pipelines/ace_step.md>） | **本次未能取到许可与显存原文**；社区普遍口径为需要 GPU；**必须自行核实** |
| **YuE** | 开源全曲（含人声）生成 | 需 GPU；许可待核实 |
| **DiffRhythm** | 快速全曲生成 | 需 GPU；许可待核实 |
| **Riffusion** | 频谱图扩散，早期音乐生成方案 | 需 GPU；许可待核实 |
| **AudioX / Mustango** | 更学术化，文本到音频 | 需 GPU；许可待核实 |

> 这一组**本次均未取得官方原文**，因此全部标记为 **【未证实】**。共同点是：**都需要 GPU**，都不适合"Windows CPU-only 环境"。

#### C12.4 程序化 / 规则化生成（不依赖 AI 模型）—— 本项目最优解

这条路线的本质是：**用代码写音符/鼓点/包络，直接输出 PCM 样本，落成 `.wav`。** 优点是**完全确定性、可复现、可精确对齐镜头卡时间轴、CPU 秒级完成、零许可风险（自己写的代码）。**

##### (a) Python：标准库 + NumPy 直接写 WAV（推荐）

```python
"""
procedural_bgm.py
用 NumPy + 标准库 wave 生成"科技感/电影感"BGM，完全离线、CPU、秒级。
pip install numpy  (可选: pip install scipy 用于更高质量滤波)
"""
from __future__ import annotations

import math
import wave
from dataclasses import dataclass

import numpy as np

SR = 44100  # 采样率


@dataclass
class Segment:
    """一个音乐段落（镜头卡可与之对齐）"""
    start_s: float
    duration_s: float
    intensity: float  # 0..1，用于控制配器密度与音量
    root_hz: float = 55.0  # A1


def adsr(n: int, a: float, d: float, s: float, r: float, sr: int = SR) -> np.ndarray:
    """生成 ADSR 包络（长度为 n 的 0..1 数组）"""
    a_n, d_n, r_n = int(a * sr), int(d * sr), int(r * sr)
    s_n = max(0, n - a_n - d_n - r_n)
    env = np.concatenate([
        np.linspace(0.0, 1.0, a_n, endpoint=False) if a_n else np.array([]),
        np.linspace(1.0, s, d_n, endpoint=False) if d_n else np.array([]),
        np.full(s_n, s),
        np.linspace(s, 0.0, r_n) if r_n else np.array([]),
    ])
    if len(env) < n:
        env = np.pad(env, (0, n - len(env)))
    return env[:n]


def saw(freq: float, n: int, sr: int = SR) -> np.ndarray:
    t = np.arange(n) / sr
    return 2.0 * ((t * freq) % 1.0) - 1.0


def sine(freq: float, n: int, sr: int = SR) -> np.ndarray:
    t = np.arange(n) / sr
    return np.sin(2 * np.pi * freq * t)


def noise(n: int, rng: np.random.Generator) -> np.ndarray:
    return rng.uniform(-1.0, 1.0, n)


def lowpass(x: np.ndarray, cutoff_hz: float, sr: int = SR) -> np.ndarray:
    """一阶低通。生产上换成 scipy.signal.lfilter，快几个数量级。"""
    from scipy.signal import butter, lfilter
    b, a = butter(2, cutoff_hz / (sr / 2), btype="low")
    return lfilter(b, a, x)


def make_pad(root: float, n: int, sr: int) -> np.ndarray:
    """失谐锯齿 pad + 低通：科技感底噪"""
    layers = [saw(root * 2 * (1 + d), n, sr) for d in (-0.006, 0.0, 0.007, 0.011)]
    layers += [saw(root * r, n, sr) * 0.35 for r in (3.0, 4.02)]  # 五度/八度泛音
    x = lowpass(np.sum(layers, axis=0) / len(layers), 1200.0, sr)
    t = np.arange(n) / sr
    x *= 0.75 + 0.25 * np.sin(2 * np.pi * 0.07 * t)   # 缓慢"呼吸"调制
    return x * 0.35


def make_kick(n: int, sr: int) -> np.ndarray:
    """底鼓：音高从 160Hz 指数下扫到 45Hz"""
    t = np.arange(n) / sr
    f = 45.0 + 115.0 * np.exp(-t * 28.0)
    body = np.sin(2 * np.pi * np.cumsum(f) / sr)
    return (body + np.exp(-t * 220.0) * 0.6) * np.exp(-t * 7.0) * 0.9


def make_hat(n: int, sr: int, rng: np.random.Generator) -> np.ndarray:
    """hi-hat：噪声高频 + 极短包络"""
    x = noise(n, rng)
    return (x - lowpass(x, 6000.0, sr)) * np.exp(-np.linspace(0, 14, n)) * 0.22


def make_riser(n: int, sr: int, rng: np.random.Generator) -> np.ndarray:
    """riser：噪声渐强 + 音高上行 4 个八度，镜头切换前 1~2 秒用"""
    x = lowpass(noise(n, rng), 800.0, sr)
    t = np.linspace(0.0, 1.0, n)
    x *= 0.15 + 0.85 * t ** 2
    tone = np.sin(2 * np.pi * np.cumsum(220.0 * (2 ** (4 * t))) / sr)
    return (x * 0.6 + tone * 0.4) * 0.5


def mix_into(track: np.ndarray, clip: np.ndarray, at: int) -> None:
    end = min(len(track), at + len(clip))
    if end > at:
        track[at:end] += clip[: end - at]


def render(segments: list[Segment], total_s: float, out_path: str, seed: int = 7) -> None:
    rng = np.random.default_rng(seed)
    total_n = int(total_s * SR)
    left, right = np.zeros(total_n), np.zeros(total_n)

    for seg in segments:
        start, n = int(seg.start_s * SR), int(seg.duration_s * SR)
        if n <= 0:
            continue
        pad = make_pad(seg.root_hz, n, SR) * adsr(n, 1.2, 0.6, 0.8, 1.5)
        mix_into(left, pad * 0.62, start)
        mix_into(right, np.roll(pad, 220) * 0.62, start)   # 轻微相位差产生立体声宽度

        if seg.intensity > 0.35:                            # 鼓点只在高强度段落进入
            bpm, beat_n = 96.0, int(60.0 / 96.0 * SR)
            for b in range(int(seg.duration_s / (60.0 / bpm))):
                at = start + b * beat_n
                if b % 4 == 0:                              # 1、3 拍底鼓
                    kick = make_kick(beat_n, SR) * 0.85 * seg.intensity
                    mix_into(left, kick, at); mix_into(right, kick, at)
                if b % 2 == 0:                              # 2、4 拍 hi-hat
                    hat = make_hat(beat_n // 2, SR, rng) * seg.intensity
                    mix_into(left, hat, at); mix_into(right, hat, at)

        if seg.intensity > 0.5:                             # 段落末尾的 riser
            riser_n = int(1.6 * SR)
            riser = make_riser(riser_n, SR, rng)
            mix_into(left, riser, max(0, start + n - riser_n))
            mix_into(right, riser, max(0, start + n - riser_n))

    fade = int(1.2 * SR)                                    # 总淡入淡出，避免爆音
    for ch in (left, right):
        ch[:fade] *= np.linspace(0.0, 1.0, fade)
        ch[-fade:] *= np.linspace(1.0, 0.0, fade)

    peak = max(np.max(np.abs(left)), np.max(np.abs(right)), 1e-9)
    left, right = left * 10 ** (-1.5 / 20) / peak, right * 10 ** (-1.5 / 20) / peak

    pcm = np.empty(total_n * 2, dtype=np.int16)
    pcm[0::2] = np.clip(left * 32767, -32768, 32767).astype(np.int16)
    pcm[1::2] = np.clip(right * 32767, -32768, 32767).astype(np.int16)
    with wave.open(out_path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"wrote {out_path} ({total_s:.1f}s)")


if __name__ == "__main__":
    # 3 段结构：引子 / 主段 / 收尾，与镜头卡时间轴对齐
    render([
        Segment(0.0, 8.0, 0.25, 55.0),
        Segment(8.0, 60.0, 0.70, 55.0),
        Segment(68.0, 12.0, 0.45, 49.0),
    ], total_s=80.0, out_path="public/bgm-tech.wav")
```

**性能量级（【推断，需实测】）**：把滤波器换成 `scipy.signal.lfilter` 后，**生成 1–3 分钟的 BGM 在普通 CPU 上是 1–10 秒量级**；写 WAV 与磁盘 IO 是毫秒级。若坚持纯 NumPy/标准库（不装 scipy）而用逐样本 Python 循环滤波，80 秒音频会退化到分钟级——**这个坑必须避开**。

##### (b) 现成库清单（Windows CPU 可用性）

| 库 | 用途 | Windows CPU | 说明 |
|---|---|---|---|
| `numpy` + `wave`（标准库）+ `struct` | 直接合成 PCM 写 WAV | ✅ 完全可跑 | **零依赖、零许可风险，首选** |
| `scipy.signal` | 滤波器（lfilter / butter） | ✅ | 让上面代码快几个数量级 |
| `librosa` | 音频分析（节拍、onset、频谱）；也含 `librosa.output` / `soundfile` 写文件 | ✅ CPU | **注意：librosa 主要是"分析"库，不是"合成"库。** 用它可以做"根据配音的语速/停顿自动对齐 BGM 节拍"这类高级功能。官方：<https://librosa.org/doc/latest/index.html> |
| `soundfile`（libsndfile） | 读写 wav/flac/ogg，比标准库更方便 | ✅ | 需要 libsndfile 二进制（`pip install soundfile` 一般自带） |
| `pydub` | 音频剪辑/拼接/格式转换（依赖 ffmpeg） | ✅ | 适合做 BGM 拼接、淡入淡出、与配音混音；**需要系统有 ffmpeg** |
| `midiutil` / `pretty_midi` / `mido` | 写 .mid 文件 | ✅ | 生成 MIDI 后可用 `fluidsynth` + SoundFont 渲染成音频；**fluidsynth 在 Windows 需额外安装** |
| `music21` | 乐理/符号音乐分析 | ✅ | 偏学术，做"和声规则化生成"有用 |
| `pyo` / `csound` / `SuperCollider` | 专业音频合成环境 | ⚠️ | pyo 在 Windows 上安装/维护状况一般；Csound、SuperCollider 需要独立安装且学习成本高。**不推荐进自动化流水线** |
| `Sonic Pi` | 实时代码音乐 | ⚠️ | 面向实时演出，**不是离线渲染工具**，不适合本场景 |

##### (c) Node.js / 浏览器侧程序化生成

- **`Tone.Offline()`**（见 C12.2）：可以在 Node 里用 `node-web-audio-api` 之类的 polyfill 跑，但生态不成熟；**更适合还是走 Python**。**【推断】**
- **纯 Node 写 WAV**：与 Python 同理——`Buffer.alloc(44 + dataSize)` 手写 44 字节 RIFF 头（`RIFF`/`WAVE`/`fmt `/`data` + 采样率/声道/位深），随后按 `writeInt16LE` 逐样本写入交织 PCM。**零依赖，可行**，但 NumPy 的向量化能力无可替代，故本项目仍建议**用 Python 生成、Node/Remotion 只负责加载**。**【推断】**

##### (d) 规则化生成的"音乐性"要点（【社区/编曲常识】）

要让程序化 BGM 听起来"科技感 + 电影感"而不是"正弦波噪音"：

1. **调式**：用**小调 / 自然小调 / 多利亚（Dorian）**，避免大调的欢快感。科技新闻常用 A 小调（A2 = 110 Hz）或 D 小调。
2. **低频铺底**：55 Hz（A1）附近的失谐锯齿/三角波 pad，加低通扫频（400 Hz → 2.2 kHz）做"由暗到亮"的推进感。
3. **节奏**：90–110 BPM，四拍一循环，底鼓在 1、3 拍，hi-hat 在 2、4 拍；**不要做复杂节奏**，因为 BGM 要让位给配音。
4. **Riser / Whoosh**：每次镜头卡切换前 1.5–2 秒加一个上升噪音 + 音高上行，这是"科技感转场"最有效的一招。
5. **Drop / 静默**：在关键信息点（例如数字、结论）前留 0.5–1 秒静默或只留 pad，之后接一个 downbeat 底鼓——这是"电影感"的核心手法。
6. **混音**：BGM 峰值归一化到 **-3 dB**（与 `@remotion/sfx` 的做法一致）；在有配音的区段把 BGM 压到 **-18 ~ -14 dB**（即音量乘 0.12~0.2）。
7. **时长对齐**：把 BGM 视为"分段的"，每段与一个镜头卡区间对齐（用 SRT 或镜头卡时间轴生成 `Segment` 列表），而不是生成一整条再裁。

#### C12.5 不需要 GPU、可在 Windows CPU 上跑的方案汇总

| 方案 | 需要 GPU？ | 大致耗时量级（生成 1 分钟 BGM） | 算力成本 | 商用许可风险 |
|---|---|---|---|---|
| **现成免版权素材** | ❌ | **0（下载即用）** | 0 | 取决于素材授权（见 C12.6） |
| **Python/NumPy 程序化合成**（用 scipy 加速） | ❌ | **1–10 秒** | 极低 | ✅ 无（自己写的代码） |
| **Node 程序化合成** | ❌ | **1–10 秒** | 极低 | ✅ 无 |
| **Remotion `OfflineAudioContext` 渲染期合成** | ❌ | 与帧渲染并行，单次 **秒级~十几秒**（受 `delayRender` 30 秒超时约束） | 极低但占渲染进程 | ✅ 无 |
| **Tone.js `Tone.Offline()`** | ❌ | 同上；大规模合成有性能 issue | 低 | ✅ 无（Tone.js 为 MIT） |
| **Magenta（MusicVAE / MelodyRNN）** | ❌（CPU 可跑） | **分钟级**（且依赖老 TF，Python 3.12 装不上） | 低 | 代码 Apache 2.0；checkpoint 需核对 |
| **MusicGen-small（CPU）** | ❌（可，但慢） | **数分钟~数十分钟量级**（【未证实，需实测】） | 中 | ❌ **CC-BY-NC 4.0，禁止商用** |
| **MusicGen-medium / large** | ✅ 实际上必需 | GPU 上数十秒；CPU 上不实用 | 高 | ❌ 同上 |
| **Stable Audio Open 1.0** | ✅（8GB+ 显存量级） | GPU 数十秒 | 高 | ⚠️ Stability Community License，需核对收入阈值 |
| **ACE-Step / YuE / DiffRhythm** | ✅ | GPU 数十秒~分钟 | 高 | **【未证实】** |
| **Suno / Udio** | ❌（云端） | 云端分钟级 | 订阅费 | ⚠️ 条款多变、无稳定 API、不可复现 |

### C13. 结论建议：本项目的 BGM 方案排序

针对**"科技感/电影感"的中文科技新闻视频**，按「最省算力 + 最可控」排序：

#### 🥇 第 1 档：现成免版权 BGM 素材（默认选项）

**算力开销：0。时间开销：下载 + 试听，分钟级。**

- 优点：音质是专业母带级，程序化合成很难达到；一次挑选可长期复用；无 GPU。
- 缺点：**每期视频的 BGM 可能撞车**（观众听腻）；需要人工挑选；**授权必须逐个核对**。
- 主流来源与授权要点：

| 来源 | 授权要点 | 自动化批量适用性 |
|---|---|---|
| **YouTube Audio Library**（<https://support.google.com/youtube/answer/3376882>） | 曲目分"需署名"和"无需署名"两类；**仅限在 YouTube/相关平台使用**，用于其他平台的商业项目可能违反条款 | ⚠️ 仅适合 YouTube 分发 |
| **Pixabay Music**（<https://pixabay.com/music/>） | Pixabay Content License：可商用、通常无需署名；**禁止把素材本身作为主要商品再分发** | ✅ 适合（需核对最新许可） |
| **Free Music Archive**（<https://freemusicarchive.org/>） | 逐曲不同（CC-BY / CC-BY-NC / CC0 都有），**必须逐曲看** | ⚠️ 需逐曲核对 |
| **ccMixter**（<https://ccmixter.org/>） | 以 CC 为主，署名要求常见 | ⚠️ 需逐曲核对 |
| **Uppbeat**（<https://uppbeat.io/>） | 免费层需署名 + 有月度下载上限；付费层免署名 | ⚠️ 需付费 |
| **Epidemic Sound / Artlist** | 订阅制，**明确允许商业使用**，是最"干净"的商用方案；但**"批量自动化生产"是否在授权范围内需要读条款** | ⚠️ 条款需核对 |
| **Remotion `@remotion/sfx`**（<https://www.remotion.dev/docs/sfx/>） | 32 个**音效**（非 BGM），"无需署名"，NPM 包 MIT；各音效许可见详情页 | ✅ 适合做转场音效 |

> **⚠️ 关键风险**：订阅制音乐库（Epidemic/Artlist）的条款通常针对"内容创作者手工制作视频"，**把素材嵌进"自动批量生成的视频"里是否被允许，需要逐家确认**。**这是本项目必须确认的合规点之一。**

#### 🥈 第 2 档：Python/Node 程序化合成（推荐作为"自有品牌 BGM"）

**算力开销：极低（CPU 秒级）。时间开销：开发 1–2 天，之后每次生成 1–10 秒。**

- 优点：**完全免费、完全可商用（自己写的代码）、完全确定性可复现、可精确对齐镜头卡时间轴、不会撞曲**；用 Python 3.12 + numpy/scipy 就能跑；可直接产出 `public/bgm-tech.wav`。
- 缺点：**音乐性上限低**。要做出"电影感"需要一定的编曲知识（小调、pad 扫频、riser、drop 静默）。
- **落地建议**：做 **3–5 条模板**（如 `tech-pulse`、`cinematic-rise`、`minimal-tension`、`news-bed`、`outro-resolve`），每条 60–120 秒、可无缝 loop；按稿件情绪选模板；**在视频里做 ducking 让位给配音**。
- **这是本项目投入产出比最高的一档。** 一旦做好，后续每条视频的 BGM 成本是 **0**。

#### 🥉 第 3 档：Remotion 渲染期用 Web Audio 合成（仅在"每条视频必须独一无二"时）

**算力开销：极低但占用渲染进程。时间开销：随渲染并行，单次秒级~十几秒。**

- 官方有 `OfflineAudioContext` 示例背书，技术上可行。
- **但必须解决 3 个工程问题**：① `delayRender` 30 秒超时；② Data URL 内存（多个并发进程各持几十 MB）；③ 合成逻辑必须完全确定性。
- **推荐折中**：**用这条路径"生成一次"，然后把结果落盘成 wav，之后永远走 `staticFile()`。** 即把"生成"和"渲染"解耦。

#### 第 4 档：本地 AI 音乐模型（MusicGen / Stable Audio / ACE-Step）

**算力开销：中~高（GPU 数十秒~分钟；CPU 上数分钟~数十分钟）。**

- **MusicGen：权重 CC-BY-NC 4.0 → 商用直接排除。** 只有纯内部原型可以用。
- **Stable Audio Open：许可相对宽松，但需要 GPU**，Windows CPU-only 环境不实用。
- **ACE-Step 等：需要 GPU，许可以及 VRAM 需求本次未证实。**
- **结论：本项目当前环境（Windows + CPU）不建议走这一档。**

#### 第 5 档：云端 AI 音乐（Suno / Udio）

**算力开销：0（云端）。时间开销：分钟级。**

- **不适合自动化流水线**：无稳定官方 API、额度限制、条款频繁变动（含 Warner 交易带来的变化）、生成结果不可复现。
- 仅适合"人工偶尔做一条特别的 BGM"。
- **合规风险最高**：AI 生成音乐的版权归属与商用范围仍在变动中，且中国的《人工智能生成合成内容标识办法》（2025-09-01 施行）要求 AI 生成内容做标识。

#### 最终推荐组合

```
主线：现成免版权 BGM 素材（挑 10~20 条，按情绪分类缓存）
      +
补充：Python 程序化合成 3~5 条自有模板（覆盖"需要独一无二"的场景）
      +
点缀：@remotion/sfx 的转场音效（whoosh / riser / ding，无需署名）
      +
混音：Remotion 侧用 volume 回调做 ducking（配音期间 BGM 压到 0.12~0.2）
      +
不使用：MusicGen（NC 许可）、Suno/Udio（不可控）
```

**算力总量级**：BGM 环节的算力开销**基本可忽略**（相对于视频渲染本身）。**真正的成本在"挑素材/做模板"的一次性人工投入。**

---

## 5. 风险与不确定项

### 5.1 我未能确证的点

| # | 未确证项 | 说明 | 建议的确认方式 |
|---|---|---|---|
| 1 | **抖音的官方视频规范原文** | 时长上限、文件大小上限、推荐码率、编码要求均未找到可公开访问的官方页面；<https://www.biaojixia.com/specs/douyin> 是第三方聚合 | 登录抖音创作者服务中心 / 抖店后台规则中心查看最新要求 |
| 2 | **小红书的官方视频规范原文** | 同上；1080×1920 / ≤15 分钟 / ≤500MB 均来自第三方聚合页 | 登录小红书创作服务平台查看 |
| 3 | **抖音"安全区"官方数值** | 抖音官方只发布了广告位避让区域文档（飞书链接，需登录，抓取被重定向到 `accounts.larkoffice.com`）；108/320/60/120 来自创作者工具类文章 | 用真机截图 + 自检静帧实测；或登录飞书文档确认 |
| 4 | **抖音/小红书横屏视频的实际展示与裁切行为** | 未找到官方说明 | 上传测试视频实测 |
| 5 | **MusicGen 在 CPU 上的实际速度** | 未找到权威基准；搜索命中的多是论文 PDF（无法可靠提取数值） | 本地实测：`musicgen-small` 生成 10 秒音频的耗时 |
| 6 | **Stable Audio Open 1.0 的许可阈值与 GPU 显存下限** | 官方 HF 页与 Stability 页面本次均抓取失败（`fetch failed` / 正文未返回） | 直接打开 <https://huggingface.co/stabilityai/stable-audio-open-1.0> 与 <https://stability.ai/license> |
| 7 | **ACE-Step / YuE / DiffRhythm 的许可与硬件需求** | 只拿到仓库/模型页 URL，正文未取到 | 逐个读模型卡 |
| 8 | **Magenta 仓库的维护状态与 Python 3.12 兼容性** | GitHub README 正文未取到（页面只返回导航） | 读 <https://github.com/magenta/magenta> README + 检查 TF 版本要求 |
| 9 | **Suno 的版权归属条款原文** | 帮助中心页面抓取失败 | 读 <https://help.suno.com/en/articles/2746945-do-i-have-the-copyrights-to-songs-i-made> |
| 10 | **Epidemic Sound / Artlist 是否允许"自动批量生成视频"使用其素材** | 未核对条款 | 读各平台条款的"AI/自动化/批量"章节，或直接问客服 |
| 11 | **`audioBufferToDataUrl()` 的官方兼容性表内容** | 官方页面的浏览器/环境兼容表格抓取后为空 | 打开 <https://www.remotion.dev/docs/audio-buffer-to-data-url> 看实表 |
| 12 | **`AudioCraft` 代码许可的准确表述** | Replicate 页面写"code in this repository is Apache 2.0"而又说"Audiocraft 仓库代码是 MIT"，两句话似有矛盾（可能指 cog 封装是 Apache、audiocraft 本体是 MIT） | 读 <https://github.com/facebookresearch/audiocraft/blob/main/LICENSE> 确认 |
| 13 | **`@remotion/sfx` 各音效的具体许可** | 官方只给"各音效详情页"链接，未汇总 | 逐个打开 32 个详情页 |
| 14 | **Remotion 的 Automators / Creators 档位对"Python 批量渲染封装"的归类** | 官方描述是 "batch rendering and automated video products" / "low volume manual video creations"，边界需要判断 | 发邮件问 hi@remotion.dev 或看 License FAQ |
| 15 | **v3 的最终版本号** | 本次确认 `v3.3.96` tag 存在并成功读取其文档源；未逐一确认它是否为 v3 最后一个版本 | `npm view remotion versions --json` 过滤 3.x |
| 16 | **`@remotion/captions` 引入的确切 v4 版本号** | 确认是 v4.0 引入、v3 不存在；未确认是 4.0.0 还是 4.0.x 某个小版本 | 查 GitHub releases / CHANGELOG |

### 5.2 必须本地实测才能定论的点

1. **中文字体渲染**：`FontFace` + `staticFile()` 加载 Noto Sans SC（或子集化后的 woff2）在**无头 Chromium** 里是否稳定命中、是否有字重回退、是否有字形缺失（`document.fonts.check()` 可验证）。**不同 Windows 机器上字体回退行为可能不同。**
2. **`--concurrency` 的最佳值**：必须用 `npx remotion benchmark` 在你的目标机器（Windows + 具体 CPU/内存）上实测；本项目含 `<OffthreadVideo>` 与大量 `<Sequence>`，官方已明确警告高 concurrency 会引发 `delayRender` 超时。
3. **`--gl` 的最优值**：默认 `null` 在本机是否稳定；是否有帧出现黑块/花屏；`angle` vs `swangle` 的实际速度差。
4. **横竖屏双版本的渲染耗时比**：竖屏 1080x1920 与横屏 1920x1080 像素数相同（2,073,600），但**布局复杂度不同**（竖屏卡片更少、文字更大；横屏可能需要更多图表），实测每版耗时。
5. **BGM ducking 的实际听感**：程序化生成 BGM + 配音压制的具体音量曲线（0.12 还是 0.2）需要**用耳朵调**，并按耳机/手机外放两种场景验证。
6. **`OfflineAudioContext` 路径在你机器上的实际表现**：合成一段 90 秒的 BGM 需要多久、是否触发 30 秒 `delayRender` 超时、Data URL 内存峰值多少。
7. **`<OffthreadVideo>` vs `<Video>` 在本项目的实测速度差**：官方说 OffthreadVideo 更快，但官方也承认"无论用哪个，嵌入视频都是显著瓶颈"，且建议与 FFmpeg 组合。**本项目是否该把视频素材预先用 FFmpeg 合成，需要 quantify。**
8. **SRT 解析的边界情况**：中文全角标点、`\r\n`、时间戳用 `.` 而非 `,`、多行字幕、重叠字幕、空块——需要用真实稿件跑一遍。
9. **平台重编码后的实际画质**：上传后平台会二次转码，CRF 18 的源在不同平台上肉眼差异，需要上传实测。
10. **props JSON 的体积**：镜头卡数据（尤其含大量文本）会让 `--props` 文件变大；官方警告 `defaultProps` 过大有性能问题（<https://v3.remotion.dev/docs/troubleshooting/defaultprops-too-big>）。**建议把稿件内容通过 `public/` 下的 JSON 文件 + `fetch()` 读取，而不是塞进 props。**

### 5.3 需要立刻做的决策

1. **v3 还是 v4？** —— 见第 0.1 节。**强烈建议 v4**，否则 captions / zod / loadFont / calculateMetadata 全部要自研。
2. **横竖屏是"两个 Composition"还是"一个 Composition + `--width/--height` 覆盖"？** —— **建议两个 Composition**（布局差异大，且 Studio 可分别预览）。
3. **中文字体是否子集化？** —— 如果稿件文本可控，**强烈建议子集化**（体积从数 MB 降到数十 KB）。
4. **BGM 走哪一档？** —— **建议第 1 档（现成素材）+ 第 2 档（程序化模板）组合**，明确排除 MusicGen（NC 许可）与 Suno/Udio（不可控）。
5. **团队规模是否 ≥4 人 / 是否对外提供服务？** —— 决定是否需要 Remotion Company License。

---

## 6. 参考来源清单

### 6.1 Remotion v3 官方文档（本文核心依据）

| 主题 | URL |
|---|---|
| 文档首页 | <https://v3.remotion.dev/docs/> |
| `<Composition>` | <https://v3.remotion.dev/docs/composition> |
| `registerRoot()` | <https://v3.remotion.dev/docs/register-root> |
| `useVideoConfig()` | <https://v3.remotion.dev/docs/use-video-config> |
| `useCurrentFrame()` | <https://v3.remotion.dev/docs/use-current-frame> |
| `interpolate()` | <https://v3.remotion.dev/docs/interpolate> |
| `spring()` | <https://v3.remotion.dev/docs/spring> |
| `<Sequence>` | <https://v3.remotion.dev/docs/sequence> |
| `<Series>` | <https://v3.remotion.dev/docs/series> |
| `<AbsoluteFill>` | <https://v3.remotion.dev/docs/absolute-fill> |
| `Easing` | <https://v3.remotion.dev/docs/easing> |
| `<Audio>` | <https://v3.remotion.dev/docs/audio> |
| `<Video>` | <https://v3.remotion.dev/docs/video> |
| `<OffthreadVideo>` | <https://v3.remotion.dev/docs/offthreadvideo> |
| 使用音频（ducking / 音量曲线） | <https://v3.remotion.dev/docs/using-audio> |
| `staticFile()` | <https://v3.remotion.dev/docs/staticfile> |
| `@remotion/media-utils` 概览 | <https://v3.remotion.dev/docs/media-utils/> |
| `getAudioDurationInSeconds()` | <https://v3.remotion.dev/docs/get-audio-duration-in-seconds> |
| 动态时长（v3 方案） | <https://v3.remotion.dev/docs/dynamic-metadata> |
| 服务器端渲染（Node API 全流程） | <https://v3.remotion.dev/docs/ssr> |
| `bundle()` | <https://v3.remotion.dev/docs/bundle> |
| `getCompositions()` | <https://v3.remotion.dev/docs/renderer/get-compositions> |
| `renderMedia()` | <https://v3.remotion.dev/docs/renderer/render-media> |
| `renderStill()` | <https://v3.remotion.dev/docs/renderer/render-still> |
| `@remotion/renderer` 概览 | <https://v3.remotion.dev/docs/renderer> |
| CLI `render` | <https://v3.remotion.dev/docs/cli/render> |
| CLI `still` | <https://v3.remotion.dev/docs/cli/still> |
| CLI `preview`（v3 的 Studio） | <https://v3.remotion.dev/docs/cli/preview> |
| CLI `compositions` | <https://v3.remotion.dev/docs/cli/compositions> |
| CLI `benchmark` | <https://v3.remotion.dev/docs/cli/benchmark> |
| 配置文件（concurrency / crf / codec / gl / timeout） | <https://v3.remotion.dev/docs/config> |
| 编码指南（CRF 表 / 音频编码表） | <https://v3.remotion.dev/docs/encoding> |
| 输出缩放（`--scale`） | <https://v3.remotion.dev/docs/scaling> |
| 使用字体 | <https://v3.remotion.dev/docs/fonts> |
| `@remotion/google-fonts` | <https://v3.remotion.dev/docs/google-fonts> |
| 性能建议 | <https://v3.remotion.dev/docs/performance> |
| 超时排查 | <https://v3.remotion.dev/docs/timeout> |
| 渲染失败排查入口 | <https://v3.remotion.dev/docs/troubleshooting/debug-failed-render> |
| `<Composition>` 挂载错误 | <https://v3.remotion.dev/docs/wrong-composition-mount> |
| `defaultProps` 过大 | <https://v3.remotion.dev/docs/troubleshooting/defaultprops-too-big> |
| 许可证 | <https://v3.remotion.dev/docs/license> |

### 6.2 Remotion v4/v5 官方文档（版本差异依据）

| 主题 | URL |
|---|---|
| v4.0 迁移指南（zod schema / ffmpeg / quality 改名） | <https://www.remotion.dev/docs/4-0-migration> |
| v5.0 迁移指南 | <https://www.remotion.dev/docs/5-0-migration> |
| `calculateMetadata()` | <https://www.remotion.dev/docs/calculate-metadata> |
| `selectComposition()` | <https://www.remotion.dev/docs/renderer/select-composition> |
| Captions 总览 | <https://www.remotion.dev/docs/captions/> |
| 从 .srt 导入（`parseSrt`） | <https://www.remotion.dev/docs/captions/importing> |
| 显示字幕（`createTikTokStyleCaptions`） | <https://www.remotion.dev/docs/captions/displaying> |
| `@remotion/zod-types` | <https://www.remotion.dev/docs/zod-types/> |
| `@remotion/fonts` | <https://www.remotion.dev/docs/fonts-api/> |
| `@remotion/sfx`（音效库） | <https://www.remotion.dev/docs/sfx/> |
| `audioBufferToDataUrl()`（**含正弦音官方示例**） | <https://www.remotion.dev/docs/audio-buffer-to-data-url> |
| 许可证与定价 | <https://www.remotion.dev/docs/license/pricing> |
| License FAQ | <https://www.remotion.dev/docs/license/faq> |
| LICENSE 文件 | <https://github.com/remotion-dev/remotion/blob/main/LICENSE.md> |

### 6.3 BGM / 音频生成相关

| 来源 | URL |
|---|---|
| Tone.js `Offline()` | <https://tonejs.github.io/docs/15.1.22/functions/Offline.html> |
| Tone.js `OfflineContext` | <https://tonejs.github.io/docs/14.7.39/OfflineContext> |
| Tone.js 离线渲染性能 issue | <https://github.com/Tonejs/Tone.js/issues/436> |
| MusicGen 许可逐字说明（Replicate 页面） | <https://replicate.com/pphu/musicgen-small/readme> |
| AudioCraft 权重许可文件（CC-BY-NC 4.0） | <https://github.com/facebookresearch/audiocraft/blob/main/LICENSE_weights> |
| MusicGen 官方模型卡 | <https://facebookresearch.github.io/audiocraft/model_cards/MUSICGEN_STYLE_MODEL_CARD.html> |
| MusicGen HF 模型页 | <https://huggingface.co/facebook/musicgen-small> |
| MusicGen 论文 | <https://arxiv.org/abs/2306.05284> |
| Stable Audio Open 1.0 HF 页 | <https://huggingface.co/stabilityai/stable-audio-open-1.0> |
| Stable Audio Open 论文公告 | <https://stability.ai/news-updates/stable-audio-open-research-paper> |
| Stability AI 许可页 | <https://stability.ai/license> |
| Stable Audio Open 自托管说明（VRAM） | <https://gigagpu.com/stable-audio-open-self-hosted/> |
| Magenta 仓库 | <https://github.com/magenta/magenta> |
| Magenta RealTime 开放性评估 | <https://roserbatlleroca.github.io/MusGO_framework/models/magenta-realtime/> |
| ACE-Step 仓库 | <https://github.com/ace-step/ACE-Step> |
| ACE-Step v1.5 XL 权重 | <https://huggingface.co/ACE-Step/acestep-v15-xl-base> |
| Diffusers 的 ACE-Step pipeline 文档 | <https://raw.githubusercontent.com/huggingface/diffusers/main/docs/source/en/api/pipelines/ace_step.md> |
| Suno 版权帮助页 | <https://help.suno.com/en/articles/2746945-do-i-have-the-copyrights-to-songs-i-made> |
| Suno × Warner 条款变动报道 | <https://www.digitalmusicnews.com/2025/12/22/suno-warner-music-deal-changes/> |
| librosa 文档 | <https://librosa.org/doc/latest/index.html> |
| Remotion × 生成式媒体的 MCP 项目（社区） | <https://github.com/stephengpope/remotion-media-mcp> |

### 6.4 平台规范 / 安全区 / 合规

| 来源 | URL |
|---|---|
| 小红书图片/视频规格（第三方聚合，2026） | <https://www.biaojixia.com/specs/xiaohongshu> |
| 抖店图片/主图视频规格（第三方聚合，2026） | <https://www.biaojixia.com/specs/douyin> |
| 抖音 TopView 避让区域（飞书，需登录） | <https://bytedance.larkoffice.com/docx/H7fvdd7cmoSrqOx23GwcRaX0nCg> |
| 抖音信息流避让区域（飞书，需登录） | <https://bytedance.larkoffice.com/docx/AHJqdO0MpokNEyx7Fgxc6dEinkc> |
| TikTok / Reels / Shorts 安全区像素值（第三方） | <https://www.ffmpeg-micro.com/blog/tiktok-safe-zone-margins-aren-t-ffmpeg-pixels-convert-them> |
| YouTube Audio Library 使用条款 | <https://support.google.com/youtube/answer/3376882> |
| Pixabay 音乐库 | <https://pixabay.com/music/> |
| Free Music Archive | <https://freemusicarchive.org/> |
| ccMixter | <https://ccmixter.org/> |
| Uppbeat | <https://uppbeat.io/> |
| 《人工智能生成合成内容标识办法》施行报道（光明网） | <https://m.gmw.cn/2025-03/14/content_1303991368.htm> |
| 同上（标识方式说明） | <https://m.gmw.cn/2025-03/14/content_1303991405.htm> |
| AI 生成内容强制"电子水印"（检察日报） | <http://news.jcrb.com/shxw/202509/t20250901_7117645.html> |
| 8 家电商平台 AI 规范承诺书（人民网） | <http://bj.people.com.cn/n2/2025/1205/c14540-41432994.html> |
| 同上（北京市监局） | <https://scjgj.beijing.gov.cn/zwxx/mtjj/202512/t20251231_4382400.html> |

---

*文档结束。全文约 950 行。所有 **【未证实】** 与 **【推断】** 标记项请按第 5 节的方式本地核实后再进入生产。*

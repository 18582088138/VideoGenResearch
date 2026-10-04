# 002 — 中文字体：msyh.ttc 是 TTC 集合，@font-face 不可靠

## 现象

设计阶段需要选定中文字体。本机 `C:\Windows\Fonts` 可用的中文（简体）字体：

| 文件 | 字体 | 格式 | 许可 | 可用性 |
|---|---|---|---|---|
| `msyh.ttc` / `msyhbd.ttc` / `msyhl.ttc` | 微软雅黑 常规/粗/细 | **TTC 集合** | 微软专有（Windows 内可自由使用） | ⚠️ 见下 |
| `simhei.ttf` | 黑体 | TTF | 微软专有 | ✅ 可用但字形老旧 |
| `simsun.ttc` | 宋体 | TTC | 微软专有 | ⚠️ 同上，且宋体不适合科技感 |
| `Deng.ttf` / `Dengb.ttf` / `Dengl.ttf` | 等线 常规/粗/细 | TTF | 微软专有 | ✅ 可用，字形现代 |
| **`NotoSansSC-VF.ttf`** | **思源黑体 可变字重** | TTF (Variable) | **SIL OFL 1.1，可商用** | ⭐ **首选** |
| `NotoSerifSC-VF.ttf` | 思源宋体 可变字重 | TTF (Variable) | SIL OFL 1.1 | 备选（衬线，偏人文） |

## 根因

**TTC（TrueType Collection）是在一个文件里打包多个字体面**（雅黑一个文件里就有
Regular/Bold/Light 等多个 face）。CSS `@font-face` 的 `src: url(...)` **没有标准方式
指定取第几个 face**，浏览器行为不一致：

- Chromium 通常只取**第 0 个 face**，导致"想要粗体却拿到常规"或直接加载失败；
- 若同时声明多个 `@font-face` 指向同一 TTC，无法区分，静默取错。

Remotion 渲染跑在无头 Chromium 上，**字体加载失败不会报错**，只会 fallback 到系统
默认字体 —— 典型的「不报错，只是不对」，且**每帧独立渲染，fallback 也可能不一致**。

## 处置

**统一使用 `NotoSansSC-VF.ttf`（思源黑体可变字体）**，理由：

1. TTF 格式，`@font-face` 支持确定；
2. 可变字重（`font-variation-settings: 'wght' N`），一个文件覆盖 100–900 全部字重，
   避免多文件管理，也方便做「数字翻转」这类需要粗体的镜头；
3. **SIL OFL 1.1 授权，免署名可商用** —— 比微软专有字体更适合将来对外发布；
4. 字形现代、笔画均匀，符合科技感调性。

字体文件复制进工程 `public/fonts/`，用 `staticFile('fonts/NotoSansSC-VF.ttf')` +
`delayRender()` 保证**渲染前字体已就绪**（否则首帧会用 fallback 字体）。

## 复发预防

- 新增任何字体前先确认**格式不是 TTC/TTC2**；是 TTC 就换 TTF/OTF/WOFF2 版本。
- 字体加载一律走 `delayRender`/`continueRender` 包裹，**不允许"加载完就画"的乐观写法**。
- 本坑与 `assets/lib` 无关，属 Remotion 通用问题。

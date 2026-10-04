/**
 * 主题 token / Theme tokens.
 *
 * 唯一权威定义处是 docs/design/01_theme_palettes.md；本文件是其代码映射。
 * 改配色必须两边同步 —— 文档说不清、代码不生效都会造成"改了没反应"的假配置。
 *
 * The single source of truth is docs/design/01_theme_palettes.md; this file maps
 * it into code. Keep both in sync.
 */

export const CYAN_NOIR = {
  bg: "#04080A", // 全局底 / global background
  surface: "#0B1418", // 卡片面 / card surface
  surface2: "#15242A", // 次级面、轨道、进度底 / secondary surface, tracks
  primary: "#2DD4BF", // 主强调：数字、进度条、主标题点缀 / primary accent
  accent: "#7DF9FF", // 次强调：高光、描边、关键数字 / secondary accent
  alert: "#F97362", // 警示/对比：规则系统、代价段 / alert
  text: "#E8F1F2", // 正文 / body text
  textMuted: "#7A8C90", // 次要文字、来源标注 / muted text
  border: "#1E3138", // 描边 / borders
} as const;

export type ThemeTokens = typeof CYAN_NOIR;

/** 已注册主题 / Registered themes. */
export const THEMES: Record<string, ThemeTokens> = {
  "cyan-noir": CYAN_NOIR,
};

/** 取主题；未知 id 回退到默认主题，不抛错。
 *
 * Resolve a theme; unknown ids fall back to the default instead of throwing,
 * so a bad props value degrades visibly rather than crashing the render.
 */
export const getTheme = (id?: string): ThemeTokens =>
  (id && THEMES[id]) || CYAN_NOIR;

/** 字体族名 —— 与 public/fonts 下实际加载的字体一致。
 * Font family names, matching what public/fonts actually loads. */
export const FONT_FAMILY =
  "Noto Sans SC, Noto Sans SC VF, Source Han Sans SC, sans-serif";

/** 数字/指标用的重字重设置（可变字体），避免为粗体再引入一个字体文件。
 * Heavy weight via variable-font axis, so no second font file is needed. */
export const NUMERIC_WEIGHT = { fontVariationSettings: "'wght' 800" } as const;

/**
 * ═══════════════════════════════════════════════════════════════════════════
 * 全局可调参数 / Global tuning knobs
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * **调视频风格只改这里。** 各镜头组件都从这里读，改一处全局生效 ——
 * 避免"每个组件各写一份字号"导致改不干净。
 *
 * Change the look of every video from this one object; shot components read
 * their sizes and offsets from here rather than hard-coding their own.
 *
 * 每个旋钮的手感说明见 docs/guides/02_video_tuning.md。
 */
export const TUNING = {
  // ── 版式垂直分布（竖屏）/ Vertical distribution, portrait ──────────────
  /**
   * 画面上部留白，作为内容的起排位置。**这是治"头重脚轻"的主旋钮**：
   * 调大 → 整体下移、上方留白更多、画面更平衡；调小 → 内容更靠上。
   */
  portraitTopBias: 0.08,
  /** 横屏同义旋钮 / Same knob for landscape. */
  landscapeTopBias: 0.1,

  /** 字幕条字号（竖屏）/ Caption font size, portrait. */
  captionSizePortrait: 40,
  /** 字幕条字号（横屏）/ Caption font size, landscape. */
  captionSizeLandscape: 38,
  /** 字数超过此值自动缩一档，避免换行溢出 / Auto-shrink above this length. */
  captionShrinkAbove: 22,

  // ── 素材面板尺寸 / Asset panel sizing ──────────────────────────────────
  /**
   * 竖屏图片可用的**安全框高度比例**。调大 → 图更大（用户反馈竖屏图偏小）；
   * 但过大会把镜头的文案挤出画面，两者要一起看。
   */
  portraitImageHeightRatio: 0.42,
  /** 横屏同义旋钮 / Same knob for landscape. */
  landscapeImageHeightRatio: 0.62,
  /** 图片宽度上限（安全框比例）/ Max width as a fraction of the safe area. */
  imageWidthRatio: 0.94,

  // ── 片头 / Opening ────────────────────────────────────────────────────
  /** 主标题字号（竖屏）/ Title size, portrait. */
  titleSizePortrait: 70,
  /** 主标题字号（横屏）/ Title size, landscape. */
  titleSizeLandscape: 92,
  /** 副标字号（竖屏）/ Subtitle size, portrait. */
  subtitleSizePortrait: 32,
  /** 副标字号（横屏）/ Subtitle size, landscape: 30. */
  subtitleSizeLandscape: 30,

  // ── 图文类镜头 / Figure shots ─────────────────────────────────────────
  /** 图文面板标题字号（竖屏）/ Figure title size, portrait. */
  figureTitlePortrait: 42,
  /** 图文面板标题字号（横屏）/ Figure title size, landscape. */
  figureTitleLandscape: 44,
  /** 图文面板正文字号（竖屏）/ Figure body size, portrait. */
  figureBodyPortrait: 29,
  /** 图文面板正文字号（横屏）/ Figure body size, landscape. */
  figureBodyLandscape: 30,
} as const;

export type Tuning = typeof TUNING;

/**
 * 按方向取调参值 / Resolve an orientation-specific tuning value.
 *
 * @param portraitKey 竖屏用的键名 / key used in portrait
 * @param landscapeKey 横屏用的键名 / key used in landscape
 */
export const tuneByOrientation = <K extends keyof Tuning>(
  portrait: boolean,
  portraitKey: K,
  landscapeKey: K,
): number => (portrait ? TUNING[portraitKey] : TUNING[landscapeKey]) as number;

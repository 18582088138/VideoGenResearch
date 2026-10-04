/**
 * 版式派生 / Layout derivation.
 *
 * ═══════════════════════════════════════════════════════════════════════════
 * 设计原则 / Design principle
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * **横屏与竖屏是两套结构不同的设计，不是同一套布局换分辨率。**
 * 铁律：1920×1080 缩到 1080 宽会得到 1080×608，不是 9:16 —— 所以不能等比缩放。
 *
 * 本模块不再只给「中心 y」这类标量，而是给出**三个矩形区域**：
 *
 *   mediaZone   素材可用的最大矩形 —— 视觉主体
 *   textZone    文案排版区（标题 / 要点 / 指标）
 *   captionBox  字幕条区域
 *
 * 镜头组件只消费矩形，**不自己算坐标**。这样：
 *   1. 「独立设计」是结构上的（横屏左右分栏 vs 竖屏上中下三段）
 *   2. 消除各组件里 `heroCenterY + panelH/2 + 常数` 式的手算 ——
 *      实测已造成文案与字幕重叠（见 docs/plan/01_delivery_optimization.md §2.3）
 *
 * LANDSCAPE: left/right split (media left, text right).
 * PORTRAIT:  top/middle/bottom stack (media, text, captions).
 *
 * 素材尺寸不在这里定死 —— 每个镜头引用的素材长宽比不同。
 * 镜头用 :func:`fitInZone` 把素材适配进 ``mediaZone``。
 *
 * 安全区数值唯一权威处：docs/design/00_platform_output_spec.md §4。
 */

import { useVideoConfig } from "remotion";
import { TUNING, tuneByOrientation } from "./theme";

export type Orientation = "landscape" | "portrait";

/** 一个矩形区域（px，相对画布左上角）/ A rectangle in canvas pixels. */
export interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface Layout {
  /** 画面方向 / Orientation. */
  orientation: Orientation;
  width: number;
  height: number;

  /** 内容安全框（已扣掉平台 UI 与字幕带）/ Safe area, platform UI excluded. */
  safe: { left: number; right: number; top: number; bottom: number };
  safeWidth: number;
  safeHeight: number;

  /** 素材区（分栏模式）：**图文类镜头**用 —— 旁边还要放文案。
   *  Media zone (split mode) for figure shots that still need a text column. */
  mediaZone: Rect;
  /**
   * 全幅素材区：**纯素材镜头**用。
   *
   * 用户口径：「使用素材图片的就不要在分镜中添加文案了，素材图片+动效已经足够了」。
   * 这类镜头没有文案，所以素材可以占满整个内容区（而不是只占分栏的一侧），
   * 素材因此显著更大。
   *
   * Full-width media zone for asset-only shots. Those shots carry no copy, so the
   * asset may use the whole content area instead of one column.
   */
  mediaZoneFull: Rect;
  /** 文案区 / Text zone. */
  textZone: Rect;
  /** 字幕区 / Caption zone. */
  captionBox: Rect;

  /** 三个区的中心 y / Center-y of each zone. */
  mediaCenterY: number;
  textCenterY: number;
  captionCenterY: number;

  /** 兼容旧字段（等于 textZone 的中心与高度）/ Back-compat aliases. */
  contentCenterY: number;
  contentHeight: number;
  heroCenterY: number;

  /** 字号缩放：按画布宽高等比，保证同一字号在两种方向的视觉大小一致。 */
  fontScale: number;
  /** 内容最大宽度 / Max content width. */
  contentWidth: number;
}

// ── 结构性常量 / Structural constants ──────────────────────────────────────
// 这些决定「区域怎么分」，与「多大字号」这类审美参数分开：
// 前者改动会破坏布局契约，后者属于 TUNING（可在 theme.ts 里调）。

/** 竖屏左侧留白 / Portrait left inset. */
const PORTRAIT_LEFT_INSET = 48;
/** 竖屏右侧留白 —— 从 180 收到 48，让素材真正成为主体。
 *  Portrait right inset, tightened from 180 so the asset can be the subject. */
const PORTRAIT_RIGHT_INSET = 48;
/** 竖屏顶部留白 / Portrait top inset. */
const PORTRAIT_TOP_INSET = 100;
/** 竖屏底部平台 UI 遮挡（账号名/文案/音乐条）/ Portrait bottom occlusion. */
const PORTRAIT_BOTTOM_INSET = 420;
/** 字幕带高度 / Caption band height. */
const CAPTION_H_PORTRAIT = 170;
const CAPTION_H_LANDSCAPE = 110;

/** 横屏：素材区占可用宽的比例（左右分栏）/ Landscape: media share of width. */
const LANDSCAPE_MEDIA_SHARE = 0.58;
/** 横屏：分栏间隙 / Landscape column gap. */
const LANDSCAPE_GAP = 40;

/** 竖屏：素材区占「扣掉字幕后的可用高」的比例 / Portrait media share of height. */
const PORTRAIT_MEDIA_SHARE = 0.62;

/**
 * 由画布尺寸派生版式 / Derive layout from canvas size.
 *
 * @param width 画布宽（px）/ canvas width
 * @param height 画布高（px）/ canvas height
 */
export const deriveLayout = (width: number, height: number): Layout => {
  const portrait = height > width;
  const fontScale = portrait ? width / 1080 : height / 1080;

  if (portrait) {
    // ── 竖屏：上中下三段 / Portrait: three stacked bands ──────────────────
    const safe = {
      left: PORTRAIT_LEFT_INSET,
      right: PORTRAIT_RIGHT_INSET,
      top: PORTRAIT_TOP_INSET,
      bottom: PORTRAIT_BOTTOM_INSET + CAPTION_H_PORTRAIT,
    };
    const safeWidth = width - safe.left - safe.right;
    const safeHeight = height - safe.top - safe.bottom;

    const captionBox: Rect = {
      x: safe.left,
      y: safe.top + safeHeight - CAPTION_H_PORTRAIT,
      w: safeWidth,
      h: CAPTION_H_PORTRAIT,
    };
    const usableH = safeHeight - CAPTION_H_PORTRAIT;
    const mediaH = usableH * PORTRAIT_MEDIA_SHARE;

    const mediaZone: Rect = { x: safe.left, y: safe.top, w: safeWidth, h: mediaH };
    const textZone: Rect = {
      x: safe.left,
      y: safe.top + mediaH,
      w: safeWidth,
      h: usableH - mediaH,
    };
    // 纯素材镜头：没有文案，素材占满整个内容区
    const mediaZoneFull: Rect = {
      x: safe.left,
      y: safe.top,
      w: safeWidth,
      h: usableH,
    };

    return {
      orientation: "portrait",
      width,
      height,
      safe,
      safeWidth,
      safeHeight,
      mediaZone,
      mediaZoneFull,
      textZone,
      captionBox,
      mediaCenterY: mediaZone.y + mediaZone.h / 2,
      textCenterY: textZone.y + textZone.h / 2,
      captionCenterY: captionBox.y + captionBox.h / 2,
      contentCenterY: textZone.y + textZone.h / 2,
      contentHeight: textZone.h,
      heroCenterY: mediaZone.y + mediaZone.h / 2,
      fontScale,
      contentWidth: safeWidth,
    };
  }

  // ── 横屏：左右分栏 / Landscape: two columns ────────────────────────────
  const safe = {
    left: 80,
    right: 80,
    top: 60,
    bottom: 140 + CAPTION_H_LANDSCAPE,
  };
  const safeWidth = width - safe.left - safe.right;
  const safeHeight = height - safe.top - safe.bottom;

  const captionBox: Rect = {
    x: safe.left,
    y: safe.top + safeHeight - CAPTION_H_LANDSCAPE,
    w: safeWidth,
    h: CAPTION_H_LANDSCAPE,
  };
  const usableH = safeHeight - CAPTION_H_LANDSCAPE;
  const mediaW = safeWidth * LANDSCAPE_MEDIA_SHARE;

  const mediaZone: Rect = { x: safe.left, y: safe.top, w: mediaW, h: usableH };
  const textZone: Rect = {
    x: safe.left + mediaW + LANDSCAPE_GAP,
    y: safe.top,
    w: safeWidth - mediaW - LANDSCAPE_GAP,
    h: usableH,
  };
  // 纯素材镜头：没有文案，素材占满整个内容区（横屏下比左栏宽 72%）
  const mediaZoneFull: Rect = {
    x: safe.left,
    y: safe.top,
    w: safeWidth,
    h: usableH,
  };

  return {
    orientation: "landscape",
    width,
    height,
    safe,
    safeWidth,
    safeHeight,
    mediaZone,
    mediaZoneFull,
    textZone,
    captionBox,
    mediaCenterY: mediaZone.y + mediaZone.h / 2,
    textCenterY: textZone.y + textZone.h / 2,
    captionCenterY: captionBox.y + captionBox.h / 2,
    contentCenterY: textZone.y + textZone.h / 2,
    contentHeight: textZone.h,
    heroCenterY: mediaZone.y + mediaZone.h / 2,
    fontScale,
    contentWidth: textZone.w,
  };
};

/** 在组件内取当前 Composition 的版式 / Layout for the current composition. */
export const useLayout = (): Layout => {
  const { width, height } = useVideoConfig();
  return deriveLayout(width, height);
};

/**
 * 把素材适配进一个区域（保持长宽比，居中）/ Fit an asset into a zone.
 *
 * 取宽高两个方向更紧的约束（``Math.min``），因此**素材永远不裁切、不变形**，
 * 且在区域里尽可能大。横图由宽度绑定、竖图由高度绑定，两者都能填满一个方向。
 *
 * Uses the tighter of the two constraints, so the asset is never cropped or
 * stretched and grows as large as the zone allows.
 *
 * @param dims 素材原始尺寸 / the asset's natural size
 * @param zone 可用区域 / the available zone
 * @param fill 占区比例（1 = 铺满区）/ how much of the zone to fill
 */
export const fitInZone = (
  dims: { w: number; h: number },
  zone: Rect,
  fill = 1,
): Rect => {
  if (dims.w <= 0 || dims.h <= 0) {
    return { x: zone.x, y: zone.y, w: zone.w, h: zone.h };
  }
  const scale = Math.min((zone.w * fill) / dims.w, (zone.h * fill) / dims.h);
  const w = dims.w * scale;
  const h = dims.h * scale;
  return {
    x: zone.x + (zone.w - w) / 2,
    y: zone.y + (zone.h - h) / 2,
    w,
    h,
  };
};

/**
 * 按方向取 `TUNING` 里的旋钮 / Resolve an orientation-specific TUNING knob.
 *
 * 组件一律经此读参数，**不要内联 `portrait ? 42 : 44`** ——
 * 那样会让 TUNING 变成改不动的死配置（本项目踩过，见优化方案 §2.2）。
 */
export const tune = (
  layout: Layout,
  portraitKey: keyof typeof TUNING,
  landscapeKey: keyof typeof TUNING,
): number =>
  tuneByOrientation(layout.orientation === "portrait", portraitKey, landscapeKey);

/**
 * 把设计稿坐标（以 1920×1080 为准）换算到当前画布。
 *
 * Map design-space units (authored against 1920×1080) onto the current canvas.
 * 用于从镜头卡 demo 抄来的具体 px 数值 —— 那些数字是按其设计坐标调的，
 * 直接用在竖屏上会错位。
 */
export const scaleFromDesign = (value: number, layout: Layout): number =>
  value * layout.fontScale;

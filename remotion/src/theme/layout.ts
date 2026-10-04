/**
 * 版式派生 / Layout derivation.
 *
 * 铁律：横竖屏**不是等比缩放**。1920×1080 缩到 1080 宽会得到 1080×608，
 * 不是 9:16。所以尺寸与安全区一律由 useVideoConfig() 的 width/height
 * 实时派生，横竖屏各走自己的分支。
 *
 * Landscape and portrait are NOT a uniform scale of one another: 1920×1080
 * scaled to width 1080 yields 1080×608, which is not 9:16. Dimensions and safe
 * areas are therefore derived from useVideoConfig() at render time.
 *
 * 安全区数值唯一权威处：docs/design/00_platform_output_spec.md §4。
 *
 * Authoritative safe-area numbers live in docs/design/00_platform_output_spec.md.
 */

import { useVideoConfig } from "remotion";

export type Orientation = "landscape" | "portrait";

export interface Layout {
  /** 画面方向 / Orientation. */
  orientation: Orientation;
  /** 画布宽高（px）/ Canvas size in px. */
  width: number;
  height: number;
  /** 内容安全框（px）/ Content safe area in px. */
  safe: { left: number; right: number; top: number; bottom: number };
  /** 安全框的实际宽高（px）/ Derived safe-area size. */
  safeWidth: number;
  safeHeight: number;
  /**
   * 内容可用区（**已扣掉底部字幕带**）的高度与中心 y。
   *
   * 这是治「头重脚轻」的关键：`safe` 把字幕带也算在里面，
   * 若按 `safe` 顶对齐，内容会堆在上半屏、下方大片空白（实测反馈）。
   * 镜头应把内容在 `contentHeight` 里**垂直居中**，
   * 而不是从 `safe.top` 往下排。
   */
  contentHeight: number;
  contentCenterY: number;
  /** 主视觉区中心 y（px）—— 与 contentCenterY 同义，保留旧名以免改动过大。 */
  heroCenterY: number;
  /** 字幕基线中心 y（px）/ Caption baseline center-y in px. */
  captionCenterY: number;
  /** 基础字号比例 / Base font scale. */
  fontScale: number;
  /** 内容最大宽度（px）/ Max content width in px. */
  contentWidth: number;
}

/** 竖屏底部平台 UI 遮挡高度（px）—— 抖音底部账号/文案/音乐条。
 * Portrait bottom occlusion from platform UI. */
const PORTRAIT_BOTTOM_INSET = 420;
/** 竖屏右侧按钮栏遮挡宽度（px）。 */
const PORTRAIT_RIGHT_INSET = 180;
/** 字幕带高度（px）—— 内容区必须把它扣掉，否则内容会与字幕打架。 */
const CAPTION_BAND_PORTRAIT = 180;
const CAPTION_BAND_LANDSCAPE = 120;

/**
 * 由画布尺寸派生版式 / Derive layout from canvas size.
 *
 * @param width 画布宽（px）/ canvas width
 * @param height 画布高（px）/ canvas height
 */
export const deriveLayout = (width: number, height: number): Layout => {
  const portrait = height > width;

  if (portrait) {
    // 1080×1920：字幕必须显著高于底部 420px 遮挡区。
    // bottom 再加 180 是**留给字幕带本身**的高度 —— 字幕条不是压在遮挡区边缘上，
    // 而是压在 safe 框下沿，所以 safe 框必须先把字幕的位置扣掉，
    // 否则镜头内容会与字幕打架（实测过这个错位）。
    const safe = {
      left: 60,
      right: PORTRAIT_RIGHT_INSET,
      top: 120,
      bottom: PORTRAIT_BOTTOM_INSET + CAPTION_BAND_PORTRAIT,
    };
    const safeWidth = width - safe.left - safe.right;
    const safeHeight = height - safe.top - safe.bottom;

    // **内容可用区 = 安全框再扣掉字幕带**。
    // 镜头把内容在这个区域里垂直居中 —— 这是治「头重脚轻」的核心：
    // 若从 safe.top 往下顶对齐，内容会堆在上半屏、下方留大片空白（实测反馈）。
    const contentHeight = safeHeight - CAPTION_BAND_PORTRAIT;
    const contentCenterY = safe.top + contentHeight / 2;

    return {
      orientation: "portrait",
      width,
      height,
      safe,
      safeWidth,
      safeHeight,
      contentHeight,
      contentCenterY,
      heroCenterY: contentCenterY,
      // 字幕条固定贴在内容区下沿再往下一点
      captionCenterY: safe.top + contentHeight + CAPTION_BAND_PORTRAIT * 0.45,
      fontScale: width / 1080,
      contentWidth: safeWidth,
    };
  }

  // 1920×1080：横屏相对宽松，同样把字幕带高度从 safe 里扣掉。
  const safe = { left: 80, right: 80, top: 60, bottom: 140 + CAPTION_BAND_LANDSCAPE };
  const safeWidth = width - safe.left - safe.right;
  const safeHeight = height - safe.top - safe.bottom;
  const contentHeight = safeHeight;
  const contentCenterY = safe.top + contentHeight / 2;

  return {
    orientation: "landscape",
    width,
    height,
    safe,
    safeWidth,
    safeHeight,
    contentHeight,
    contentCenterY,
    heroCenterY: contentCenterY,
    captionCenterY: safe.top + contentHeight + CAPTION_BAND_LANDSCAPE * 0.45,
    fontScale: height / 1080,
    contentWidth: safeWidth,
  };
};

/** 在组件内取当前 Composition 的版式 / Layout for the current composition. */
export const useLayout = (): Layout => {
  const { width, height } = useVideoConfig();
  return deriveLayout(width, height);
};

/**
 * 把设计稿坐标（以 1920×1080 为准）换算到当前画布。
 *
 * Map design-space units (authored against 1920×1080) onto the current canvas.
 * 用于从镜头卡 demo 抄来的具体 px 数值 —— 那些数字是按其设计坐标调的，
 * 直接用在竖屏上会错位。
 */
export const scaleFromDesign = (value: number, layout: Layout): number =>
  value * layout.fontScale;

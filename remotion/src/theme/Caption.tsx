/**
 * 字幕条 / Caption bar.
 *
 * 承载中文字幕。设计约束（来自 docs/design/00_platform_output_spec.md §4）：
 * 竖屏底部 420px 被平台 UI 遮挡，所以字幕位置由 layout.captionCenterY 决定，
 * **不允许**各镜头自行写死 y 坐标。
 *
 * Captions are positioned by layout.captionCenterY; individual shots must not
 * hard-code a y coordinate, because portrait's bottom 420px is occluded.
 */

import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { FONT_FAMILY, ThemeTokens, TUNING, tuneByOrientation } from "./theme";
import { Layout } from "./layout";

export interface CaptionProps {
  /** 当前应显示的字幕文本 / Current cue text. */
  text: string;
  /** 本段字幕在所属 Sequence 内的起始帧 / Cue start frame within its Sequence. */
  from: number;
  /** 本段字幕在所属 Sequence 内的结束帧 / Cue end frame within its Sequence. */
  to: number;
  theme: ThemeTokens;
  layout: Layout;
  /** 淡入淡出帧数 / Fade-in and fade-out length in frames. */
  fadeFrames?: number;
}

/**
 * 单条字幕：淡入 → 长 hold → 淡出，底垫半透明面板保证深色画面上的可读性。
 *
 * One cue: fade in, long hold, fade out, over a translucent panel so it stays
 * legible on a dark background.
 */
export const Caption: React.FC<CaptionProps> = ({
  text,
  from,
  to,
  theme,
  layout,
  fadeFrames = 6,
}) => {
  const frame = useCurrentFrame();

  if (frame < from || frame > to) {
    return null;
  }

  // 用平滑曲线做透明度，避免频闪；clamp 保护 fadeFrames 大于段长的情况。
  const opacity = interpolate(
    frame,
    [from, from + fadeFrames, to - fadeFrames, to],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  // 字号来自全局 TUNING（用户反馈"字幕字体过大"→ 已从 46/44 降到 40/38）。
  // 字数超过阈值再自动收一档，避免长条换行溢出安全框。
  const baseSize = tuneByOrientation(
    layout.orientation === "portrait",
    "captionSizePortrait",
    "captionSizeLandscape",
  );
  const fontSize =
    text.length > TUNING.captionShrinkAbove ? baseSize * 0.84 : baseSize;

  return (
    <div
      style={{
        position: "absolute",
        left: layout.safe.left,
        width: layout.safeWidth,
        top: layout.captionCenterY,
        transform: "translateY(-50%)",
        display: "flex",
        justifyContent: "center",
        opacity,
        fontFamily: FONT_FAMILY,
      }}
    >
      <div
        style={{
          maxWidth: layout.safeWidth,
          padding: `${fontSize * 0.34}px ${fontSize * 0.72}px`,
          borderRadius: fontSize * 0.36,
          // 半透明面 + 描边：纯透明会与背景曲线相亲，纯实心会挡住画面
          background: "rgba(4,8,10,0.66)",
          border: `1px solid ${theme.border}`,
          color: theme.text,
          fontSize,
          lineHeight: 1.42,
          fontWeight: 500,
          textAlign: "center",
          letterSpacing: "0.01em",
        }}
      >
        {text}
      </div>
    </div>
  );
};

/** 给 fps 计算的辅助：把秒换算成帧，供各处复用。
 * Shared helper: seconds to frames. */
export const sec = (seconds: number, fps: number): number =>
  Math.round(seconds * fps);

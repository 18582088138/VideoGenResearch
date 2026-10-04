/**
 * 片头字标揭示 / Opening wordmark reveal.
 *
 * 借鉴 video-shotcraft `letterspace-materialize` 卡的**动机**（大字距字标逐字描画结晶、
 * 末段长 hold），但**实现与参数是本项目自行调校的** —— 原卡按米白衬线风调参，
 * 与本项目深青科技风不同，按 SKILL.md 要求「只继承运动语法，视觉重新蒙皮」。
 *
 * Inspired by the `letterspace-materialize` card's motion grammar (wide-tracked
 * wordmark materialising character by character, then a long hold). The
 * implementation and parameters are tuned here, not copied: that card was tuned
 * for a cream serif style, and only the motion grammar transfers.
 *
 * 时间结构 / Timing:
 *   0 → 18f     : 字距从 0.5em 收拢到 0.02em（"结晶"）
 *   0 → 30f     : 字符逐个由模糊变清晰（每字间隔 3f）
 *   30f → 结束  : 长 hold（≥1s，SKILL.md 要求品牌字标落定后 hold ≥1s）
 */

import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { ThemeTokens, FONT_FAMILY } from "../theme/theme";
import { Layout } from "../theme/layout";

/** 按方向取字号的小工具 / Pick a size by orientation. */
const portraitSize = (layout: Layout, portraitPx: number, landscapePx: number): number =>
  layout.orientation === "portrait" ? portraitPx : landscapePx;

export interface TitleRevealProps {
  title: string;
  subtitle?: string;
  /** 角标：主标上方的等宽小字（期刊/年份/栏目）/ Eyebrow above the title. */
  eyebrow?: string;
  theme: ThemeTokens;
  layout: Layout;
  /** 本镜头总帧数 / Total frames of this shot. */
  durationInFrames: number;
}

export const TitleReveal: React.FC<TitleRevealProps> = ({
  title,
  subtitle,
  eyebrow,
  theme,
  layout,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();

  // 字距收拢：这是"结晶"感的主要来源
  const tracking = interpolate(frame, [0, 18], [0.5, 0.02], {
    extrapolateRight: "clamp",
  });

  // 标题整体位移与透明度
  const titleOpacity = interpolate(frame, [0, 12], [0, 1], {
    extrapolateRight: "clamp",
  });

  // 副标晚于主标出现，且从下方 18px 浮上
  const subOpacity = interpolate(frame, [26, 42], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const subShift = interpolate(frame, [26, 42], [18, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // 收尾 12 帧整体轻微上浮失焦，交棒下一镜
  const exitOpacity = interpolate(
    frame,
    [durationInFrames - 12, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  // **字号自适应**：按最长一行的字符宽度估算，避免在单词中间折行。
  // 中文字宽 ≈ 1.0em，拉丁字母 ≈ 0.55em —— 混排时必须按这个折算，
  // 否则「清华团队登 Science Robotics」会被切成「Science Rob / otics」（实测）。
  //
  // Size the title from the longest line so it never wraps mid-word. CJK glyphs
  // are ~1.0em wide and Latin ~0.55em; ignoring that split "Robotics" in half.
  const emWidth = (s: string): number => {
    let w = 0;
    for (const ch of s) {
      w += /[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]/.test(ch) ? 1.0 : 0.55;
    }
    return Math.max(w, 1);
  };
  const longest = Math.max(emWidth(title), emWidth(subtitle ?? ""));
  const baseTitle = layout.orientation === "portrait" ? 74 : 96;
  const titleSize = Math.min(baseTitle, (layout.safeWidth * 0.94) / longest);
  const subSize = Math.min(
    layout.orientation === "portrait" ? 34 : 30,
    (layout.safeWidth * 0.94) / emWidth(subtitle ?? title),
  );

  // 逐字解锁：每个字符晚 3 帧出现，制造"连续描画"的观感
  const chars = Array.from(title);

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: FONT_FAMILY,
        opacity: exitOpacity,
      }}
    >
      {/* 角标：先于主标出现，给一个"这是什么栏目/什么来源"的交代。
          v1 没有片头，直接进内容 —— 观众缺少开场信号。 */}
      {eyebrow ? (
        <div
          style={{
            opacity: interpolate(frame, [0, 10], [0, 1], {
              extrapolateRight: "clamp",
            }),
            fontFamily: "monospace",
            fontSize: portraitSize(layout, 22, 20),
            letterSpacing: "0.3em",
            color: theme.primary,
            marginBottom: layout.orientation === "portrait" ? 34 : 28,
          }}
        >
          {eyebrow}
        </div>
      ) : null}

      <div
        style={{
          opacity: titleOpacity,
          fontSize: titleSize,
          fontWeight: 700,
          color: theme.text,
          letterSpacing: `${tracking}em`,
          textAlign: "center",
          maxWidth: layout.contentWidth,
          lineHeight: 1.24,
          // 文字自带极淡光晕，与背景光斑呼应但不喧哗
          textShadow: `0 0 42px ${theme.primary}33`,
        }}
      >
        {chars.map((ch, i) => {
          const appear = interpolate(frame, [i * 3, i * 3 + 12], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          return (
            <span
              key={`${ch}-${i}`}
              style={{
                opacity: appear,
                display: "inline-block",
                // 未就位的字符轻微模糊，模拟"描画中"
                filter: `blur(${(1 - appear) * 6}px)`,
              }}
            >
              {ch === " " ? "\u00A0" : ch}
            </span>
          );
        })}
      </div>

      {subtitle ? (
        <div
          style={{
            opacity: subOpacity,
            transform: `translateY(${subShift}px)`,
            marginTop: titleSize * 0.38,
            fontSize: subSize,
            fontWeight: 400,
            color: theme.primary,
            letterSpacing: "0.16em",
            textAlign: "center",
            maxWidth: layout.contentWidth * 0.92,
          }}
        >
          {subtitle}
        </div>
      ) : null}
    </div>
  );
};

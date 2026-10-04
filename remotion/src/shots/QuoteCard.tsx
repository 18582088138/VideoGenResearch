/**
 * 论断引卡 / Quote card — 单句论断或结论.
 *
 * 内容形态：一句话结论、一句引用、一个立场（"这套框架的代价是不可复现"）。
 * 这种内容不该被拆成要点列表 —— 拆了就丢了「一句话就是全部」的力度。
 *
 * A single statement or conclusion. This shape must not be broken into bullets:
 * its whole force is that one sentence *is* the content.
 *
 * 动效（动效即节拍）：
 *   - 大号引号先淡入并轻微放大（`0–12f`）
 *   - 正文**逐行上浮**（每行 12f，错峰 6f）—— 行由换行符或句末标点切出
 *   - 底部细线由中间向两侧展开（`scaleX`，origin center）
 *   - `subtext`（出处）最后淡入
 *
 * 命门：细线必须**后于**正文出现 —— 它读作"落款"，先出现就变成装饰下划线。
 */

import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { FONT_FAMILY, ThemeTokens } from "../theme/theme";
import { Layout, tune } from "../theme/layout";

export interface QuoteCardProps {
  /** 论断正文 / The statement itself. */
  text: string;
  /** 出处或补充说明 / Attribution or addendum. */
  subtext?: string;
  /** 底部结论条 / Closing takeaway line. */
  footer?: string;
  theme: ThemeTokens;
  layout: Layout;
  durationInFrames: number;
}

/**
 * 把整句切成"行" / Split a statement into lines.
 *
 * 中文长句通常没有换行符，所以：先按显式换行切，再按句末标点切句 ——
 * 标点是文本里最可靠的断点，比按字符数硬切读起来自然。
 */
const splitLines = (text: string): string[] => {
  const hard = text
    .split(/\n+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
  const paras = hard.length ? hard : [text.trim()];
  const lines: string[] = [];
  for (const para of paras) {
    const sentences = para
      .split(/(?<=[。！？；!?;])/)
      .map((s) => s.trim())
      .filter((s) => s.length > 0);
    if (sentences.length <= 1) {
      lines.push(para);
    } else {
      lines.push(...sentences);
    }
  }
  return lines.length ? lines : [text];
};

export const QuoteCard: React.FC<QuoteCardProps> = ({
  text,
  subtext,
  footer,
  theme,
  layout,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();

  const lines = splitLines(text);
  const lineCount = Math.max(1, lines.length);

  // 引号先落，再排版正文
  const markIn = interpolate(frame, [0, 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  const LINE_FROM = 10;
  const LINE_STAGGER = 6;
  const lineStart = (i: number): number => LINE_FROM + i * LINE_STAGGER;

  const lineTail = lineStart(lineCount - 1) + 12;

  // 细线在正文最后一行落定后才展开（它是"落款"，不是下划线）
  const ruleGrow = Math.max(
    0,
    interpolate(frame, [lineTail + 2, lineTail + 18], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.out(Easing.cubic),
    }),
  );

  const exit = interpolate(
    frame,
    [durationInFrames - 10, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const titleSize = tune(layout, "figureTitlePortrait", "figureTitleLandscape");
  const bodySize = tune(layout, "figureBodyPortrait", "figureBodyLandscape");
  const quoteSize = titleSize * 2.1;

  return (
    <AbsoluteFill style={{ fontFamily: FONT_FAMILY, opacity: exit }}>
      <div
        style={{
          position: "absolute",
          left: layout.textZone.x,
          top: layout.textZone.y,
          width: layout.textZone.w,
          height: layout.textZone.h,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
        }}
      >
        {/* 大号引号：只做一次落定，不参与后续节拍 */}
        <div
          style={{
            opacity: markIn * 0.75,
            transform: `scale(${0.7 + markIn * 0.3})`,
            transformOrigin: "left bottom",
            fontSize: quoteSize,
            lineHeight: 0.8,
            color: theme.primary,
            height: quoteSize * 0.6,
          }}
        >
          &ldquo;
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: layout.textZone.h * 0.012,
          }}
        >
          {lines.map((line, i) => {
            const start = lineStart(i);
            const t = interpolate(frame, [start, start + 12], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.out(Easing.cubic),
            });
            return (
              <div
                key={i}
                style={{
                  opacity: t,
                  transform: `translateY(${(1 - t) * 18}px)`,
                  fontSize: titleSize,
                  fontWeight: 700,
                  color: theme.text,
                  lineHeight: 1.45,
                  letterSpacing: "0.01em",
                }}
              >
                {line}
              </div>
            );
          })}
        </div>

        {/* 细线：由中间向两侧展开 */}
        <div
          style={{
            marginTop: layout.textZone.h * 0.05,
            width: layout.safeWidth * 0.46,
            height: 2,
            background: `linear-gradient(90deg, transparent, ${theme.primary}, transparent)`,
            transform: `scaleX(${ruleGrow})`,
            transformOrigin: "center center",
          }}
        />

        {subtext ? (
          <div
            style={{
              marginTop: layout.textZone.h * 0.035,
              opacity: interpolate(frame, [lineTail + 14, lineTail + 30], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }),
              fontFamily: "monospace",
              fontSize: bodySize * 0.72,
              letterSpacing: "0.12em",
              color: theme.textMuted,
            }}
          >
            {subtext}
          </div>
        ) : null}

        {footer ? (
          <div
            style={{
              marginTop: layout.textZone.h * 0.035,
              opacity: interpolate(frame, [lineTail + 24, lineTail + 38], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }),
              fontSize: bodySize,
              fontWeight: 700,
              color: theme.accent,
              letterSpacing: "0.02em",
            }}
          >
            {footer}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

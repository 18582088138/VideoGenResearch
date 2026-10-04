/**
 * 并列枚举网格 / Icon grid — 无序多项的并列呈现.
 *
 * 内容形态：一篇文章里「同时并列、没有先后」的几项（三种能力、四条原则、
 * 若干参与方…）。这类内容原先只能塞进 figure-panel 的要点列表，读起来是
 * 「顺序清单」，读者会默认它有先后 —— 网格则天然读作「并列」。
 *
 * A grid of parallel, unordered items. A bullet list reads as a sequence; a grid
 * reads as peers — which is the actual relationship for "three capabilities" or
 * "four principles".
 *
 * 命门（已遵守）：
 *   - 列数**由项数决定**（2–4 项 2 列、5–6 项 3 列），不看横竖屏 ——
 *     同一份分镜在两种画幅下的分栏结构必须一致
 *   - 图标位只用简单几何字形，**不引图标库**（新增依赖会让渲染体积与
 *     字体/图形加载路径一起变复杂）
 *   - 每格错峰弹入并带轻微 scale 过冲（`out(back)`），落定后真静止
 *   - 伪随机（字形选择）从 index 推出，绝不用 `Math.random`
 */

import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { FONT_FAMILY, ThemeTokens } from "../theme/theme";
import { Layout, tune } from "../theme/layout";

export interface IconGridProps {
  /** 网格标题 / Grid title. */
  title: string;
  /** 来源/角标 / Eyebrow above the title. */
  eyebrow?: string;
  /** 每个格子的标签（一项一个）/ One label per cell. */
  bullets: string[];
  /** 底部结论条 / Closing takeaway line. */
  footer?: string;
  theme: ThemeTokens;
  layout: Layout;
  durationInFrames: number;
}

/**
 * 图标字形表 / Glyph set.
 *
 * 只取简单几何符号（Unicode 几何区，系统中文字体栈里都有），
 * 避免引入图标库；按 index 取，确定性。
 */
const GLYPHS = ["●", "■", "◆", "▲", "○", "▮", "✦", "▼"];

/** 列数：2–4 项 2 列、5–6 项 3 列（与 Python 侧形态表同口径）/ Columns by item count. */
const columnsFor = (count: number): number => {
  if (count <= 1) return 1;
  if (count <= 4) return 2;
  return 3;
};

export const IconGrid: React.FC<IconGridProps> = ({
  title,
  eyebrow,
  bullets,
  footer,
  theme,
  layout,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const n = Math.max(1, bullets.length);
  const cols = columnsFor(n);
  const rows = Math.ceil(n / cols);

  const titleIn = interpolate(frame, [0, 14], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  // 错峰：整段约 40% 时长用于铺开，其余留读图
  const stagger = Math.max(6, Math.min(14, Math.floor((durationInFrames * 0.4) / n)));
  const cellStart = (i: number): number => 14 + i * stagger;

  const exit = interpolate(
    frame,
    [durationInFrames - 10, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  // 字号与间距一律经 TUNE / 区域派生，不内联 `portrait ? a : b`
  const titleSize = tune(layout, "figureTitlePortrait", "figureTitleLandscape");
  const bodySize = tune(layout, "figureBodyPortrait", "figureBodyLandscape");
  const eyebrowSize = bodySize * 0.68;
  const gap = layout.safeWidth * 0.022;
  const pad = layout.textZone.h * 0.03;

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
        }}
      >
        {eyebrow ? (
          <div
            style={{
              opacity: titleIn,
              fontFamily: "monospace",
              fontSize: eyebrowSize,
              letterSpacing: "0.22em",
              color: theme.primary,
              marginBottom: layout.textZone.h * 0.015,
            }}
          >
            {eyebrow}
          </div>
        ) : null}

        <div
          style={{
            opacity: titleIn,
            transform: `translateY(${(1 - titleIn) * 12}px)`,
            fontSize: titleSize,
            fontWeight: 700,
            color: theme.text,
            lineHeight: 1.3,
            marginBottom: layout.textZone.h * 0.05,
          }}
        >
          {title}
        </div>

        {/* 网格：行高按行数等分，铺满标题与结论条之间的剩余高度 */}
        <div
          style={{
            flex: 1,
            display: "grid",
            gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))`,
            gridTemplateRows: `repeat(${rows}, minmax(0, 1fr))`,
            gap,
          }}
        >
          {bullets.map((label, i) => {
            const start = cellStart(i);
            // out(back) 输出会略过 1 —— scale 因此自然带一次轻微过冲
            const appear = interpolate(frame, [start, start + 14], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.out(Easing.back(1.7)),
            });
            return (
              <div
                key={i}
                style={{
                  opacity: Math.min(1, appear * 1.5),
                  transform: `scale(${0.84 + appear * 0.16})`,
                  background: theme.surface,
                  border: `1px solid ${theme.border}`,
                  borderRadius: 14,
                  boxShadow: "0 16px 44px rgba(0,0,0,0.5)",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: pad * 0.5,
                  padding: `${pad * 0.6}px ${pad * 0.5}px`,
                  textAlign: "center",
                }}
              >
                {/* 图标位：几何字形 + 一圈强调色描边，不引图标库 */}
                <div
                  style={{
                    width: bodySize * 1.7,
                    height: bodySize * 1.7,
                    borderRadius: "50%",
                    border: `1.5px solid ${theme.primary}66`,
                    background: `${theme.primary}14`,
                    color: theme.primary,
                    fontSize: bodySize * 0.86,
                    lineHeight: `${bodySize * 1.7}px`,
                  }}
                >
                  {GLYPHS[i % GLYPHS.length]}
                </div>
                <div
                  style={{
                    fontSize: bodySize,
                    fontWeight: 600,
                    color: theme.text,
                    lineHeight: 1.4,
                  }}
                >
                  {label}
                </div>
              </div>
            );
          })}
        </div>

        {footer ? (
          <div
            style={{
              marginTop: layout.textZone.h * 0.045,
              opacity: interpolate(
                frame,
                [cellStart(n - 1) + 16, cellStart(n - 1) + 30],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
              ),
              fontSize: bodySize * 1.04,
              fontWeight: 700,
              color: theme.primary,
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

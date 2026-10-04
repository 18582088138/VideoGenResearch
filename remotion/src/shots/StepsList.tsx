/**
 * 有序步骤列表 / Ordered step list.
 *
 * 内容形态：**有先后**的步骤或阶段（训练流程、审批链路、发布步骤）。
 * 与 icon-grid 的分工：这里序号是信息本体，所以序号圆点必须逐点点亮 ——
 * 一步一亮，读者才能跟上"到第几步了"。
 *
 * Ordered steps, where the number *is* the content. The numbered dots light up
 * one at a time so the viewer can follow "which step are we on".
 *
 * 动效：
 *   - 左侧序号圆点 1,2,3… 逐个点亮（底色由 `surface2` 填充到 `primary`）
 *   - 圆点间连线向下生长（`scaleY`，origin top），排在对应圆点点亮之后
 *   - 每行 `nodes[i].label` + `nodes[i].sub`
 *
 * 命门：连线**必须后于圆点**生长，且只连接已点亮的相邻圆点 ——
 * 抢先画出导轨会让"逐步"读成"已完成"。
 */

import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { FONT_FAMILY, ThemeTokens } from "../theme/theme";
import { Layout, tune } from "../theme/layout";
import type { ShotNode } from "../compositions/types";

export interface StepsListProps {
  /** 列表标题 / List title. */
  title: string;
  /** 来源/角标 / Eyebrow above the title. */
  eyebrow?: string;
  /** 有序步骤；顺序即步骤序 / Ordered steps — the order is the sequence. */
  nodes: ShotNode[];
  /** 底部结论条 / Closing takeaway line. */
  footer?: string;
  theme: ThemeTokens;
  layout: Layout;
  durationInFrames: number;
}

export const StepsList: React.FC<StepsListProps> = ({
  title,
  eyebrow,
  nodes,
  footer,
  theme,
  layout,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const n = Math.max(1, nodes.length);

  const titleIn = interpolate(frame, [0, 14], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  // 错峰：整段约 45% 时长用于"一步一亮"
  const stagger = Math.max(7, Math.min(16, Math.floor((durationInFrames * 0.45) / n)));
  const dotStart = (i: number): number => 14 + i * stagger;

  const exit = interpolate(
    frame,
    [durationInFrames - 10, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const titleSize = tune(layout, "figureTitlePortrait", "figureTitleLandscape");
  const bodySize = tune(layout, "figureBodyPortrait", "figureBodyLandscape");
  const dotSize = layout.safeWidth * 0.062;
  const gapX = layout.safeWidth * 0.035;
  const rowPad = layout.textZone.h * 0.026;

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
              fontSize: bodySize * 0.68,
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
            marginBottom: layout.textZone.h * 0.045,
          }}
        >
          {title}
        </div>

        <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
          {nodes.map((node, i) => {
            const start = dotStart(i);
            // 圆点点亮：底色填充 + 数字反色
            const lit = interpolate(frame, [start, start + 10], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.out(Easing.cubic),
            });
            const rowIn = interpolate(frame, [start, start + 12], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.out(Easing.cubic),
            });
            // 连线后于圆点生长（origin top：由上向下长）
            const lineGrow = Math.max(
              0,
              interpolate(frame, [start + 8, start + 20], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
                easing: Easing.out(Easing.cubic),
              }),
            );
            const isLast = i === n - 1;

            return (
              <div key={`${node.label}-${i}`} style={{ display: "flex", gap: gapX }}>
                {/* 序号列：圆点 + 向下生长的连线 */}
                <div
                  style={{
                    width: dotSize,
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                  }}
                >
                  <div
                    style={{
                      position: "relative",
                      width: dotSize,
                      height: dotSize,
                      borderRadius: "50%",
                      background: theme.surface2,
                      border: `2px solid ${lit > 0.5 ? theme.primary : theme.border}`,
                      overflow: "hidden",
                      flexShrink: 0,
                    }}
                  >
                    <div
                      style={{
                        position: "absolute",
                        inset: 0,
                        background: theme.primary,
                        opacity: lit,
                      }}
                    />
                    <div
                      style={{
                        position: "relative",
                        width: "100%",
                        height: "100%",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: dotSize * 0.48,
                        fontWeight: 800,
                        color: lit > 0.55 ? theme.bg : theme.text,
                        fontVariantNumeric: "tabular-nums",
                      }}
                    >
                      {i + 1}
                    </div>
                  </div>

                  {!isLast ? (
                    <div
                      style={{
                        width: 2,
                        flex: 1,
                        minHeight: dotSize * 0.4,
                        background: `linear-gradient(180deg, ${theme.primary}, ${theme.border})`,
                        transformOrigin: "top center",
                        transform: `scaleY(${lineGrow})`,
                      }}
                    />
                  ) : null}
                </div>

                {/* 行内容：label + sub */}
                <div
                  style={{
                    flex: 1,
                    minWidth: 0,
                    paddingBottom: rowPad,
                    opacity: rowIn,
                    transform: `translateY(${(1 - rowIn) * 12}px)`,
                  }}
                >
                  <div
                    style={{
                      fontSize: bodySize * 1.06,
                      fontWeight: 700,
                      color: theme.text,
                      lineHeight: 1.4,
                    }}
                  >
                    {node.label}
                  </div>
                  {node.sub ? (
                    <div
                      style={{
                        marginTop: layout.textZone.h * 0.008,
                        fontSize: bodySize * 0.86,
                        color: theme.textMuted,
                        lineHeight: 1.45,
                      }}
                    >
                      {node.sub}
                    </div>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>

        {footer ? (
          <div
            style={{
              marginTop: layout.textZone.h * 0.03,
              opacity: interpolate(
                frame,
                [dotStart(n - 1) + 18, dotStart(n - 1) + 32],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
              ),
              fontSize: bodySize,
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

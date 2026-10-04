/**
 * 横向对比 / Side-by-side comparison.
 *
 * 补强点：原文里"学习策略 vs 规则系统"、"误差 0.344 → 0.186"这类**对比关系**
 * 原先只能靠旁白说，画面上没有对照结构。本组件把它画成两根竞赛条 ——
 * 差值用长度直接看出来，不需要读数字。
 *
 * Carries comparisons the narration used to state verbally: two racing bars make
 * the delta visible without reading numbers.
 *
 * 动效：条从 0 生长（outQuart），落后一方在"被超过"的瞬间闪一下强调色。
 */

import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { FONT_FAMILY, ThemeTokens } from "../theme/theme";
import { Layout } from "../theme/layout";

export interface CompareSide {
  /** 名称 / Label. */
  label: string;
  /** 数值（用于条长）/ Value driving the bar length. */
  value: number;
  /** 显示文本（如 "1.5 秒"）/ Display text. */
  display: string;
  /** 是否为"更好"的一方 / Whether this side is the winner. */
  better?: boolean;
}

export interface StatCompareProps {
  title: string;
  /** 对比维度说明（如 "静止球启动到触球"）/ What is being compared. */
  metric: string;
  sides: CompareSide[];
  footer?: string;
  theme: ThemeTokens;
  layout: Layout;
  durationInFrames: number;
}

export const StatCompare: React.FC<StatCompareProps> = ({
  title,
  metric,
  sides,
  footer,
  theme,
  layout,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const portrait = layout.orientation === "portrait";

  const titleIn = interpolate(frame, [0, 14], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  // 条生长：前快后慢（outQuart），读作"冲刺到位"
  const GROW_FROM = 18;
  const GROW_SPAN = 40;

  // 条形动画完成时闪一下（"比出来了"）
  const flash = interpolate(
    frame,
    [GROW_FROM + GROW_SPAN, GROW_FROM + GROW_SPAN + 5, GROW_FROM + GROW_SPAN + 16],
    [0, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const max = Math.max(...sides.map((s) => s.value), 0.0001);
  const exit = interpolate(
    frame,
    [durationInFrames - 10, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const barH = portrait ? 54 : 48;
  const labelSize = portrait ? 30 : 28;
  const valueSize = portrait ? 40 : 38;

  return (
    <AbsoluteFill style={{ fontFamily: FONT_FAMILY, opacity: exit }}>
      <div
        style={{
          position: "absolute",
          left: layout.safe.left,
          top: layout.contentCenterY,
          width: layout.safeWidth,
          transform: "translateY(-50%)",
        }}
      >
        <div
          style={{
            opacity: titleIn,
            transform: `translateY(${(1 - titleIn) * 12}px)`,
            fontSize: portrait ? 42 : 42,
            fontWeight: 700,
            color: theme.text,
            lineHeight: 1.3,
          }}
        >
          {title}
        </div>
        <div
          style={{
            marginTop: 12,
            opacity: titleIn,
            fontFamily: "monospace",
            fontSize: portrait ? 20 : 19,
            letterSpacing: "0.18em",
            color: theme.textMuted,
            marginBottom: portrait ? 44 : 38,
          }}
        >
          {metric}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: portrait ? 38 : 32 }}>
          {sides.map((s, i) => {
            const start = GROW_FROM + i * 6;
            const w = interpolate(
              frame,
              [start, start + GROW_SPAN],
              [0, (s.value / max) * 100],
              {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
                easing: Easing.out(Easing.poly(4)),
              },
            );
            const labelIn = interpolate(frame, [start - 8, start + 6], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            const color = s.better ? theme.primary : theme.alert;

            return (
              <div key={s.label}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "baseline",
                    justifyContent: "space-between",
                    marginBottom: 10,
                    opacity: labelIn,
                  }}
                >
                  <span style={{ fontSize: labelSize, color: theme.textMuted, letterSpacing: "0.08em" }}>
                    {s.label}
                  </span>
                  <span
                    style={{
                      fontSize: valueSize,
                      fontWeight: 800,
                      color,
                      fontVariantNumeric: "tabular-nums",
                      transform: `scale(${1 + (s.better ? flash : 0) * 0.06})`,
                      display: "inline-block",
                    }}
                  >
                    {s.display}
                  </span>
                </div>

                {/* 轨道 + 生长条 */}
                <div
                  style={{
                    height: barH * 0.34,
                    borderRadius: 999,
                    background: theme.surface2,
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      width: `${w}%`,
                      height: "100%",
                      borderRadius: 999,
                      background: `linear-gradient(90deg, ${color}, ${s.better ? theme.accent : color})`,
                      boxShadow: `0 0 ${(s.better ? flash : 0) * 22}px ${color}`,
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>

        {footer ? (
          <div
            style={{
              marginTop: portrait ? 40 : 32,
              opacity: interpolate(
                frame,
                [GROW_FROM + GROW_SPAN + 8, GROW_FROM + GROW_SPAN + 22],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
              ),
              fontSize: portrait ? 32 : 30,
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

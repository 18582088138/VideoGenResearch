/**
 * 多方案对比表 / Comparison table.
 *
 * 内容形态：**三个以上**方案逐项对比（三种模型的参数/成本/效果、
 * 四个方案的取舍）。stat-compare 只够放两方；三方以上必须用表，
 * 否则读者要靠记忆横向对齐。
 *
 * Multi-option comparison (3+). `stat-compare` only carries two sides; with
 * three or more, readers cannot align the columns from memory — a table can.
 *
 * 结构（列 = `sides`，行 = `bullets` 的对比维度）：
 *   - 表头先滑入：第一格留白（维度列），其后每列是 `sides[i].label`
 *   - 数值条按 `value` 归一化生长，条头显示 `sides[i].display`
 *   - `bullets` 逐行出现，作为对比维度行（**不编造格子数据** ——
 *     契约里没有"每格一个值"的字段，所以维度行只列维度名）
 *   - `metric` 作副标题说明"在比什么"，`footer` 收尾
 *
 * 命门：条长一律除以 `max(value)` 归一化 —— 用绝对值会在两边量级差异大时
 * 让强势一方直接出框。
 */

import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { FONT_FAMILY, ThemeTokens } from "../theme/theme";
import { Layout, tune } from "../theme/layout";
import type { ShotCompareSide } from "../compositions/types";

export interface ComparisonTableProps {
  /** 表标题 / Table title. */
  title: string;
  /** 对比维度说明（在比什么）/ What the columns are compared on. */
  metric?: string;
  /** 各方案（列，3 项以上最佳）/ The options — one table column each. */
  sides: ShotCompareSide[];
  /** 对比维度（每行一项）/ Comparison dimensions, one per row. */
  bullets: string[];
  /** 底部结论条 / Closing takeaway line. */
  footer?: string;
  theme: ThemeTokens;
  layout: Layout;
  durationInFrames: number;
}

export const ComparisonTable: React.FC<ComparisonTableProps> = ({
  title,
  metric,
  sides,
  bullets,
  footer,
  theme,
  layout,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const cols = Math.max(1, sides.length);
  const max = Math.max(...sides.map((s) => s.value), 0.0001);

  const titleIn = interpolate(frame, [0, 14], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  // 表头：逐列滑入（错峰 4f）
  const HEAD_FROM = 10;
  // 数值条：表头落定后生长，前快后慢（outQuart）读作"冲刺到位"
  const BAR_FROM = 30;
  const BAR_SPAN = 34;
  // 维度行：数值条之后逐个出现
  const ROW_FROM = BAR_FROM + BAR_SPAN + 6;

  const exit = interpolate(
    frame,
    [durationInFrames - 10, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const titleSize = tune(layout, "figureTitlePortrait", "figureTitleLandscape");
  const bodySize = tune(layout, "figureBodyPortrait", "figureBodyLandscape");
  const labelSize = bodySize * 1.02;
  // 维度列宽由列数派生（不内联横竖屏分支），保证列宽随方案数自适应
  const labelW = layout.safeWidth / (cols + 1);
  const barH = Math.max(10, layout.textZone.h * 0.022);
  const gridColumns = `${labelW}px repeat(${cols}, minmax(0, 1fr))`;
  const cellGap = layout.safeWidth * 0.014;

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
        <div
          style={{
            opacity: titleIn,
            transform: `translateX(${(1 - titleIn) * -18}px)`,
            fontSize: titleSize,
            fontWeight: 700,
            color: theme.text,
            lineHeight: 1.3,
          }}
        >
          {title}
        </div>

        {metric ? (
          <div
            style={{
              marginTop: layout.textZone.h * 0.012,
              opacity: titleIn,
              fontFamily: "monospace",
              fontSize: bodySize * 0.66,
              letterSpacing: "0.18em",
              color: theme.textMuted,
            }}
          >
            {metric}
          </div>
        ) : null}

        {/* ── 表头：第一格留白（维度列），其后每列一个方案名 ── */}
        <div
          style={{
            marginTop: layout.textZone.h * 0.05,
            display: "grid",
            gridTemplateColumns: gridColumns,
            columnGap: cellGap,
            borderBottom: `1px solid ${theme.border}`,
            paddingBottom: layout.textZone.h * 0.014,
          }}
        >
          <div />
          {sides.map((s, i) => {
            const t = interpolate(frame, [HEAD_FROM + i * 4, HEAD_FROM + i * 4 + 12], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.out(Easing.cubic),
            });
            return (
              <div
                key={`h-${s.label}-${i}`}
                style={{
                  opacity: t,
                  transform: `translateY(${(1 - t) * 14}px)`,
                  fontSize: labelSize,
                  fontWeight: 700,
                  color: s.better ? theme.primary : theme.text,
                  letterSpacing: "0.03em",
                  textAlign: "center",
                  lineHeight: 1.35,
                }}
              >
                {s.label}
              </div>
            );
          })}
        </div>

        {/* ── 数值行：每列一根按 value 归一化生长的条 + display 数字 ── */}
        <div
          style={{
            marginTop: layout.textZone.h * 0.03,
            display: "grid",
            gridTemplateColumns: gridColumns,
            columnGap: cellGap,
            alignItems: "end",
          }}
        >
          <div />
          {sides.map((s, i) => {
            const start = BAR_FROM + i * 6;
            const grow = Math.max(
              0,
              interpolate(frame, [start, start + BAR_SPAN], [0, s.value / max], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
                easing: Easing.out(Easing.poly(4)),
              }),
            );
            const color = s.better ? theme.primary : theme.accent;
            const numIn = interpolate(frame, [start + 6, start + 22], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            return (
              <div key={`v-${s.label}-${i}`} style={{ textAlign: "center" }}>
                <div
                  style={{
                    opacity: numIn,
                    fontSize: bodySize * 1.24,
                    fontWeight: 800,
                    color,
                    fontVariantNumeric: "tabular-nums",
                    marginBottom: barH * 0.6,
                  }}
                >
                  {s.display}
                </div>
                <div
                  style={{
                    height: barH,
                    borderRadius: 999,
                    background: theme.surface2,
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      width: `${grow * 100}%`,
                      height: "100%",
                      marginLeft: "auto",
                      marginRight: "auto",
                      borderRadius: 999,
                      background: `linear-gradient(90deg, ${color}, ${s.better ? theme.accent : color})`,
                      boxShadow: `0 0 18px ${color}44`,
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>

        {/* ── 对比维度行：逐行出现；只列维度名，不编造格子数据 ── */}
        {bullets.length ? (
          <div style={{ marginTop: layout.textZone.h * 0.04 }}>
            {bullets.map((b, i) => {
              const t = interpolate(frame, [ROW_FROM + i * 8, ROW_FROM + i * 8 + 14], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
                easing: Easing.out(Easing.cubic),
              });
              return (
                <div
                  key={`${b}-${i}`}
                  style={{
                    display: "grid",
                    gridTemplateColumns: gridColumns,
                    columnGap: cellGap,
                    alignItems: "center",
                    borderBottom: `1px solid ${theme.border}`,
                    padding: `${layout.textZone.h * 0.016}px 0`,
                  }}
                >
                  <div
                    style={{
                      opacity: t,
                      transform: `translateX(${(1 - t) * -12}px)`,
                      fontSize: bodySize * 0.94,
                      color: theme.text,
                      lineHeight: 1.4,
                      paddingRight: cellGap,
                    }}
                  >
                    {b}
                  </div>
                  {sides.map((_side, j) => (
                    <div
                      key={`c-${i}-${j}`}
                      style={{
                        opacity: t * 0.6,
                        height: 2,
                        width: "62%",
                        justifySelf: "center",
                        background: theme.surface2,
                      }}
                    />
                  ))}
                </div>
              );
            })}
          </div>
        ) : null}

        {footer ? (
          <div
            style={{
              marginTop: layout.textZone.h * 0.04,
              opacity: interpolate(
                frame,
                [ROW_FROM + bullets.length * 8 + 6, ROW_FROM + bullets.length * 8 + 20],
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

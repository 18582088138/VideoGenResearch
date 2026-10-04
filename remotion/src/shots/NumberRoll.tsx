/**
 * 数字滚动大字报 / Odometer number board.
 *
 * 实现镜头卡 `odometer-digit-roll` 的语义：单个／多个王牌指标的全屏亮相。
 * 每位独立滚轮、从左到右逐位过冲锁定、全体锁定后整体加深脉冲。
 *
 * Implements the `odometer-digit-roll` recipe: full-frame hero metrics, each
 * digit rolling on its own strip, locking left-to-right, then a加深 pulse once
 * every digit has settled.
 *
 * 卡上命门（已遵守）：
 *   - 必须 tabular-nums（见 `ui/DigitRoll.tsx`）
 *   - 数位 ≤6：本项目数字都在 4 位以内，无需缩写
 *   - 收尾真静止 ≥45f（R1）
 */

import React from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";
import { FONT_FAMILY, ThemeTokens } from "../theme/theme";
import { Layout } from "../theme/layout";
import { DigitRoll } from "../ui/DigitRoll";

export interface NumberRollProps {
  title: string;
  metrics: Array<{ label: string; value: string }>;
  theme: ThemeTokens;
  layout: Layout;
  durationInFrames: number;
}

/** 把 "50 帧" / "2070 TFLOPS" 拆成数字部分与尾缀，好让只有数字滚动。
 * Split "50 帧" into the rollable numeric part and a static suffix. */
const splitValue = (value: string): { numeric: string; suffix: string } => {
  const m = value.match(/^([\d.,]+)(.*)$/);
  if (!m) {
    return { numeric: "", suffix: value };
  }
  return { numeric: m[1], suffix: m[2] };
};

export const NumberRoll: React.FC<NumberRollProps> = ({
  title,
  metrics,
  theme,
  layout,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();

  // 布局：先出标题，指标逐个错峰入场
  const titleIn = interpolate(frame, [4, 18], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  // 每行指标错峰 10f：滚轮一列接一列锁定，节奏像仪表自检
  const rowStart = (i: number) => 22 + i * 10;

  // 全体锁定帧之后做一次整体脉冲（加深 + 微缩放）
  const lastRow = Math.max(0, metrics.length - 1);
  const allLocked = rowStart(lastRow) + 24 + 22; // 行起点 + 错峰 + 单字锁定
  const pulse = interpolate(frame, [allLocked, allLocked + 4, allLocked + 8], [0, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // 收尾淡出，交棒下一镜
  const exit = interpolate(
    frame,
    [durationInFrames - 10, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const portrait = layout.orientation === "portrait";
  const titleSize = portrait ? 42 : 46;

  // 字号与行距都必须让「标题 + N 行指标」整体落在字幕带**之上**。
  // 竖屏安全框高 1020px 左右，3 行指标 + 标题必须挤进约 0.72 的画面高度。
  const rowCount = Math.max(metrics.length, 1);
  const valueSize = portrait
    ? Math.min(84, Math.round(560 / rowCount))
    : Math.min(96, Math.round(360 / rowCount));
  const labelSize = portrait ? 25 : 23;
  const rowGap = portrait ? 30 : 26;

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        fontFamily: FONT_FAMILY,
        opacity: exit,
      }}
    >
      {/* 顶部锚定而非 flex 居中：居中会让内容随行数上下浮动，撞进底部字幕带 */}
      <div
        style={{
          position: "absolute",
          left: layout.safe.left,
          width: layout.safeWidth,
          top: layout.safe.top + layout.safeHeight * 0.08,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          transform: `scale(${1 + pulse * 0.035})`,
          // 脉冲期整体加深：用亮度而非变色，避免与主题色冲突
          filter: `brightness(${1 - pulse * 0.25})`,
        }}
      >
        <div
          style={{
            opacity: titleIn,
            transform: `translateY(${(1 - titleIn) * 14}px)`,
            fontSize: titleSize,
            fontWeight: 600,
            color: theme.text,
            letterSpacing: "0.04em",
            textAlign: "center",
            maxWidth: layout.contentWidth * 0.9,
            marginBottom: portrait ? 52 : 44,
          }}
        >
          {title}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: rowGap }}>
          {metrics.map((m, i) => {
            const { numeric, suffix } = splitValue(m.value);
            const start = rowStart(i);
            const rowIn = interpolate(frame, [start - 12, start], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            const isLast = i === metrics.length - 1;

            return (
              <div
                key={m.label}
                style={{
                  display: "flex",
                  alignItems: "baseline",
                  justifyContent: "center",
                  gap: portrait ? 24 : 28,
                  opacity: rowIn,
                }}
              >
                <span
                  style={{
                    fontSize: labelSize,
                    color: theme.textMuted,
                    letterSpacing: "0.18em",
                    minWidth: portrait ? 140 : 160,
                    textAlign: "right",
                  }}
                >
                  {m.label}
                </span>

                <span style={{ display: "inline-flex", alignItems: "baseline" }}>
                  <DigitRoll
                    value={numeric}
                    delay={start}
                    stagger={7}
                    duration={16}
                    fontSize={valueSize}
                    // 最后一行用次强调色做主次区分，避免三行都一样重
                    color={isLast ? theme.accent : theme.primary}
                  />
                  {suffix ? (
                    <span
                      style={{
                        fontSize: valueSize * 0.42,
                        color: theme.textMuted,
                        marginLeft: 12,
                        letterSpacing: "0.06em",
                      }}
                    >
                      {suffix}
                    </span>
                  ) : null}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

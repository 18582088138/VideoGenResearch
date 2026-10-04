/**
 * 环形进度 / Progress ring — 部分 vs 总体.
 *
 * 内容形态：占比（覆盖率 62%、完成度 8/10、份额）。柱状条读作"两项竞赛"，
 * 环形读作"占整体的多少" —— 这是两种不同的语义，不能互相替代。
 *
 * Part-vs-whole. Bars read as a race between two things; a ring reads as "what
 * share of the whole" — different semantics, not interchangeable.
 *
 * 动效：
 *   - 环从 0 生长到 `metric` 里的数字（`out(cubic)`，先快后慢读作"冲刺到位"）
 *   - 环内数字**同步**滚动到目标（同一进度变量驱动，两者永远一致）
 *   - `subtext` 放补充说明
 *
 * 命门：数字与环必须由**同一个**进度变量驱动 —— 分别插值会在中途出现
 * "环到 62% 而数字还停在 41%"的错帧，看起来像 bug。
 */

import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { FONT_FAMILY, ThemeTokens } from "../theme/theme";
import { Layout, tune } from "../theme/layout";

export interface ProgressMeterProps {
  /** 指标名称 / What the figure measures. */
  title: string;
  /** 占比数值，如 `"62%"` / The part-vs-whole figure, e.g. `"62%"`. */
  metric: string;
  /** 补充说明 / Supporting note. */
  subtext?: string;
  theme: ThemeTokens;
  layout: Layout;
  durationInFrames: number;
}

/** 从任意文本里抽出数字与前后缀 / Split a figure string into number + affixes. */
const parseFigure = (
  raw: string,
): { num: number; prefix: string; suffix: string; decimals: number } => {
  const m = /[\d.]+/.exec(raw);
  if (!m) {
    return { num: 0, prefix: raw, suffix: "", decimals: 0 };
  }
  const text = m[0];
  const at = m.index;
  const decimals = text.includes(".") ? text.split(".")[1].length : 0;
  return {
    num: Number(text),
    prefix: raw.slice(0, at),
    suffix: raw.slice(at + text.length),
    decimals,
  };
};

export const ProgressMeter: React.FC<ProgressMeterProps> = ({
  title,
  metric,
  subtext,
  theme,
  layout,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();

  const { num, prefix, suffix, decimals } = parseFigure(metric);
  // 有百分号或数值大于 1 ⇒ 按百分比解释；否则数值本身就是 0–1 的比例
  const isShare = suffix.includes("%") || prefix.includes("%") || num > 1;
  const ratio = isShare ? num / 100 : num;
  const target = Math.max(0, Math.min(1, ratio));

  // 唯一进度变量：环与数字共用，避免两者错帧
  const grow = interpolate(frame, [12, 56], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  const titleIn = interpolate(frame, [0, 14], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  const exit = interpolate(
    frame,
    [durationInFrames - 10, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const titleSize = tune(layout, "figureTitlePortrait", "figureTitleLandscape");
  const bodySize = tune(layout, "figureBodyPortrait", "figureBodyLandscape");
  const noteSize = bodySize * 0.86;
  // 环径由文案区派生：宽度与（扣掉标题/说明后的）高度取紧的一侧，不内联方向分支
  const ringSize = Math.min(layout.textZone.w * 0.52, layout.textZone.h * 0.56);
  const stroke = Math.max(8, ringSize * 0.075);
  const r = (ringSize - stroke) / 2;
  const circumference = 2 * Math.PI * r;

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
          alignItems: "center",
        }}
      >
        <div
          style={{
            alignSelf: "flex-start",
            opacity: titleIn,
            transform: `translateY(${(1 - titleIn) * 12}px)`,
            fontSize: titleSize,
            fontWeight: 700,
            color: theme.text,
            lineHeight: 1.3,
          }}
        >
          {title}
        </div>

        {/* 环 + 环内数字：共用 `grow` */}
        <div
          style={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: "100%",
          }}
        >
          <div
            style={{
              position: "relative",
              width: ringSize,
              height: ringSize,
            }}
          >
            <svg
              width={ringSize}
              height={ringSize}
              viewBox={`0 0 ${ringSize} ${ringSize}`}
              // -90° 让进度从 12 点方向开始生长
              style={{ transform: "rotate(-90deg)" }}
            >
              <circle
                cx={ringSize / 2}
                cy={ringSize / 2}
                r={r}
                fill="none"
                stroke={theme.surface2}
                strokeWidth={stroke}
              />
              <circle
                cx={ringSize / 2}
                cy={ringSize / 2}
                r={r}
                fill="none"
                stroke={theme.primary}
                strokeWidth={stroke}
                strokeLinecap="round"
                strokeDasharray={circumference}
                strokeDashoffset={circumference * (1 - target * grow)}
                style={{ filter: `drop-shadow(0 0 14px ${theme.primary}66)` }}
              />
            </svg>

            <div
              style={{
                position: "absolute",
                inset: 0,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: ringSize * 0.3,
                fontWeight: 800,
                color: theme.accent,
                fontVariantNumeric: "tabular-nums",
                letterSpacing: "-0.01em",
              }}
            >
              {prefix}
              {/* 数字与环同步：同一个 grow */}
              {(num * grow).toFixed(decimals)}
              {suffix}
            </div>
          </div>
        </div>

        {subtext ? (
          <div
            style={{
              alignSelf: "flex-start",
              opacity: interpolate(frame, [48, 64], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }),
              fontSize: noteSize,
              color: theme.textMuted,
              lineHeight: 1.5,
              borderLeft: `3px solid ${theme.border}`,
              paddingLeft: layout.safeWidth * 0.016,
              maxWidth: layout.textZone.w * 0.9,
            }}
          >
            {subtext}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

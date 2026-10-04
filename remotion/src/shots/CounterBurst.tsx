/**
 * 计数爆点 / Counter with confetti burst.
 *
 * 实现镜头卡 `counter-confetti`：大数字 easeOutQuart 冲刺计数 + scale 过冲，
 * 纸屑**抢拍**炸入，到位冲击环扩散，标签字距收紧收尾。
 *
 * Implements `counter-confetti`: an easeOutQuart number sprint with scale
 * overshoot, confetti fired in *before* the count lands, an impact ring, and a
 * label whose letter-spacing tightens on landing.
 *
 * 卡上命门（已遵守）：
 *   - 计数走 `easeOutQuart`（换 outCubic 冲刺感减弱；线性计数是"没有情绪"的写法）
 *   - **抢拍**：`BURST` 比计数终点早 0.04 归一化时间（约 5 帧）
 *   - scale 0.2→1.3 冲入（outCubic）→ 1.3→1 回落（outBack 轻弹）
 *   - 到位冲击环 scale 0.35→2.95 扩散淡出（outQuart）
 *   - 标签 0.62 淡入且字距 11px→5px 收紧
 */

import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { FONT_FAMILY, ThemeTokens } from "../theme/theme";
import { Layout } from "../theme/layout";
import { Confetti } from "../ui/Confetti";

export interface CounterBurstProps {
  text?: string;
  subtext?: string;
  metrics: Array<{ label: string; value: string }>;
  theme: ThemeTokens;
  layout: Layout;
  durationInFrames: number;
}

/** 从 "46%" 抽出数字与单位 / Split "46%" into number and unit. */
const parseMetric = (value: string): { num: number; unit: string; decimals: number } => {
  const m = value.match(/^([\d.]+)(.*)$/);
  if (!m) {
    return { num: 0, unit: value, decimals: 0 };
  }
  const decimals = m[1].includes(".") ? m[1].split(".")[1].length : 0;
  return { num: Number(m[1]), unit: m[2], decimals };
};

export const CounterBurst: React.FC<CounterBurstProps> = ({
  text,
  subtext,
  metrics,
  theme,
  layout,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const portrait = layout.orientation === "portrait";

  const metric = metrics[0] ?? { label: "", value: "0" };
  const { num, unit, decimals } = parseMetric(metric.value);

  // 归一化进度 / Normalised progress
  const t = frame / durationInFrames;

  // 计数窗口 0.06–0.56；**抢拍**：纸屑早 0.04
  const COUNT_FROM = 0.06;
  const COUNT_TO = 0.56;
  const BURST = COUNT_TO - 0.04;

  const countT = interpolate(t, [COUNT_FROM, COUNT_TO], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    // easeOutQuart：前 1/3 时间跑完 2/3 数值，读作"冲刺–减速–压线"
    easing: Easing.out(Easing.poly(4)),
  });
  const shown = (num * countT).toFixed(decimals);

  // scale 两段：冲入放大 → 落定收正
  const scaleIn = interpolate(t, [COUNT_FROM, COUNT_TO - 0.02], [0.2, 1.3], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const scaleBack = interpolate(t, [COUNT_TO - 0.02, COUNT_TO + 0.06], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.back(1.6)),
  });
  const scale = t < COUNT_TO - 0.02 ? scaleIn : 1.3 - scaleBack * 0.3;

  // 到位冲击环
  const ringT = interpolate(t, [COUNT_TO - 0.015, COUNT_TO + 0.12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.poly(4)),
  });
  const ringScale = 0.35 + ringT * 2.6;
  const ringOpacity = ringT <= 0 ? 0 : Math.max(0, 1 - ringT);

  // 标签：0.62 淡入 + 字距 11px→5px 收紧
  const labelIn = interpolate(t, [0.62, 0.72], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const tracking = interpolate(t, [0.62, 0.78], [11, 5], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const exit = interpolate(
    frame,
    [durationInFrames - 10, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const numSize = portrait ? 190 : 230;

  return (
    <AbsoluteFill style={{ opacity: exit, fontFamily: FONT_FAMILY }}>
      {/* ── 纸屑抢拍（在数字落定之前 0.04 爆开）── */}
      <Confetti burstFrame={Math.round(BURST * durationInFrames)} />

      {/* ── 主体：数字 + 冲击环 + 标签 ── */}
      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "column",
          // 整体上移一点，给底部字幕带留位置
          paddingBottom: layout.safeHeight * 0.1,
        }}
      >
        <div style={{ position: "relative", display: "flex", alignItems: "baseline" }}>
          {/* 冲击环：在数字背后扩散 */}
          {ringOpacity > 0.01 ? (
            <div
              style={{
                position: "absolute",
                left: "50%",
                top: "50%",
                width: numSize * 2.1,
                height: numSize * 2.1,
                marginLeft: -numSize * 1.05,
                marginTop: -numSize * 1.05,
                borderRadius: "50%",
                border: `3px solid ${theme.primary}`,
                opacity: ringOpacity * 0.5,
                transform: `scale(${ringScale})`,
              }}
            />
          ) : null}

          <div
            style={{
              fontSize: numSize,
              fontWeight: 800,
              color: theme.primary,
              transform: `scale(${scale})`,
              fontVariantNumeric: "tabular-nums",
              fontVariationSettings: "'wght' 800",
              letterSpacing: "-0.02em",
              textShadow: `0 0 60px ${theme.primary}44`,
            }}
          >
            {shown}
            <span style={{ fontSize: numSize * 0.46, color: theme.accent, marginLeft: 8 }}>
              {unit}
            </span>
          </div>
        </div>

        {text ? (
          <div
            style={{
              marginTop: portrait ? 46 : 40,
              opacity: labelIn,
              fontSize: portrait ? 40 : 38,
              fontWeight: 600,
              color: theme.text,
              letterSpacing: `${tracking}px`,
              textAlign: "center",
              maxWidth: layout.contentWidth * 0.9,
            }}
          >
            {text}
          </div>
        ) : null}

        {subtext ? (
          <div
            style={{
              marginTop: 14,
              opacity: labelIn,
              fontSize: portrait ? 30 : 28,
              color: theme.textMuted,
              letterSpacing: "0.06em",
              textAlign: "center",
            }}
          >
            {subtext}
          </div>
        ) : null}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/**
 * 收尾字标 lockup / Outro wordmark lockup.
 *
 * 实现镜头卡 `logo-shrink-wordmark-lockup` 的语义：满屏图形能量收束成中央小标，
 * 让位、字标逐字滑入、强调色标语押尾 —— 品牌从动态里「站定」。
 *
 * Implements `logo-shrink-wordmark-lockup`: full-screen energy collapses into a
 * small mark, which yields, the wordmark slides in letter by letter, and an
 * accent tagline closes the film.
 *
 * 卡上命门（已遵守）：
 *   - 收束 scale 起始倍率 ≥3 才有冲击力（本项目用 4.6）
 *   - 刹车过冲 +6%，sin 包络（砍掉读作硬冻结，>10% 变果冻）
 *   - 愈合必须在**落位前**完成（落位后还在变色读作"没准备好"）
 *   - 字母 stagger 按字数反算，保证在 0.7 前进完
 *   - 标语整行淡入、不逐字（它是注脚不是主角）
 *   - 收尾后真静止（R1）
 */

import React from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";
import { FONT_FAMILY, ThemeTokens } from "../theme/theme";
import { Layout } from "../theme/layout";

export interface OutroLockupProps {
  /** 主字标文字 / Wordmark text. */
  text: string;
  /** 强调色标语 / Accent tagline. */
  tagline?: string;
  theme: ThemeTokens;
  layout: Layout;
  durationInFrames: number;
}

/** t 归一化到 0–1 后按窗口取值 / Normalise to 0–1 then map a window. */
const win = (t: number, a: number, b: number) =>
  interpolate(t, [a, b], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

export const OutroLockup: React.FC<OutroLockupProps> = ({
  text,
  tagline,
  theme,
  layout,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const t = frame / durationInFrames;
  const portrait = layout.orientation === "portrait";

  // ── 收束：scale 4.6→1（t 0.02–0.28），叠 sin 过冲刹车 ──
  const collapse = interpolate(t, [0.02, 0.28], [4.6, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });
  const brake = Math.sin(Math.PI * win(t, 0.26, 0.37)) * 0.06;
  const markScale = collapse * (1 + brake);

  // 愈合窗口与收束同轨：辉光淡出、描边转白 —— 落位前完成
  const heal = win(t, 0.1, 0.28);

  // 图标左移让位（0.34–0.47），与字母首入 0.46 几乎无缝
  const shift = interpolate(t, [0.34, 0.47], [0, -1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });

  // 字母 stagger：按字数反算间隔，保证 0.7 前进完
  const letters = Array.from(text);
  const span = 0.7 - 0.46;
  const step = span / Math.max(letters.length, 1);

  // 标语整行淡入（0.72–0.84）
  const taglineIn = win(t, 0.72, 0.84);

  const markSize = portrait ? 96 : 88;
  const wordSize = portrait ? 62 : 66;

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
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: portrait ? 20 : 24,
          // 整体随让位左移，让 lockup 在画面居中（-68px 的原值按字号折算）
          transform: `translateX(${shift * markSize * 0.78}px)`,
        }}
      >
        {/* ── 几何 mark：双弧开口环，收束 + 愈合 ── */}
        <svg
          width={markSize}
          height={markSize}
          viewBox="0 0 100 100"
          style={{
            transform: `scale(${markScale})`,
            // 收束期带霓虹辉光，愈合后归零 —— 「演出态 → 标准态」
            filter: `drop-shadow(0 0 ${18 * (1 - heal)}px ${theme.primary})`,
            flexShrink: 0,
          }}
        >
          <circle
            cx="50"
            cy="50"
            r="34"
            fill="none"
            stroke={heal > 0.5 ? "#FFFFFF" : theme.accent}
            strokeWidth="7"
            strokeLinecap="round"
            // 缺口：愈合靠 dashoffset 收掉
            strokeDasharray="150 64"
            strokeDashoffset={-22}
            opacity={0.5 + heal * 0.5}
          />
          <circle cx="50" cy="50" r="13" fill="#FFFFFF" opacity={heal} />
        </svg>

        {/* ── 字标逐字滑入 ── */}
        <div style={{ display: "flex", alignItems: "baseline" }}>
          {letters.map((ch, i) => {
            const start = 0.46 + i * step;
            const a = win(t, start, start + 0.1);
            return (
              <span
                key={`${ch}-${i}`}
                style={{
                  fontSize: wordSize,
                  fontWeight: 700,
                  color: theme.text,
                  letterSpacing: "0.01em",
                  opacity: a,
                  transform: `translateX(${(1 - a) * 8}px)`,
                  display: "inline-block",
                }}
              >
                {ch === " " ? "\u00A0" : ch}
              </span>
            );
          })}
        </div>
      </div>

      {tagline ? (
        <div
          style={{
            marginTop: portrait ? 34 : 30,
            fontSize: portrait ? 26 : 24,
            color: theme.primary,
            letterSpacing: "0.3em",
            opacity: taglineIn,
            textAlign: "center",
          }}
        >
          {tagline}
        </div>
      ) : null}
    </div>
  );
};

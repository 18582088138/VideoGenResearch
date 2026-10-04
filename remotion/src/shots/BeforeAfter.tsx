/**
 * 前后对比拉杆 / Before–after slider scrub.
 *
 * 实现镜头卡 `before-after-slider-scrub`：两版叠放，分割杆**先猛甩后慢扫**，
 * 杆过处新版「显影」揭出。
 *
 * Implements `before-after-slider-scrub`: two versions stacked, a divider that
 * whips fast then scrubs slowly, revealing the "after" layer where it passes.
 *
 * 卡上命门（已遵守）：
 *   - **速度比 5:1**（快甩 12f vs 慢扫 48f）—— 比例 <3:1 节奏对比不可感
 *   - 快甩带**过冲回弹**（76% → 70%），停一拍让观众看清
 *   - 揭示用 `clip-path: inset()` 右边界跟随杆 x，**杆与揭示边界必须同值**
 *   - 手柄按速度差分做 `scaleX` 微拉伸（峰值 1.18），静止自动归 1
 *   - 慢扫终点停 40% 而非 0% —— 留一段 after 在画面定格（结论可见）
 *   - before 用可信的低对比灰蒙（不是手搓"故意丑"）
 *
 * ⚠️ 本项目是「单素材对比」的适配：原卡要求 before/after 都是真实截图。
 * 我们只有一份素材图，因此 before = 该图的低对比灰蒙态（模拟未优化），
 * after = 该图的正常态。**这是有意的降级**，记录在
 * docs/design/02_storyboard.md；若后续拿到真实 before 截图，替换 `file` 即可。
 */

import React from "react";
import { AbsoluteFill, Easing, Img, interpolate, useCurrentFrame } from "remotion";
import { FONT_FAMILY, ThemeTokens } from "../theme/theme";
import { imageUrl } from '../theme/assetPath';
import { Layout } from "../theme/layout";
import { fitSize } from "../theme/assetDims";

export interface BeforeAfterProps {
  file: string;
  text?: string;
  subtext?: string;
  metrics?: Array<{ label: string; value: string }>;
  theme: ThemeTokens;
  layout: Layout;
  durationInFrames: number;
}

export const BeforeAfter: React.FC<BeforeAfterProps> = ({
  file,
  text,
  subtext,
  metrics,
  theme,
  layout,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const portrait = layout.orientation === "portrait";

  // 阶段（归一化）：静置 → 快甩 → 回弹 → 停顿 → 慢扫 → 定格
  const SETTLE_END = 0.1; // 静置期
  const WHIP_END = 0.18; // 快甩到过冲位
  const REBOUND_END = 0.26; // 回到 70%
  const HOLD_END = 0.38; // 停顿
  const SCAN_END = 0.72; // 慢扫到 40%

  // 分割杆位置（0–1）
  const x = (() => {
    if (frame / durationInFrames < SETTLE_END) {
      return 0.08;
    }
    if (frame / durationInFrames < WHIP_END) {
      // 快甩：out cubic，冲到 76% 过冲
      return interpolate(frame / durationInFrames, [SETTLE_END, WHIP_END], [0.08, 0.76], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: Easing.out(Easing.cubic),
      });
    }
    if (frame / durationInFrames < REBOUND_END) {
      // 回弹：76% → 70%
      return interpolate(frame / durationInFrames, [WHIP_END, REBOUND_END], [0.76, 0.7], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: Easing.out(Easing.cubic),
      });
    }
    if (frame / durationInFrames < HOLD_END) {
      return 0.7;
    }
    if (frame / durationInFrames < SCAN_END) {
      // 慢扫：70% → 40%（约 5 倍于快甩的时长）
      return interpolate(frame / durationInFrames, [HOLD_END, SCAN_END], [0.7, 0.4], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: Easing.inOut(Easing.cubic),
      });
    }
    // 定格在 40%：留一段 after 可见
    return 0.4;
  })();

  // 手柄按速度差分做 scaleX 微拉伸（"被甩"的重量感）
  const prevX = (() => {
    const tPrev = Math.max(0, frame - 2) / durationInFrames;
    if (tPrev < SETTLE_END) return 0.08;
    if (tPrev < WHIP_END)
      return interpolate(tPrev, [SETTLE_END, WHIP_END], [0.08, 0.76], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: Easing.out(Easing.cubic),
      });
    if (tPrev < REBOUND_END)
      return interpolate(tPrev, [WHIP_END, REBOUND_END], [0.76, 0.7], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
    if (tPrev < HOLD_END) return 0.7;
    if (tPrev < SCAN_END)
      return interpolate(tPrev, [HOLD_END, SCAN_END], [0.7, 0.4], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
    return 0.4;
  })();
  const speed = Math.abs(x - prevX);
  const gripStretch = 1 + Math.min(0.18, speed * 9);

  // 角标淡入（放在内容区，不压内容）
  const badgeIn = interpolate(frame, [4, 16], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const textIn = interpolate(
    frame,
    [SCAN_END * durationInFrames, SCAN_END * durationInFrames + 16],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) },
  );

  const exit = interpolate(
    frame,
    [durationInFrames - 10, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  // 宽高双约束算确定尺寸（避免宽度撑高把文案挤出画面）
  const { w: panelW, h: panelH } = fitSize(
    file,
    layout.safeWidth * 0.92,
    layout.safeHeight * (portrait ? 0.5 : 0.58),
  );

  const metric = metrics?.[0];
  const badgeFont = portrait ? 20 : 18;

  return (
    <AbsoluteFill style={{ opacity: exit, fontFamily: FONT_FAMILY }}>
      <div
        style={{
          position: "absolute",
          left: "50%",
          top: layout.heroCenterY,
          transform: "translate(-50%, -50%)",
          width: panelW,
          height: panelH,
          borderRadius: 14,
          border: `1px solid ${theme.border}`,
          boxShadow: "0 26px 80px rgba(0,0,0,0.66)",
          // 两层叠放在同一容器里，靠 clip-path 分割
          overflow: "hidden",
        }}
      >
        {/* ── before 层（底）：可信的低对比灰蒙 ── */}
        <Img
          src={imageUrl(file)}
          style={{
            position: "absolute",
            inset: 0,
            width: panelW,
            height: panelH,
            filter: "grayscale(0.72) contrast(0.72) brightness(0.86)",
          }}
        />

        {/* ── after 层（上）：右边界跟随杆 x 显影 ── */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            // 杆左侧是 after，右侧被裁掉露出底下的 before
            clipPath: `inset(0 ${(1 - x) * 100}% 0 0)`,
          }}
        >
          <Img
            src={imageUrl(file)}
            style={{
              width: panelW,
              height: panelH,
              filter: "brightness(0.96) contrast(1.1) saturate(1.12)",
            }}
          />
        </div>

        {/* ── 分割杆 + 圆形手柄 ── */}
        <div
          style={{
            position: "absolute",
            top: 0,
            bottom: 0,
            left: `${x * 100}%`,
            width: 2,
            marginLeft: -1,
            background: `linear-gradient(180deg, ${theme.accent}, ${theme.primary})`,
            boxShadow: `0 0 16px 3px ${theme.accent}66`,
          }}
        />
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: `${x * 100}%`,
            width: 46,
            height: 46,
            marginLeft: -23,
            marginTop: -23,
            borderRadius: "50%",
            background: theme.surface,
            border: `2px solid ${theme.accent}`,
            boxShadow: `0 6px 24px rgba(0,0,0,0.6), 0 0 22px ${theme.accent}55`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 5,
            // 速度差分驱动的微拉伸
            transform: `scaleX(${gripStretch})`,
          }}
        >
          {[-1, 1].map((d) => (
            <div
              key={d}
              style={{
                width: 0,
                height: 0,
                borderTop: "5px solid transparent",
                borderBottom: "5px solid transparent",
                [d < 0 ? "borderRight" : "borderLeft"]: `7px solid ${theme.accent}`,
              }}
            />
          ))}
        </div>

        {/* ── 角标：放在内容区，不压主体 ── */}
        <div
          style={{
            position: "absolute",
            left: 12,
            bottom: 12,
            opacity: badgeIn,
            fontFamily: "monospace",
            fontSize: badgeFont,
            letterSpacing: "2px",
            color: theme.textMuted,
            background: "rgba(4,8,10,0.72)",
            padding: "3px 9px",
            borderRadius: 5,
          }}
        >
          BEFORE
        </div>
        <div
          style={{
            position: "absolute",
            right: 12,
            bottom: 12,
            opacity: badgeIn,
            fontFamily: "monospace",
            fontSize: badgeFont,
            letterSpacing: "2px",
            color: theme.accent,
            background: "rgba(4,8,10,0.72)",
            padding: "3px 9px",
            borderRadius: 5,
          }}
        >
          AFTER
        </div>
      </div>

      {/* ── 主文案在图下方 ── */}
      {text ? (
        <div
          style={{
            position: "absolute",
            left: layout.safe.left,
            width: layout.safeWidth,
            top: layout.heroCenterY + panelH / 2 + (portrait ? 32 : 24),
            textAlign: "center",
            opacity: textIn,
          }}
        >
          <div style={{ fontSize: portrait ? 36 : 34, fontWeight: 600, color: theme.text }}>
            {text}
          </div>
          {subtext ? (
            <div
              style={{
                marginTop: 10,
                fontSize: portrait ? 26 : 24,
                color: theme.primary,
                letterSpacing: "0.04em",
              }}
            >
              {subtext}
            </div>
          ) : null}
          {metric ? (
            <div
              style={{
                marginTop: 14,
                fontSize: portrait ? 30 : 28,
                fontWeight: 800,
                color: theme.accent,
                letterSpacing: "0.02em",
              }}
            >
              {metric.label} {metric.value}
            </div>
          ) : null}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

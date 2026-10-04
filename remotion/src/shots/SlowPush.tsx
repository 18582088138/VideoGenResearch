/**
 * 慢推压迫 / Slow push-in.
 *
 * 实现镜头卡 `tension-camera-moves` 的 **C 式 slow-push-in**：
 * 匀加速推近 + 暗角渐深，把张力积压起来。
 *
 * Implements the **C variant** of `tension-camera-moves`: an accelerating push-in
 * with a deepening vignette that蓄 the tension.
 *
 * 卡上命门（已遵守）：
 *   - **加速曲线是本体**：`Easing.in(quad)`，匀速推读作普通 zoom，情绪为零
 *   - 幅度 1.00→1.14 —— 超过 1.2 就变成普通推镜头，情绪语义丢失
 *   - 暗角 opacity 0→0.5 与推近**同曲线**（分开调会读作两个动作）
 *   - 收尾真静止（R1）
 *
 * 卡上还说「C 式前 2 秒不可察是设计意图」，所以验收要看完整播放，
 * 抽帧 diff 前段变化极小属正常 —— 这一条写在这里避免后人当成 bug 去"修"。
 */

import React from "react";
import { AbsoluteFill, Easing, Img, interpolate, useCurrentFrame } from "remotion";
import { FONT_FAMILY, ThemeTokens } from "../theme/theme";
import { imageUrl } from '../theme/assetPath';
import { Layout } from "../theme/layout";
import { fitSize } from "../theme/assetDims";

export interface SlowPushProps {
  file: string;
  text?: string;
  theme: ThemeTokens;
  layout: Layout;
  durationInFrames: number;
}

export const SlowPush: React.FC<SlowPushProps> = ({
  file,
  text,
  theme,
  layout,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const portrait = layout.orientation === "portrait";

  // 推近只用前 75% 的时长，剩下 25% 让暗角继续加深并保持静止
  const pushEnd = Math.round(durationInFrames * 0.75);
  const scale = interpolate(frame, [0, pushEnd], [1.0, 1.14], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    // 匀加速：张力从"几乎察觉不到"爬到"压不住"
    easing: Easing.in(Easing.quad),
  });
  const vignette = interpolate(frame, [0, pushEnd], [0, 0.5], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.in(Easing.quad),
  });

  const { w: panelW, h: panelH } = fitSize(
    file,
    layout.safeWidth * 0.96,
    layout.safeHeight * (portrait ? 0.54 : 0.62),
  );

  const textIn = interpolate(frame, [8, 24], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  return (
    <AbsoluteFill style={{ fontFamily: FONT_FAMILY }}>
      <div
        style={{
          position: "absolute",
          left: "50%",
          top: layout.heroCenterY,
          transform: "translate(-50%, -50%)",
          width: panelW,
          height: panelH,
          borderRadius: 14,
          overflow: "hidden",
          border: `1px solid ${theme.border}`,
          boxShadow: "0 26px 80px rgba(0,0,0,0.66)",
        }}
      >
        <Img
          src={imageUrl(file)}
          style={{
            width: panelW,
            height: panelH,
            // 缩放绑在图上，不是容器上 —— 否则边框会跟着一起放大
            transform: `scale(${scale})`,
            transformOrigin: "center center",
            filter: "brightness(0.9) contrast(1.06)",
          }}
        />
        {/* 暗角：与推近同曲线 */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            pointerEvents: "none",
            background: `radial-gradient(ellipse 78% 78% at 50% 50%, transparent 38%, rgba(0,0,0,${vignette}) 100%)`,
          }}
        />
      </div>

      {/* 文案：情绪段给一句陈述，不抢画面 */}
      {text ? (
        <div
          style={{
            position: "absolute",
            left: layout.safe.left,
            width: layout.safeWidth,
            top: layout.heroCenterY + panelH / 2 + (portrait ? 34 : 26),
            textAlign: "center",
            opacity: textIn * (1 - Math.max(0, (vignette - 0.4) / 0.1) * 0.25),
          }}
        >
          <div
            style={{
              fontSize: portrait ? 34 : 32,
              fontWeight: 600,
              color: theme.text,
              letterSpacing: "0.02em",
              lineHeight: 1.42,
            }}
          >
            {text}
          </div>
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

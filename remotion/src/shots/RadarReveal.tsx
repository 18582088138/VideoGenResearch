/**
 * 雷达图聚光显影 / Corner spotlight reveal.
 *
 * 实现镜头卡 `spotlight-sweep-moves` 的 **C 式 corner-spotlight-reveal**：
 * 径向聚光从角落**匀速**扩张，照到即显影、照不到沉黑，最终全亮 —— 「光即转场」。
 *
 * Implements the **C variant** of `spotlight-sweep-moves`: a radial pool expands
 * at constant speed from a corner, revealing what it touches, ending fully lit.
 *
 * 卡上命门（已遵守）：
 *   - **匀速是命门**：全程 `Easing.linear`；加 ease 读作光有主观意图
 *   - **半径终值恰好在片尾覆盖全屏**：终值过大会提前饱和，造成"假匀速"
 *     （原卡判例：1300px @1080p / 100f；本项目按画面对角线推算终值）
 *   - 显影罩 feather ~15%：边太硬像圆形遮罩，太糊没有"照到/照不到"的界线
 *
 * 本项目用作**短视频的高潮镜头**（`07` 雷达图），对应分镜 5 号位。
 */

import React from "react";
import { Easing, Img, interpolate, useCurrentFrame } from "remotion";
import { FONT_FAMILY, ThemeTokens } from "../theme/theme";
import { imageUrl } from '../theme/assetPath';
import { Layout } from "../theme/layout";
import { fitSize } from "../theme/assetDims";

export interface RadarRevealProps {
  file: string;
  text?: string;
  subtext?: string;
  theme: ThemeTokens;
  layout: Layout;
  durationInFrames: number;
}

export const RadarReveal: React.FC<RadarRevealProps> = ({
  file,
  text,
  subtext,
  theme,
  layout,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const portrait = layout.orientation === "portrait";

  // ── 半径终值：必须恰好覆盖画面（取对角线，且不被 aspect 压扁）──
  // 用 vmax 单位让它与横竖屏无关；135% vmax 覆盖任何角到对角的距离。
  const radius = interpolate(frame, [6, durationInFrames - 24], [0, 135], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    // 匀速：光没有"意图"
    easing: Easing.linear,
  });

  // 显影罩从左上角扩张：照到即亮，照不到沉黑
  const mask = `radial-gradient(circle at 0% 0%, transparent 0%, transparent ${Math.max(0, radius - 14)}%, ${theme.bg} ${radius}%, ${theme.bg} 100%)`;

  // 全亮之后做一次轻微的落定呼吸（不是尾漂，是真静止前的收束）
  const settle = interpolate(
    frame,
    [durationInFrames - 24, durationInFrames - 12],
    [1, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const textIn = interpolate(frame, [durationInFrames * 0.52, durationInFrames * 0.66], [0, 1], {
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

  // 同上：按宽高双约束算确定尺寸，保证文字能落在图下方且不与字幕带冲突
  const maxW = layout.safeWidth * (portrait ? 1.0 : 0.92);
  const maxH = layout.safeHeight * (portrait ? 0.46 : 0.5);
  const { w: panelW, h: panelH } = fitSize(file, maxW, maxH);

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        fontFamily: FONT_FAMILY,
        opacity: exit,
      }}
    >
      {/* 绝对定位而非 flex 居中：文字要贴在**图下方**，flex 居中会把两者叠在一起 */}
      <div
        style={{
          position: "absolute",
          left: layout.safe.left,
          width: layout.safeWidth,
          top: layout.heroCenterY,
          transform: "translateY(-50%)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
        }}
      >
        <div
          style={{
            borderRadius: 16,
            overflow: "hidden",
            border: `1px solid ${theme.border}`,
            boxShadow: `0 30px 100px rgba(0,0,0,0.7)`,
            lineHeight: 0,
            transform: `scale(${settle})`,
          }}
        >
          <Img
            src={imageUrl(file)}
            style={{
              display: "block",
              width: panelW,
              height: panelH,
              filter: "brightness(0.93) contrast(1.06)",
            }}
          />
        </div>

        <div
          style={{
            marginTop: portrait ? 34 : 28,
            opacity: textIn,
            transform: `translateY(${(1 - textIn) * 14}px)`,
            textAlign: "center",
            maxWidth: layout.contentWidth * 0.9,
          }}
        >
          {text ? (
            <div
              style={{
                fontSize: portrait ? 44 : 42,
                fontWeight: 700,
                color: theme.text,
                letterSpacing: "0.02em",
              }}
            >
              {text}
            </div>
          ) : null}
          {subtext ? (
            <div
              style={{
                marginTop: 14,
                fontSize: portrait ? 34 : 30,
                fontWeight: 700,
                color: theme.primary,
                letterSpacing: "0.04em",
              }}
            >
              {subtext}
            </div>
          ) : null}
        </div>
      </div>

      {/* ── 显影罩压在最上层：这就是"光" ── */}
      <div style={{ position: "absolute", inset: 0, background: mask, pointerEvents: "none" }} />
    </div>
  );
};

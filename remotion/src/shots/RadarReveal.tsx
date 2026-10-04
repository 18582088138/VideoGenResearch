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
 *
 * 用户口径：本镜是「用素材图」的镜头，**渲染时不再输出任何镜头内文案**，
 * 因此素材改用 `mediaZoneFull` 全幅素材区。
 */

import React from "react";
import { Easing, Img, interpolate, useCurrentFrame } from "remotion";
import { FONT_FAMILY, ThemeTokens } from "../theme/theme";
import { imageUrl } from '../theme/assetPath';
import { Layout, tune } from "../theme/layout";
import { fitSize } from "../theme/assetDims";

export interface RadarRevealProps {
  file: string;
  // 用户口径：素材镜头不再输出文案 —— 字段保留以维持 Python 侧 spec 契约，渲染时忽略。
  text?: string;
  subtext?: string;
  theme: ThemeTokens;
  layout: Layout;
  durationInFrames: number;
}

export const RadarReveal: React.FC<RadarRevealProps> = ({
  file,
  theme,
  layout,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();

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

  const exit = interpolate(
    frame,
    [durationInFrames - 10, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  // 素材适配进 mediaZoneFull —— 尺寸由区域驱动，不再写死 safeWidth/safeHeight 比例。
  // 本镜无文案，素材占满整个内容区，因此比左栏素材显著更大。
  // fill 经 `tune` 读 TUNING（竖屏 portraitMediaFill = 1.05），不内联 portrait ? a : b。
  const fill = tune(layout, "portraitMediaFill", "landscapeMediaFill");
  const { w: panelW, h: panelH } = fitSize(
    file,
    layout.mediaZoneFull.w * fill,
    layout.mediaZoneFull.h * fill,
  );

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        fontFamily: FONT_FAMILY,
        opacity: exit,
      }}
    >
      {/* 素材区容器 = mediaZoneFull，flex 居中；不再用 translateY(-50%) 手算居中 */}
      <div
        style={{
          position: "absolute",
          left: layout.mediaZoneFull.x,
          width: layout.mediaZoneFull.w,
          top: layout.mediaZoneFull.y,
          height: layout.mediaZoneFull.h,
          display: "flex",
          justifyContent: "center",
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
      </div>

      {/* ── 显影罩压在最上层：这就是"光" ── */}
      <div style={{ position: "absolute", inset: 0, background: mask, pointerEvents: "none" }} />
    </div>
  );
};

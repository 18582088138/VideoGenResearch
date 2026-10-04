/**
 * 素材面板 / Asset panel — 承载白底学术图的「屏幕」.
 *
 * 设计依据 docs/design/01_theme_palettes.md §3.2：
 *   素材 04/05/06/07/08 都是**白底**学术图，直接贴在深色底上会刺眼。
 *   统一放进圆角卡片，带描边 + 外阴影 + 轻微压暗，让它读作「一块屏幕」
 *   而不是「一块白」。
 *
 * White-background academic figures sit inside a rounded, bordered card with a
 * soft shadow and slight darkening so they read as a lit panel, not a white
 * hole punched in the dark background.
 *
 * 同时提供 Ken-Burns 式推近：暗场里静止的图会显得"死"，缓慢推近给它生命。
 */

import React from "react";
import { Easing, Img, interpolate, useCurrentFrame } from "remotion";
import { ThemeTokens } from "../theme/theme";
import { imageUrl } from '../theme/assetPath';
import { Layout, tune } from "../theme/layout";
import { fitSize } from "../theme/assetDims";

export interface ImagePanelProps {
  /** public/images 下的文件名 / Filename under public/images. */
  file: string;
  theme: ThemeTokens;
  layout: Layout;
  durationInFrames: number;
  /** 起始缩放与结束缩放（缓慢推近）/ Ken-Burns zoom range. */
  zoomFrom?: number;
  zoomTo?: number;
  /** 起止帧（本镜内）/ Frame window within this shot. */
  inFrames?: number;
  outFrames?: number;
  /** 额外缩放系数（乘在 TUNING 的 mediaFill 上）/ Extra scale on top of mediaFill. */
  fit?: number;
  /** 额外样式（如位移）/ Extra style. */
  style?: React.CSSProperties;
}

export const ImagePanel: React.FC<ImagePanelProps> = ({
  file,
  theme,
  layout,
  durationInFrames,
  zoomFrom = 1.0,
  zoomTo = 1.06,
  inFrames = 12,
  outFrames = 10,
  fit = 1,
  style,
}) => {
  const frame = useCurrentFrame();

  const inT = interpolate(frame, [0, inFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const outT = interpolate(
    frame,
    [durationInFrames - outFrames, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  // 缓慢推近：整镜匀速推进，避免"死图"
  const zoom = interpolate(frame, [0, durationInFrames], [zoomFrom, zoomTo], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // 素材适配进 mediaZone —— 素材是**视觉主体**，不再受 safeHeight 硬编码限制。
  // 旧实现写死 `maxH = safeHeight * 0.62`，导致同一张 16:9 图在竖屏被缩到
  // 790×444（占画布 16.9%），是竖屏观感差的直接原因。
  //
  // **必须除以最大缩放倍数**：Ken-Burns 会一直放大到 `zoomTo`，
  // 若不预留这段空间，素材在推近过程中会溢出 mediaZone、压住文案区
  // （实测：1.05 的溢出量 × 组件内 zoom 叠加后，素材宽度达到画布的 148%）。
  //
  // Divide by the maximum zoom: Ken-Burns grows the asset to `zoomTo`, so the
  // space must be reserved up front or the asset escapes its zone mid-shot.
  const fill = tune(layout, "portraitMediaFill", "landscapeMediaFill") * fit;
  const zoomMax = Math.max(zoomFrom, zoomTo, 1);
  const { w: panelW, h: panelH } = fitSize(
    file,
    (layout.mediaZone.w * fill) / zoomMax,
    (layout.mediaZone.h * fill) / zoomMax,
  );

  return (
    <div
      style={{
        position: "absolute",
        left: layout.mediaZone.x,
        width: layout.mediaZone.w,
        top: layout.mediaZone.y,
        height: layout.mediaZone.h,
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        opacity: inT * outT,
        ...style,
      }}
    >
      <div
        style={{
          transform: `scale(${zoom})`,
          borderRadius: 18,
          overflow: "hidden",
          border: `1px solid ${theme.border}`,
          // 外阴影把面板从深底上「抬起来」，内发光避免边缘与背景糊在一起
          boxShadow: `0 28px 90px rgba(0,0,0,0.62), 0 0 0 1px ${theme.primary}18 inset`,
          lineHeight: 0,
        }}
      >
        <Img
          src={imageUrl(file)}
          style={{
            display: "block",
            width: panelW,
            height: panelH,
            // 白底图压暗一档，避免与深底反差过冲
            filter: "brightness(0.93) contrast(1.05)",
          }}
        />
      </div>
    </div>
  );
};

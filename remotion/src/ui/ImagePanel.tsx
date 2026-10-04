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
import { Layout } from "../theme/layout";
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
  /** 面板在安全框内的占比 / Panel size as a fraction of the safe area. */
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
  fit = 0.94,
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

  // 按宽高双约束算确定显示尺寸（避免宽度撑高把版面挤出画面）
  const maxW = layout.safeWidth * fit;
  const maxH = layout.safeHeight * 0.62;
  const { w: panelW, h: panelH } = fitSize(file, maxW, maxH);

  return (
    <div
      style={{
        position: "absolute",
        left: layout.safe.left,
        width: layout.safeWidth,
        top: layout.heroCenterY,
        transform: "translateY(-50%)",
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

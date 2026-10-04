/**
 * 页面聚光锁定 / Page spotlight lock-on.
 *
 * 实现镜头卡 `spotlight-hero-card` 的语义：暗场里一束聚光扫过页面，
 * 锁定目标后推近，页面从暗到亮被「读」出来。
 *
 * Implements `spotlight-hero-card`: a spotlight sweeps the page, locks onto the
 * target, then pushes in — the page is "read" from darkness into light.
 *
 * 相对原卡的取舍（本项目是「页面截图作为素材」，不是活的 web 页面）：
 *   - 保留：聚光游走 → 锁定 → 推近 → 长 hold 的动作弧
 *   - 省略：卡片弹起悬浮 / 轮廓光束两圈 / 3D 悬空注记
 *     （原卡这些依赖真实元素级切片与 3D 相机；本项目素材是整页截图，
 *      按 SKILL.md「允许适配性改动，但已知坑参数不得降档」处理 —— 这里
 *      降的是**构件数量**而非质量参数，且动作弧完整保留）
 *   - 遵守：锁定→落定后真静止（R1）、光效只给主角一次（Q4）
 */

import React from "react";
import { Easing, Img, interpolate, useCurrentFrame } from "remotion";
import { FONT_FAMILY, ThemeTokens } from "../theme/theme";
import { imageUrl } from '../theme/assetPath';
import { Layout } from "../theme/layout";
import { fitSize } from "../theme/assetDims";

export interface PageSpotlightProps {
  file: string;
  text?: string;
  source?: string;
  theme: ThemeTokens;
  layout: Layout;
  durationInFrames: number;
}

export const PageSpotlight: React.FC<PageSpotlightProps> = ({
  file,
  text,
  source,
  theme,
  layout,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const portrait = layout.orientation === "portrait";

  // ── 动作弧：游走(0-24) → 锁定(24-34) → 推近(34-58) → hold(58-结束)
  // 原卡节奏是 82→220f（≈4.6s）；本镜更长，按比例拉伸但保持「慢而稳」
  const LOCK_START = 24;
  const LOCK_END = 34;
  const PUSH_START = 34;
  const PUSH_END = 58;

  // 聚光头从左上游走到目标中心；光池同时收拢
  const beamX = interpolate(frame, [4, LOCK_START], [0.18, 0.5], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });
  const beamY = interpolate(frame, [4, LOCK_START], [0.24, 0.42], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });
  const poolRadius = interpolate(frame, [4, LOCK_START, LOCK_END], [64, 46, 38], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // 锁定瞬间的脉冲：光池猛地亮一下（"就是它"）
  const lockPulse = interpolate(
    frame,
    [LOCK_START, LOCK_START + 4, LOCK_END + 6],
    [0, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  // 相机推进：全页 → 目标区域特写
  const zoom = interpolate(frame, [PUSH_START, PUSH_END], [1.0, 1.55], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.33, 0, 0.15, 1),
  });

  // 暗场 → 点亮：vignette 从重到轻
  const lift = interpolate(frame, [4, PUSH_END], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const exit = interpolate(
    frame,
    [durationInFrames - 10, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  // 按宽高双约束算确定尺寸。
  // 竖屏用 0.70 × 0.32：整页截图是**宽幅**图（1280×544），按宽度撑满后高度
  // 仍过大，会把镜头文案推进图片底部并叠上底部字幕带（实测返工两次）。
  // 竖屏本来就该把它当"引证小图"处理，不是主视觉。
  //
  // Portrait: a landscape page screenshot must be treated as a small cited
  // figure, not the hero — at full width it grows tall enough to collide with
  // both the shot caption and the subtitle band.
  const { w: panelW, h: panelH } = fitSize(
    file,
    layout.safeWidth * (portrait ? 0.7 : 0.96),
    layout.safeHeight * (portrait ? 0.32 : 0.6),
  );
  const captionIn = interpolate(frame, [LOCK_END, LOCK_END + 16], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        opacity: exit,
        fontFamily: FONT_FAMILY,
        overflow: "hidden",
      }}
    >
      {/* ── 页面在暗场里被聚光读出 ── */}
      <div
        style={{
          position: "absolute",
          left: layout.safe.left,
          width: layout.safeWidth,
          top: layout.heroCenterY,
          transform: `translateY(-50%) scale(${zoom})`,
          display: "flex",
          justifyContent: "center",
          // 亮度随聚光锁定抬升；未锁定区域保持压暗，制造"光到即亮"
          filter: `brightness(${0.42 + lift * 0.46}) contrast(1.04)`,
          transition: "none",
        }}
      >
        <div
          style={{
            borderRadius: 14,
            overflow: "hidden",
            border: `1px solid ${theme.border}`,
            boxShadow: `0 30px 100px rgba(0,0,0,0.7), 0 0 0 1px ${theme.primary}22 inset`,
            lineHeight: 0,
          }}
        >
          <Img
            src={imageUrl(file)}
            style={{ display: "block", width: panelW, height: panelH }}
          />
        </div>
      </div>

      {/* ── 聚光罩：用径向渐变做"照到/照不到"的界线（feather ~15%）── */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          pointerEvents: "none",
          background: `radial-gradient(circle ${poolRadius}% at ${beamX * 100}% ${beamY * 100}%, transparent 0%, transparent 46%, ${theme.bg} ${68 + lift * 8}%, ${theme.bg} 100%)`,
        }}
      />

      {/* ── 锁定脉冲：一圈强调色光环闪一下（全片只给主角一次，Q4）── */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          pointerEvents: "none",
          opacity: lockPulse * 0.5,
          background: `radial-gradient(circle ${poolRadius * 1.3}% at ${beamX * 100}% ${beamY * 100}%, ${theme.accent}22 0%, transparent 60%)`,
        }}
      />

      {/* ── 主文案：紧贴图下方（不按画面比例绝对定位，避免与字幕带打架）── */}
      {text ? (
        <div
          style={{
            position: "absolute",
            left: layout.safe.left,
            width: layout.safeWidth,
            top: layout.heroCenterY + panelH / 2 + (portrait ? 32 : 24),
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 12,
            opacity: captionIn,
            transform: `translateY(${(1 - captionIn) * 12}px)`,
          }}
        >
          <div
            style={{
              fontSize: portrait ? 40 : 38,
              fontWeight: 600,
              color: theme.text,
              letterSpacing: "0.03em",
              textAlign: "center",
            }}
          >
            {text}
          </div>
          {source ? (
            <div
              style={{
                fontSize: portrait ? 22 : 20,
                color: theme.primary,
                letterSpacing: "0.16em",
                fontFamily: "monospace",
              }}
            >
              {source}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
};

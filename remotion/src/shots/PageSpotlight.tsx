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
 *
 * 用户口径：本镜是「用素材图」的镜头，**渲染时不再输出任何镜头内文案**
 * （素材图片 + 动效已经足够），因此素材改用 `mediaZoneFull` 全幅素材区。
 */

import React from "react";
import { Easing, Img, interpolate, useCurrentFrame } from "remotion";
import { FONT_FAMILY, ThemeTokens } from "../theme/theme";
import { imageUrl } from '../theme/assetPath';
import { Layout, tune } from "../theme/layout";
import { fitSize } from "../theme/assetDims";

export interface PageSpotlightProps {
  file: string;
  // 用户口径：素材镜头不再输出文案 —— 字段保留以维持 Python 侧 spec 契约，渲染时忽略。
  text?: string;
  source?: string;
  theme: ThemeTokens;
  layout: Layout;
  durationInFrames: number;
}

export const PageSpotlight: React.FC<PageSpotlightProps> = ({
  file,
  theme,
  layout,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();

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
  // 推近幅度：1.55 → 1.28 → **1.08**。
  // 改用全幅素材区（mediaZoneFull）后素材本身已占满内容区，再大幅推近只会把
  // 素材上下裁掉（实测 1.28 时顶部标题被切）。1.08 保留轻微推近的生命感，
  // 裁切量约 2.5%，素材内容完整可读。
  const zoom = interpolate(frame, [PUSH_START, PUSH_END], [1.0, 1.08], {
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

  // 素材适配进 mediaZoneFull —— 尺寸由区域驱动，不再写死 safeWidth/safeHeight 比例。
  // 本镜无文案，素材用全幅素材区（横屏 1760 宽 vs 分栏 1020），因此明显更大。
  // 宽幅整页截图在竖屏由区域宽度绑定，天然不会撑高去压字幕带。
  // fill 经 `tune` 读 TUNING（竖屏 portraitMediaFill，**必须 ≤1**）。
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
        opacity: exit,
        fontFamily: FONT_FAMILY,
        overflow: "hidden",
      }}
    >
      {/* ── 页面在暗场里被聚光读出 ──
          分两层是必须的：**视窗层不加 transform**，只负责裁切；
          缩放层在里面做推近。若把 scale 加在带 overflow:hidden 的同一个元素上，
          CSS 会把裁切边界一起缩放，裁切就失效了（素材会溢出到画布外）。 */}
      <div
        style={{
          position: "absolute",
          left: layout.mediaZoneFull.x,
          width: layout.mediaZoneFull.w,
          top: layout.mediaZoneFull.y,
          height: layout.mediaZoneFull.h,
          overflow: "hidden",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          // 亮度随聚光锁定抬升；未锁定区域保持压暗，制造"光到即亮"
          filter: `brightness(${0.42 + lift * 0.46}) contrast(1.04)`,
        }}
      >
        <div
          style={{
            transform: `scale(${zoom})`,
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
    </div>
  );
};

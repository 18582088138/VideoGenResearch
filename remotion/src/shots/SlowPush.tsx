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
 *
 * 用户口径：本镜是「用素材图」的镜头，**渲染时不再输出任何镜头内文案**，
 * 因此素材改用 `mediaZoneFull` 全幅素材区。
 */

import React from "react";
import { AbsoluteFill, Easing, Img, interpolate, useCurrentFrame } from "remotion";
import { FONT_FAMILY, ThemeTokens } from "../theme/theme";
import { imageUrl } from '../theme/assetPath';
import { Layout, tune } from "../theme/layout";
import { fitSize } from "../theme/assetDims";

export interface SlowPushProps {
  file: string;
  // 用户口径：素材镜头不再输出文案 —— 字段保留以维持 Python 侧 spec 契约，渲染时忽略。
  text?: string;
  theme: ThemeTokens;
  layout: Layout;
  durationInFrames: number;
}

export const SlowPush: React.FC<SlowPushProps> = ({
  file,
  theme,
  layout,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();

  // 推近只用前 75% 的时长，剩下 25% 让暗角继续加深并保持静止
  const pushEnd = Math.round(durationInFrames * 0.75);
  /** 推近的终点倍数 —— 素材适配时要按它预留空间，否则推近会把图挤出素材区。 */
  const PUSH_MAX = 1.14;
  const scale = interpolate(frame, [0, pushEnd], [1.0, PUSH_MAX], {
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

  // 素材适配进 mediaZoneFull —— 尺寸由区域驱动，不再写死 safeHeight 比例。
  // fill 经 `tune` 读 TUNING，不内联 `portrait ? a : b`。
  // **除以 PUSH_MAX 预留推近空间**：静止时素材占区域约 88%，推到终点恰好填满，
  // 全程不溢出、不裁切。
  const fill = tune(layout, "portraitMediaFill", "landscapeMediaFill");
  const { w: panelW, h: panelH } = fitSize(
    file,
    (layout.mediaZoneFull.w * fill) / PUSH_MAX,
    (layout.mediaZoneFull.h * fill) / PUSH_MAX,
  );

  return (
    <AbsoluteFill style={{ fontFamily: FONT_FAMILY }}>
      {/* 素材区容器 = mediaZoneFull，flex 居中；不再用 translate(-50%,-50%) 手算居中 */}
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
            position: "relative",
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
      </div>
    </AbsoluteFill>
  );
};

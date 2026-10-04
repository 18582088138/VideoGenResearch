/**
 * 双图并排 / Image pair — 两张素材左右对照.
 *
 * 素材类镜头（与 page-spotlight / slow-push 同口径）：**只渲染素材与动效，
 * 不渲染 text/subtext 文案** —— 用户口径是「使用素材图片的就不要在分镜中添加
 * 文案了，素材图片+动效已经足够了」。所以这里用 `mediaZoneFull` 全幅素材区，
 * 素材因此比图文类的分栏素材显著更大。
 *
 * Asset-only shot: the asset and its motion carry the frame, no in-shot copy
 * (matching page-spotlight / slow-push). Uses `mediaZoneFull`, so the images are
 * markedly larger than the column-constrained assets of figure shots.
 *
 * 动效：
 *   - `image` 与 `image2` 左右各半，**分别从两侧滑入**（右侧晚 4f，错峰）
 *   - 中间分隔线**从上向下**生长（`scaleY`，origin top）
 *   - 两张图各自按区域保持长宽比（`fitSize`，与 SlowPush 同法）
 *   - `eyebrow` 放左上角标（角标属动效层，不是镜头文案）
 *
 * 降级：`image2` 缺失时（例如上游还没把第二张图编译进 props）只渲染左图并占满
 * 整个素材区，不画分隔线 —— 宁可退化成单图镜头，也不要 404 让整片渲染失败。
 */

import React from "react";
import { AbsoluteFill, Easing, Img, interpolate, useCurrentFrame } from "remotion";
import { FONT_FAMILY, ThemeTokens } from "../theme/theme";
import { imageUrl } from "../theme/assetPath";
import { Layout, tune } from "../theme/layout";
import { fitSize } from "../theme/assetDims";

export interface ImagePairProps {
  /** 左图（相对 public/images）/ Left image. */
  file: string;
  /** 右图（相对 public/images）/ Right image. */
  file2: string;
  /** 左上角标 / Corner eyebrow. */
  eyebrow?: string;
  // 用户口径：素材镜头不再输出文案 —— 字段保留以维持 Python 侧 spec 契约，渲染时忽略。
  text?: string;
  subtext?: string;
  theme: ThemeTokens;
  layout: Layout;
  durationInFrames: number;
}

export const ImagePair: React.FC<ImagePairProps> = ({
  file,
  file2,
  eyebrow,
  theme,
  layout,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const zone = layout.mediaZoneFull;

  const hasPair = Boolean(file && file2);
  const gap = zone.w * 0.02;
  const halfW = hasPair ? (zone.w - gap) / 2 : zone.w;

  // 素材适配进各自半区（保持长宽比，永不裁切/变形）；fill 经 `tune` 读 TUNING
  const fill = tune(layout, "portraitMediaFill", "landscapeMediaFill");
  const leftBox = fitSize(file, halfW * fill, zone.h * fill);
  const rightBox = fitSize(file2, halfW * fill, zone.h * fill);

  // 两侧分别滑入：位移用半区宽度的比例（不写死像素，画幅变了也成立）
  const slideIn = (delay: number): number =>
    interpolate(frame, [delay, delay + 16], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.out(Easing.cubic),
    });
  const leftT = slideIn(0);
  const rightT = slideIn(4);

  // 分隔线：从上向下生长，排在两图落位之后
  const dividerT = interpolate(frame, [10, 28], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  const eyebrowIn = interpolate(frame, [0, 14], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const exit = interpolate(
    frame,
    [durationInFrames - 10, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const bodySize = tune(layout, "figureBodyPortrait", "figureBodyLandscape");
  const dividerH = zone.h * 0.72;

  return (
    <AbsoluteFill style={{ fontFamily: FONT_FAMILY, opacity: exit }}>
      <div
        style={{
          position: "absolute",
          left: zone.x,
          top: zone.y,
          width: zone.w,
          height: zone.h,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap,
        }}
      >
        {/* 左图：从左侧滑入 */}
        <div
          style={{
            position: "relative",
            width: halfW,
            height: zone.h,
            overflow: "hidden",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            opacity: Math.min(1, leftT * 1.4),
          }}
        >
          {file ? (
            <div
              style={{
                transform: `translateX(${(1 - leftT) * -halfW * 0.85}px)`,
                borderRadius: 14,
                overflow: "hidden",
                border: `1px solid ${theme.border}`,
                boxShadow: "0 26px 80px rgba(0,0,0,0.66)",
                lineHeight: 0,
              }}
            >
              <Img
                src={imageUrl(file)}
                style={{
                  display: "block",
                  width: leftBox.w,
                  height: leftBox.h,
                  filter: "brightness(0.95) contrast(1.06)",
                }}
              />
            </div>
          ) : null}
        </div>

        {/* 右图：从右侧滑入（错峰 4f）。image2 缺失时整块不渲染 —— 见文件头降级说明 */}
        {hasPair ? (
          <div
            style={{
              position: "relative",
              width: halfW,
              height: zone.h,
              overflow: "hidden",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              opacity: Math.min(1, rightT * 1.4),
            }}
          >
            <div
              style={{
                transform: `translateX(${(1 - rightT) * halfW * 0.85}px)`,
                borderRadius: 14,
                overflow: "hidden",
                border: `1px solid ${theme.border}`,
                boxShadow: "0 26px 80px rgba(0,0,0,0.66)",
                lineHeight: 0,
              }}
            >
              <Img
                src={imageUrl(file2)}
                style={{
                  display: "block",
                  width: rightBox.w,
                  height: rightBox.h,
                  filter: "brightness(0.95) contrast(1.06)",
                }}
              />
            </div>
          </div>
        ) : null}

        {/* 中间分隔线：从上向下生长 */}
        {hasPair ? (
          <div
            style={{
              position: "absolute",
              left: zone.w / 2 - 1,
              top: (zone.h - dividerH) / 2,
              width: 2,
              height: dividerH,
              background: `linear-gradient(180deg, ${theme.accent}, ${theme.primary}22)`,
              boxShadow: `0 0 16px 2px ${theme.accent}44`,
              transformOrigin: "top center",
              transform: `scaleY(${dividerT})`,
            }}
          />
        ) : null}
      </div>

      {/* 左上角标（放在素材区外侧层，不随滑入被裁切） */}
      {eyebrow ? (
        <div
          style={{
            position: "absolute",
            left: zone.x + zone.w * 0.012,
            top: zone.y + zone.h * 0.02,
            opacity: eyebrowIn,
            fontFamily: "monospace",
            fontSize: bodySize * 0.68,
            letterSpacing: "0.18em",
            color: theme.primary,
            background: "rgba(4,8,10,0.72)",
            padding: `${bodySize * 0.14}px ${bodySize * 0.34}px`,
            borderRadius: 5,
          }}
        >
          {eyebrow}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

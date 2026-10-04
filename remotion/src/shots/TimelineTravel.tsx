/**
 * 时间轴横移 / Timeline travel.
 *
 * 实现镜头卡 `timeline-travel`：镜头沿水平刻度轴**分段变速**横移
 * （缓起 → 冲刺 → 急刹），每过一格卡片 spring 弹立，末刻度急停推近。
 *
 * Implements `timeline-travel`: a segmented-speed horizontal travel along a
 * timeline axis (ease-in, sprint, hard brake), cards springing upright as they
 * pass, ending in a push-in on the final tick.
 *
 * 卡上命门（已遵守）：
 *   - **变速曲线**：输入断点 `[0, 0.15, 0.88, 1]` → 输出 `[0, 0.055, 0.9, 1]`；
 *     中段不够快就没有"旅行感"，全程匀速即廉价 PPT
 *   - **弹立时机**：相机到达刻度**前 6f** 起弹（到了才弹观众已经错过）
 *   - **次刻度小点是速度感的唯一参照物**，删掉就感觉不到快
 *   - **急停推近** 1→1.28 —— 不推近急停就只是"停了"，推近才是"到了"
 *   - **静止预算前置**：先给末段留 ≥30f 再倒推行程
 *
 * ⚠️ 世界层定位用的是「相机跟随」模型：**相机位置 = 当前活动刻度**，
 * 世界位移 = 基准位 − 相机位。早先用「世界匀速左移 + 总量估算」的写法
 * 会把末刻度推出画外（实测翻车），跟随模型天然保证活动刻度始终居中。
 */

import React from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { FONT_FAMILY, ThemeTokens } from "../theme/theme";
import { Layout } from "../theme/layout";

export interface TimelineStop {
  /** 刻度标签（如 "2025"）/ Tick label. */
  label: string;
  /** 该刻度的一句话说明 / One-line description. */
  note?: string;
}

export interface TimelineTravelProps {
  text?: string;
  stops: TimelineStop[];
  metrics?: Array<{ label: string; value: string }>;
  theme: ThemeTokens;
  layout: Layout;
  durationInFrames: number;
}

export const TimelineTravel: React.FC<TimelineTravelProps> = ({
  text,
  stops,
  metrics,
  theme,
  layout,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const portrait = layout.orientation === "portrait";

  const n = Math.max(1, stops.length);
  const gap = layout.safeWidth * (portrait ? 0.62 : 0.46);
  const cardW = gap * 0.86;

  // 时间轴的**局部坐标**：本镜用一个居中的容器，内部坐标全部相对它算。
  // 关键：容器加了 translateY(-50%) 之后，内部**不能**再用 layout.safe.top /
  // safeHeight 这类页面绝对坐标 —— 那会让卡片跑到画框外（实测踩过）。
  // 这里把可用高度换算成本地坐标：轴线放在容器内偏下处。
  //
  // Local coordinate space: the container is centred with translateY(-50%), so
  // internals must not use page-absolute layout values or content escapes the
  // frame. Derive the axis from the local content height instead.
  const localHeight = layout.contentHeight * (portrait ? 0.86 : 0.9);
  const axisY = localHeight * (portrait ? 0.72 : 0.62);

  // 静止预算前置：先扣末段静止，再倒推行程
  const REST = Math.max(30, Math.round(durationInFrames * 0.18));
  const travelEnd = durationInFrames - REST;
  const brakeFrame = Math.max(1, travelEnd - 10);

  // ── 相机位置：0 → n-1，分段变速（卡上给出的断点/输出）──
  // 三段线性，闭式可反解 —— 反解用于「到达前 6f 起弹」的时机计算。
  const BREAKS: Array<[number, number]> = [
    [0, 0],
    [Math.round(travelEnd * 0.15), (n - 1) * 0.055],
    [Math.round(travelEnd * 0.88), (n - 1) * 0.9],
    [brakeFrame, n - 1],
  ];

  const camAt = (f: number): number => {
    if (f <= BREAKS[0][0]) return BREAKS[0][1];
    for (let i = 0; i < BREAKS.length - 1; i++) {
      const [f0, x0] = BREAKS[i];
      const [f1, x1] = BREAKS[i + 1];
      if (f <= f1 && f1 > f0) {
        return x0 + ((f - f0) / (f1 - f0)) * (x1 - x0);
      }
    }
    return BREAKS[BREAKS.length - 1][1];
  };

  /** 闭式反解：相机位置达到 target 时的帧号 / Closed-form inversion. */
  const frameForCam = (target: number): number => {
    for (let i = 0; i < BREAKS.length - 1; i++) {
      const [f0, x0] = BREAKS[i];
      const [f1, x1] = BREAKS[i + 1];
      if (target <= x1 && x1 > x0) {
        return Math.round(f0 + ((target - x0) / (x1 - x0)) * (f1 - f0));
      }
    }
    return brakeFrame;
  };

  const camPos = camAt(frame);

  // 世界位移 = 基准位 − 相机位（活动刻度恒在画面中心偏左，给右侧留出"前方"）
  const focusX = layout.width * (portrait ? 0.5 : 0.46);
  const baseX = layout.safe.left + cardW / 2;
  const worldX = focusX - (baseX + camPos * gap);

  // 急停推近：1 → 1.28，10f，out cubic
  const push = interpolate(frame, [brakeFrame, brakeFrame + 10], [1, 1.28], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  // 次刻度小点：速度感的唯一参照物
  const minorPerGap = 5;
  const minors: number[] = [];
  for (let i = 0; i < n * minorPerGap; i++) {
    minors.push(baseX + (i / minorPerGap) * gap + worldX);
  }

  return (
    <AbsoluteFill style={{ fontFamily: FONT_FAMILY, overflow: "hidden" }}>
      {/* ── 内容容器：在 contentCenterY 上居中，内部一律用本地坐标 ──
          必须自己建立坐标系（不能用 inset:0 铺满画布），否则 axisY 这个
          本地值会被当成页面绝对坐标，卡片直接跑出画框（实测踩过）。 */}
      <div
        style={{
          position: "absolute",
          left: 0,
          top: layout.contentCenterY,
          width: layout.width,
          height: localHeight,
          transform: "translateY(-50%)",
        }}
      >
        {/* ── 世界层：整体横移 + 末段推近（origin 对准活动刻度）── */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            transform: `scale(${push})`,
            transformOrigin: `${focusX}px ${axisY}px`,
          }}
        >
        {/* 主轴 */}
        <div
          style={{
            position: "absolute",
            left: -layout.safeWidth * 0.5,
            width: layout.width + layout.safeWidth,
            top: axisY,
            height: 2,
            background: `linear-gradient(90deg, transparent, ${theme.border} 10%, ${theme.primary}55 50%, ${theme.border} 90%, transparent)`,
          }}
        />

        {/* 次刻度 */}
        {minors.map((px, i) =>
          px < -40 || px > layout.width + 40 ? null : (
            <div
              key={`m${i}`}
              style={{
                position: "absolute",
                left: px - 1.5,
                top: axisY + 13,
                width: 3,
                height: 3,
                borderRadius: "50%",
                background: theme.border,
              }}
            />
          ),
        )}

        {/* 主刻度 + 卡片 */}
        {stops.map((s, i) => {
          const px = baseX + i * gap + worldX;
          if (px < -gap || px > layout.width + gap) {
            return null;
          }
          const isLast = i === n - 1;

          // 弹立时机：相机到达该刻度**前 6f**（闭式反解，不用扫帧）
          const popStart = frameForCam(i) - 6;
          if (frame < popStart) {
            return null;
          }

          // spring 弹立：底边为轴 scaleY 0→1，damping ~11 明显过冲
          const rise = spring({
            frame: frame - popStart,
            fps,
            from: 0,
            to: 1,
            config: { damping: 11, stiffness: 130, mass: 0.8 },
          });

          return (
            <React.Fragment key={`s${i}`}>
              <div
                style={{
                  position: "absolute",
                  left: px - 1,
                  top: axisY - 18,
                  width: 2,
                  height: 36,
                  background: isLast ? theme.accent : theme.primary,
                  boxShadow: `0 0 14px 3px ${isLast ? theme.accent : theme.primary}55`,
                }}
              />

              {/* 卡片：底边锚定在轴线上，spring 弹立（scaleY 以底边为轴）。
                  垂直位置**不能写死像素** —— 竖屏卡内容会换行、屏横屏高度不同，
                  写死会让卡片悬空在轴上方很远处（实测返工）。
                  用 translateY(-100%) 让卡片自己贴住轴。 */}
              <div
                style={{
                  position: "absolute",
                  left: px - cardW / 2,
                  top: axisY,
                  width: cardW,
                  transformOrigin: "bottom center",
                  transform: `translateY(-100%) scaleY(${Math.max(0, Math.min(1.08, rise))})`,
                  opacity: Math.min(1, rise * 2),
                  background: theme.surface,
                  border: `1px solid ${isLast ? theme.accent : theme.border}`,
                  borderRadius: 12,
                  padding: portrait ? "20px 18px" : "16px 18px",
                  boxShadow: "0 18px 50px rgba(0,0,0,0.6)",
                }}
              >
                <div
                  style={{
                    fontSize: portrait ? 34 : 30,
                    fontWeight: 800,
                    color: isLast ? theme.accent : theme.primary,
                    letterSpacing: "0.03em",
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  {s.label}
                </div>
                {s.note ? (
                  <div
                    style={{
                      marginTop: 8,
                      fontSize: portrait ? 20 : 19,
                      color: theme.textMuted,
                      lineHeight: 1.4,
                    }}
                  >
                    {s.note}
                  </div>
                ) : null}
              </div>
            </React.Fragment>
          );
        })}
      </div>

        {/* ── 顶部标题（不随世界层动）── 用本地坐标，标题落在轴线上方 ── */}
        {text ? (
          <div
            style={{
              position: "absolute",
              left: layout.safe.left,
              width: layout.safeWidth,
              top: Math.max(0, axisY - localHeight * 0.82),
              fontSize: portrait ? 38 : 34,
              fontWeight: 600,
              color: theme.text,
              letterSpacing: "0.02em",
              textAlign: "center",
            }}
          >
            {text}
          </div>
        ) : null}

        {/* ── 底部指标：急停后浮现，给"到了"一个落点 ── */}
        {metrics && metrics.length > 0 ? (
          <div
            style={{
              position: "absolute",
              left: layout.safe.left,
              width: layout.safeWidth,
              top: axisY + (portrait ? 90 : 76),
              display: "flex",
              justifyContent: "center",
              gap: portrait ? 46 : 56,
              opacity: interpolate(frame, [brakeFrame + 4, brakeFrame + 16], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
                easing: Easing.out(Easing.cubic),
              }),
            }}
          >
          {metrics.map((m) => (
            <div key={m.label} style={{ textAlign: "center" }}>
              <div
                style={{
                  fontSize: portrait ? 46 : 42,
                  fontWeight: 800,
                  color: theme.accent,
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {m.value}
              </div>
              <div
                style={{
                  marginTop: 6,
                  fontSize: portrait ? 20 : 18,
                  color: theme.textMuted,
                  letterSpacing: "0.16em",
                }}
              >
                {m.label}
              </div>
            </div>
          ))}
        </div>
      ) : null}
      </div>
    </AbsoluteFill>
  );
};

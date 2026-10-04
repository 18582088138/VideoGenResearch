/**
 * 扫描线标注 / Scanline annotation.
 *
 * 实现镜头卡 `scanline-annotate-focus`：一条亮扫描线自上而下**匀速**掠过，
 * 扫过之处按先后弹出取景框（1.75 倍收拢 + 过冲），随后旁侧打出等宽小字标注。
 *
 * Implements `scanline-annotate-focus`: a scanline sweeps top-to-bottom at
 * constant speed; viewfinder brackets snap onto targets in the order they are
 * reached, then monospace labels fade in beside them.
 *
 * 卡上命门（已遵守）：
 *   - **扫描线零缓动**：加 ease 就读作"有人在拖进度条"
 *   - **触发时刻由目标 bbox 反算**：`ft = 0.06 + ((y+h+30)/330)·0.60`，
 *     再按 y 排序钳制最小间隔 0.05，避免两框同时弹
 *   - **计数行实时统计**已触发框数，不写死时间轴
 *   - 角标臂长 9px（超过目标短边 1/3 就变成完整边框，丢掉"取景"语义）
 *   - 对焦闪 fill 峰值 0.07（>0.15 会盖住内容）
 *
 * 相对原卡的适配：原卡 bbox 是针对某个具体产品页面手调的像素值。
 * 本项目素材是学术图表，目标由 `targets` prop 传入**归一化坐标**，
 * 换图时只需改数据、不必改动画代码。
 */

import React from "react";
import { Easing, Img, interpolate, useCurrentFrame } from "remotion";
import { FONT_FAMILY, ThemeTokens } from "../theme/theme";
import { imageUrl } from '../theme/assetPath';
import { Layout } from "../theme/layout";
import { fitSize } from "../theme/assetDims";

/** 一个标注目标 / One annotation target, in normalised image coordinates. */
export interface AnnoTarget {
  /** 归一化包围盒（0–1）/ Normalised bbox within the image. */
  x: number;
  y: number;
  w: number;
  h: number;
  /** 标注文字 / Label text. */
  label: string;
  /** 标注放在框的哪一侧 / Which side the label sits on. */
  side?: "left" | "right";
}

export interface ScanAnnotateProps {
  file: string;
  text?: string;
  subtext?: string;
  targets: AnnoTarget[];
  theme: ThemeTokens;
  layout: Layout;
  durationInFrames: number;
}

/** 扫描线行程（归一化 y 的起止）。分母与触发换算必须同改，否则框会提前弹。 */
const SCAN_FROM = 0.06;
const SCAN_TO = 0.66;
const SCAN_TRAVEL = SCAN_TO - SCAN_FROM;

export const ScanAnnotate: React.FC<ScanAnnotateProps> = ({
  file,
  text,
  subtext,
  targets,
  theme,
  layout,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const portrait = layout.orientation === "portrait";

  // t 是整镜的归一化进度，参照原卡的 0.06→0.66 窗口
  const scanT = interpolate(frame, [0, durationInFrames * 0.66], [SCAN_FROM, SCAN_TO], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    // 零缓动：匀速才读作机械扫掠
    easing: Easing.linear,
  });

  const scanOpacity =
    interpolate(frame, [0, durationInFrames * 0.04], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }) *
    interpolate(
      frame,
      [durationInFrames * 0.66, durationInFrames * 0.71],
      [1, 0],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
    );

  // 触发时刻：扫描线越过目标**下缘**的那一刻，再钳制最小间隔
  const sorted = [...targets].sort((a, b) => a.y + a.h - (b.y + b.h));
  let prev = -Infinity;
  const fired: number[] = sorted.map((t) => {
    const raw = SCAN_FROM + ((t.y + t.h) / 1.0) * SCAN_TRAVEL;
    const v = Math.max(raw, prev + 0.05);
    prev = v;
    return v;
  });
  // fired 与 sorted 同序；用原索引回查
  const firedOf = new Map<AnnoTarget, number>();
  sorted.forEach((t, i) => firedOf.set(t, fired[i]));

  const progress = frame / durationInFrames;
  const firedCount = targets.filter((t) => progress >= (firedOf.get(t) ?? 0)).length;
  const complete = progress >= 0.78;
  const statusColor = complete ? theme.primary : theme.textMuted;

  // 图按**宽高双约束**算出确定显示尺寸：容器与图严格同尺寸，
  // 标注百分比才有意义；同时把文字与字幕带的位置预留出来（横屏曾整个溢出）。
  const maxW = layout.safeWidth * 0.86;
  const maxH = layout.safeHeight * (portrait ? 0.5 : 0.56);
  const { w: panelW, h: panelH } = fitSize(file, maxW, maxH);

  // 文字压在**图下方**（图已留出余量，不再需要绝对定位到画面比例位置）
  const textTop = layout.heroCenterY + panelH / 2 + (portrait ? 34 : 26);

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        fontFamily: FONT_FAMILY,
      }}
    >
      {/* ── 顶部状态行：实时计数，不写死 ── */}
      <div
        style={{
          position: "absolute",
          left: layout.safe.left,
          top: layout.safe.top * 0.7,
          fontFamily: "monospace",
          fontSize: portrait ? 22 : 20,
          letterSpacing: "2px",
          color: statusColor,
          zIndex: 2,
        }}
      >
        {complete
          ? "ANALYSIS · COMPLETE"
          : `SCAN · 0${firedCount}/0${targets.length}`}
      </div>

      {/* ── 图 + 扫描线 + 取景框，共用同一尺寸的定位容器 ──
          **水平居中**（left 50% + translateX(-50%)）：早先只写了 translateY，
          面板会贴左边安全框，与其它镜头不对齐。
          **不要 overflow:hidden** —— 标注按整图尺寸换算百分比，
          一旦容器裁剪，标注会被切掉（实测过）。圆角直接加在图上。 */}
      <div
        style={{
          position: "absolute",
          left: "50%",
          top: layout.heroCenterY,
          transform: "translate(-50%, -50%)",
          width: panelW,
          height: panelH,
          border: `1px solid ${theme.border}`,
          borderRadius: 14,
          boxShadow: `0 26px 80px rgba(0,0,0,0.65), 0 0 0 1px ${theme.primary}14 inset`,
        }}
      >
        <Img
          src={imageUrl(file)}
          style={{
            display: "block",
            width: panelW,
            height: panelH,
            borderRadius: 13,
            filter: "brightness(0.93) contrast(1.05)",
          }}
        />

        {/* 扫描线：1px 亮线 + 上下渐隐拖尾，让它像"光"不像"横杠" */}
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            top: `${scanT * 100}%`,
            height: 2,
            opacity: scanOpacity,
            background: `linear-gradient(90deg, transparent, ${theme.accent} 12%, #FFFFFF 50%, ${theme.accent} 88%, transparent)`,
            boxShadow: `0 0 18px 4px ${theme.accent}55`,
          }}
        />

        {/* 取景框：4 个 L 角，outBack 收拢 + 对焦闪 */}
        {targets.map((t, i) => {
          const ft = firedOf.get(t) ?? 1;
          const fireFrame = ft * durationInFrames;
          // 触发帧起 8f 内快速浮现（inputRange/outputRange 必须等长）
          const a = interpolate(frame, [fireFrame, fireFrame + 8], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          if (a <= 0) return null;

          const settle = interpolate(
            frame,
            [fireFrame, fireFrame + 0.13 * durationInFrames],
            [1.75, 1],
            {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              // outBack：过冲后回稳，读作"对准"
              easing: Easing.out(Easing.back(1.6)),
            },
          );
          const flash = interpolate(
            frame,
            [
              (ft + 0.04) * durationInFrames,
              (ft + 0.07) * durationInFrames,
              (ft + 0.22) * durationInFrames,
            ],
            [0, 0.07, 0],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
          );
          const labelIn = interpolate(
            frame,
            [(ft + 0.05) * durationInFrames, (ft + 0.16) * durationInFrames],
            [0, 1],
            {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.out(Easing.cubic),
            },
          );

          const ARM = 9;
          const box = {
            left: `${t.x * 100}%`,
            top: `${t.y * 100}%`,
            width: `${t.w * 100}%`,
            height: `${t.h * 100}%`,
            position: "absolute" as const,
            transform: `scale(${settle})`,
            transformOrigin: "center center",
          };
          const armStyle: React.CSSProperties = {
            position: "absolute",
            width: ARM,
            height: ARM,
            borderColor: theme.accent,
            borderStyle: "solid",
            borderWidth: 0,
          };

          return (
            <React.Fragment key={i}>
              <div style={{ ...box, opacity: a }}>
                <div
                  style={{
                    position: "absolute",
                    inset: 0,
                    background: "#FFFFFF",
                    opacity: flash,
                  }}
                />
                <div style={{ ...armStyle, left: 0, top: 0, borderLeftWidth: 1.5, borderTopWidth: 1.5 }} />
                <div style={{ ...armStyle, right: 0, top: 0, borderRightWidth: 1.5, borderTopWidth: 1.5 }} />
                <div style={{ ...armStyle, left: 0, bottom: 0, borderLeftWidth: 1.5, borderBottomWidth: 1.5 }} />
                <div style={{ ...armStyle, right: 0, bottom: 0, borderRightWidth: 1.5, borderBottomWidth: 1.5 }} />
              </div>

              {/* 标注：等宽小字，滞后于取景框出现（"框稳了才命名"）。
                  放在框的**正下方居中**而不是侧边 —— 竖屏安全框只有 840px 宽，
                  侧置标注必然溢出图外或被裁掉；下方居中在横竖屏都成立。 */}
              <div
                style={{
                  position: "absolute",
                  left: `${(t.x + t.w / 2) * 100}%`,
                  top: `${(t.y + t.h) * 100}%`,
                  transform: `translateX(-50%) translateY(${4 + (1 - labelIn) * 4}px)`,
                  opacity: labelIn,
                  fontFamily: "monospace",
                  fontSize: portrait ? 16 : 15,
                  letterSpacing: "1.5px",
                  color: theme.text,
                  whiteSpace: "nowrap",
                  textShadow: "0 2px 10px rgba(0,0,0,0.95)",
                  background: "rgba(4,8,10,0.72)",
                  padding: "3px 9px",
                  borderRadius: 5,
                }}
              >
                {t.label}
              </div>
            </React.Fragment>
          );
        })}
      </div>

      {/* ── 主文案：紧贴图下方，不再按画面比例绝对定位 ── */}
      {text ? (
        <div
          style={{
            position: "absolute",
            left: layout.safe.left,
            width: layout.safeWidth,
            top: textTop,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            textAlign: "center",
          }}
        >
          <div
            style={{
              fontSize: portrait ? 34 : 32,
              fontWeight: 600,
              color: theme.text,
              letterSpacing: "0.02em",
            }}
          >
            {text}
          </div>
          {subtext ? (
            <div
              style={{
                marginTop: 10,
                fontSize: portrait ? 24 : 22,
                color: theme.primary,
                letterSpacing: "0.04em",
              }}
            >
              {subtext}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
};

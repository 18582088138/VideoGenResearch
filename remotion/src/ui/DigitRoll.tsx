/**
 * 数字滚动 / Odometer-style digit roll.
 *
 * 移植自 video-shotcraft `assets/lib/DigitRoll.tsx`，按本项目需要扩展：
 *   - 字号 / 颜色 / 字重可配（原版固定字号与琥珀色）
 *   - 支持逐位错峰（`delay + i * stagger`），做出「哒、哒、哒」的锁定节奏
 *
 * Ported from video-shotcraft's `DigitRoll.tsx`, extended with configurable
 * size/colour/weight and per-digit stagger so digits lock left-to-right.
 *
 * 命门（来自 `odometer-digit-roll` 卡）：
 *   - 必须 `tabular-nums`，否则每位非等宽会让整行在滚动态抖动
 *   - 非数字位（`.` `%` 等）全程驻场不滚
 */

import React from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";

const DIGITS = "0123456789";

export interface DigitRollProps {
  /** 要滚动的字符串，非数字字符原样静态显示 / String to roll. */
  value: string;
  /** 起始帧 / Start frame. */
  delay?: number;
  /** 每位错峰帧数 / Stagger frames per digit. */
  stagger?: number;
  /** 单个数字**滚动段**的帧数（卡：16f）/ Frames for the roll leg. */
  duration?: number;
  /**
   * 过冲后回弹锁定的帧数（卡：6f）/ Frames to settle back after overshoot.
   *
   * 卡上明确：**「无过冲读作滑到即停，机械感减半」** —— 这是本卡的命门，
   * 不是可选装饰。所以它默认开启且非零。
   */
  settle?: number;
  /** 过冲量（行数，卡：+0.5 行）/ Overshoot in line-heights. */
  overshoot?: number;
  fontSize?: number;
  color?: string;
  /** 字重；可变字体用 fontVariationSettings 生效 / Weight via variable axis. */
  weight?: number;
}

export const DigitRoll: React.FC<DigitRollProps> = ({
  value,
  delay = 0,
  stagger = 4,
  duration = 16,
  settle = 6,
  overshoot = 0.5,
  fontSize = 30,
  color = "#E8F1F2",
  weight = 800,
}) => {
  const frame = useCurrentFrame();
  const lineH = fontSize * 1.15;

  return (
    <span
      style={{
        display: "inline-flex",
        overflow: "hidden",
        height: lineH,
        verticalAlign: "bottom",
        fontVariationSettings: `'wght' ${weight}`,
      }}
    >
      {value.split("").map((ch, i) => {
        const target = DIGITS.indexOf(ch);

        // 小数点、百分号、单位符号等：不滚动，全程驻场
        if (target < 0) {
          return (
            <span key={i} style={{ fontSize, lineHeight: `${lineH}px`, color }}>
              {ch}
            </span>
          );
        }

        const start = delay + i * stagger;

        // ── 两段式落位：先过冲半格，再 6f 弹回整数（镜头卡 `odometer-digit-roll`）
        //    「位 i 于 20+i×7f 开始 16f out(cubic) 减速至目标 +0.5 行过冲，
        //      再 6f 弹回整数锁定」—— 过冲是机械感的来源，去掉就读作「滑到即停」。
        const rollT = interpolate(
          frame,
          [start, start + duration],
          [0, 1],
          {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            // 减速落位：快起慢停，读作「锁定」而非「滑到就停」
            easing: Easing.bezier(0.25, 0.8, 0.25, 1),
          },
        );
        const settleT = interpolate(
          frame,
          [start + duration, start + duration + settle],
          [0, 1],
          {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.inOut(Easing.quad),
          },
        );

        // 先滚满一整条 strip（10 位）到 (目标 + 过冲)，settleT 再把过冲量收回去
        const posLines = (10 + target + overshoot) * rollT - overshoot * settleT;
        const offset = posLines * lineH;

        return (
          <span key={i} style={{ display: "inline-block", height: lineH }}>
            <span style={{ display: "block", transform: `translateY(${-offset}px)` }}>
              {(DIGITS + DIGITS).split("").map((d, j) => (
                <span
                  key={j}
                  style={{
                    display: "block",
                    fontSize,
                    lineHeight: `${lineH}px`,
                    color,
                    // 等宽数字：缺了它整行会在滚动期左右抖动
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  {d}
                </span>
              ))}
            </span>
          </span>
        );
      })}
    </span>
  );
};

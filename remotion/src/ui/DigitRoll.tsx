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
  /** 单个数字走完的帧数 / Frames for one digit to settle. */
  duration?: number;
  fontSize?: number;
  color?: string;
  /** 字重；可变字体用 fontVariationSettings 生效 / Weight via variable axis. */
  weight?: number;
}

export const DigitRoll: React.FC<DigitRollProps> = ({
  value,
  delay = 0,
  stagger = 4,
  duration = 22,
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

        const t = interpolate(
          frame,
          [delay + i * stagger, delay + i * stagger + duration],
          [0, 1],
          {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            // 减速落位：快起慢停，读作「锁定」而非「滑到就停」
            easing: Easing.bezier(0.25, 0.8, 0.25, 1),
          },
        );

        // 先滚满一整条 strip（10 位）再落到目标位
        const offset = (10 + target) * t * lineH;

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

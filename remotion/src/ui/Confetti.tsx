/**
 * 彩纸爆点 / Confetti burst.
 *
 * 实现镜头卡 `counter-confetti` 的纸屑层：52 片真物理，从画面两侧抛物线炸入。
 *
 * Implements the confetti layer from `counter-confetti`: 52 pieces of real
 * parabolic physics, fired in from both sides of the frame.
 *
 * 卡上命门（已遵守）：
 *   - **抢拍**：纸屑必须早于计数到位（由调用方传入 `burstFrame`，
 *     要比计数终点早约 0.04 归一化时间）——「庆祝比结果先到半拍」是这张卡的灵魂
 *   - 重力/初速比 g ≈ 2.5×|vy|，决定抛物线顶点落在画面上 1/3 处
 *   - 自转 ±750°，每片错峰 ≤0.06
 *   - 尾段 opacity 从 ~1 衰减到 0.05，落定段需要干净背景
 *   - **确定性**：每片参数由 index 派生（禁 `Math.random()`）
 */

import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";

/** 8 色调色板：演出彩纸，一般不随品牌换色（卡上参数表）。
 * Stage confetti palette — deliberately not re-skinned per brand. */
const PAL = [
  "#FF6B6B", "#FFD93D", "#6BCB77", "#4D96FF",
  "#F473B9", "#FF9F45", "#9B8CFF", "#31D0AA",
];

const COUNT = 52;

interface Piece {
  /** 归一化起爆延迟（0–0.06）/ Normalised delay after the burst. */
  delay: number;
  /** 起始 x，相对画面宽的倍数（负=画面左侧外）/ Start x as a width multiple. */
  x0: number;
  vx: number;
  vy: number;
  g: number;
  rot0: number;
  spin: number;
  w: number;
  h: number;
  color: string;
}

/**
 * 由 index 派生确定性参数 / Deterministic per-index parameters.
 *
 * 用整数哈希而不是 PRNG 库：同一 index 永远得同一片，
 * 因此逐帧可复现、渲染间零抖动（开发守则 §4 的确定性要求）。
 */
const pieceAt = (i: number): Piece => {
  const h = (salt: number): number => {
    let x = (i * 2654435761 + salt * 40503) >>> 0;
    x ^= x >>> 13;
    x = (x * 1274126177) >>> 0;
    return ((x ^ (x >>> 16)) >>> 0) / 4294967296;
  };
  const side = i % 2 === 0 ? -1 : 1;
  return {
    delay: h(1) * 0.06,
    x0: side * (1.08 + h(2) * 0.16),
    vx: -side * (150 + h(3) * 300),
    vy: -(230 + h(4) * 220),
    g: 900 + h(5) * 520,
    rot0: h(6) * 360,
    spin: (h(7) - 0.5) * 750,
    w: 9 + h(8) * 7,
    h: 13 + h(9) * 9,
    color: PAL[i % PAL.length],
  };
};

const PIECES: Piece[] = Array.from({ length: COUNT }, (_, i) => pieceAt(i));

export interface ConfettiProps {
  /** 爆点帧（本镜内）/ Burst frame within this shot. */
  burstFrame: number;
  /** 纸屑存活时长（秒）/ Lifespan in seconds. */
  lifespanSeconds?: number;
}

export const Confetti: React.FC<ConfettiProps> = ({
  burstFrame,
  lifespanSeconds = 1.1,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  return (
    <AbsoluteFill style={{ pointerEvents: "none", overflow: "hidden" }}>
      {PIECES.map((p, i) => {
        const startFrame = burstFrame + p.delay * fps;
        const t = (frame - startFrame) / fps; // 秒
        if (t < 0) {
          return null;
        }

        // 物理：x 匀速、y 抛物（初速上抛 + 重力拉回）
        const x = p.x0 * width + p.vx * t;
        const y = 0.52 * height + p.vy * t + 0.5 * p.g * t * t;

        // 尾段衰减：后 26% 把不透明度压到 0.05，落定段需要干净背景
        const k = Math.min(1, t / lifespanSeconds);
        const opacity =
          k < 0.74 ? 1 : Math.max(0.05, 1 - ((k - 0.74) / 0.26) * 0.95);
        if (k >= 1) {
          return null;
        }

        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: 0,
              top: 0,
              width: p.w,
              height: p.h,
              backgroundColor: p.color,
              borderRadius: 2,
              opacity,
              transform: `translate(${x}px, ${y}px) rotate(${p.rot0 + p.spin * t}deg)`,
              willChange: "transform",
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};

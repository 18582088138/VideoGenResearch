/**
 * 分层架构堆叠 / Layer stack.
 *
 * 内容形态：**分层结构**（自下而上：硬件 → 驱动 → 框架 → 应用；
 * 或数据 → 模型 → 服务）。flow-diagram 讲的是"流向"，但分层讲的是"依赖"——
 * 自下而上堆叠本身就是语义，用横向流程画就把依赖关系画丢了。
 *
 * A layered architecture, stacked bottom-up. Dependency is the meaning here, so
 * it must stack vertically rather than read as a left-to-right flow.
 *
 * 动效：
 *   - `nodes[0]` 是**最底层**（Python 侧口径：nodes 从下到上），从下往上依次滑入
 *   - 用 `column-reverse` 让 DOM 顺序直接读作"底 → 顶"，不需要反转数组
 *   - 层用等宽横条 + 轻透视（容器 `perspective` + 层 `rotateX`）+ 阴影
 *   - `footer` 放在堆叠区**最底下**作注
 */

import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { FONT_FAMILY, ThemeTokens } from "../theme/theme";
import { Layout, tune } from "../theme/layout";
import type { ShotNode } from "../compositions/types";

export interface LayerStackProps {
  /** 标题 / Title. */
  title: string;
  /** 来源/角标 / Eyebrow above the title. */
  eyebrow?: string;
  /** 各层；**从下到上** / Layers, bottom-up. */
  nodes: ShotNode[];
  /** 底部注 / Footnote under the stack. */
  footer?: string;
  theme: ThemeTokens;
  layout: Layout;
  durationInFrames: number;
}

export const LayerStack: React.FC<LayerStackProps> = ({
  title,
  eyebrow,
  nodes,
  footer,
  theme,
  layout,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const n = Math.max(1, nodes.length);

  const titleIn = interpolate(frame, [0, 14], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  // 错峰：整段约 45% 时长用于"一层一层堆上去"
  const stagger = Math.max(7, Math.min(16, Math.floor((durationInFrames * 0.45) / n)));
  const layerStart = (i: number): number => 14 + i * stagger;

  const exit = interpolate(
    frame,
    [durationInFrames - 10, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const titleSize = tune(layout, "figureTitlePortrait", "figureTitleLandscape");
  const bodySize = tune(layout, "figureBodyPortrait", "figureBodyLandscape");
  const layerGap = layout.textZone.h * 0.018;
  const stackH = layout.textZone.h * 0.66;
  const layerH = Math.max(bodySize * 1.6, (stackH - layerGap * (n - 1)) / n);

  return (
    <AbsoluteFill style={{ fontFamily: FONT_FAMILY, opacity: exit }}>
      <div
        style={{
          position: "absolute",
          left: layout.textZone.x,
          top: layout.textZone.y,
          width: layout.textZone.w,
          height: layout.textZone.h,
          display: "flex",
          flexDirection: "column",
        }}
      >
        {eyebrow ? (
          <div
            style={{
              opacity: titleIn,
              fontFamily: "monospace",
              fontSize: bodySize * 0.68,
              letterSpacing: "0.22em",
              color: theme.primary,
              marginBottom: layout.textZone.h * 0.015,
            }}
          >
            {eyebrow}
          </div>
        ) : null}

        <div
          style={{
            opacity: titleIn,
            transform: `translateY(${(1 - titleIn) * 12}px)`,
            fontSize: titleSize,
            fontWeight: 700,
            color: theme.text,
            lineHeight: 1.3,
            marginBottom: layout.textZone.h * 0.04,
          }}
        >
          {title}
        </div>

        {/* 堆叠区：column-reverse ⇒ nodes[0] 落在最下面（layer-stack 的约定） */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column-reverse",
            justifyContent: "flex-start",
            gap: layerGap,
            perspective: layout.textZone.h * 3,
          }}
        >
          {nodes.map((node, i) => {
            const start = layerStart(i);
            const t = interpolate(frame, [start, start + 14], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.out(Easing.cubic),
            });
            // 从下方滑入：初始位置压在目标位之下，落定后归零
            const dy = (1 - t) * layerH * 0.55;
            return (
              <div
                key={`${node.label}-${i}`}
                style={{
                  height: layerH,
                  opacity: t,
                  transform: `translateY(${dy}px) scaleX(${0.95 + t * 0.05}) rotateX(7deg)`,
                  transformOrigin: "center bottom",
                  background: `linear-gradient(180deg, ${theme.surface2}, ${theme.surface})`,
                  border: `1px solid ${theme.border}`,
                  borderLeft: `3px solid ${i === n - 1 ? theme.primary : theme.accent}`,
                  borderRadius: 10,
                  boxShadow: "0 18px 46px rgba(0,0,0,0.55)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: layout.safeWidth * 0.02,
                  padding: `0 ${layout.safeWidth * 0.028}px`,
                }}
              >
                <div
                  style={{
                    fontSize: bodySize * 1.06,
                    fontWeight: 700,
                    color: i === n - 1 ? theme.primary : theme.text,
                    lineHeight: 1.3,
                    // 层是等宽横条，长标签允许收缩换行而不撑破条
                    minWidth: 0,
                  }}
                >
                  {node.label}
                </div>
                {node.sub ? (
                  <div
                    style={{
                      fontFamily: "monospace",
                      fontSize: bodySize * 0.72,
                      letterSpacing: "0.1em",
                      color: theme.accent,
                      opacity: interpolate(frame, [start + 8, start + 18], [0, 1], {
                        extrapolateLeft: "clamp",
                        extrapolateRight: "clamp",
                      }),
                      flexShrink: 0,
                    }}
                  >
                    {node.sub}
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>

        {footer ? (
          <div
            style={{
              marginTop: layout.textZone.h * 0.03,
              opacity: interpolate(
                frame,
                [layerStart(n - 1) + 18, layerStart(n - 1) + 32],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
              ),
              fontSize: bodySize * 0.86,
              color: theme.textMuted,
              lineHeight: 1.5,
              borderLeft: `3px solid ${theme.border}`,
              paddingLeft: layout.safeWidth * 0.016,
            }}
          >
            {footer}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

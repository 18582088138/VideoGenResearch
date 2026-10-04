/**
 * 流程图 / Flow diagram.
 *
 * 补强点：原文的核心贡献是「统一感知-运动框架」（视觉 25Hz → 策略 → 50Hz 控制），
 * 这是**结构关系**，原先只能靠旁白讲。本组件按论文自己的架构图画成数字流程图 ——
 * 节点逐个点亮、连线生长、频率徽章落定。
 *
 * Draws the paper's own architecture as a code-generated diagram: nodes light up
 * in order, connectors grow, frequency badges land. Structure carried visually.
 *
 * 动效（对应 video-shotcraft 的 `scanline-assemble-flyin` 与 `cycle-glass-node-morph`
 * 的运动语法，但按本项目调参）：
 *   - 节点：错峰 pop（scale 0.86→1，outBack 轻过冲）
 *   - 连线：从前一节点向右 draw-on（scaleX 0→1）
 *   - 徽章：在节点落定后淡入，带一次高亮脉冲
 */

import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { FONT_FAMILY, ThemeTokens } from "../theme/theme";
import { Layout } from "../theme/layout";

export interface FlowNode {
  /** 节点标题 / Node title. */
  label: string;
  /** 节点副标（如 "25 Hz"）/ Node subtitle, e.g. a frequency. */
  sub?: string;
}

export interface FlowDiagramProps {
  title: string;
  eyebrow?: string;
  /** 横向排列的节点 / Nodes laid out horizontally. */
  nodes: FlowNode[];
  /** 底部说明 / Caption under the diagram. */
  caption?: string;
  theme: ThemeTokens;
  layout: Layout;
  durationInFrames: number;
}

export const FlowDiagram: React.FC<FlowDiagramProps> = ({
  title,
  eyebrow,
  nodes,
  caption,
  theme,
  layout,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const portrait = layout.orientation === "portrait";
  const n = Math.max(1, nodes.length);

  const titleIn = interpolate(frame, [0, 14], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  // 节点错峰：整段预留约 45% 时长给"点亮"，其余留读图
  const STAGGER = Math.max(7, Math.floor((durationInFrames * 0.45) / n));
  const nodeStart = (i: number) => 18 + i * STAGGER;

  // 版式：竖屏纵向排（横向放不下 N 个节点），横屏一行横向排
  const gap = portrait ? 0 : 18;
  const nodeW = portrait
    ? layout.safeWidth
    : (layout.safeWidth - gap * (n - 1)) / n;

  const exit = interpolate(
    frame,
    [durationInFrames - 10, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const padV = portrait ? 20 : 18;

  // 内容块在 contentCenterY 上垂直居中（已扣掉字幕带）—— 治「头重脚轻」
  return (
    <AbsoluteFill style={{ fontFamily: FONT_FAMILY, opacity: exit }}>
      <div
        style={{
          position: "absolute",
          left: layout.safe.left,
          top: layout.contentCenterY,
          width: layout.safeWidth,
          transform: "translateY(-50%)",
        }}
      >
        {eyebrow ? (
          <div
            style={{
              opacity: titleIn,
              fontFamily: "monospace",
              fontSize: portrait ? 20 : 19,
              letterSpacing: "0.22em",
              color: theme.primary,
              marginBottom: 10,
            }}
          >
            {eyebrow}
          </div>
        ) : null}

        <div
          style={{
            opacity: titleIn,
            transform: `translateY(${(1 - titleIn) * 12}px)`,
            fontSize: portrait ? 42 : 42,
            fontWeight: 700,
            color: theme.text,
            lineHeight: 1.3,
            marginBottom: portrait ? 40 : 34,
          }}
        >
          {title}
        </div>

        {/* 节点序列：竖屏换成纵向，连线变成向下的箭头 */}
        <div
          style={{
            display: "flex",
            flexDirection: portrait ? "column" : "row",
            alignItems: portrait ? "stretch" : "center",
            gap: portrait ? 14 : gap,
          }}
        >
          {nodes.map((node, i) => {
            const start = nodeStart(i);
            const appear = interpolate(frame, [start, start + 12], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.out(Easing.back(1.5)),
            });
            const isLast = i === n - 1;
            const accent = isLast || i === 0;

            return (
              <React.Fragment key={`${node.label}-${i}`}>
                <div
                  style={{
                    width: nodeW,
                    opacity: Math.min(1, appear * 1.6),
                    transform: `scale(${0.86 + appear * 0.14})`,
                    background: theme.surface,
                    border: `1.5px solid ${accent ? theme.primary : theme.border}`,
                    borderRadius: 12,
                    padding: `${padV}px ${portrait ? 22 : 14}px`,
                    boxShadow: accent ? `0 0 0 1px ${theme.primary}22 inset` : undefined,
                    textAlign: "center",
                  }}
                >
                  <div
                    style={{
                      fontSize: portrait ? 30 : 26,
                      fontWeight: 700,
                      color: accent ? theme.primary : theme.text,
                      lineHeight: 1.35,
                    }}
                  >
                    {node.label}
                  </div>
                  {node.sub ? (
                    <div
                      style={{
                        marginTop: 8,
                        fontFamily: "monospace",
                        fontSize: portrait ? 20 : 18,
                        letterSpacing: "0.12em",
                        color: theme.accent,
                        // 徽章落定后脉冲一次 —— "这个频率是重点"
                        opacity: interpolate(
                          frame,
                          [start + 8, start + 16],
                          [0, 1],
                          { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
                        ),
                      }}
                    >
                      {node.sub}
                    </div>
                  ) : null}
                </div>

                {/* 连线：非末节点之后画一段向右/向下的箭头 */}
                {!isLast ? (
                  <div
                    style={
                      portrait
                        ? {
                            alignSelf: "center",
                            width: 2,
                            height: 26,
                            background: theme.border,
                            transformOrigin: "top center",
                            transform: `scaleY(${Math.max(
                              0,
                              interpolate(frame, [start + 10, start + 22], [0, 1], {
                                extrapolateLeft: "clamp",
                                extrapolateRight: "clamp",
                              }),
                            )})`,
                          }
                        : {
                            width: gap,
                            height: 2,
                            background: theme.border,
                            transformOrigin: "left center",
                            transform: `scaleX(${Math.max(
                              0,
                              interpolate(frame, [start + 10, start + 22], [0, 1], {
                                extrapolateLeft: "clamp",
                                extrapolateRight: "clamp",
                              }),
                            )})`,
                          }
                    }
                  />
                ) : null}
              </React.Fragment>
            );
          })}
        </div>

        {caption ? (
          <div
            style={{
              marginTop: portrait ? 34 : 30,
              opacity: interpolate(
                frame,
                [nodeStart(n - 1) + 20, nodeStart(n - 1) + 36],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
              ),
              fontSize: portrait ? 28 : 26,
              lineHeight: 1.5,
              color: theme.textMuted,
              borderLeft: `3px solid ${theme.border}`,
              paddingLeft: 16,
            }}
          >
            {caption}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

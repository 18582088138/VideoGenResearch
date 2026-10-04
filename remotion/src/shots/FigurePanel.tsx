/**
 * 图文说明面板 / Figure panel — 用代码画内容，而不是贴截图.
 *
 * 这是本次优化的核心补强之一。原先画面只能"放一张素材图 + 一行字"，
 * 导致 video-shotcraft 的动效与模板库几乎没被用上、画面信息密度极低。
 *
 * 本组件让画面承载**独立于旁白的视频内容文案**：标题、要点列表、
 * 关键词高亮，全部按节奏逐个进场 —— 动效本身就是信息载体。
 *
 * This is the main gap this round closes. Previously a shot could only show one
 * asset plus one line, so the shot-card motion library went mostly unused and
 * the frame carried almost no information. Now the frame carries its own
 * content script — title, bullets, highlighted keywords — animated in on beats.
 */

import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { FONT_FAMILY, ThemeTokens, tuneByOrientation } from "../theme/theme";
import { Layout } from "../theme/layout";

export interface FigurePanelProps {
  /** 面板标题 / Panel title. */
  title: string;
  /** 来源/角标 / Eyebrow above the title. */
  eyebrow?: string;
  /** 要点列表；`**词**` 标强调 / Bullets; `**word**` marks emphasis. */
  bullets: string[];
  /** 底部结论条 / Closing takeaway line. */
  footer?: string;
  theme: ThemeTokens;
  layout: Layout;
  durationInFrames: number;
}

/** 解析 `**强调**` / Parse `**emphasis**` markers. */
const parseEmphasis = (text: string): Array<{ t: string; accent: boolean }> => {
  const out: Array<{ t: string; accent: boolean }> = [];
  const re = /\*\*(.+?)\*\*/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push({ t: text.slice(last, m.index), accent: false });
    out.push({ t: m[1], accent: true });
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push({ t: text.slice(last), accent: false });
  return out.length ? out : [{ t: text, accent: false }];
};

export const FigurePanel: React.FC<FigurePanelProps> = ({
  title,
  eyebrow,
  bullets,
  footer,
  theme,
  layout,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const portrait = layout.orientation === "portrait";

  // 节奏：标题 0–14f，要点每条错峰 10f，结论条最后
  const titleIn = interpolate(frame, [0, 14], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const bulletStart = 16;
  const stagger = Math.min(12, Math.max(6, Math.floor(120 / Math.max(bullets.length, 1))));

  const exit = interpolate(
    frame,
    [durationInFrames - 10, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const pad = portrait ? 34 : 30;
  const titleSize = tuneByOrientation(portrait, "figureTitlePortrait", "figureTitleLandscape");
  const bulletSize = tuneByOrientation(portrait, "figureBodyPortrait", "figureBodyLandscape");
  const eyebrowSize = portrait ? 20 : 19;

  // 内容块整体在 `contentCenterY` 上**垂直居中**（已扣掉字幕带）。
  // 用 translateY(-50%) 让高度自适应：要点多/少都不会顶到底或悬空。
  return (
    <AbsoluteFill style={{ fontFamily: FONT_FAMILY, opacity: exit }}>
      <div
        style={{
          position: "absolute",
          left: layout.safe.left,
          top: layout.contentCenterY,
          width: layout.safeWidth,
          transform: "translateY(-50%)",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {eyebrow ? (
          <div
            style={{
              opacity: titleIn,
              fontFamily: "monospace",
              fontSize: eyebrowSize,
              letterSpacing: "0.22em",
              color: theme.primary,
              marginBottom: 12,
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
            letterSpacing: "0.01em",
            marginBottom: portrait ? 34 : 28,
          }}
        >
          {title}
        </div>

        {/* 要点卡片：逐条从左侧滑入，带强调色竖条 —— 动效即节拍 */}
        <div style={{ display: "flex", flexDirection: "column", gap: portrait ? 18 : 16 }}>
          {bullets.map((b, i) => {
            const start = bulletStart + i * stagger;
            const a = interpolate(frame, [start, start + 12], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.out(Easing.cubic),
            });
            const dx = interpolate(frame, [start, start + 12], [-26, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.out(Easing.cubic),
            });
            return (
              <div
                key={i}
                style={{
                  opacity: a,
                  transform: `translateX(${dx}px)`,
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 16,
                  background: "rgba(11,20,24,0.72)",
                  border: `1px solid ${theme.border}`,
                  borderLeft: `3px solid ${theme.primary}`,
                  borderRadius: 10,
                  padding: `${pad * 0.42}px ${pad * 0.55}px`,
                }}
              >
                <div
                  style={{
                    fontSize: bulletSize,
                    lineHeight: 1.45,
                    color: theme.text,
                    fontWeight: 500,
                  }}
                >
                  {parseEmphasis(b).map((seg, j) => (
                    <span
                      key={j}
                      style={
                        seg.accent
                          ? { color: theme.accent, fontWeight: 800 }
                          : undefined
                      }
                    >
                      {seg.t}
                    </span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        {footer ? (
          <div
            style={{
              marginTop: portrait ? 30 : 24,
              opacity: interpolate(
                frame,
                [bulletStart + bullets.length * stagger + 8,
                 bulletStart + bullets.length * stagger + 24],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
              ),
              fontSize: portrait ? 30 : 28,
              fontWeight: 700,
              color: theme.primary,
              letterSpacing: "0.02em",
            }}
          >
            {footer}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

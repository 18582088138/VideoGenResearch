/**
 * 关键词高亮 / Keyword highlight — 长句里逐个点亮关键词.
 *
 * 内容形态：一句**必须完整读出**的长句，重点只在句中几个词上
 * （"这套框架把感知、决策、控制统一到同一时间基准上"）。拆成要点就丢了
 * 句子本身的逻辑，所以句子必须整句在场，靠高亮引导注意力。
 *
 * A long sentence that must be read whole, where only a few words carry the
 * point. Breaking it into bullets would lose the sentence's logic.
 *
 * 动效：
 *   - `text` 整句先淡入
 *   - `bullets` 里的关键词**依次**被高亮色块扫过（`background-size` 宽度 0→100%，窄到宽展开）
 *   - 每次扫过附一次轻微发光（textShadow 随扫过强度增强）
 *
 * 稳健性（硬要求）：**关键词在句内匹配不到就跳过该词，不抛错**——
 * LLM 给的词与 `text` 不完全一致是常态（多字、少字、标点差异），
 * 视图层必须容错，绝不能因为一个词对不上就让整片渲染失败。
 */

import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { FONT_FAMILY, ThemeTokens } from "../theme/theme";
import { Layout, tune } from "../theme/layout";

export interface KeywordHighlightProps {
  /** 整句文案 / The full sentence. */
  text: string;
  /** 要突出的关键词（句内匹配不到的会被跳过）/ Keywords; unmatched ones are skipped. */
  bullets: string[];
  /** 句子下方的补充说明 / Note under the sentence. */
  subtext?: string;
  /** 来源/角标 / Eyebrow above the sentence. */
  eyebrow?: string;
  theme: ThemeTokens;
  layout: Layout;
  durationInFrames: number;
}

/** 句子被切成的片段：命中的关键词带 `hit` 序号（决定点亮顺序）。 */
interface Piece {
  t: string;
  hit: number | null;
}

/**
 * 按关键词把整句切开 / Split the sentence around its keywords.
 *
 * 每个词独立在整句里查找（不依赖词的给出顺序），再按出现位置排序并去重叠。
 * 找不到的词直接丢弃 —— 跳过而不是抛错。
 */
const splitByKeywords = (text: string, keywords: string[]): Piece[] => {
  const hits = keywords
    .map((raw) => {
      const word = raw.trim();
      if (!word) return null;
      const at = text.indexOf(word);
      return at < 0 ? null : { start: at, end: at + word.length };
    })
    .filter((h): h is { start: number; end: number } => h !== null)
    .sort((a, b) => a.start - b.start || b.end - a.end);

  // 去重叠：保留先出现的那一个（长词优先，因为同起点时长词 end 更大）
  const kept: Array<{ start: number; end: number }> = [];
  for (const h of hits) {
    const last = kept[kept.length - 1];
    if (last && h.start < last.end) continue;
    kept.push(h);
  }

  const pieces: Piece[] = [];
  let cursor = 0;
  kept.forEach((h, hit) => {
    if (h.start > cursor) pieces.push({ t: text.slice(cursor, h.start), hit: null });
    pieces.push({ t: text.slice(h.start, h.end), hit });
    cursor = h.end;
  });
  if (cursor < text.length) pieces.push({ t: text.slice(cursor), hit: null });
  return pieces.length ? pieces : [{ t: text, hit: null }];
};

export const KeywordHighlight: React.FC<KeywordHighlightProps> = ({
  text,
  bullets,
  subtext,
  eyebrow,
  theme,
  layout,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();

  const pieces = splitByKeywords(text, bullets);
  const hitCount = pieces.reduce((acc, p) => (p.hit === null ? acc : acc + 1), 0);

  // 整句先淡入，再开始逐个扫词
  const sentenceIn = interpolate(frame, [0, 14], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  const HIT_FROM = 20;
  const HIT_STAGGER = 14;
  const HIT_SPAN = 16;
  const tail = HIT_FROM + Math.max(1, hitCount) * HIT_STAGGER + HIT_SPAN;

  const exit = interpolate(
    frame,
    [durationInFrames - 10, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const sentenceSize = tune(layout, "figureTitlePortrait", "figureTitleLandscape") * 0.98;
  const bodySize = tune(layout, "figureBodyPortrait", "figureBodyLandscape");

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
          justifyContent: "center",
        }}
      >
        {eyebrow ? (
          <div
            style={{
              opacity: sentenceIn,
              fontFamily: "monospace",
              fontSize: bodySize * 0.68,
              letterSpacing: "0.22em",
              color: theme.primary,
              marginBottom: layout.textZone.h * 0.03,
            }}
          >
            {eyebrow}
          </div>
        ) : null}

        <div
          style={{
            opacity: sentenceIn,
            transform: `translateY(${(1 - sentenceIn) * 14}px)`,
            fontSize: sentenceSize,
            fontWeight: 700,
            color: theme.text,
            lineHeight: 1.62,
            letterSpacing: "0.01em",
          }}
        >
          {pieces.map((p, i) => {
            if (p.hit === null) {
              return <span key={i}>{p.t}</span>;
            }
            const start = HIT_FROM + p.hit * HIT_STAGGER;
            // 色块由窄到宽展开（background-size 宽度）—— 读作"被扫过"
            const grow = Math.max(
              0,
              interpolate(frame, [start, start + HIT_SPAN], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
                easing: Easing.out(Easing.cubic),
              }),
            );
            return (
              <span
                key={i}
                style={{
                  backgroundImage: `linear-gradient(90deg, ${theme.primary}55, ${theme.accent}3d)`,
                  backgroundRepeat: "no-repeat",
                  backgroundSize: `${grow * 100}% 78%`,
                  backgroundPosition: "0% 66%",
                  // 跨行时让色块在每个行片段上完整重绘，而不是被截断
                  WebkitBoxDecorationBreak: "clone",
                  textShadow: grow > 0.05 ? `0 0 ${grow * 16}px ${theme.accent}55` : undefined,
                }}
              >
                {p.t}
              </span>
            );
          })}
        </div>

        {subtext ? (
          <div
            style={{
              marginTop: layout.textZone.h * 0.04,
              opacity: interpolate(frame, [tail + 4, tail + 20], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }),
              fontSize: bodySize,
              color: theme.textMuted,
              lineHeight: 1.5,
              borderLeft: `3px solid ${theme.border}`,
              paddingLeft: layout.safeWidth * 0.016,
            }}
          >
            {subtext}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

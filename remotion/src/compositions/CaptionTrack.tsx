/**
 * 字幕轨道 / Caption track.
 *
 * 把 SRT 的每条字幕渲染成独立的 `<Sequence>`，从而不必在单个组件里
 * 手算绝对帧号 —— 段内帧号由 Sequence 自动归零。
 *
 * Renders each SRT cue as its own `<Sequence>`, so frame numbers reset per cue
 * and no absolute-frame bookkeeping is needed inside `Caption`.
 *
 * SRT 在**渲染期**用 fetch 读取（`staticFile` 提供 URL）。Remotion 的
 * `delayRender` 由 `@remotion/captions` 或自定义实现负责；这里用最省依赖的做法：
 * `useDelayRender` 风格的手工 await。
 */

import React, { useEffect, useState } from "react";
import { Sequence, delayRender, continueRender } from "remotion";
import { audioUrl } from "../theme/assetPath";
import { Caption } from "../theme/Caption";
import { Layout } from "../theme/layout";
import { ThemeTokens } from "../theme/theme";

export interface Cue {
  start: number; // 秒 / seconds
  end: number; // 秒 / seconds
  text: string;
}

/**
 * 解析 SRT 文本 / Parse SRT text.
 *
 * 与 Python 侧 `videogen.timeline.parse_srt` **行为对齐**：按时间码行切块，
 * 容忍 BOM / CRLF / 点号毫秒 / 缺序号。两边不一致会导致字幕与画面错位。
 *
 * Behaviourally mirrors the Python parser; any divergence would desync captions.
 */
export const parseSrt = (text: string): Cue[] => {
  const norm = text
    .replace(/^\uFEFF/, "")
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n");
  const lines = norm.split("\n");
  const timeRe =
    /(\d{1,2}):(\d{2}):(\d{2})[.,](\d{1,3})\s*-->\s*(\d{1,2}):(\d{2}):(\d{2})[.,](\d{1,3})/;

  const toSec = (h: string, m: string, s: string, ms: string) =>
    Number(h) * 3600 + Number(m) * 60 + Number(s) + Number(ms.padEnd(3, "0")) / 1000;

  const cues: Cue[] = [];
  let i = 0;
  while (i < lines.length) {
    const m = timeRe.exec(lines[i]);
    if (!m) {
      i += 1;
      continue;
    }
    const start = toSec(m[1], m[2], m[3], m[4]);
    const end = toSec(m[5], m[6], m[7], m[8]);
    i += 1;
    const textLines: string[] = [];
    while (i < lines.length && lines[i].trim() && !timeRe.test(lines[i])) {
      textLines.push(lines[i].trim());
      i += 1;
    }
    while (i < lines.length && !lines[i].trim()) {
      i += 1;
    }
    cues.push({ start, end, text: textLines.join(" ") });
  }
  return cues;
};

/** 读取并解析 SRT（渲染期）/ Fetch and parse an SRT at render time. */
export const useCues = (srtPath: string): Cue[] | null => {
  const [cues, setCues] = useState<Cue[] | null>(null);

  useEffect(() => {
    const handle = delayRender(`读取字幕 / fetching subtitles: ${srtPath}`);
    fetch(audioUrl(srtPath))
      .then((r) => r.text())
      .then((t) => {
        setCues(parseSrt(t));
        continueRender(handle);
      })
      .catch((err) => {
        continueRender(handle);
        throw err;
      });
  }, [srtPath]);

  return cues;
};

export interface CaptionTrackProps {
  cues: Cue[];
  theme: ThemeTokens;
  layout: Layout;
  fps: number;
  /**
   * 要**跳过**的帧区间 / Frame ranges to skip.
   *
   * 收尾镜要求画面干净（旁白此时就是 CTA，与 lockup 重复），
   * 所以它的帧区间要排除在字幕轨之外。
   */
  excludeRanges?: Array<[number, number]>;
}

/** 把每条字幕铺到时间轴上 / Lay every cue onto the timeline. */
export const CaptionTrack: React.FC<CaptionTrackProps> = ({
  cues,
  theme,
  layout,
  fps,
  excludeRanges = [],
}) => (
  <>
    {cues.map((cue, idx) => {
      const from = Math.round(cue.start * fps);
      const to = Math.round(cue.end * fps);

      // 整条落在排除区间内 → 不铺（收尾镜的干净画面）
      const skipped = excludeRanges.some(([a, b]) => from >= a && to <= b);
      if (skipped) {
        return null;
      }

      return (
        <Sequence key={idx} from={from} durationInFrames={Math.max(1, to - from)}>
          <Caption
            text={cue.text}
            from={0}
            to={to - from}
            theme={theme}
            layout={layout}
          />
        </Sequence>
      );
    })}
  </>
);

/**
 * 成片公共骨架 / Shared film shell.
 *
 * 两个成片（短视频 / 中视频）唯一的差别是**默认分镜**与时长；
 * 结构完全相同，所以抽到这里，避免两份几乎一样的组件各自漂移。
 *
 * Short and mid films differ only in default storyboard and length; the shell is
 * shared so the two don't drift apart.
 */

import React from "react";
import { Audio, Sequence, useVideoConfig } from "remotion";
import { audioUrl } from "../theme/assetPath";
import { ShotScaffold } from "../theme/ShotScaffold";
import { Layout } from "../theme/layout";
import { ThemeTokens } from "../theme/theme";
import { CaptionTrack, useCues } from "./CaptionTrack";
import { ShotRenderer } from "../shots/ShotRenderer";
import type { FilmProps, ShotSpec } from "./types";

export interface FilmShellProps extends FilmProps {
  /** 当 props.shots 为空时使用的内置分镜 / Built-in storyboard when shots is empty. */
  defaultShots: ShotSpec[];
}

/**
 * 收尾镜占据的帧区间 / Frame ranges occupied by outro shots.
 *
 * 收尾镜要求画面干净（不铺字幕带）—— 旁白此时**就是** CTA，
 * 与 lockup 的字标+标语重复，两处一起显示既冗余又互相压。
 * 这是镜头卡的明确要求（aesthetic-rules C1：「品牌收尾镜头除外，保持干净」）。
 *
 * The outro shot renders no subtitle band: the narration there *is* the CTA, so
 * it duplicates the lockup text and tagline.
 */
const outroRanges = (plan: ShotSpec[]): Array<[number, number]> =>
  plan
    .filter((s) => s.type === "outro-lockup")
    .map((s) => [s.from, s.from + s.durationInFrames] as [number, number]);

const FilmBody: React.FC<
  FilmShellProps & { theme: ThemeTokens; layout: Layout }
> = ({ srtPath, audioPath, source, shots, defaultShots, theme, layout }) => {
  const { fps, durationInFrames } = useVideoConfig();
  const cues = useCues(srtPath);

  // props 带分镜时以 props 为准（Python 侧 spec 是权威），
  // 否则用组件内置分镜 —— 这样 Studio 里不传 props 也能直接预览。
  // Props-driven when present (the Python spec is authoritative); otherwise the
  // built-in storyboard, so Studio preview works with no props at all.
  const plan = shots && shots.length > 0 ? shots : defaultShots;

  return (
    <>
      {/* 配音：整轨播完即可，不做裁剪 —— 时长已由 Composition 锁定 */}
      <Audio src={audioUrl(audioPath)} />

      {plan.map((shot, idx) => (
        <Sequence
          key={`${shot.type}-${idx}`}
          from={shot.from}
          durationInFrames={shot.durationInFrames}
        >
          <ShotRenderer shot={shot} theme={theme} layout={layout} />
        </Sequence>
      ))}

      {/* 字幕最后叠加，保证压在画面之上。
          **收尾镜不铺字幕**：旁白此时就是 CTA 本身，与 lockup 的字标+标语重复，
          两处一起显示既冗余又互相压。这是镜头卡的明确要求
          （aesthetic-rules C1：「品牌收尾镜头除外，保持干净」）。
          The outro shot renders no subtitle band: the narration there *is* the
          CTA, so it duplicates the lockup text and tagline. */}
      {cues ? (
        <CaptionTrack
          cues={cues}
          theme={theme}
          layout={layout}
          fps={fps}
          excludeRanges={outroRanges(plan)}
        />
      ) : null}

      {/* 右上角常驻来源标注：低存在感，但满足「注明出处」的要求。
          **必须来自 props** —— 写死会在换一篇文章后继续显示上一家的来源，
          这是实测发现的兼容性缺陷（见 docs/issues/006）。
          The source label must come from props; hard-coding it kept showing the
          previous article's attribution after switching materials. */}
      {source ? (
        <div
          style={{
            position: "absolute",
            right: layout.safe.right,
            top: layout.safe.top * 0.6,
            maxWidth: layout.safeWidth * 0.6,
            textAlign: "right",
            fontSize: layout.orientation === "portrait" ? 22 : 20,
            letterSpacing: "0.1em",
            color: theme.textMuted,
            fontFamily: "monospace",
          }}
        >
          {source}
        </div>
      ) : null}
      <span style={{ display: "none" }}>{durationInFrames}</span>
    </>
  );
};

export const FilmShell: React.FC<FilmShellProps> = (props) => (
  <ShotScaffold themeId={props.themeId}>
    {({ theme, layout }) => (
      <FilmBody {...props} theme={theme} layout={layout} />
    )}
  </ShotScaffold>
);

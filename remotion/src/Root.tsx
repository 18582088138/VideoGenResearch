/**
 * Composition 注册表 / Composition registry.
 *
 * 四个 Composition = 2 种视频 × 2 个方向。横竖屏**各自一套尺寸**，
 * 不做等比缩放（`--scale` 无法把 16:9 变成 9:16，见 docs/plan/00_dev_plan.md D14）。
 *
 * Four compositions = 2 video kinds × 2 orientations, each with its own
 * dimensions. No uniform scaling: `--scale` cannot turn 16:9 into 9:16.
 *
 * 帧数已按实测音频锁定（30fps）：
 *   短视频 49.66s → 1490 帧；中视频 155.48s → 4665 帧。
 * 这两个数字会随 props 里的 durationInFrames 覆盖（见 calculateMetadata）。
 */

import React from "react";
import { Composition } from "remotion";
import type { AnyZodObject, CalculateMetadataFunction } from "remotion";
import { ShortFilm } from "./compositions/ShortFilm";
import { MidFilm } from "./compositions/MidFilm";
import type { FilmProps } from "./compositions/types";
/** 长短视频的实测基准帧数（音频时长 × 30fps，向上取整）。 */
export const SHORT_FRAMES = 1490;
export const MID_FRAMES = 4665;

/** 横竖屏尺寸 / Landscape and portrait dimensions. */
export const SIZES = {
  landscape: { width: 1920, height: 1080 },
  portrait: { width: 1080, height: 1920 },
} as const;

/** 每个 Composition 的默认 props —— 保证「什么都不传」也能渲出成片。 */
const baseProps = (kind: "short" | "mid"): FilmProps => ({  kind,
  themeId: "cyan-noir",
  // **短视频用 ASR 重切后的字幕**，不用素材自带的 srt：
  // 原 srt 按长句切（单条最长约 10s），既拖慢节奏又对不上画面。
  // ASR 版按停顿切分，单条约 2.2s / 14 字（见 docs/guides/02_video_tuning.md §7）。
  // 中视频本轮暂不优化，仍用原 srt。
  //
  // Short video uses the ASR re-segmented subtitles; the original was cut by long
  // sentences (up to ~10 s per cue), which dragged the pacing. The mid video keeps
  // its original SRT because optimisation is paused for it this round.
  srtPath: kind === "short" ? "short.asr.srt" : "narration.zh.srt",
  audioPath: kind === "short" ? "shortvideo.zh.wav" : "narration.zh.wav",
  title: "清华团队登 Science Robotics",
  subtitle:
    kind === "short"
      ? "人形机器人视觉足球技能，误差降 46%"
      : "视觉驱动人形机器人足球，误差降 46%",
  // 空数组 = 用主题内置的默认分镜，便于在 Studio 里先看效果
  shots: [],
});

/**
 * 通用成片组件：按 ``kind`` 选内置分镜。
 *
 * Generic film component; picks the built-in storyboard by ``kind``. Props 里的
 * ``shots`` 非空时优先用它们（见 FilmShell）。
 */
const SetFilm: React.FC<FilmProps> = (props) =>
  props.kind === "mid" ? <MidFilm {...props} /> : <ShortFilm {...props} />;

/**
 * 从 props 推导时长与帧率 / Derive duration and fps from props.
 *
 * 为什么必须这么做：Composition 上写死的 ``durationInFrames`` 只对
 * **本项目最早两套素材**成立。换一篇文章音频长度就变了 —— 帧数写小了片尾
 * 被截断、写大了尾部黑屏。改从 props 读，一个 id 就能服务任意素材集。
 *
 * Hard-coded frame counts only hold for this project's first two asset sets; any
 * other article changes the audio length, truncating the tail or leaving it black.
 * Reading them from props lets one composition id serve every asset set.
 */
const fromProps: CalculateMetadataFunction<FilmProps> = ({ props }) => {
  const duration = Number((props as { durationInFrames?: number }).durationInFrames);
  const fps = Number((props as { fps?: number }).fps);
  return {
    durationInFrames: Number.isFinite(duration) && duration > 0 ? duration : SHORT_FRAMES,
    fps: Number.isFinite(fps) && fps > 0 ? fps : 30,
  };
};

export const RemotionRoot: React.FC = () => (  <>
    <Composition<AnyZodObject, FilmProps>
      id="ShortLandscape"
      component={ShortFilm}
      fps={30}
      durationInFrames={SHORT_FRAMES}
      width={SIZES.landscape.width}
      height={SIZES.landscape.height}
      defaultProps={baseProps("short")}
    />
    <Composition<AnyZodObject, FilmProps>
      id="ShortPortrait"
      component={ShortFilm}
      fps={30}
      durationInFrames={SHORT_FRAMES}
      width={SIZES.portrait.width}
      height={SIZES.portrait.height}
      defaultProps={baseProps("short")}
    />
    <Composition<AnyZodObject, FilmProps>
      id="MidLandscape"
      component={MidFilm}
      fps={30}
      durationInFrames={MID_FRAMES}
      width={SIZES.landscape.width}
      height={SIZES.landscape.height}
      defaultProps={baseProps("mid")}
    />
    <Composition<AnyZodObject, FilmProps>
      id="MidPortrait"
      component={MidFilm}
      fps={30}
      durationInFrames={MID_FRAMES}
      width={SIZES.portrait.width}
      height={SIZES.portrait.height}
      defaultProps={baseProps("mid")}
    />

    {/*
      ── 通用 Composition：一个 id 吃任意素材 / Generic compositions ──
      上面的 4 个 id 把「时长」写死成了本项目最早两套素材的帧数。
      换一篇文章音频长度就变了，写死的帧数会把片尾截断。

      这两个 id 通过 calculateMetadata 从 props 读时长与帧率，
      所以 `--props <任意素材集导出的 props.json>` 就能直接渲染，
      不必为每篇文章新增 Composition —— 这是脚本化量产的关键。

      The four ids above hard-code the frame count of this project's first two
      asset sets. These two read fps/duration from props via calculateMetadata,
      so any asset set's compiled props render without registering a new id.
    */}
    <Composition<AnyZodObject, FilmProps>
      id="SetLandscape"
      component={SetFilm}
      fps={30}
      durationInFrames={SHORT_FRAMES}
      width={SIZES.landscape.width}
      height={SIZES.landscape.height}
      defaultProps={baseProps("short")}
      calculateMetadata={fromProps}
    />
    <Composition<AnyZodObject, FilmProps>
      id="SetPortrait"
      component={SetFilm}
      fps={30}
      durationInFrames={SHORT_FRAMES}
      width={SIZES.portrait.width}
      height={SIZES.portrait.height}
      defaultProps={baseProps("short")}
      calculateMetadata={fromProps}
    />
  </>
);

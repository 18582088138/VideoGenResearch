/**
 * 中视频成片 / Mid film composition.
 *
 * 内置分镜与 docs/design/02_storyboard.md §2 一一对应（10 镜 / 4665 帧 @30fps）。
 *
 * The built-in storyboard mirrors docs/design/02_storyboard.md §2
 * (10 shots / 4665 frames @30fps).
 */

import React from "react";
import { FilmShell } from "./FilmShell";
import type { FilmProps, ShotSpec } from "./types";

/** 10 镜默认分镜 / Default ten-shot storyboard. */
export const MID_SHOTS: ShotSpec[] = [
  {
    type: "title-reveal",
    from: 0,
    durationInFrames: 126, // 0.00–4.20s
    text: "清华团队登 Science Robotics",
    subtext: "视觉驱动人形机器人足球 · 误差降 46%",
  },
  {
    type: "page-spotlight",
    from: 126,
    durationInFrames: 608, // 4.20–24.47s
    text: "清华大学 × 字节跳动 Seed × 中国农业大学",
    image: "04_mmbiz-qpic-cn.png",
    source: "Science Robotics · November 7, 2025",
  },
  {
    type: "scan-annotate",
    from: 734,
    durationInFrames: 523, // 24.47–41.90s
    text: "视觉 25Hz 感知 · 控制器 50Hz 输出",
    subtext: "视觉平均延迟约 116 毫秒",
    image: "05_mmbiz-qpic-cn.png",
    targets: [
      { x: 0.32, y: 0.1, w: 0.2, h: 0.34, label: "POLICY · 策略网络", side: "right" },
      { x: 0.06, y: 0.04, w: 0.3, h: 0.26, label: "BEV PROJECTION", side: "right" },
    ],
  },
  {
    type: "number-roll",
    from: 1257,
    durationInFrames: 534, // 41.90–59.71s
    text: "过去 50 帧观测压缩为 64 维隐藏状态",
    metrics: [
      { label: "观测窗口", value: "50 帧" },
      { label: "隐藏状态", value: "64 维" },
      { label: "训练方式", value: "端到端" },
    ],
  },
  {
    type: "slow-push",
    from: 1791,
    durationInFrames: 527, // 59.71–77.27s
    text: "对抗运动先验 AMP：76 秒全向行走 + 30 秒脚弓射门，让动作像人",
    image: "06_mmbiz-qpic-cn.png",
  },
  {
    type: "counter-burst",
    from: 2318,
    durationInFrames: 407, // 77.27–90.82s
    text: "射门前一秒足球位置误差降幅",
    subtext: "0.344 米 → 0.186 米",
    metrics: [{ label: "误差降幅", value: "46%" }],
  },
  {
    type: "before-after",
    from: 2725,
    durationInFrames: 593, // 90.82–110.60s
    text: "静止球启动到触球",
    subtext: "学习策略 1.5 秒 · 规则系统 2–5 秒",
    metrics: [{ label: "最高降幅", value: "64%" }],
    image: "07_mmbiz-qpic-cn.png",
  },
  {
    type: "scan-annotate",
    from: 3318,
    durationInFrames: 224, // 110.60–118.06s
    text: "代价：依赖稳定本体、控制周期与板载算力",
    image: "08_mmbiz-qpic-cn.png",
    targets: [{ x: 0.53, y: 0.36, w: 0.34, h: 0.23, label: "ERROR GROWTH", side: "right" }],
  },
  {
    type: "timeline-travel",
    from: 3542,
    durationInFrames: 419, // 118.06–132.04s
    text: "两项赛事累计进 76 球 · 失 11 球",
    stops: [
      { label: "2025", note: "RoboCup 成人组人形联赛冠军" },
      { label: "2025", note: "世界人形机器人运动会冠军" },
      { label: "2026", note: "RoboCup Large Size 卫冕" },
    ],
  },
  {
    type: "number-roll",
    from: 3961,
    durationInFrames: 704, // 132.04–155.48s
    text: "Booster T2 专业版搭载 NVIDIA Thor",
    metrics: [
      { label: "端侧算力", value: "2070 TFLOPS" },
      { label: "协同机队", value: "80 台" },
      { label: "总算力", value: "17 万 TFLOPS" },
    ],
  },
];

export const MidFilm: React.FC<FilmProps> = (props) => (
  <FilmShell {...props} defaultShots={MID_SHOTS} />
);

/**
 * 短视频成片 / Short film composition.
 *
 * 内置分镜与 docs/design/02_storyboard.md §1 对应（**v3 优化版**）。
 *
 * v3 相对 v1/v2 的改变（对应用户本轮反馈）：
 *   1. **单镜 ≤5s**（150 帧 @30fps）。v1/v2 有 10+ 秒的长镜，节奏明显拖沓。
 *      总时长由音频锁定，所以只能靠**增加镜数**消化 —— 6 镜 → 12 镜。
 *   2. **画面承载独立的内容文案**，不再搬运旁白：引入 `flow-diagram` /
 *      `stat-compare` / `figure-panel` 三类图文镜头，动效成为信息载体。
 *   3. **真正的片头与片尾**：v1 没有片头、片尾只有一行字。
 *
 * The v3 storyboard holds every shot to the 5-second ceiling, carries its own
 * content script instead of restating the narration, and has a real opening and
 * closing. Total duration is pinned by the audio, so pacing is bought with more
 * shots: 6 → 12.
 */

import React from "react";
import { FilmShell } from "./FilmShell";
import type { FilmProps, ShotSpec } from "./types";

/** 12 镜分镜 / Twelve-shot storyboard. 合计 1490 帧（49.66s @30fps）。 */
export const SHORT_SHOTS: ShotSpec[] = [
  {
    // ① 片头：eyebrow + 主标 + 副标
    type: "title-reveal",
    from: 0,
    durationInFrames: 114, // 3.80s
    eyebrow: "SCIENCE ROBOTICS · 2026",
    text: "清华团队登 Science Robotics",
    subtext: "视觉驱动人形机器人足球 · 误差降 46%",
  },
  {
    // ② 权威锚点：期刊页面聚光
    type: "page-spotlight",
    from: 114,
    durationInFrames: 120, // 4.00s
    text: "人形机器人特刊全球仅收录三家",
    image: "01_mmbiz-qpic-cn.jpg",
    source: "Science Robotics · RESEARCH",
  },
  {
    // ③ 论文是谁做的（三家单位署名，用图文卡讲关系而非念名字）
    type: "figure-panel",
    from: 234,
    durationInFrames: 132, // 4.40s
    eyebrow: "AUTHORS & AFFILIATIONS",
    text: "三家单位联合署名",
    bullets: [
      "清华大学自动化系 **赵明国**团队",
      "字节跳动 **Seed**",
      "中国农业大学",
    ],
    footer: "真机平台：加速进化人形机器人",
  },
  {
    // ④ 结构①：把感知与控制放进同一目标
    type: "flow-diagram",
    from: 366,
    durationInFrames: 126, // 4.20s
    eyebrow: "UNIFIED OBJECTIVE",
    text: "感知与控制，同一个优化目标",
    nodes: [{ label: "视觉感知" }, { label: "运动控制" }],
    footer: "不再拆成视觉 / 决策 / 控制三个串联模块，端到端一次训练",
  },
  {
    // ⑤ 结构②：观测压缩链路（论文最核心的一段机制）
    type: "flow-diagram",
    from: 492,
    durationInFrames: 132, // 4.40s
    eyebrow: "OBSERVATION → ACTION",
    text: "一秒观测，压成 64 维",
    nodes: [
      { label: "历史观测", sub: "50 帧 ≈ 1s" },
      { label: "隐藏状态", sub: "64 维" },
      { label: "关节指令", sub: "50 Hz" },
    ],
    footer: "解码器只在训练期存在，部署时移除，推理不带额外开销",
  },
  {
    // ⑥ 机制：虚拟感知系统先量噪声
    type: "figure-panel",
    from: 624,
    durationInFrames: 138, // 4.60s
    eyebrow: "VIRTUAL PERCEPTION",
    text: "先在仿真里把视觉弄脏",
    bullets: [
      "真机多距离多视角观察足球，采集约 **1 小时**数据",
      "与动捕对照，量出噪声、检测成功率、频率与延迟",
      "视觉 **25 Hz** 更新，平均延迟 **116 毫秒**",
    ],
    footer: "仿真里的视觉必须像真的，策略才不会一上真机就废",
  },
  {
    // ⑦ 效果对比：误差 0.344 → 0.186（条长直接看出差值）
    type: "stat-compare",
    from: 762,
    durationInFrames: 132, // 4.40s
    eyebrow: "STATE ESTIMATION",
    text: "射门前一秒的足球位置误差",
    metric: "原始视觉 vs 状态估计后 / 米",
    sides: [
      { label: "原始视觉", value: 0.344, display: "0.344 m" },
      { label: "状态估计后", value: 0.186, display: "0.186 m", better: true },
    ],
    footer: "降幅约 46%",
  },
  {
    // ⑧ 鲁棒性：视觉中断仍能踢（原文最亮的一个数字）
    type: "figure-panel",
    from: 894,
    durationInFrames: 126, // 4.20s
    eyebrow: "ROBUSTNESS",
    text: "视觉被遮住，它还能踢",
    bullets: [
      "仿真中视觉中断 **0.3 秒**，触球成功率仍 **>90%**",
      "进球率 **>50%**，球速低于 0.5 m/s 时成功率仍过半",
      "真机前场成功率 **80–90%**，后场 **60–70%**，全程无摔倒",
    ],
  },
  {
    // ⑨ 高潮：雷达图（素材自身把"学习策略包住规则系统"画出来了）
    type: "radar-reveal",
    from: 1020,
    durationInFrames: 132, // 4.40s
    text: "学习策略全面包住规则系统",
    subtext: "启动到触球 1.5 秒 · 最高降幅 64%",
    image: "07_mmbiz-qpic-cn.png",
  },
  {
    // ⑩ 战绩：火神队（时间轴旅行）
    type: "timeline-travel",
    from: 1152,
    durationInFrames: 126, // 4.20s
    text: "已进清华火神队比赛系统",
    stops: [
      { label: "2025", note: "RoboCup 成人组人形联赛冠军" },
      { label: "2025", note: "世界人形机器人运动会冠军" },
      { label: "2026", note: "Large Size 卫冕" },
    ],
  },
  {
    // ⑪ 平台侧：算力量级
    type: "number-roll",
    from: 1278,
    durationInFrames: 114, // 3.80s
    text: "Booster T2 专业版 · NVIDIA Thor",
    metrics: [
      { label: "端侧算力", value: "2070 TFLOPS" },
      { label: "协同机队", value: "80 台" },
    ],
  },
  {
    // ⑫ 片尾：CTA + 落版（v1 只有一行字）
    type: "outro-lockup",
    from: 1392,
    durationInFrames: 98, // 3.27s
    text: "关注我",
    tagline: "下期分享 AI 行业最新进展",
  },
];

export const ShortFilm: React.FC<FilmProps> = (props) => (
  <FilmShell {...props} defaultShots={SHORT_SHOTS} />
);

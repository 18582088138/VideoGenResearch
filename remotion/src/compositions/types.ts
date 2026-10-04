/**
 * 成片 props 契约 / Film props contract.
 *
 * 这是 **Python 侧 `VideoSpec` 编译后的产物形状** —— Node 侧只消费它，
 * 不做任何业务决策（见 docs/architecture/00_pipeline.md 阶段 4）。
 *
 * This mirrors the compiled output of the Python-side `VideoSpec`. Node only
 * consumes it; all planning decisions happen in Python.
 */

/** 镜头类型（封闭集合）/ Shot type — a closed set. */
export type ShotType =
  | "title-reveal" // 片头字标 / opening wordmark
  | "page-spotlight" // 页面聚光锁定 / page spotlight lock-on
  | "number-roll" // 数字滚动 / odometer-style number roll
  | "scan-annotate" // 扫描线标注图表 / scanline figure annotation
  | "radar-reveal" // 雷达图聚光显影 / corner spotlight reveal
  | "counter-burst" // 大数字计数 + 彩纸 / counter with confetti
  | "before-after" // 前后对比拉杆 / before-after slider
  | "slow-push" // 慢推压迫 / slow push-in
  | "timeline-travel" // 时间轴横移 / timeline travel
  | "outro-lockup" // 收尾字标 / outro wordmark lockup
  // ——— 图文类：承载独立于旁白的「视频内容文案」/ Figure types ———
  | "figure-panel" // 图文说明面板 / titled bullet panel
  | "stat-compare" // 横向对比条 / side-by-side comparison bars
  | "flow-diagram"; // 流程图 / architecture flow diagram

/** 图内标注目标（归一化坐标）/ Annotation target in normalised image coords. */
export interface ShotTarget {
  x: number;
  y: number;
  w: number;
  h: number;
  label: string;
  side?: "left" | "right";
}

/** 时间轴刻度（timeline-travel 用）/ Timeline tick. */
export interface ShotStop {
  label: string;
  note?: string;
}

/** 流程图节点（flow-diagram 用）/ Flow node. */
export interface ShotNode {
  label: string;
  sub?: string;
}

/** 对比条的一方（stat-compare 用）/ One side of a comparison. */
export interface ShotCompareSide {
  label: string;
  value: number;
  display: string;
  better?: boolean;
}

/** 单个镜头 / One shot. */
export interface ShotSpec {
  /** 镜头类型 / Shot type. */
  type: ShotType;
  /** 在本片内的起始帧 / Start frame within the film. */
  from: number;
  /** 持续帧数 / Duration in frames. */
  durationInFrames: number;
  /** 主文案 / Primary text. */
  text?: string;
  /** 副文案 / Secondary text. */
  subtext?: string;
  /** 强调色标语（收尾镜用）/ Accent tagline, used by the outro shot. */
  tagline?: string;
  /** 角标（图文类用）/ Eyebrow above a figure title. */
  eyebrow?: string;
  /** 底部结论条（图文类用）/ Closing takeaway line. */
  footer?: string;
  /** 要点列表图（figure-panel 用）/ Bullets for a figure panel. */
  bullets?: string[];
  /** 数字指标（number-roll / counter-burst 用）/ Numeric metrics. */
  metrics?: Array<{ label: string; value: string }>;
  /** 引用的图片文件名（相对 public/images）/ Referenced image file. */
  image?: string;
  /** 图内标注目标（scan-annotate 用）/ Annotation targets. */
  targets?: ShotTarget[];
  /** 时间轴刻度（timeline-travel 用）/ Timeline ticks. */
  stops?: ShotStop[];
  /** 流程节点（flow-diagram 用）/ Flow nodes. */
  nodes?: ShotNode[];
  /** 对比双方（stat-compare 用）/ Comparison sides. */
  sides?: ShotCompareSide[];
  /** 对比维度说明（stat-compare 用）/ What is being compared. */
  metric?: string;
  /** 来源标注 / Source attribution. */
  source?: string;
}

/** 成片 props / Props for one film composition.
 *
 * 用 `type` 而非 `interface`，并带索引签名 —— Remotion v4 的 `<Composition>`
 * 把 props 约束为 `Record<string, unknown>`，interface 不满足该约束。
 *
 * Declared as a `type` with an index signature because Remotion v4 constrains
 * composition props to `Record<string, unknown>`; a bare interface does not
 * satisfy it.
 */
export type FilmProps = {
  kind: "short" | "mid";
  themeId: string;
  /** 字幕路径（相对 public/，**可以带素材集目录**）。
   * Subtitle path relative to public/; may include the asset-set folder. */
  srtPath: string;
  /** 配音路径（相对 public/，可以带素材集目录）/ Voiceover path. */
  audioPath: string;
  title: string;
  subtitle: string;
  /**
   * 右上角常驻来源标注 / Persistent source attribution in the top-right corner.
   *
   * **必须由 props 传入**：写死会在换一篇文章后继续显示上一家的来源。
   * 由 ``videogen.compile`` 从素材集的 ``set.json`` 编译出来。
   */
  source?: string;
  /** 分镜列表；空数组时用组件内置默认分镜。
   * Shot list; an empty array means "use the built-in default storyboard". */
  shots: ShotSpec[];
  /**
   * 成片总帧数与帧率 —— **由 props 传入，不写死在 Composition 上**。
   *
   * 写死的帧数只对本项目最早两套素材成立；换一篇文章音频长度就变了。
   * 这两个字段由 ``videogen.compile`` 从音频实测时长编译出来，
   * 通用 Composition（``SetLandscape`` / ``SetPortrait``）用
   * ``calculateMetadata`` 读取它们。
   */
  durationInFrames?: number;
  fps?: number;
  /** 索引签名：满足 Remotion 的 props 约束 / Satisfies Remotion's constraint. */
  [key: string]: unknown;
};

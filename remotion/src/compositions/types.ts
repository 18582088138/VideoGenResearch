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
  | "flow-diagram" // 流程图 / architecture flow diagram
  // ——— 本轮补充：7 个图文形态 + 1 个素材形态 / Added this round ———
  //
  // ⚠️ **为什么一次补 8 个**：实测发现「不同文章的图文类镜头高度雷同」，
  //    根因是**选择空间太小** —— 补之前图文类只有 3 个
  //    （figure-panel / stat-compare / flow-diagram），任何文章都只能从这 3 个里凑，
  //    组合必然相似。这 8 个各自对应一种**内容形态**，而不是"再多几个好看的动效"。
  //
  // Eight types added at once because the figure-type space was too small: with
  // only three figure types every article's storyboard converged on the same mix.
  // Each new type maps to a distinct *content shape*, not just another animation.
  | "icon-grid" // 并列枚举（无序多项）/ icon grid of parallel items
  | "quote-card" // 单句论断 / 结论 / one-statement quote card
  | "steps-list" // 有序步骤（带编号）/ ordered step list
  | "comparison-table" // 多方案逐项对比（3 项以上）/ multi-option comparison table
  | "layer-stack" // 分层架构（自下而上）/ bottom-up layer stack
  | "progress-meter" // 部分 vs 总体（覆盖率）/ part-vs-whole progress ring
  | "keyword-highlight" // 长句里的关键词逐个点亮 / keywords swept through a long sentence
  // ——— 素材类补充 / Multi-image type ———
  | "image-pair"; // 双图并排 / two images side by side

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
  /** 要点列表（figure-panel / icon-grid / keyword-highlight 用）
   * Bullets: a figure panel's points, an icon grid's items, or the keywords to
   * highlight inside a long sentence. */
  bullets?: string[];
  /** 数字指标（number-roll / counter-burst 用）/ Numeric metrics. */
  metrics?: Array<{ label: string; value: string }>;
  /** 引用的图片文件名（相对 public/images）/ Referenced image file. */
  image?: string;
  /** 第二张图（image-pair 用）/ Second image, used by `image-pair`. */
  image2?: string;
  /** 图内标注目标（scan-annotate 用）/ Annotation targets. */
  targets?: ShotTarget[];
  /** 时间轴刻度（timeline-travel 用）/ Timeline ticks. */
  stops?: ShotStop[];
  /** 节点序列（flow-diagram / steps-list / layer-stack 用）
   * Nodes: a flow's stages, an ordered step list, or stacked layers bottom-up. */
  nodes?: ShotNode[];
  /** 对比各方（stat-compare / comparison-table 用）
   * Sides: the compared parties — two racing bars, or a table's columns. */
  sides?: ShotCompareSide[];
  /** 对比维度说明或占比数值（stat-compare / progress-meter 用）
   * What is being compared, or the part-vs-whole figure, e.g. `"62%"`. */
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
   * 是否渲染字幕轨 / Whether to render the caption track.
   *
   * 默认 ``true``。**导出分镜片段时传 ``false``** ——
   * 交付要求「分镜片段不要渲染字幕」（片段用于二次修改，字幕是独立交付物）。
   */
  captionsEnabled?: boolean;
  /**
   * 是否渲染配音轨 / Whether to render the audio track.
   *
   * 默认 ``true``。**导出分镜片段时传 ``false``** ——
   * 切碎后的每段音频大多停在句子中间，单独听没有意义，且静音可显著减小体积。
   */
  audioEnabled?: boolean;
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

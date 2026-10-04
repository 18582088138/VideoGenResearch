/**
 * 镜头分发器 / Shot dispatcher.
 *
 * 把 props 里的 `ShotSpec.type` 映射到具体组件。**封闭集合** ——
 * 未实现的类型不报错，落到占位实现（渲染上明确可辨），
 * 这样分镜可以逐步补全而不阻塞整片渲染。
 *
 * Maps `ShotSpec.type` onto components. The set is closed; unimplemented types
 * fall back to a clearly-visible placeholder instead of throwing, so shots can
 * be filled in incrementally without blocking a full render.
 */

import React from "react";
import { AbsoluteFill } from "remotion";
import { FONT_FAMILY, ThemeTokens } from "../theme/theme";
import { Layout } from "../theme/layout";
import type { ShotSpec } from "../compositions/types";
import { TitleReveal } from "./TitleReveal";
import { NumberRoll } from "./NumberRoll";
import { PageSpotlight } from "./PageSpotlight";
import { ScanAnnotate } from "./ScanAnnotate";
import { RadarReveal } from "./RadarReveal";
import { OutroLockup } from "./OutroLockup";
import { CounterBurst } from "./CounterBurst";
import { BeforeAfter } from "./BeforeAfter";
import { SlowPush } from "./SlowPush";
import { TimelineTravel } from "./TimelineTravel";
import { FigurePanel } from "./FigurePanel";
import { StatCompare } from "./StatCompare";
import { FlowDiagram } from "./FlowDiagram";
import { IconGrid } from "./IconGrid";
import { QuoteCard } from "./QuoteCard";
import { StepsList } from "./StepsList";
import { ComparisonTable } from "./ComparisonTable";
import { LayerStack } from "./LayerStack";
import { ProgressMeter } from "./ProgressMeter";
import { KeywordHighlight } from "./KeywordHighlight";
import { ImagePair } from "./ImagePair";

export interface ShotRendererProps {
  shot: ShotSpec;
  theme: ThemeTokens;
  layout: Layout;
}

type Inner = ShotRendererProps;

/** 未实现镜头的占位：明确写出类型与文案，避免"看着像成品"的假象。 */
const PlaceholderShot: React.FC<Inner> = ({ shot, theme, layout }) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", fontFamily: FONT_FAMILY }}>
    <div
      style={{
        border: `2px dashed ${theme.border}`,
        borderRadius: 18,
        padding: "28px 40px",
        maxWidth: layout.contentWidth * 0.8,
        textAlign: "center",
      }}
    >
      <div style={{ color: theme.textMuted, fontSize: 20, letterSpacing: "0.14em" }}>
        待实现镜头 / SHOT NOT IMPLEMENTED
      </div>
      <div
        style={{
          color: theme.primary,
          fontSize: 34,
          fontWeight: 700,
          marginTop: 10,
          fontFamily: "monospace",
        }}
      >
        {shot.type}
      </div>
      {shot.text ? (
        <div style={{ color: theme.text, fontSize: 26, marginTop: 18 }}>{shot.text}</div>
      ) : null}
    </div>
  </AbsoluteFill>
);

export const ShotRenderer: React.FC<ShotRendererProps> = ({ shot, theme, layout }) => {
  const base = { theme, layout, durationInFrames: shot.durationInFrames };

  switch (shot.type) {
    case "title-reveal":
      return (
        <TitleReveal
          title={shot.text ?? ""}
          subtitle={shot.subtext}
          eyebrow={shot.eyebrow}
          {...base}
        />
      );

    case "outro-lockup":
      return (
        <OutroLockup
          text={shot.text ?? ""}
          tagline={shot.tagline ?? shot.subtext}
          {...base}
        />
      );

    case "number-roll":
      return <NumberRoll title={shot.text ?? ""} metrics={shot.metrics ?? []} {...base} />;

    case "page-spotlight":
      return (
        <PageSpotlight
          file={shot.image ?? ""}
          text={shot.text}
          source={shot.source}
          {...base}
        />
      );

    case "scan-annotate":
      return (
        <ScanAnnotate
          file={shot.image ?? ""}
          text={shot.text}
          subtext={shot.subtext}
          targets={shot.targets ?? []}
          {...base}
        />
      );

    case "radar-reveal":
      return (
        <RadarReveal
          file={shot.image ?? ""}
          text={shot.text}
          subtext={shot.subtext}
          {...base}
        />
      );

    case "counter-burst":
      return (
        <CounterBurst
          text={shot.text}
          subtext={shot.subtext}
          metrics={shot.metrics ?? []}
          {...base}
        />
      );

    case "before-after":
      return (
        <BeforeAfter
          file={shot.image ?? ""}
          text={shot.text}
          subtext={shot.subtext}
          metrics={shot.metrics}
          {...base}
        />
      );

    case "slow-push":
      return <SlowPush file={shot.image ?? ""} text={shot.text} {...base} />;

    case "timeline-travel":
      return (
        <TimelineTravel
          text={shot.text}
          stops={shot.stops ?? []}
          metrics={shot.metrics}
          {...base}
        />
      );

    case "figure-panel":
      return (
        <FigurePanel
          title={shot.text ?? ""}
          eyebrow={shot.eyebrow}
          bullets={shot.bullets ?? []}
          footer={shot.footer}
          {...base}
        />
      );

    case "stat-compare":
      return (
        <StatCompare
          title={shot.text ?? ""}
          metric={shot.metric ?? ""}
          sides={shot.sides ?? []}
          footer={shot.footer}
          {...base}
        />
      );

    case "flow-diagram":
      return (
        <FlowDiagram
          title={shot.text ?? ""}
          eyebrow={shot.eyebrow}
          nodes={shot.nodes ?? []}
          caption={shot.footer ?? shot.subtext}
          {...base}
        />
      );

    // ——— 本轮补充的 7 个图文形态 / Figure types added this round ———
    // 字段一律复用现有结构（bullets / nodes / sides / metric），不新增数据类型。

    case "icon-grid":
      return (
        <IconGrid
          title={shot.text ?? ""}
          eyebrow={shot.eyebrow}
          bullets={shot.bullets ?? []}
          footer={shot.footer}
          {...base}
        />
      );

    case "quote-card":
      return (
        <QuoteCard
          text={shot.text ?? ""}
          subtext={shot.subtext}
          footer={shot.footer}
          {...base}
        />
      );

    case "steps-list":
      return (
        <StepsList
          title={shot.text ?? ""}
          eyebrow={shot.eyebrow}
          nodes={shot.nodes ?? []}
          footer={shot.footer}
          {...base}
        />
      );

    case "comparison-table":
      return (
        <ComparisonTable
          title={shot.text ?? ""}
          metric={shot.metric}
          sides={shot.sides ?? []}
          bullets={shot.bullets ?? []}
          footer={shot.footer}
          {...base}
        />
      );

    case "layer-stack":
      return (
        <LayerStack
          title={shot.text ?? ""}
          eyebrow={shot.eyebrow}
          nodes={shot.nodes ?? []}
          footer={shot.footer}
          {...base}
        />
      );

    case "progress-meter":
      return (
        <ProgressMeter
          title={shot.text ?? ""}
          metric={shot.metric ?? ""}
          subtext={shot.subtext}
          {...base}
        />
      );

    case "keyword-highlight":
      return (
        <KeywordHighlight
          text={shot.text ?? ""}
          bullets={shot.bullets ?? []}
          subtext={shot.subtext}
          eyebrow={shot.eyebrow}
          {...base}
        />
      );

    // ——— 素材类补充：双图并排 / Multi-image type ———
    // 素材类不渲染镜头文案（用户口径），只把 image / image2 与 eyebrow 传下去。
    case "image-pair":
      return (
        <ImagePair
          file={shot.image ?? ""}
          file2={shot.image2 ?? ""}
          eyebrow={shot.eyebrow}
          {...base}
        />
      );

    default:
      return <PlaceholderShot shot={shot} theme={theme} layout={layout} />;
  }
};

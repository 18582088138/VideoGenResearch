/**
 * 镜头骨架 / Shot scaffold — 所有镜头组件的公共外框.
 *
 * 统一负责三件事，镜头组件自己不再重复：
 *   1. 背景（含极轻的径向渐变，避免大片纯黑在 H.264 暗部出色带）
 *   2. 字体就绪门禁（未就绪直接不渲染，绝不渲 fallback 字体）
 *   3. 版式与主题的上下文传递
 *
 * Owns three things so individual shots don't repeat them: the background
 * (with a faint radial gradient to avoid H.264 banding in the darks), the
 * font-readiness gate, and theme/layout plumbing.
 */

import React from "react";
import { AbsoluteFill, useVideoConfig } from "remotion";
import { useFontsReady } from "./fonts";
import { deriveLayout, Layout } from "./layout";
import { getTheme, ThemeTokens } from "./theme";

export interface ShotScaffoldProps {
  /** 主题 id / Theme id. */
  themeId?: string;
  children: (ctx: { theme: ThemeTokens; layout: Layout }) => React.ReactNode;
}

/**
 * 背景层：底色 + 两处极淡光斑，制造景深而不喧哗。
 * SKILL.md 明确「装饰性泛光群发即廉价」，所以只给两处、且极淡。
 */
const Background: React.FC<{ theme: ThemeTokens }> = ({ theme }) => (
  <AbsoluteFill
    style={{
      backgroundColor: theme.bg,
      backgroundImage: [
        `radial-gradient(ellipse 62% 46% at 26% 30%, ${theme.primary}14, transparent 62%)`,
        `radial-gradient(ellipse 54% 40% at 78% 74%, ${theme.accent}0f, transparent 65%)`,
      ].join(", "),
    }}
  />
);

export const ShotScaffold: React.FC<ShotScaffoldProps> = ({
  themeId,
  children,
}) => {
  const fontsReady = useFontsReady();
  const { width, height } = useVideoConfig();
  const theme = getTheme(themeId);
  const layout = deriveLayout(width, height);

  // 字体未就绪返回 null：宁可短暂空白，也不要渲出 fallback 字体的帧。
  if (!fontsReady) {
    return null;
  }

  return (
    <AbsoluteFill>
      <Background theme={theme} />
      {children({ theme, layout })}
    </AbsoluteFill>
  );
};

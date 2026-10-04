/**
 * 素材尺寸表 / Asset dimension table.
 *
 * `assets/images/index.json` 的**编译期镜像**。为什么不在运行期 fetch：
 *   Remotion 渲染时 fetch 会引入 `delayRender` 等待，而这份数据在构建期就已知；
 *   更重要的是，标注百分比定位需要**在渲染前就知道显示尺寸**，否则图会被
 *   宽度约束撑高、把文字与字幕挤出画面（横屏实测过这个错）。
 *
 * A compile-time mirror of `assets/images/index.json`. Fetching at render time
 * would add a `delayRender` wait and, more importantly, the annotated overlays
 * need the display size known *before* rendering — otherwise a width-constrained
 * figure grows too tall and pushes text and captions off-frame (observed in
 * landscape).
 *
 * 改素材后**必须同步这张表** —— 数据源是 assets/images/index.json。
 */

export interface AssetDims {
  width: number;
  height: number;
}

export const ASSET_DIMS: Record<string, AssetDims> = {
  "01_mmbiz-qpic-cn.jpg": { width: 1280, height: 544 },
  "03_mmbiz-qpic-cn.jpg": { width: 1080, height: 608 },
  "04_mmbiz-qpic-cn.png": { width: 1080, height: 1070 },
  "05_mmbiz-qpic-cn.png": { width: 1080, height: 609 },
  "06_mmbiz-qpic-cn.png": { width: 1080, height: 865 },
  "07_mmbiz-qpic-cn.png": { width: 1080, height: 484 },
  "08_mmbiz-qpic-cn.png": { width: 1080, height: 959 },
};

/**
 * 在给定宽高上限内等比缩放，返回确定的显示尺寸。
 *
 * Fit within a max width and max height, preserving aspect ratio, returning a
 * deterministic display size.
 *
 * 图未知（不在表里）时按 16:9 兜底，保证不会退化成"撑满宽度"。
 */
export const fitSize = (
  file: string,
  maxW: number,
  maxH: number,
): { w: number; h: number } => {
  const dims = ASSET_DIMS[file] ?? { width: 16, height: 9 };
  const scale = Math.min(maxW / dims.width, maxH / dims.height);
  return { w: Math.round(dims.width * scale), h: Math.round(dims.height * scale) };
};

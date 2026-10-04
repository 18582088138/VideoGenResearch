/**
 * 素材路径解析 / Asset path resolution.
 *
 * 为什么需要它：镜头组件原先写死 ``staticFile(`images/${file}`)``，
 * 只支持「图片放在 public/images/ 下」这一种布局。引入素材集后，
 * 图片实际在 ``public/<set>/images/`` —— 硬拼前缀就会拼成
 * ``public/images/<set>/images/...``，渲染直接 404（实测踩过）。
 *
 * Components used to hard-code the `images/` prefix, which only works when every
 * asset sits directly under `public/images/`. Asset sets live under
 * `public/<set>/images/`, so prefixing again produced `images/<set>/images/...`
 * and the render 404'd.
 *
 * 现在约定：**props 里的资源路径是「相对 public/ 的完整路径」**，
 * 组件一律经过本模块取 URL，不再自己拼前缀。
 * Asset paths in props are now complete paths relative to `public/`; components
 * resolve them here instead of building prefixes themselves.
 */

import { staticFile } from "remotion";

/**
 * 图片路径 → 可用的 URL / Image path to a usable URL.
 *
 * 兼容两种写法，便于平滑迁移与 Studio 里直接预览：
 * - ``images/a.png``（已带前缀）→ 原样使用
 * - ``a.png``（裸文件名）→ 补 ``images/``
 */
export const imageUrl = (file: string): string => {
  if (!file) {
    return "";
  }
  const normalized = file.replace(/\\/g, "/").replace(/^\/+/, "");
  return staticFile(
    normalized.includes("/") ? normalized : `images/${normalized}`,
  );
};

/**
 * 音频路径 → 可用的 URL / Audio path to a usable URL.
 *
 * 同理：props 里给 ``audio/x.wav`` 或 ``<set>/audio/x.wav`` 都直接用；
 * 只有裸文件名时补 ``audio/``。
 */
export const audioUrl = (file: string): string => {
  if (!file) {
    return "";
  }
  const normalized = file.replace(/\\/g, "/").replace(/^\/+/, "");
  return staticFile(
    normalized.includes("/") ? normalized : `audio/${normalized}`,
  );
};

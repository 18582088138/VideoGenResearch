/**
 * 字体加载 / Font loading.
 *
 * 关键点：**必须等字体真正就绪再渲染**。Remotion 跑在无头 Chromium 上，
 * 字体加载失败 **不会报错**，只会静默 fallback 到系统默认字体 ——
 * 于是首帧与后续帧可能字体不一致，画面「不报错，只是不对」。
 * 见 docs/issues/002-cjk-font-ttc-face-ambiguity.md。
 *
 * Fonts MUST be ready before the first frame renders. On headless Chromium a
 * failed font load does not throw; it silently falls back, which can make the
 * first frame differ from the rest.
 */

import { useEffect, useState } from "react";
import { continueRender, delayRender, staticFile } from "remotion";

/** public/fonts 下的字体清单 / Font files under public/fonts. */
const FONT_FILES = ["fonts/NotoSansSC-VF.ttf"] as const;

let loadedOnce: Promise<void> | null = null;

/**
 * 加载全部字体，返回可缓存的 Promise（模块级缓存，多次挂载只加载一次）。
 *
 * Load all fonts, memoized at module scope so repeated mounts load once.
 */
const loadFonts = (): Promise<void> => {
  if (loadedOnce) {
    return loadedOnce;
  }

  loadedOnce = (async () => {
    if (typeof document === "undefined") {
      return; // 非浏览器环境（理论上不会发生）/ non-browser guard
    }
    await Promise.all(
      FONT_FILES.map(async (file) => {
        const url = staticFile(file);
        const face = new FontFace("Noto Sans SC", `url(${url})`);
        await face.load();
        document.fonts.add(face);
      }),
    );
    // 可变字体已注册，再确认一次 document 已就绪
    await document.fonts.ready;
  })();

  return loadedOnce;
};

/**
 * 等待字体就绪的 hook；组件挂载期间会 hold 住渲染。
 *
 * Hook that holds rendering until fonts are ready.
 *
 * @returns 就绪为 true；未就绪时调用方应渲染占位或返回 null。
 */
export const useFontsReady = (): boolean => {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // delayRender 返回 handle，必须与 continueRender 成对，否则渲染会挂起超时。
    const handle = delayRender("加载中文字体 / loading CJK fonts");
    loadFonts()
      .then(() => {
        setReady(true);
        continueRender(handle);
      })
      .catch((err) => {
        // 不吞错：字体加载失败必须让人看到，否则会静默渲出 fallback 字体的片子。
        // Do not swallow: a font failure must be visible, not rendered silently.
        continueRender(handle);
        throw err;
      });
  }, []);

  return ready;
};

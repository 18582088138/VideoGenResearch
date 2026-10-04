/**
 * Remotion 入口 / Remotion entry point.
 *
 * registerRoot 必须单独一个文件（不能与 Root 组件同文件），否则 Studio 无法热更新。
 * registerRoot must live in its own file, separate from the Root component,
 * otherwise Studio cannot hot-reload.
 */

import { registerRoot } from "remotion";
import { RemotionRoot } from "./Root";

registerRoot(RemotionRoot);

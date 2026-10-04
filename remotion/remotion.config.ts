import { Config } from "@remotion/cli/config";

// 渲染产物走 png 序列再编码；h264 + yuv420p 是平台兼容性最好的组合。
// Render via a png sequence, then encode. h264 + yuv420p is the most
// broadly compatible combination across Xiaohongshu / Douyin.
Config.setVideoImageFormat("png");
Config.setCodec("h264");
Config.setPixelFormat("yuv420p");
Config.setOverwriteOutput(true);

// 并发从 4 起步：过高会打满 CPU 反而变慢，且本机内存有限。
// Start at 4: higher concurrency saturates CPU and can be slower, and local
// memory is limited.
Config.setConcurrency(4);

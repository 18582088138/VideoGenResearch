# 005 — 整片渲染失败：真因是 `%TEMP%` 在工作区外，报错却显示为 `write EOF`

> ⚠️ **本文档经过一次重大更正。** 初版把根因判为「沙箱禁止命名管道」，
> 那是**错的**，且错了两次（先归因管道，后又以为沙箱外可解）。
> 下面留档错误的诊断路径，因为**这个误导性报错本身**才是最大的坑。

## 现象（真实报错，`--log=verbose` 才拿得到）

```
[compositor] Freed memory from compositor

Error: ffmpeg version n7.1 ...
Input #0, image2pipe, from 'fd:':
  Stream #0:0: Video: png, rgb24(pc, gbr/unknown/unknown), 1920x1080, 30 fps, 30 tbr, 30 tbn
[out#0/mp4 @ 00000218e90ded80] Error opening output
  C:\Users\75203\AppData\Local\Temp\react-motion-renderv6Cp8o\pre-encode.mp4: Permission denied
Error opening output file C:\...\Temp\react-motion-renderv6Cp8o\pre-encode.mp4.
Error opening output files: Permission denied

    at waitForPrestitcherIfNecessary (...\@remotion\renderer\dist\render-media.js:268:23)
```

而**默认日志级别下**，用户与 Node 侧只能看到：

```
Error: write EOF
    at WriteWrap.onWriteComplete [as oncomplete] (node:internal/stream_base_commons:87:19)
  errno: -4095, code: 'EOF', syscall: 'write'
```

## 真因

1. **Remotion 把预编码的 mp4 写到 `%TEMP%`**：
   `%TEMP%\react-motion-render<随机>\pre-encode.mp4`。
2. 本机 `%TEMP%` = `C:\Users\75203\AppData\Local\Temp`，**在工作区
   `C:\Users\75203\Downloads\xkd` 之外**。
3. DSH 沙箱（`workspace-write`）拒绝在工作区外创建文件 → ffmpeg 报
   `Permission denied`。
4. compositor 子进程随即崩溃。它向 Node 父进程回报的那条管道被关闭，
   Node 侧只看到 `write EOF` —— **真正的 ffmpeg 报错被截断了**。

**关键结论：这不是管道/stdio 限制，是工作区外的文件写入被拒。**

## 为什么我判错了两次（留档警示）

| 错误判断 | 当时的依据 | 为什么站不住 |
|---|---|---|
| ①「沙箱禁止非继承 stdio 的进程间管道」 | `compositor.js:47` 的 `spawn` 确实未传 `stdio`，Node 默认 `'pipe'`；`write EOF` 字面像管道问题 | 只解释了**表象**。而且 `still`（单帧）能跑是因为它不经过 compositor 编码，这条"对照"反而让我更确信，属于**用巧合强化错误假设** |
| ②「沙箱外执行就能解决」 | 以为用户会在纯外部终端运行 | 用户实际在**同一 DSH 会话**里运行，沙箱对子进程仍生效；即便真在外部终端，只要 `%TEMP%` 仍在工作区外且沙箱策略生效，一样会崩 |

**教训**：`write EOF` 这类底层报错**必须拿到被截断的上游错误**才能定性。
我第一次查 `--log=verbose` 时只看了日志**尾部**，尾部正好是那行 `write EOF`；
真正的 `Permission denied` 在上面的 ffmpeg 输出里，被我漏掉了。
**以后排查此类问题：先 `Select-String` 搜 `Error|denied|failed` 全日志，不要只看尾部。**

## 修复

把 `TMP` / `TEMP` 指到工作区内，让 Remotion 的预编码文件落在沙箱允许的范围内：

```powershell
$env:TMP  = 'C:\Users\75203\Downloads\xkd\.render-tmp'
$env:TEMP = $env:TMP
New-Item -ItemType Directory -Force -Path $env:TMP | Out-Null
npx remotion render src/index.ts ShortLandscape out\short.mp4 --crf=18 --codec=h264 --pixel-format=yuv420p
```

**已实测生效**：3 帧最小复现从「必崩」变为成功（`Encoded 3/3`，输出 35.9 kB mp4）。

`remotion/scripts/render.ps1` 已内置这段设置；`src/videogen/render/remotion.py`
的 `build_env()` 同样设置，保证两条路径一致。

`.render-tmp/` 已加入 `.gitignore`。

## 复发预防

| 场景 | 规则 |
|---|---|
| 任何 Remotion **编码**（render） | 必须先把 `TMP`/`TEMP` 指进工作区。`still` 不需要（不写预编码文件） |
| 见到 `write EOF` / `EPERM` / `errno -4095` | **先去全量日志里搜 `denied`/`failed`**，不要只看尾部；真因通常在别处 |
| 新增任何会写临时文件的工具 | 同样检查它的临时目录是否落在工作区内 |
| 想确认是不是管道问题 | 看 `stdlib` 报错之外的**上游**进程报错；管道问题不会伴随 `Permission denied` |

## 影响范围

- ✅ **整片渲染在本会话内可行**（修好临时目录后），不需要沙箱外执行
- ✅ 单帧 `still` 一直正常（与临时目录无关）
- ⚠️ 沙箱策略若改为可在工作区外写入，此问题会自动消失 —— 但脚本里的设置无害，保留

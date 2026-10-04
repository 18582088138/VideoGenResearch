"""渲染编排 / Render orchestration.

**Node 薄壳的 Python 侧**：把 props 文件与 rendring 参数交给 Remotion CLI，
报错原样回传。业务决策全在 spec 里，这一层不做任何创作决定。

The Python side of the Node shell: hands the props file and render parameters to
the Remotion CLI and relays errors verbatim. No creative decisions here.

⚠️ ``render`` 在受限沙箱内**不可用**：Remotion 4.x 的编码由原生 Rust
compositor 子进程完成，靠管道 stdio 通信，而沙箱禁止非继承 stdio 的进程间管道
（见 ``docs/issues/005``）。``still``（单帧）不受影响。
"""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from videogen.compile import RenderTarget
from videogen.paths import PROJECT_ROOT


class RenderError(RuntimeError):
    """渲染失败 / Render failed. 消息里带退出码与日志尾部。"""


@dataclass
class RenderResult:
    """一次渲染的结果 / Result of one render."""

    output: Path
    seconds: float
    log_path: Path
    exit_code: int


def remotion_dir() -> Path:
    """Remotion 工程目录 / The Remotion project directory."""
    return PROJECT_ROOT / "remotion"


def _cli_command() -> list[str]:
    """构造 Remotion CLI 的调用命令前缀 / Build the CLI command prefix.

    **不用 ``npx``**：Windows 上 ``npx`` 是 ``.cmd`` shim，而
    ``subprocess`` 用 ``CreateProcess`` 不解析它（``FileNotFoundError``）。
    直接跑 ``node <cli.js>`` 有三个好处：

    1. shell 无关（不需要 ``shell=True``，路径含空格也安全）
    2. 跳过 npx 的解析开销
    3. 版本由工程内 node_modules 锁定，不受全局环境影响

    Running ``node <cli.js>`` directly instead of ``npx``: on Windows ``npx`` is
    a ``.cmd`` shim that ``CreateProcess`` will not resolve, and this form is
    shell-independent and immune to spaces in paths.
    """
    cli = remotion_dir() / "node_modules" / "@remotion" / "cli" / "remotion-cli.js"
    if not cli.exists():
        # 兜底：某些布局把入口放在 dist 下
        alt = remotion_dir() / "node_modules" / "@remotion" / "cli" / "dist" / "index.js"
        if not alt.exists():
            raise RenderError(
                "找不到 Remotion CLI / Remotion CLI not found。"
                "请先在 remotion/ 下执行 npm install（见 docs/guides/01_remotion_guide.md）。\n"
                f"已查找 / looked for: {cli}"
            )
        cli = alt
    return ["node", str(cli)]


def build_env() -> dict[str, str]:
    """构造渲染所需的环境变量 / Build the environment for rendering.

    三个变量都必须指向**工作区内**，否则会撞沙箱的文件访问限制：

    ``npm_config_cache`` / ``npm_config_tmp``
        npm 默认缓存目录在 ``%LocalAppData%``，在工作区外（见 ``docs/issues/001``）。

    ``TMP`` / ``TEMP``
        **Remotion 把预编码的 mp4 写到 ``%TEMP%``**
        （``%TEMP%\\react-motion-render<随机>\\pre-encode.mp4``）。
        若 ``%TEMP%`` 在工作区外，沙箱拒绝写入 → ffmpeg 报 ``Permission denied``
        → compositor 崩溃 → Node 侧只抛出**极具误导性**的 ``Error: write EOF``
        （见 ``docs/issues/005`` —— 那个报错让人误判成管道问题，白查了两轮）。

    Three variables must point inside the workspace; otherwise the sandbox denies
    the write and Node surfaces a misleading ``write EOF``.
    """
    env = dict(os.environ)
    workspace = PROJECT_ROOT.parent
    env["npm_config_cache"] = str(workspace / ".npm-cache")
    env["npm_config_tmp"] = str(workspace / ".npm-tmp")
    render_tmp = workspace / ".render-tmp"
    render_tmp.mkdir(parents=True, exist_ok=True)
    env["TMP"] = str(render_tmp)
    env["TEMP"] = str(render_tmp)
    return env


def _run_cli(args: list[str], log_path: Path, *, timeout: float) -> int:
    """跑一次 Remotion CLI，输出重定向到日志文件。

    Run the Remotion CLI once, redirecting output to a log file.

    **不用管道捕获输出** —— 沙箱禁止非继承 stdio 的进程间管道，
    ``| Select-Object`` 或 ``subprocess.PIPE`` 都会让子进程写 stdout 时崩。
    所以 stdout/stderr 直接落到文件句柄。
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8", errors="replace") as log:
        proc = subprocess.run(
            args,
            cwd=str(remotion_dir()),
            env=build_env(),
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
            shell=False,
        )
    return proc.returncode


def render_still(
    target: RenderTarget,
    props_path: Path,
    frame: int,
    output: Path,
    *,
    timeout: float = 300.0,
) -> RenderResult:
    """出单帧静帧 / Render a single still frame.

    这是**开发期最高频的验收手段**（秒级），改任何镜头后先跑它。
    """
    log_path = output.with_suffix(".log")
    # 路径一律转绝对：子进程的 cwd 是 remotion/，相对路径会解析错
    # (Remotion 会把它当成"不是合法 JSON 也不是合法文件路径"而报错)
    # Paths are resolved to absolute: the subprocess cwd is remotion/, so a
    # relative props path would fail to resolve.
    args = _cli_command() + [
        "still",
        "src/index.ts",
        target.composition_id,
        str(output.resolve()),
        f"--frame={frame}",
        f"--props={props_path.resolve()}",
        "--log=info",
    ]
    started = time.monotonic()
    code = _run_cli(args, log_path, timeout=timeout)
    seconds = time.monotonic() - started

    if code != 0 or not output.exists():
        raise RenderError(
            f"静帧渲染失败 / still failed (exit {code})：{target.composition_id} frame={frame}\n"
            f"日志尾部 / log tail:\n{_tail(log_path)}"
        )
    return RenderResult(output=output, seconds=seconds, log_path=log_path, exit_code=code)


def render_video(
    target: RenderTarget,
    props_path: Path,
    output: Path,
    *,
    timeout: float = 3600.0,
    concurrency: int | None = None,
) -> RenderResult:
    """渲染整片 / Render the full video.

    :raises RenderError: 失败；消息里区分「沙箱管道受限」与其它原因，
        便于对症处理（前者只能换个环境，后者要改代码）。
    """
    log_path = output.with_suffix(".log")
    # 同 render_still：路径必须绝对（子进程 cwd 为 remotion/）
    args = _cli_command() + [
        "render",
        "src/index.ts",
        target.composition_id,
        str(output.resolve()),
        f"--props={props_path.resolve()}",
        "--codec=h264",
        f"--crf={target.crf}",
        "--pixel-format=yuv420p",
        "--audio-codec=aac",
        "--audio-bitrate=192K",
        "--log=info",
    ]
    if concurrency:
        args.append(f"--concurrency={concurrency}")

    started = time.monotonic()
    code = _run_cli(args, log_path, timeout=timeout)
    seconds = time.monotonic() - started

    if code != 0 or not output.exists():
        tail = _tail(log_path)
        hint = ""
        if "write EOF" in tail or "EPERM" in tail or "Permission denied" in tail:
            hint = (
                "\n提示 / hint: 若日志里出现 `Permission denied` 或只看到 `write EOF`，"
                "几乎一定是**临时目录在工作区外**被沙箱拒绝写入"
                "（Remotion 把预编码 mp4 写到 %TEMP%）。\n"
                "本项目已让 build_env() 把 TMP/TEMP 指向工作区内的 .render-tmp/；"
                "手工执行时请自行设置，见 docs/issues/005。"
            )
        raise RenderError(
            f"整片渲染失败 / render failed (exit {code})：{target.composition_id}\n"
            f"日志尾部 / log tail:\n{tail}{hint}"
        )
    return RenderResult(output=output, seconds=seconds, log_path=log_path, exit_code=code)


def _tail(log_path: Path, lines: int = 25) -> str:
    """取日志尾部用于报错 / Tail the log for error messages."""
    if not log_path.exists():
        return "(无日志 / no log)"
    content = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(content[-lines:])

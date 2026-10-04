"""VideoGenResearch-deepseek 的可复用 Python 模块。

Reusable Python module for the VideoGenResearch-deepseek project.

**对外唯一稳定入口是** :func:`videogen.pipeline.generate_video` ——
调用方不需要知道 Remotion 存在。其余子模块为内部实现，
但允许独立导入以便单测与调试。
"""

from __future__ import annotations

from videogen.paths import PROJECT_ROOT, assets_dir, docs_dir, out_dir

__all__ = [
    "PROJECT_ROOT",
    "assets_dir",
    "docs_dir",
    "generate_video",
    "out_dir",
    "__version__",
]

__version__ = "0.1.0"


def generate_video(*args: object, **kwargs: object):  # type: ignore[no-untyped-def]
    """延迟导入的对外入口 / Lazily imported public entry point.

    延迟导入是有意的：``pipeline`` 会拉起 LLM 与渲染编排的重依赖，
    而只想用 ``paths``/``timeline`` 的调用方不该为此付出导入代价。

    The lazy import is deliberate: ``pipeline`` pulls in the LLM and render
    orchestration, which callers wanting only ``paths``/``timeline`` should not
    pay for.
    """
    from videogen.pipeline import generate_video as _impl

    return _impl(*args, **kwargs)  # type: ignore[arg-type]

"""渲染子包 / Rendering subpackage（阶段 4）。

Node 薄壳的 Python 侧：只负责把 props 与参数交给 Remotion，不做创作决策。
"""

from __future__ import annotations

from videogen.render.remotion import (
    RenderError,
    RenderResult,
    build_env,
    remotion_dir,
    render_still,
    render_video,
)

__all__ = [
    "RenderError",
    "RenderResult",
    "build_env",
    "remotion_dir",
    "render_still",
    "render_video",
]

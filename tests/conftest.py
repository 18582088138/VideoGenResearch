"""pytest 公共配置 / Shared pytest configuration.

把 ``src/`` 加进 ``sys.path``，让测试无需先 ``pip install -e .`` 就能 import
``videogen`` —— 本项目的依赖纪律是「能不装就不装」，可编辑安装留给工程化阶段。

Adds ``src/`` to ``sys.path`` so tests can import ``videogen`` without a prior
``pip install -e .`` — this project's rule is to install nothing it can avoid.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

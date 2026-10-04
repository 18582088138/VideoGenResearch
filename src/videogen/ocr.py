"""Agentic_OCR_Module 集成 / Integration with the local OCR module.

对应 ``https://github.com/18582088138/Agentic_OCR_Module``。

**为什么值得接**：它对本项目有两个别处拿不到的能力。

1. **准确的文字**（不编造）。VLM 会看错专有名词 —— 实测把 ``Omni-IO``
   读成了 ``Omni-10``。OCR 不会。把这些文字作为 grounding 喂给 VLM，
   标注里的专有名词就不再靠模型的"眼力"。
2. **ROI 截图**（表格 / 公式 / 插图）。``mineru`` 后端会把一页版面切成
   多个 ROI —— 这等于**把一张复杂配图拆成多个可用素材**，
   正好对上「素材数量不足时才用文案补充分镜」：与其用图文卡凑数，
   不如把一张图拆成 4-5 个更聚焦的镜头。

.. note::
   本模块**可选**。没装 ``agentic_ocr`` 时 ``is_available()`` 返回 ``False``，
   调用方应静默跳过（整条链路照常跑，只是少了 grounding 与 ROI）。

安装（用户自行执行，本项目不代装）::

    git clone https://github.com/18582088138/Agentic_OCR_Module
    conda create -n agentic_ocr python=3.12 -y
    conda activate agentic_ocr
    pip install -r requirements-xpu.txt      # Intel XPU；或 -cuda / -cpu
    pip install -e ".[ppocr]"                # OpenVINO 路线，无需 paddlepaddle
    python scripts/download_models.py ppocr --tier medium   # det+rec ONNX（需代理）

跑通后，本项目即可用 ``OCR_BACKEND=ppocr``（快，~1.5s/页）或
``OCR_BACKEND=mineru``（慢但**带 ROI 截图**）。ROI 只有 mineru 有。
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from videogen.llm_config import load_dotenv

# 常见 clone 位置（相对 xkd 根）。找到就用，找不到就降级。
_CANDIDATE_ROOTS = (
    Path(r"C:\Users\75203\Downloads\xkd\Agentic_OCR_Module"),
    Path(r"C:\Users\75203\Downloads\Agentic_OCR_Module"),
)

# 环境变量名 / Env vars
_ENV_MODULE_PATH = "AGENTIC_OCR_PATH"
_ENV_BACKEND = "OCR_BACKEND"          # ppocr（默认真实后端） | mineru | dummy


@dataclass
class OCRPage:
    """一页的 OCR 结果 / OCR result for one page."""

    text: str = ""
    markdown: str = ""
    rois: list[Path] = field(default_factory=list)
    quality: float | None = None


def module_root() -> Path | None:
    """定位 Agentic_OCR_Module / Locate the OCR module checkout."""
    load_dotenv()
    configured = os.environ.get(_ENV_MODULE_PATH, "").strip()
    if configured:
        path = Path(configured)
        if path.exists():
            return path
    for candidate in _CANDIDATE_ROOTS:
        if candidate.exists():
            return candidate
    return None


def is_available() -> bool:
    """本机是否能用 OCR / Whether the OCR module is usable here.

    判据是**模块根目录存在**（而不是 ``import agentic_ocr`` 成功）——
    因为它通常装在**另一个 conda 环境**里，本项目所处的解释器 import 不到。
    真正调用时由 :func:`ocr_text` 决定用 import 还是走 CLI。
    """
    return module_root() is not None


def describe() -> str:
    """给人和日志看的一句话状态 / One-line human-readable status."""
    root = module_root()
    if root is None:
        return (
            "OCR 未接入 / not connected —— 标注只用视觉模型（专有名词可能有误读）。"
            "接入方法见 src/videogen/ocr.py 顶部注释。"
        )
    backend = os.environ.get(_ENV_BACKEND, "ppocr")
    has_dummy = (root / "agentic_ocr").exists()
    return (
        f"OCR 已接入 / connected: {root}（backend={backend}"
        f"{'' if has_dummy else '，但没看到 agentic_ocr 包目录'}）"
    )


def _resolve_python() -> str:
    """选一个能 import agentic_ocr 的 Python / Pick an interpreter that can import it.

    优先 ``AGENTIC_OCR_PYTHON``（用户在专用的 conda 环境里装的），
    否则退回当前解释器。
    """
    load_dotenv()
    configured = os.environ.get("AGENTIC_OCR_PYTHON", "").strip()
    if configured and Path(configured).exists():
        return configured
    return shutil.which("python") or "python"


def ocr_text(path: Path, *, timeout: float = 300.0) -> str:
    """提取图片里的文字，用作 VLM 的 grounding / Extract text for grounding.

    调用方式按可用性自动选择：

    1. 当前解释器能 ``import agentic_ocr`` → 直接当库用；
    2. 否则用 ``AGENTIC_OCR_PYTHON``（或当前 python）跑一段内联脚本；
    3. 两条路都不通 → 返回空串（**不抛异常**，调用方静默降级）。

    :returns: 提取到的文字（多块用换行拼接）；不可用时为空串。
    """
    root = module_root()
    if root is None:
        return ""

    # 路线 1：直接当库用
    try:
        from agentic_ocr import OCRModule  # type: ignore[import-not-found]

        result = OCRModule().process(str(path))
        return str(getattr(result, "markdown", "") or getattr(result, "text", "") or "")
    except Exception:  # noqa: BLE001 - 任何失败都降级到路线 2
        pass

    # 路线 2：换个解释器跑内联脚本（模块通常装在独立 conda 环境）
    import subprocess
    import sys

    script = (
        "import sys\n"
        f"sys.path.insert(0, r'{root}')\n"
        "from agentic_ocr import OCRModule\n"
        f"r = OCRModule().process(r'{path}')\n"
        "sys.stdout.write(str(getattr(r, 'markdown', '') or getattr(r, 'text', '') or ''))\n"
    )
    try:
        completed = subprocess.run(
            [_resolve_python(), "-c", script],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""

    text = (completed.stdout or "").strip()
    if not text and completed.returncode != 0:
        # 兜底：直接跑仓库自带 CLI（不同版本入口可能不同）
        cli = root / "scripts" / "run_ocr.py"
        if cli.exists():
            try:
                completed = subprocess.run(
                    [_resolve_python(), str(cli), str(path)],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", timeout=timeout, check=False, cwd=str(root),
                )
                text = (completed.stdout or "").strip()
            except (OSError, subprocess.SubprocessError):
                return ""
    _ = sys  # 保持 import 有用途，避免 linter 误报
    return text


def extract_rois(path: Path, out_dir: Path, *, timeout: float = 600.0) -> list[Path]:
    """抽取表格/公式/插图的 ROI 截图 / Crop figure ROIs.

    **只有 mineru 后端有 ROI**（ppocr 是纯文字检测，``rois`` 为空）。
    产出的每张 ROI 都可以当作**独立素材**参与分镜 —— 这是扩充素材数量的
    主要手段。

    :returns: 落盘的 ROI 文件列表；不可用时为空列表。
    """
    root = module_root()
    if root is None:
        return []

    import json as _json
    import subprocess

    out_dir.mkdir(parents=True, exist_ok=True)
    script = (
        "import sys, json, pathlib\n"
        f"sys.path.insert(0, r'{root}')\n"
        "from agentic_ocr import OCRModule\n"
        f"r = OCRModule().process(r'{path}')\n"
        "rois = []\n"
        "for i, roi in enumerate(getattr(r, 'rois', []) or []):\n"
        "    p = getattr(roi, 'path', None) or getattr(roi, 'image_path', None)\n"
        "    if p: rois.append(str(p))\n"
        "print(json.dumps(rois))\n"
    )
    try:
        completed = subprocess.run(
            [_resolve_python(), "-c", script],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout, check=False,
        )
        paths = _json.loads((completed.stdout or "").strip() or "[]")
    except (OSError, subprocess.SubprocessError, ValueError):
        return []

    saved: list[Path] = []
    for index, raw in enumerate(paths):
        source = Path(str(raw))
        if not source.exists():
            continue
        target = out_dir / f"roi_{index:02d}_{source.name}"
        shutil.copy2(source, target)
        saved.append(target)
    return saved

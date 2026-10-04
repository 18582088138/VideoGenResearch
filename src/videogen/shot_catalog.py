"""镜头卡索引加载 / Shot-card catalog loading.

数据源是 ``scripts/build_shot_catalog.py`` 生成的 JSON，本模块只读不写。
**不读取卡片正文** —— 正文按需单独读，避免把 157 张卡的全文灌进上下文。

Reads the JSON produced by ``scripts/build_shot_catalog.py``. Card bodies
(motion recipe / parameter table / known pitfalls) are deliberately **not**
loaded here; read them individually on demand.
"""

from __future__ import annotations

import json
from pathlib import Path

from videogen.models import ShotCard
from videogen.paths import shot_catalog_json


def load_catalog(path: Path | None = None) -> list[ShotCard]:
    """读取全部镜头卡元数据 / Load all shot-card metadata.

    :param path: 覆盖默认索引位置（供单测注入 fixture）/ Override for tests.
    :raises FileNotFoundError: 索引不存在，提示先跑生成脚本。
    """
    target = path or shot_catalog_json()
    if not target.exists():
        raise FileNotFoundError(
            f"镜头卡索引不存在 / shot catalog not found: {target}\n"
            "请先运行 / run first: python scripts/build_shot_catalog.py"
        )

    raw = json.loads(target.read_text(encoding="utf-8"))
    return [
        ShotCard(
            name=item["name"],
            category=item.get("category", ""),
            file=item.get("file", ""),
            summary=item.get("summary", ""),
            use_for=item.get("use_for", ""),
            duration=item.get("duration", ""),
            duration_frames=item.get("duration_frames"),
            energy=item.get("energy", ""),
            tags=item.get("tags", ""),
        )
        for item in raw
    ]


def index_by_name(cards: list[ShotCard]) -> dict[str, ShotCard]:
    """按卡名建索引，供按名查找与校验。

    Index cards by name, for lookup and for validating LLM-proposed names.
    """
    return {c.name: c for c in cards}


def filter_by_category(cards: list[ShotCard], category: str) -> list[ShotCard]:
    """按类别筛选 / Filter cards by category directory name."""
    return [c for c in cards if c.category == category]


def load_body(card: ShotCard, repo_root: Path | None = None) -> str:
    """按需读取**单张**卡片正文 / Read a single card body on demand.

    只在真正要按卡实现时调用 —— 这是本模块唯一会读正文的入口，
    以便控制上下文成本。
    """
    from videogen.paths import source_repo_root

    root = repo_root or source_repo_root()
    return (root / "references" / "shots" / card.file).read_text(encoding="utf-8")

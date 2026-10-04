"""素材加载与镜头卡索引单测 / Unit tests for asset and shot-catalog loaders.

测试说明文档 / Test documentation
    见 docs/03_unit_tests.md 「assets / shot_catalog」一节。

复测指令 / How to re-run
    cd C:\\Users\\75203\\Downloads\\xd\\VideoGenResearch-deepseek
    C:\\Users\\75203\\miniforge3\\envs\\ov_env_py312\\python.exe -m pytest tests/test_assets.py -v

预期结果 / Expected
    全部通过。零费用、不联网。

前置条件 / Precondition
    assets/shot_catalog.json 存在。若缺失，先跑：
    python scripts/build_shot_catalog.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from videogen import assets as assets_mod
from videogen import shot_catalog as catalog_mod
from videogen.paths import assets_dir, images_index_json, shot_catalog_json


# ── 镜头卡目录 / Shot catalog ──────────────────────────────────────────────


def test_catalog_loads_all_cards() -> None:
    """镜头卡总数为 157（video-shotcraft @ 5ddbf52 实测）。"""
    cards = catalog_mod.load_catalog()

    assert len(cards) == 157


def test_catalog_categories_match_source_layout() -> None:
    """10 个类别的卡片数与源仓库子目录一致。"""
    cards = catalog_mod.load_catalog()
    counts: dict[str, int] = {}
    for c in cards:
        counts[c.category] = counts.get(c.category, 0) + 1

    assert counts == {
        "opening": 11,
        "typography": 26,
        "camera": 10,
        "data": 13,
        "ui-entrance": 28,
        "interaction": 15,
        "effects": 17,
        "transition": 19,
        "rhythm": 11,
        "outro": 7,
    }


def test_catalog_index_by_name_is_unique() -> None:
    """卡名唯一 —— LLM 输出卡名时按名查表必须无歧义。"""
    cards = catalog_mod.load_catalog()
    idx = catalog_mod.index_by_name(cards)

    assert len(idx) == len(cards)
    assert "counter-confetti" in idx
    assert idx["counter-confetti"].category == "data"


def test_catalog_every_card_has_summary_and_file() -> None:
    """每张卡都必须有「一句话」与相对文件路径，否则无法用于选型或定位正文。"""
    for card in catalog_mod.load_catalog():
        assert card.summary, f"{card.name} 缺一句话"
        assert card.file.endswith(".md"), f"{card.name} 的 file 不是 md"


def test_filter_by_category() -> None:
    """按类别筛选返回的卡全部属于该类别。"""
    cards = catalog_mod.load_catalog()
    outro = catalog_mod.filter_by_category(cards, "outro")

    assert len(outro) == 7
    assert all(c.category == "outro" for c in outro)


def test_load_catalog_missing_file_gives_actionable_error(tmp_path: Path) -> None:
    """索引缺失时应报错并提示修复脚本，而不是抛裸 FileNotFoundError。"""
    missing = tmp_path / "nope.json"

    with pytest.raises(FileNotFoundError, match="build_shot_catalog"):
        catalog_mod.load_catalog(missing)


# ── 图片素材 / Image assets ────────────────────────────────────────────────


def test_images_index_has_seven_assets() -> None:
    """图片素材共 7 张，与源目录一致。"""
    imgs = assets_mod.load_images()

    assert len(imgs) == 7
    assert {i.file for i in imgs} == {
        "01_mmbiz-qpic-cn.jpg",
        "03_mmbiz-qpic-cn.jpg",
        "04_mmbiz-qpic-cn.png",
        "05_mmbiz-qpic-cn.png",
        "06_mmbiz-qpic-cn.png",
        "07_mmbiz-qpic-cn.png",
        "08_mmbiz-qpic-cn.png",
    }


def test_every_image_has_semantic_label() -> None:
    """每张图都必须有人工判读的语义标签。

    原始抓取元数据 caption 全为 null，没有标签就不能让 LLM 做素材分配。
    """
    for img in assets_mod.load_images():
        assert img.label, f"{img.file} 缺 label"
        assert img.narrative_use, f"{img.file} 缺 narrative_use"
        assert img.suggested_shots, f"{img.file} 缺 suggested_shots"


def test_declared_dimensions_match_real_files() -> None:
    """索引里声明的宽高必须与真实文件一致（防止素材被替换后静默错版）。"""
    problems = assets_mod.verify_images(assets_mod.load_images())

    assert problems == [], problems


def test_radar_chart_is_the_designated_hero_shot() -> None:
    """07 雷达图被指定为全场最佳镜头，其 suggested_shots 不应为空。

    这是设计决策的回归保护：若有人误删该标注，选型阶段会失去依据。
    """
    radar = next(i for i in assets_mod.load_images() if i.file.startswith("07_"))

    assert radar.kind == "radar_comparison"
    assert radar.aspect > 2.0  # 宽幅横向图
    assert len(radar.suggested_shots) >= 1


def test_missing_image_index_gives_clear_error(tmp_path: Path) -> None:
    """索引缺失时报错信息应含实际查找路径。"""
    with pytest.raises(FileNotFoundError, match="image index"):
        assets_mod.load_images(tmp_path / "nope.json")


# ── 生成物自洽性 / Generated-artifact consistency ──────────────────────────


def test_catalog_json_is_valid_and_utf8() -> None:
    """索引 JSON 可被解析且中文未被转义成 unicode 逃逸。

    中文保持可读是有意的：这些文件要给人 grep 和人工审阅。
    """
    text = shot_catalog_json().read_text(encoding="utf-8")
    data = json.loads(text)

    assert len(data) == 157
    assert "\\u" not in text[:2000], "中文应保持可读，不应被转义"


def test_image_index_json_declares_its_source() -> None:
    """图片索引应记录来源路径，便于追溯素材出处（版权核查需要）。"""
    raw = json.loads(images_index_json().read_text(encoding="utf-8"))

    assert "DailyNewsAssistant" in raw["_source"]
    assert "Science" in raw["_article"]

"""中文数字规范化单测 / Chinese numeral normalisation tests.

对应 ``src/videogen/numbers.py``。用户口径：视频文案与分镜里的数字直接用数字。

**这些用例的重点是「不该转的不要转」** —— 中文里「一」的构词能力极强
（一起 / 一致 / 这是一个），误伤会让文案读起来像机翻，比不转更糟。

复测指令 / How to re-run:
    $py = "C:\\Users\\75203\\miniforge3\\envs\\ov_env_py312\\python.exe"
    cd C:\\Users\\75203\\Downloads\\xd\\VideoGenResearch-deepseek
    & $py -m pytest tests\\test_numbers.py -v
"""

from __future__ import annotations

import pytest

from videogen.numbers import normalize


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # ── 小数量词：含「点」一律是数值 ──
        ("零点三四四米", "0.344米"),
        ("零点一八六米", "0.186米"),
        ("零点三秒", "0.3秒"),
        ("约一秒观测", "约1秒观测"),
        # ── 百分之 → % ──
        # 「百分之」里的「百」不能被单独当成数值，否则会得到「100分之46%」
        ("降幅约百分之四十六", "降幅约46%"),
        ("成功率百分之八十至百分之九十", "成功率80%至90%"),
        ("百分之百", "100%"),
        # ── 位值制整数 ──
        ("压缩为六十四维", "压缩为64维"),
        ("控制器以五十赫兹输出", "控制器以50赫兹输出"),
        ("平均延迟一百一十六毫秒", "平均延迟116毫秒"),
        # ── 逐位读（年份/编号）──
        ("二零二五年拿下冠军", "2025年拿下冠军"),
        # ── 单字 + 量词 ──
        ("覆盖七种模态", "覆盖7种模态"),
        ("流程分四层", "流程分4层"),
        ("文本、图像、音频、视频、文档、三维、代码", "文本、图像、音频、视频、文档、3维、代码"),
    ],
)
def test_converts_real_numbers(text: str, expected: str) -> None:
    """真正的数值要转成阿拉伯数字。"""
    assert normalize(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        # 「一」的非数值构词 —— 这些是最容易被误伤的
        "一起接进通用智能体",
        "一致收敛到同一个目标",
        "这是一个关键点",
        "一般来说这样更好",
        "一直在跑",
        "一定可以",
        "一切正常",
    ],
)
def test_keeps_non_numeric_words(text: str) -> None:
    """非数值词原样保留 —— 这是本模块最重要的防御。"""
    assert normalize(text) == text


def test_empty_and_ascii_untouched() -> None:
    """空串与纯 ASCII 不做任何改动。"""
    assert normalize("") == ""
    assert normalize("Omni-IO Skills") == "Omni-IO Skills"
    assert normalize("50 Hz / 64 dims") == "50 Hz / 64 dims"


def test_numeric_shortens_text() -> None:
    """规范化会让文案**变短** —— 对字数约束是好事。"""
    before = "真机前场成功率百分之八十至百分之九十"
    after = normalize(before)

    assert len(after) < len(before)

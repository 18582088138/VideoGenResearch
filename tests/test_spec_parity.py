"""跨语言契约一致性 / Cross-language contract parity.

**这个测试是"补"出来的**：``src/videogen/spec.py`` 的注释从很早就引用
``tests/test_spec_parity.py``，但该文件**实际不存在**（2026-10 复核时发现，
全工作区搜索无果）。注释与仓库现状不符，比没有注释更危险 ——
它让人以为有一道防线，其实没有。

它守的是一个**真实踩过的坑**：TS 端加过 3 个图文类型却忘了同步 Python 侧，
于是脚本一生成 ``figure-panel`` 就被校验器拒绝（见 ``docs/issues/006``）。

做法是**直接解析 TypeScript 源文件**（不跑 node），把两侧的权威定义摆在一起比：

1. ``ShotType`` 联合 == ``SHOT_TYPES``（含顺序）
2. ``Literal[...]`` 类型 == ``SHOT_TYPES``
3. ``REQUIRED_FIELDS`` 的键集 == ``SHOT_TYPES``
4. 两侧都无重复项
5. ``REQUIRED_FIELDS`` 用到的字段名都能在 TS ``ShotSpec`` 接口里找到
6. TS ``ShotSpec`` 有 ``image2``（``image-pair`` 依赖）
7. ``ShotRenderer.tsx`` 为每个 type 都有 case

复测指令 / How to re-run::

    $py = "C:\\Users\\75203\\miniforge3\\envs\\ov_env_py312\\python.exe"
    cd C:\\Users\\75203\\Downloads\\xd\\VideoGenResearch-deepseek
    & $py -m pytest tests\\test_spec_parity.py -v

为什么解析源码而不是生成 JSON 再比：生成物会过期，源码不会 ——
两边**同时**改才可能一致，这正是要守的东西。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from videogen.spec import IMAGE_SHOT_TYPES, REQUIRED_FIELDS, SHOT_TYPES

ROOT = Path(__file__).resolve().parents[1]
TYPES_TS = ROOT / "remotion" / "src" / "compositions" / "types.ts"
RENDERER_TS = ROOT / "remotion" / "src" / "shots" / "ShotRenderer.tsx"


def _read(path: Path) -> str:
    assert path.exists(), f"找不到契约文件 / contract file missing: {path}"
    return path.read_text(encoding="utf-8")


def _ts_union_members() -> list[str]:
    """解析 ``ShotType`` 联合的成员（含顺序）/ Parse the union members in order."""
    source = _read(TYPES_TS)
    match = re.search(r"export type ShotType\s*=(.*?);", source, re.S)
    assert match, "types.ts 里找不到 ShotType 联合"
    body = match.group(1)
    return re.findall(r'"([a-z-]+)"', body)


def _ts_interface_fields(interface: str = "ShotSpec") -> set[str]:
    """解析某个接口的字段名 / Parse the field names of one interface."""
    source = _read(TYPES_TS)
    match = re.search(rf"export interface {interface}\s*\{{(.*?)\n\}}", source, re.S)
    assert match, f"types.ts 里找不到 {interface} 接口"
    body = match.group(1)
    # 只取行首的 `name?: type;` / `name: type;`，避开注释里的示例
    return set(re.findall(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\??\s*:", body, re.M))


# ── 1. 类型集合一致 ────────────────────────────────────────────────────────


def test_ts_union_matches_python_shot_types_in_order() -> None:
    """TS 的 ShotType 联合与 Python 的 SHOT_TYPES 必须逐项、同序一致。

    顺序也查，是因为 ``build_catalog`` 按 SHOT_TYPES 的分组顺序生成清单，
    两侧顺序不一致会让"可用动效清单"的归类看起来随机。
    """
    assert _ts_union_members() == list(SHOT_TYPES)


def test_no_duplicate_types() -> None:
    """两侧都不能有重复项（重复会让校验与分派出现"幽灵分支"）。"""
    ts = _ts_union_members()
    assert len(ts) == len(set(ts)), f"TS 联合有重复: {ts}"

    py = list(SHOT_TYPES)
    assert len(py) == len(set(py)), f"SHOT_TYPES 有重复: {py}"


def test_required_fields_covers_every_type() -> None:
    """REQUIRED_FIELDS 的键集必须与 SHOT_TYPES 完全一致。"""
    assert set(REQUIRED_FIELDS) == set(SHOT_TYPES)


# ── 2. 字段名两侧都存在 ────────────────────────────────────────────────────


def test_required_field_names_exist_on_ts_interface() -> None:
    """REQUIRED_FIELDS 里用到的字段名，TS 接口里必须都有。

    这是**最容易漏的一环**：Python 侧加了必需字段、TS 侧忘了加，
    于是 props 传不过去、组件拿不到数据（``image2`` 就是这么漏的 ——
    ``compile.py`` 当时也没输出它）。
    """
    fields = _ts_interface_fields()
    used: set[str] = set()
    for names in REQUIRED_FIELDS.values():
        used.update(names)

    missing = sorted(used - fields)
    assert not missing, f"TS ShotSpec 缺这些字段: {missing}"


def test_ts_interface_has_image2() -> None:
    """``image-pair`` 依赖 ``image2`` —— 这是它能不能工作的关键字段。"""
    assert "image2" in _ts_interface_fields()


def test_image_shot_types_are_declared_in_ts() -> None:
    """素材类类型必须都在 TS 联合里（它们要用 image）。"""
    missing = sorted(IMAGE_SHOT_TYPES - set(_ts_union_members()))
    assert not missing, f"TS 联合缺素材类类型: {missing}"


# ── 3. 渲染器有对应分支 ────────────────────────────────────────────────────


def test_renderer_handles_every_type() -> None:
    """``ShotRenderer`` 必须为**每个** type 都有分支。

    少一个 case 的后果不是编译错误，而是运行时那个镜头**画不出东西**
    （或落到默认分支），属于最难查的一类问题。
    """
    source = _read(RENDERER_TS)
    missing = [t for t in SHOT_TYPES if f'"{t}"' not in source and f"'{t}'" not in source]
    assert not missing, f"ShotRenderer 缺这些 type 的分支: {missing}"


def test_renderer_imports_every_shot_component() -> None:
    """每个 type 都应有对应的组件文件（命名按 camel case 映射）。"""
    shots_dir = ROOT / "remotion" / "src" / "shots"
    missing: list[str] = []
    for shot_type in SHOT_TYPES:
        # kebab-case → PascalCase，例如 page-spotlight → PageSpotlight
        component = "".join(part.capitalize() for part in shot_type.split("-")) + ".tsx"
        if not (shots_dir / component).exists():
            missing.append(f"{shot_type} → {component}")
    assert not missing, f"缺少组件文件: {missing}"


@pytest.mark.parametrize("shot_type", sorted(IMAGE_SHOT_TYPES))
def test_image_types_require_an_image(shot_type: str) -> None:
    """素材类类型必须要求 ``image`` —— 否则镜头会渲成空白。"""
    assert "image" in REQUIRED_FIELDS[shot_type]

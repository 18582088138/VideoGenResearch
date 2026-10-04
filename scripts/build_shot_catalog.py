"""从 video-shotcraft 镜头卡抽取索引目录 / Build shot-card catalog from video-shotcraft.

用途 / Purpose
    157 张镜头卡的 frontmatter（含 name / 一句话 / 适用 / 时长 / 能量）抽取成
    一张速查表 + 机器可读 JSON，作为本项目 ``shot_catalog`` 的唯一数据源。
    **只读 frontmatter，不读卡片正文** —— 正文按需加载，避免 token 浪费。

数据源 / Source
    C:\\Users\\75203\\Downloads\\xd\\video-shotcraft\\references\\shots\\**\\*.md
    （157 张卡，10 个类别子目录）

复测指令 / How to re-run
    C:\\Users\\75203\\miniforge3\\envs\\ov_env_py312\\python.exe ^
        VideoGenResearch-deepseek\\scripts\\build_shot_catalog.py

预期输出 / Expected
    VideoGenResearch-deepseek\\docs\\research\\shot_catalog.md   人类速查表
    VideoGenResearch-deepseek\\assets\\shot_catalog.json        机器可读索引
    终端打印各类别卡片数与总卡数。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOTS_DIR = ROOT.parent / "video-shotcraft" / "references" / "shots"

MD_OUT = ROOT / "docs" / "research" / "shot_catalog.md"
JSON_OUT = ROOT / "assets" / "shot_catalog.json"

# frontmatter 里出现的键；顺序即输出顺序，便于人工扫读
KEYS = ["name", "一句话", "适用", "时长", "能量", "标签"]

# 类别排序：按「一支视频的时间顺序」而非字母序，扫表更顺
CATEGORY_ORDER = [
    "opening",
    "typography",
    "camera",
    "data",
    "ui-entrance",
    "interaction",
    "effects",
    "transition",
    "rhythm",
    "outro",
]

CATEGORY_CN = {
    "opening": "开场",
    "typography": "文字/排版",
    "camera": "运镜",
    "data": "数据/图表",
    "ui-entrance": "UI 元素入场",
    "interaction": "交互/光标",
    "effects": "特效/光效",
    "transition": "转场",
    "rhythm": "节奏/卡点",
    "outro": "收尾",
}


def parse_frontmatter(text: str) -> dict[str, str]:
    """解析 YAML frontmatter 的顶层 `key: value` 行。

    Parse top-level ``key: value`` lines of the YAML frontmatter.
    只做浅解析：本仓库的卡片卡头全是单行标量，引入 PyYAML 不划算。
    """
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return {}
    data: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.startswith((" ", "\t", "#", "-")):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        data[key.strip()] = value.strip()
    return data


def extract_duration_frames(duration: str) -> int | None:
    """从「时长」文本里尽力抽出主时长（秒），用于粗排时间线。

    Best-effort primary duration in seconds, for rough timeline budgeting.
    卡片里常见写法：「约 6.0s（180f@30fps…）」「约 0.5s 动作 + 前后 hold」。
    取第一个 ``N.Ns`` 作为主时长；带区间的取区间上限。
    """
    seconds = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*s", duration)]
    if not seconds:
        return None
    # 形如「2–5s」「2-5s」区间，取靠后的较大值
    return int(round(max(seconds[:2]) * 30))


def main() -> None:
    cards: list[dict] = []
    for path in sorted(SHOTS_DIR.rglob("*.md")):
        if path.name == "ATTRIBUTION.md":
            continue
        fm = parse_frontmatter(path.read_text(encoding="utf-8"))
        if not fm.get("name"):
            continue
        rel = path.relative_to(SHOTS_DIR)
        cards.append(
            {
                "name": fm.get("name", ""),
                "category": path.parent.name,
                "file": str(rel).replace("\\", "/"),
                "summary": fm.get("一句话", ""),
                "use_for": fm.get("适用", ""),
                "duration": fm.get("时长", ""),
                "duration_frames": extract_duration_frames(fm.get("时长", "")),
                "energy": fm.get("能量", ""),
                "tags": fm.get("标签", ""),
            }
        )

    # 按类别顺序 + 卡名排序，保证输出稳定（可复现）
    order = {c: i for i, c in enumerate(CATEGORY_ORDER)}
    cards.sort(key=lambda c: (order.get(c["category"], 99), c["name"]))

    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(cards, ensure_ascii=False, indent=2), encoding="utf-8")

    lines: list[str] = [
        "# 镜头卡索引 — video-shotcraft 157 张",
        "",
        "> **什么时候加载**：选镜头卡、构建 `shot_catalog`、核算分镜时长预算时。",
        "> **本文件由脚本生成，请勿手工编辑** —— 改 `scripts/build_shot_catalog.py` 后重跑。",
        "> 卡片正文（动效核心 / 参数表 / 已知坑 / 参考实现）**按需单独读**，不要一次读进来。",
        "",
        f"数据源：`video-shotcraft/references/shots/`　卡片总数：**{len(cards)}**",
        "",
        "「帧预估」由「时长」文本粗抽（30fps），仅用于排时间线时的心算参考，**非精确值**。",
        "",
        "## 类别目录",
        "",
        "| 类别 | 中文 | 卡片数 |",
        "|---|---|---|",
    ]
    counts: dict[str, int] = {}
    for c in cards:
        counts[c["category"]] = counts.get(c["category"], 0) + 1
    for cat in CATEGORY_ORDER:
        if cat in counts:
            lines.append(f"| `{cat}` | {CATEGORY_CN.get(cat, '')} | {counts[cat]} |")
    lines.append(f"| **合计** | | **{len(cards)}** |")
    lines.append("")

    for cat in CATEGORY_ORDER:
        group = [c for c in cards if c["category"] == cat]
        if not group:
            continue
        lines.append(f"## {CATEGORY_CN.get(cat, cat)} · `{cat}`（{len(group)} 张）")
        lines.append("")
        lines.append("| 卡名 | 一句话 | 时长 | 帧预估 | 能量 |")
        lines.append("|---|---|---|---|---|")
        for c in group:
            summary = c["summary"].replace("|", "\\|")
            duration = c["duration"].replace("|", "\\|")
            energy = c["energy"].split("（")[0]
            frames = c["duration_frames"] or ""
            lines.append(f"| `{c['name']}` | {summary} | {duration} | {frames} | {energy} |")
        lines.append("")

    MD_OUT.parent.mkdir(parents=True, exist_ok=True)
    MD_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"saved: {MD_OUT}")
    print(f"saved: {JSON_OUT}")
    print(f"total cards: {len(cards)}")
    for cat in CATEGORY_ORDER:
        if cat in counts:
            print(f"  {cat:<14} {counts[cat]}")


if __name__ == "__main__":
    main()

"""素材图片自动语义标注 / Auto-annotate asset images.

薄壳：`素材集里的图片 → 视觉模型 → images/index.json`。
**零业务逻辑** —— 逻辑在 ``videogen.vision``。

Thin shell over ``videogen.vision``: turn a set's images into the semantic index
the planner reads. This used to be the only hand-written step in the pipeline.

复测指令 / How to re-run:
    $py = "C:\\Users\\75203\\miniforge3\\envs\\ov_env_py312\\python.exe"
    cd C:\\Users\\75203\\Downloads\\xd\\VideoGenResearch-deepseek

    # 标注一个素材集（**会产生视觉模型调用费用；默认走免费模型**）
    & $py scripts\\annotate_images.py --set omni-io-skills

    # 只标注某一张（已有标注的跳过）
    & $py scripts\\annotate_images.py --set omni-io-skills --only 04_arxiv-org.png

    # 重标全部（覆盖已有标注）
    & $py scripts\\annotate_images.py --set omni-io-skills --force

输出 / Output:
    assets/sets/<set>/images/index.json   语义索引（规划质量的主要输入）

**默认不覆盖已有标注** —— 人工改过的内容不该被一次重跑抹掉。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from videogen import ocr  # noqa: E402
from videogen.sources import AssetSetError, load_set  # noqa: E402
from videogen.vision import VisionError, annotate_image  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="素材图片自动标注 / Auto-annotate images")
    ap.add_argument("--set", dest="set_name", required=True, help="素材集名")
    ap.add_argument("--only", default=None, help="只标注这一个文件名")
    ap.add_argument("--force", action="store_true", help="覆盖已有标注")
    args = ap.parse_args()

    try:
        asset_set = load_set(args.set_name)
    except AssetSetError as exc:
        print(f"素材集错误 / asset set error: {exc}")
        return 2

    images = asset_set.image_files()
    if not images:
        print(f"素材集里没有图片 / no images under {asset_set.images_dir}")
        return 2

    # 读已有索引，保留其中的人工/既有标注
    index_path = asset_set.images_index
    existing: dict[str, dict] = {}
    if index_path.exists():
        try:
            raw = json.loads(index_path.read_text(encoding="utf-8"))
            existing = {item["file"]: item for item in raw.get("assets", [])}
        except (json.JSONDecodeError, KeyError, OSError) as exc:
            print(f"已有索引读不动，将重建 / existing index unreadable: {exc}")

    print(f"素材集 / set : {asset_set.describe()}")
    print(f"图片 / images: {len(images)} 张")
    print(f"OCR         : {ocr.describe()}")
    print()

    ocr_ready = ocr.is_available()
    entries: list[dict] = []
    annotated = skipped = failed = 0

    for path in images:
        if args.only and path.name != args.only:
            # 未指定的图：沿用已有标注（没有则跳过，留待下次）
            if path.name in existing:
                entries.append(existing[path.name])
            continue

        if path.name in existing and not args.force:
            entries.append(existing[path.name])
            skipped += 1
            print(f"  [跳过] {path.name}（已有标注，用 --force 重标）")
            continue

        # 有 OCR 就先取文字，作为 grounding 交给视觉模型 ——
        # 专有名词以 OCR 为准，避免 VLM 把它们看错（实测 Omni-IO 被读成 Omni-10）。
        grounding = ""
        if ocr_ready:
            grounding = ocr.ocr_text(path)
            if grounding:
                print(f"  [OCR]  {path.name}: 取到 {len(grounding)} 字作为 grounding")

        try:
            note = annotate_image(path, grounding=grounding)
        except VisionError as exc:
            failed += 1
            print(f"  [失败] {path.name}: {exc}")
            if path.name in existing:
                entries.append(existing[path.name])
            continue

        from PIL import Image

        with Image.open(path) as im:
            width, height = im.size
        entry = note.to_index_entry(path.name, width, height)
        entries.append(entry)
        annotated += 1
        print(f"  [标注] {path.name}")
        print(f"         label : {entry['label']}")
        print(f"         desc  : {entry['description'][:70]}…")
        print(f"         用途  : {entry['narrative_use'][:60]}…")
        print(f"         建议  : {', '.join(entry['suggested_shots'])}")
        print()

    # 按文件名排序，输出稳定（便于 diff）
    entries.sort(key=lambda e: e["file"])
    index_path.write_text(
        json.dumps(
            {
                "set": asset_set.name,
                "note": "由 scripts/annotate_images.py 自动标注；建议人工复核后再正式出片。",
                "assets": entries,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"已落盘 / saved: {index_path}")
    print(f"  新标注 {annotated} · 跳过 {skipped} · 失败 {failed} · 索引共 {len(entries)} 条")
    if failed:
        print("  有失败项：可稍后重跑（已标注的会跳过，不会重复计费）")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

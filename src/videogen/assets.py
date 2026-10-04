"""素材加载 / Asset loading.

图片素材的语义标注在 ``assets/images/index.json``（人工判读，因为原始抓取
元数据的 ``caption`` 全为 null）。本模块把该索引读成 :class:`ImageAsset`。

Image semantics live in ``assets/images/index.json`` (hand-annotated, since the
scrape metadata has null captions everywhere).
"""

from __future__ import annotations

import json
from pathlib import Path

from videogen.models import ImageAsset
from videogen.paths import assets_dir, images_index_json


def load_images(path: Path | None = None) -> list[ImageAsset]:
    """读取图片素材语义索引 / Load the image asset semantic index.

    :param path: 覆盖默认索引位置（供单测注入 fixture）/ Override for tests.
    """
    target = path or images_index_json()
    if not target.exists():
        raise FileNotFoundError(
            f"图片素材索引不存在 / image index not found: {target}"
        )

    raw = json.loads(target.read_text(encoding="utf-8"))
    return [
        ImageAsset(
            file=item["file"],
            width=int(item["width"]),
            height=int(item["height"]),
            aspect=float(item["aspect"]),
            role=item.get("role", ""),
            kind=item.get("kind", ""),
            label=item.get("label", ""),
            description=item.get("description", ""),
            narrative_use=item.get("narrative_use", ""),
            suggested_shots=tuple(item.get("suggested_shots", ())),
            notes=item.get("notes", ""),
        )
        for item in raw["assets"]
    ]


def image_path(asset: ImageAsset, base: Path | None = None) -> Path:
    """解析素材的绝对路径 / Resolve an asset's absolute path."""
    root = base or (assets_dir() / "images")
    return root / asset.file


def verify_images(assets: list[ImageAsset], base: Path | None = None) -> list[str]:
    """核对索引里声明的文件是否真实存在且尺寸一致。

    Verify that every indexed file exists and matches its recorded dimensions.

    :return: 问题描述列表；空列表表示全部通过。
        A list of problem descriptions; empty means everything checks out.
    """
    problems: list[str] = []
    for asset in assets:
        path = image_path(asset, base)
        if not path.exists():
            problems.append(f"文件缺失 / missing: {asset.file}")
            continue
        try:
            from PIL import Image

            with Image.open(path) as im:
                if (im.width, im.height) != (asset.width, asset.height):
                    problems.append(
                        f"尺寸不符 / size mismatch: {asset.file} "
                        f"索引 {asset.width}x{asset.height}，实际 {im.width}x{im.height}"
                    )
        except ImportError:  # Pillow 缺失时只做存在性检查
            continue
    return problems

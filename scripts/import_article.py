"""素材导入入口 / Asset-set import entry script.

薄壳：把一篇 DailyNewsAssistant 产物目录导入成一套素材集。
**零业务逻辑** —— 逻辑在 ``videogen.sources``。

Thin shell over ``videogen.sources``: turn one DailyNewsAssistant article output
folder into an asset set the planner and renderer can consume.

复测指令 / How to re-run:
    $py = "C:\\Users\\75203\\miniforge3\\envs\\ov_env_py312\\python.exe"
    cd C:\\Users\\75203\\Downloads\\xd\\VideoGenResearch-deepseek

    # 导入（自动推导素材集名，去掉末尾 hash）
    & $py scripts\\import_article.py "C:\\...\\20261004\\Omni-IO-Skills开源-...__4111bfcf"

    # 指定名字 / 覆盖已存在的
    & $py scripts\\import_article.py "<目录>" --name omni-io-skills --force

    # 看看有哪些素材集
    & $py scripts\\import_article.py --list

零费用：本脚本只做本地文件复制与元信息解析，不调用任何 API。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from videogen.assets import verify_images  # noqa: E402
from videogen.assets import load_images  # noqa: E402
from videogen.sources import (  # noqa: E402
    AssetSetError,
    import_from_article,
    list_sets,
    load_set,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="导入素材集 / Import an asset set")
    ap.add_argument("article_dir", nargs="?", help="DailyNewsAssistant 产物目录")
    ap.add_argument("--name", default=None, help="素材集名（默认由目录名推导）")
    ap.add_argument("--force", action="store_true", help="覆盖同名素材集")
    ap.add_argument("--list", action="store_true", help="列出已有素材集后退出")
    args = ap.parse_args()

    if args.list or not args.article_dir:
        names = list_sets()
        print(f"素材集 / asset sets（{len(names)}）:")
        for name in names:
            try:
                print(f"  - {load_set(name).describe()}")
            except AssetSetError as exc:  # 元信息坏了也要能列出来
                print(f"  - {name}  (读取失败 / unreadable: {exc})")
        return 0 if args.list else 2

    try:
        asset_set = import_from_article(
            Path(args.article_dir), name=args.name, force=args.force
        )
    except AssetSetError as exc:
        print(f"导入失败 / import failed: {exc}")
        return 2

    # ── 校验：图片索引存在且尺寸对得上 ──────────────────────────────────────
    print(f"导入完成 / imported: {asset_set.describe()}")
    print(f"  目录 / root : {asset_set.root}")
    print(f"  音频 / audio: {asset_set.audio.name}")
    print(f"  字幕 / srt  : {asset_set.srt().name}")
    print(f"  标题 / title: {asset_set.title or '(空)'}")
    print(f"  副标 / sub  : {asset_set.subtitle or '(空)'}")

    if asset_set.images_index.exists():
        images = load_images(asset_set.images_index())
        problems = verify_images(images, asset_set.images_dir)
        print(f"  图片 / images: {len(images)} 张，索引校验 "
              f"{'通过' if not problems else f'{len(problems)} 个问题'}")
        for problem in problems:
            print(f"    ! {problem}")
    else:
        print(f"  ! 缺少图片语义索引 / no image index: {asset_set.images_index}")
        print(f"    规划质量依赖语义标注，建议补一份"
              f"（结构见 assets/sets/omni-io-skills/images/index.json）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

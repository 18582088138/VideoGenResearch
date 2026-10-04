"""生成主题配色色卡预览图 / Generate theme palette swatch previews.

用途 / Purpose
    为视频主题选定配色时，快速出一张可视化色卡供人工挑选。
    纯离线绘图，不依赖网络与 Remotion。

复测指令 / How to re-run
    C:\\Users\\75203\\miniforge3\\envs\\ov_env_py312\\python.exe ^
        VideoGenResearch-deepseek\\scripts\\make_palette_swatch.py

预期输出 / Expected
    VideoGenResearch-deepseek\\docs\\design\\01_theme_swatches.png
    终端打印 5 套主题名与各自 tag 列表。
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# 输出路径：脚本位于 scripts/，文档在 docs/design/
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "design" / "01_theme_swatches.png"

# 中文字体优先用思源黑体（OFL 可商用）；msyh.ttc 是 TTC 集合，PIL 索引不稳定，不优先
CJK_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\NotoSansSC-VF.ttf",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\msyh.ttc",
]

# ── 主题定义 / Theme definitions ────────────────────────────────────────────
# 每套主题给出 5~6 个色：底 / 面 / 面2 / 主强调 / 次强调 / 警示(可选)
THEMES: list[dict] = [
    {
        "id": "deep-space",
        "name": "深空蓝 · Deep Space",
        "note": "标准科技蓝，最稳。蓝→青渐变，适合新闻/科研选题。",
        "colors": [
            ("bg", "#05070D"),
            ("surface", "#0E1524"),
            ("surface2", "#1A2438"),
            ("primary", "#4D8DFF"),
            ("accent", "#22D3EE"),
            ("alert", "#FFB020"),
        ],
    },
    {
        "id": "cyan-noir",
        "name": "暗青水墨 · Cyan Noir",
        "note": "近黑底 + 青绿高光，电影感最强，画面最「贵」。",
        "colors": [
            ("bg", "#04080A"),
            ("surface", "#0B1418"),
            ("surface2", "#15242A"),
            ("primary", "#2DD4BF"),
            ("accent", "#7DF9FF"),
            ("alert", "#F97362"),
        ],
    },
    {
        "id": "violet-pulse",
        "name": "赛博紫 · Violet Pulse",
        "note": "紫 + 电光青，赛博感最强，偏年轻向平台。",
        "colors": [
            ("bg", "#0A0714"),
            ("surface", "#171029"),
            ("surface2", "#241A3D"),
            ("primary", "#8B5CF6"),
            ("accent", "#22D3EE"),
            ("alert", "#F472B6"),
        ],
    },
    {
        "id": "carbon-lime",
        "name": "碳黑荧光 · Carbon Lime",
        "note": "近黑 + 荧光绿，数据/算法气质，数字翻转最抓眼。",
        "colors": [
            ("bg", "#060A08"),
            ("surface", "#101815"),
            ("surface2", "#1B2622"),
            ("primary", "#A3E635"),
            ("accent", "#38BDF8"),
            ("alert", "#FB7185"),
        ],
    },
    {
        "id": "ember-teal",
        "name": "熔岩青 · Ember Teal",
        "note": "暖橙 + 冷青互补，冲击力最强，适合「对决/对比」叙事。",
        "colors": [
            ("bg", "#0B0806"),
            ("surface", "#1A1310"),
            ("surface2", "#2A1F19"),
            ("primary", "#FF7A45"),
            ("accent", "#2DD4BF"),
            ("alert", "#FFD166"),
        ],
    },
]

W, ROW_H = 1500, 190
PAD, SW = 34, 132


def load_font(size: int) -> ImageFont.FreeTypeFont:
    """挑选第一个可用的中文字体。Pick the first usable CJK font."""
    for path in CJK_FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def relative_luminance(rgb: tuple[int, int, int]) -> float:
    """WCAG 相对亮度，用于自动决定色块上的文字用黑还是白。

    WCAG relative luminance; decides black vs white label text on a swatch.
    """
    channels = []
    for c in rgb:
        s = c / 255
        channels.append(s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4)
    r, g, b = channels
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def draw_theme(draw: ImageDraw.ImageDraw, theme: dict, top: int) -> None:
    f_title, f_note, f_tag = load_font(30), load_font(20), load_font(18)
    f_hex = load_font(19)

    draw.text((PAD, top + 16), theme["name"], font=f_title, fill="#FFFFFF")
    draw.text((PAD, top + 56), theme["note"], font=f_note, fill="#9AA4B2")

    x = PAD
    y = top + 92
    for tag, value in theme["colors"]:
        rgb = hex_to_rgb(value)
        draw.rounded_rectangle([x, y, x + SW, y + 62], radius=10, fill=rgb)
        # 色块上的文字按亮度自动取黑/白，保证可读
        label_fill = "#0B0B0B" if relative_luminance(rgb) > 0.45 else "#FFFFFF"
        draw.text((x + 10, y + 8), tag, font=f_tag, fill=label_fill)
        draw.text((x + 10, y + 32), value, font=f_hex, fill=label_fill)
        x += SW + 12

    # 右侧：模拟「深色底 + 强调色文字 + 主色进度条」的实际观感
    bg = hex_to_rgb(dict(theme["colors"])["bg"])
    draw.rectangle([W - 430, top + 16, W - PAD, top + 168], fill=bg)
    draw.text((W - 410, top + 32), "数字 46%", font=f_title,
              fill=hex_to_rgb(dict(theme["colors"])["accent"]))
    bar = hex_to_rgb(dict(theme["colors"])["primary"])
    draw.rounded_rectangle([W - 410, top + 96, W - 410 + 340, top + 110], radius=7, fill=bar)
    draw.rounded_rectangle([W - 410, top + 126, W - 410 + 150, top + 140], radius=7,
                           fill=hex_to_rgb(dict(theme["colors"])["surface2"]))

    draw.line([PAD, top + ROW_H - 6, W - PAD, top + ROW_H - 6], fill="#232A35", width=1)


def main() -> None:
    height = PAD * 2 + ROW_H * len(THEMES) + 70
    img = Image.new("RGB", (W, height), "#0A0C10")
    draw = ImageDraw.Draw(img)
    draw.text((PAD, 18), "VideoGenResearch-deepseek · 主题配色候选 / Theme candidates",
              font=load_font(26), fill="#E5E7EB")

    for i, theme in enumerate(THEMES):
        draw_theme(draw, theme, PAD + 46 + i * ROW_H)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT)

    # 同时落一份机器可读的 JSON，供 Remotion 主题文件直接消费
    json_out = OUT.with_suffix(".json")
    json_out.write_text(
        json.dumps(
            [{"id": t["id"], "name": t["name"], "note": t["note"],
              "colors": dict(t["colors"])} for t in THEMES],
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )

    print(f"saved: {OUT}")
    print(f"saved: {json_out}")
    for t in THEMES:
        print(f"  {t['id']:<14} {t['name']}  ({len(t['colors'])} colors)")


if __name__ == "__main__":
    main()

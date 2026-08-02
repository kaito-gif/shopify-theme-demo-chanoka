#!/usr/bin/env python3
"""無地で生成したパッケージのラベルにブランド名を合成する。

generate-images.py は「文字はAIが崩す」という理由でラベルを無地のまま出力する。
その前提のうえで、ブランド名はここで版ずれなく載せる。画像生成に文字を書かせると
6点で字形も位置も揃わないため、合成は必ずこちら側で行うこと。

使い方:
    .venv/bin/python scripts/brand-packages.py            # 6点すべて
    .venv/bin/python scripts/brand-packages.py sencha     # 1点だけ
    .venv/bin/python scripts/brand-packages.py --guide    # ラベル枠を重ねた確認用

入力  scripts/output/product-<name>.png
出力  scripts/output/branded/product-<name>.png
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "scripts" / "output"
BRANDED_DIR = OUTPUT_DIR / "branded"

# ラベルに刷る品名。seed-products.py の商品名と対応させる。煎茶だけ品種名まで入れると
# ラベル内で窮屈になるため、パッケージ表記としては茶種のみに留める。
NAMES = {
    "sencha": "煎茶",
    "fukamushi": "深蒸し煎茶",
    "gyokuro": "玉露",
    "hojicha": "ほうじ茶",
    "genmaicha": "玄米茶",
    "matcha": "抹茶",
}

# ラベルの矩形（1024x1024 における left, top, right, bottom）。
# 6点はマスターからの派生なので位置はほぼ同一で、実測のばらつきは十数pxに収まる。
# 個別に検出させると淡いラベル（玄米茶）で地のクラフト紙と混ざって外すため、
# 全点共通の固定値で置く。generate-images.py のマスターを作り直したら測り直すこと。
LABEL = (330, 258, 690, 566)

MINCHO = "/System/Library/Fonts/ヒラギノ明朝 ProN.ttc"
MINCHO_W6 = 2
MINCHO_W3 = 0
OPTIMA = "/System/Library/Fonts/Optima.ttc"
OPTIMA_REGULAR = 0

WORDMARK = "茶の香"
WORDMARK_SIZE = 76
WORDMARK_TRACKING = 18  # 和文は字間を空けたほうが銘柄らしく見える

LATIN = "chanoka"
LATIN_SIZE = 27
LATIN_TRACKING = 9

PRODUCT_SIZE = 30
PRODUCT_TRACKING = 8

RULE_WIDTH = 108  # ワードマークと欧文の間に入れる罫線の長さ
GAP_ABOVE_RULE = 30
GAP_BELOW_RULE = 26
GAP_ABOVE_PRODUCT = 34

# 濃いラベルには生成り、淡いラベルには墨。玄米茶だけラベルが淡いため色を分ける。
INK_LIGHT = (243, 238, 226)
INK_DARK = (46, 42, 34)
# 刷りに見せるための不透明度。100%だと後載せ感が出る
INK_ALPHA = 232


def font(path: str, size: int, index: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size, index=index)


def tracked_width(f: ImageFont.FreeTypeFont, text: str, tracking: int) -> int:
    total = sum(f.getlength(ch) for ch in text)
    return int(total + tracking * (len(text) - 1))


def draw_tracked(
    draw: ImageDraw.ImageDraw,
    f: ImageFont.FreeTypeFont,
    text: str,
    center_x: int,
    top: int,
    tracking: int,
    fill: tuple[int, int, int, int],
) -> None:
    """字間を空けて中央揃えで描く。Pillow に字送りの指定が無いため1文字ずつ置く。"""
    x = center_x - tracked_width(f, text, tracking) / 2
    for ch in text:
        draw.text((x, top), ch, font=f, fill=fill)
        x += f.getlength(ch) + tracking


def label_is_light(image: Image.Image) -> bool:
    left, top, right, bottom = LABEL
    patch = image.crop((left + 40, top + 40, right - 40, bottom - 40)).resize((1, 1))
    r, g, b = patch.getpixel((0, 0))[:3]
    return (0.299 * r + 0.587 * g + 0.114 * b) > 140


def brand(source: Path, destination: Path, product_name: str) -> None:
    image = Image.open(source).convert("RGB")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    ink = (INK_DARK if label_is_light(image) else INK_LIGHT) + (INK_ALPHA,)
    left, top, right, bottom = LABEL
    center_x = (left + right) // 2

    wordmark = font(MINCHO, WORDMARK_SIZE, MINCHO_W6)
    latin = font(OPTIMA, LATIN_SIZE, OPTIMA_REGULAR)
    product = font(MINCHO, PRODUCT_SIZE, MINCHO_W3)

    # 4要素（和文・罫線・欧文・品名）を積んだ高さを出してから、ラベル内で天地中央に置く
    block_height = (
        WORDMARK_SIZE
        + GAP_ABOVE_RULE
        + 1
        + GAP_BELOW_RULE
        + LATIN_SIZE
        + GAP_ABOVE_PRODUCT
        + PRODUCT_SIZE
    )
    y = (top + bottom) // 2 - block_height // 2

    draw_tracked(draw, wordmark, WORDMARK, center_x, y, WORDMARK_TRACKING, ink)
    y += WORDMARK_SIZE + GAP_ABOVE_RULE

    draw.line(
        [(center_x - RULE_WIDTH // 2, y), (center_x + RULE_WIDTH // 2, y)],
        fill=ink[:3] + (int(INK_ALPHA * 0.7),),
        width=1,
    )
    y += 1 + GAP_BELOW_RULE

    draw_tracked(draw, latin, LATIN, center_x, y, LATIN_TRACKING, ink)
    y += LATIN_SIZE + GAP_ABOVE_PRODUCT

    draw_tracked(draw, product, product_name, center_x, y, PRODUCT_TRACKING, ink)

    destination.parent.mkdir(parents=True, exist_ok=True)
    Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB").save(destination)
    print(f"  保存: {destination.relative_to(REPO_ROOT)}")


def guide(source: Path, destination: Path) -> None:
    """ラベル枠を赤で重ねる。LABEL を測り直したときの確認用。"""
    image = Image.open(source).convert("RGB")
    ImageDraw.Draw(image).rectangle(LABEL, outline=(255, 0, 0), width=2)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination)
    print(f"  保存: {destination.relative_to(REPO_ROOT)}")


def main() -> None:
    arguments = sys.argv[1:]
    as_guide = "--guide" in arguments
    only = [a for a in arguments if not a.startswith("--")]

    targets = [n for n in NAMES if not only or n in only]
    if only and not targets:
        sys.exit(f"該当なし。指定できるのは: {', '.join(NAMES)}")

    for name in targets:
        source = OUTPUT_DIR / f"product-{name}.png"
        if not source.is_file():
            sys.exit(
                f"{source.relative_to(REPO_ROOT)} がありません。"
                "先に generate-images.py で商品画像を作ってください。"
            )
        print(f"- {name}")
        if as_guide:
            guide(source, BRANDED_DIR / f"product-{name}-guide.png")
        else:
            brand(source, BRANDED_DIR / f"product-{name}.png", NAMES[name])

    print("完了")


if __name__ == "__main__":
    main()

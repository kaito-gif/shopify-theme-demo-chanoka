#!/usr/bin/env python3
"""chanoka（架空の日本茶D2C）のデモ用画像を OpenAI の画像生成モデルで作る。

計画どおり「マスター画像＋参照画像による派生」で作る。テキストプロンプトを
揃えるだけでは毎回別のパッケージが生成され、商品一覧が素材の寄せ集めに見える
ため、商品画像は必ずマスターを入力に渡す編集モードで派生させること。

使い方:
    python3 scripts/generate-images.py master     # まず1枚。ここで納得いくまで回す
    python3 scripts/generate-images.py products   # マスターから商品バリエーション
    python3 scripts/generate-images.py lifestyle  # 世界観カット
    python3 scripts/generate-images.py steps      # 淹れ方4ステップ（index.jsonと1対1）
    python3 scripts/generate-images.py hero       # 横長バナー

APIキーは環境変数 OPENAI_API_KEY、無ければ ~/.claude/portfolio/openai-key を読む。
生成物は scripts/output/ に入る（公開リポジトリには入れない。.gitignore 済み）。
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

API_BASE = "https://api.openai.com/v1"
MODEL = "gpt-image-1"

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "scripts" / "output"
MASTER_PATH = OUTPUT_DIR / "master-package.png"
KEY_FILE = Path.home() / ".claude" / "portfolio" / "openai-key"

# 全カットで共有する画づくり。ここを1か所に持つことでトーンが揃う。
# 文字はAIが崩すため、パッケージのラベルは無地で生成し、ブランド名は後段で合成する。
# 「文字を入れるな」は一度書くだけでは効かない。実際に初回生成で崩れた漢字と
# 架空のブランド名が入ったため、否定を具体的に列挙して繰り返す形にしている。
NO_TEXT = (
    "CRITICAL: the packaging must be completely blank and unprinted. "
    "Absolutely no text of any kind anywhere in the image: "
    "no brand name, no logo, no kanji, no kana, no Chinese characters, "
    "no Latin letters, no numbers, no barcode, no label printing, no watermark. "
    "The label area is a plain empty surface with nothing written on it."
)

STYLE = (
    "Photorealistic product photography for a calm, modern Japanese tea brand. "
    "Muted natural palette of deep green, warm beige and off-white. "
    "Soft diffused studio light from the upper left, gentle contact shadow. "
    "Not resembling any real existing brand. " + NO_TEXT
)

MASTER_PROMPT = (
    "A single matte kraft-paper stand-up pouch of Japanese loose-leaf green tea, "
    "standing upright and centered on a pure white seamless background. "
    "The front has a plain cream-colored rectangular label area, entirely blank. "
    "A small oval window near the bottom shows the green tea leaves inside. "
    "Shot straight on at eye level, full product visible with even margins. " + STYLE
)

# 商品バリエーション。マスターと同じパッケージのまま、ラベル色と「窓から見える中身」を
# 変える。ラベル色だけ変えると、ほうじ茶なのに緑の茶葉が見えるといった破綻が起きる。
# 背景も明示的に固定する。中身の指示を足したときに背景まで変えられ、
# 商品一覧に並べたとき背景色がばらついた実績があるため。
KEEP = (
    "Keep the exact same pouch shape, material, camera angle and lighting. "
    "Keep the background exactly as in the reference image: a plain, very light "
    "warm off-white seamless studio background. Do not change the background color. "
)
PRODUCTS = [
    ("sencha", KEEP + "Change the label area color to a fresh deep green. The window shows fine needle-shaped green sencha leaves."),
    ("fukamushi", KEEP + "Change the label area color to a darker forest green. The window shows finely broken deep-steamed green tea leaves."),
    ("gyokuro", KEEP + "Change the label area color to a deep indigo blue. The window shows glossy dark green gyokuro needles."),
    ("hojicha", KEEP + "Change the label area color to a warm roasted brown. The window shows roasted hojicha: reddish brown, toasted tea leaves and stems, not green."),
    ("genmaicha", KEEP + "Change the label area color to a soft golden beige. The window shows genmaicha: green tea leaves mixed with pale toasted brown rice grains."),
    ("matcha", KEEP + "Change the label area color to a vivid matcha green. The window shows fine bright green matcha powder, not whole leaves."),
]

LIFESTYLE = [
    ("kyusu", "A traditional Japanese kyusu teapot pouring green tea into a small ceramic cup on a light wooden table, steam rising softly. " + STYLE),
    ("tea-field", "A terraced Japanese green tea field in soft morning light, rows of trimmed tea bushes receding into gentle mist. " + STYLE),
    ("table", "A quiet breakfast table setting with a cup of green tea, a small plate of wagashi and a linen cloth, shot from a high angle. " + STYLE),
]

# ステップスライダーの4カット。index.json の step-1〜4 の見出しと1対1で対応させる。
# 商品画像と同じ理由で**基準画像からの派生**にする。テキストで「同じ器」と書いても
# 器の色が揃わず、実際に初回生成で step-3 だけ緑の急須になった。
# step-1 を基準（STEP_BASE）として generate し、step-2〜4 はそれを入力に derive する。
STEP_BASE = OUTPUT_DIR / "step-1-measure.png"

STEPS_KEEP = (
    "Keep the exact same scene as the reference image: the same light wooden table, "
    "the same plain off-white wall, the same beige speckled ceramic kyusu teapot and "
    "the same pair of beige speckled ceramic cups. Do not change the color of the "
    "teapot or the cups. Keep the same camera angle, distance and lighting. "
)
STEP_FIRST = (
    "step-1-measure",
    "A hand holding a small wooden tea scoop, lifting dry green tea leaves from an "
    "open unlabeled tin toward a small beige speckled ceramic kyusu teapot, with a "
    "pair of matching beige cups beside it. A light unfinished wooden table, a plain "
    "off-white wall behind, soft natural daylight from the upper left. ",
)
STEPS = [
    ("step-2-cool", "Hot water being poured from a dark cast-iron kettle into a shallow ceramic cooling vessel, gentle steam rising. " + STEPS_KEEP),
    ("step-3-wait", "The teapot with its lid closed, resting on the table beside a small wooden-framed sand timer. Nothing is being touched: a quiet waiting moment. " + STEPS_KEEP),
    ("step-4-pour", "Tea being poured from the teapot into the two small cups placed side by side, both filled to the same level. " + STEPS_KEEP),
]

HERO = [
    ("hero-main", "Wide banner composition: a ceramic cup of freshly brewed green tea on the right third of the frame, generous empty negative space on the left for overlaying text later, soft neutral background. " + STYLE),
    ("hero-field", "Wide banner composition: a Japanese tea field at dawn with low mist, generous empty sky in the upper left for overlaying text later. " + STYLE),
]


def api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return key
    if KEY_FILE.is_file():
        return KEY_FILE.read_text(encoding="utf-8").strip()
    sys.exit(
        f"OPENAI_API_KEY が見つかりません。環境変数に設定するか、{KEY_FILE} に保存してください。"
    )


def post(url: str, body: bytes, content_type: str) -> dict:
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Authorization": f"Bearer {api_key()}", "Content-Type": content_type},
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        # API のエラー本文にこそ原因が書いてあるので必ず出す
        detail = error.read().decode("utf-8", "replace")
        sys.exit(f"APIエラー {error.code}: {detail}")


def multipart(fields: list[tuple[str, str]], files: list[tuple[str, Path]]) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    buffer = bytearray()

    for name, value in fields:
        buffer += f"--{boundary}\r\n".encode()
        buffer += f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
        buffer += value.encode() + b"\r\n"

    for name, path in files:
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        buffer += f"--{boundary}\r\n".encode()
        buffer += (
            f'Content-Disposition: form-data; name="{name}"; filename="{path.name}"\r\n'
        ).encode()
        buffer += f"Content-Type: {mime}\r\n\r\n".encode()
        buffer += path.read_bytes() + b"\r\n"

    buffer += f"--{boundary}--\r\n".encode()
    return bytes(buffer), f"multipart/form-data; boundary={boundary}"


def save(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64decode(payload["data"][0]["b64_json"]))
    size_kb = path.stat().st_size // 1024
    print(f"  保存: {path.relative_to(REPO_ROOT)} ({size_kb} KB)")


def generate(prompt: str, size: str, path: Path) -> None:
    body = json.dumps(
        {"model": MODEL, "prompt": prompt, "size": size, "n": 1}
    ).encode()
    save(post(f"{API_BASE}/images/generations", body, "application/json"), path)


def derive(reference: Path, prompt: str, size: str, path: Path) -> None:
    """マスター画像を入力に渡して派生させる。同一ブランドに見せる要はここ。"""
    body, content_type = multipart(
        [("model", MODEL), ("prompt", prompt), ("size", size)],
        [("image[]", reference)],
    )
    save(post(f"{API_BASE}/images/edits", body, content_type), path)


def require_master() -> None:
    if not MASTER_PATH.is_file():
        sys.exit(
            "マスター画像がありません。先に `python3 scripts/generate-images.py master` を実行してください。"
        )


def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else ""

    if target == "master":
        print("マスター画像を生成します（納得いくまで再実行してください）")
        generate(MASTER_PROMPT, "1024x1024", MASTER_PATH)

    elif target == "products":
        require_master()
        # 第2引数以降で対象を絞れる。1点だけ作り直したいときに全点課金しないため
        only = set(sys.argv[2:])
        targets = [p for p in PRODUCTS if not only or p[0] in only]
        if only and not targets:
            sys.exit(f"該当なし。指定できるのは: {', '.join(name for name, _ in PRODUCTS)}")
        print(f"マスターから商品バリエーションを{len(targets)}点派生させます")
        for name, instruction in targets:
            print(f"- {name}")
            derive(MASTER_PATH, instruction + " " + STYLE, "1024x1024", OUTPUT_DIR / f"product-{name}.png")

    elif target == "lifestyle":
        print(f"世界観カットを{len(LIFESTYLE)}点生成します")
        for name, prompt in LIFESTYLE:
            print(f"- {name}")
            generate(prompt, "1024x1024", OUTPUT_DIR / f"lifestyle-{name}.png")

    elif target == "steps":
        only = set(sys.argv[2:])
        names = [STEP_FIRST[0]] + [name for name, _ in STEPS]
        if only and not only.issubset(set(names)):
            sys.exit(f"該当なし。指定できるのは: {', '.join(names)}")

        # 基準カット。これが変わると2〜4も揃わなくなるため、単独でやり直せるようにする
        if not only or STEP_FIRST[0] in only:
            print(f"- {STEP_FIRST[0]}（基準）")
            generate(STEP_FIRST[1] + STYLE, "1024x1024", STEP_BASE)

        targets = [s for s in STEPS if not only or s[0] in only]
        if targets and not STEP_BASE.is_file():
            sys.exit(
                "基準カットがありません。先に `python3 scripts/generate-images.py steps step-1-measure` を実行してください。"
            )
        for name, instruction in targets:
            print(f"- {name}")
            derive(STEP_BASE, instruction + STYLE, "1024x1024", OUTPUT_DIR / f"{name}.png")

    elif target == "hero":
        print(f"横長バナーを{len(HERO)}点生成します")
        for name, prompt in HERO:
            print(f"- {name}")
            generate(prompt, "1536x1024", OUTPUT_DIR / f"{name}.png")

    else:
        sys.exit(__doc__)

    print("完了")


if __name__ == "__main__":
    main()

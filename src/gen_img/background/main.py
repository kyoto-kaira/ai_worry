# gen_img/background/main.py

import argparse
import os
from dotenv import load_dotenv  # .env 読み込み用

from google import genai

from gen_img.background.config import THEMES
from gen_img.background.generate import generate_background
from gen_img.paths import BACKGROUND_DIR

# .env ファイルから GEMINI_API_KEY や IMAGE_MODEL を自動読み込み
load_dotenv()


def main():
    parser = argparse.ArgumentParser()
    # デフォルトで THEMES に存在するすべての ID (1, 2, 3... 12...) が対象になります
    parser.add_argument(
        "ids", nargs="*", type=int, default=sorted(list(THEMES.keys()))
    )
    parser.add_argument(
        "--force", action="store_true", help="overwrite existing images"
    )
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY が見つかりません。.env ファイルを確認してください。"
        )

    client = genai.Client(api_key=api_key)

    for bg_id in args.ids:
        out = BACKGROUND_DIR / f"{bg_id}.png"
        # 既に存在する画像はスキップ（--force オプション指定時のみ上書き）
        if out.exists() and not args.force:
            print(f"skip {out.name} (already exists)")
            continue

        if bg_id not in THEMES:
            print(f"skip {bg_id} (config.py にテーマが定義されていません)")
            continue

        print(f"Generating {out.name} for theme [{bg_id}]...")
        generate_background(client, bg_id).save(out)
        print(f"saved {out.name}")


if __name__ == "__main__":
    main()
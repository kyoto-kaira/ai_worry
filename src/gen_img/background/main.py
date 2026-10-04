import argparse
import os

from google import genai

from gen_img.background.config import THEMES
from gen_img.background.generate import generate_background
from gen_img.paths import BACKGROUND_DIR


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ids", nargs="*", type=int, default=list(THEMES))
    parser.add_argument("--force", action="store_true", help="overwrite existing images")
    args = parser.parse_args()

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    for bg_id in args.ids:
        out = BACKGROUND_DIR / f"{bg_id}.png"
        if out.exists() and not args.force:
            print(f"skip {out.name} (already exists)")
            continue
        generate_background(client, bg_id).save(out)
        print(f"saved {out.name}")


if __name__ == "__main__":
    main()

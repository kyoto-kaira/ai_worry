"""
Gemini API (gemini-3-pro-image) を利用して AI で偽物キャラを一括生成するスクリプト
"""

import io
import os
from pathlib import Path
from PIL import Image
from dotenv import load_dotenv

from google import genai
from google.genai import types

from gen_img.paths import FAKE_DIR, REAL_DIR

load_dotenv()

FAKE_VARIATIONS = {
    "three_eyes": "Add a third eye on its forehead.",
    "single_eye": "Replace the two eyes with a single large centered eye.",
    "spiral_eyes": "Replace the pupils with hypnotic spiral lines.",
    "cross_eyes": "Replace the pupils with X-shaped cross lines.",
    "sleeping_eyes": "Change the eyes to happy closed arc lines (smiling eyes).",
    "droopy_eyes": "Modify the eyes to have sad droopy eyelids.",
    "heart_eyes": "Replace the pupils with small heart shapes.",
    "eyepatch": "Add a black pirate eyepatch over one eye with a thin strap.",
    "vertical_eyes": "Rearrange the two eyes to be stacked vertically instead of horizontally.",
    "thick_arms": "Redraw the arms to be thick and muscular.",
    "leaf_on_head": "Add a small single leaf sprouting from the top of its head.",
    "two_horns": "Add two small cute devil horns on top of its head.",
    "academic_cap": "Add a classic university mortarboard (academic cap) on top of its head.",
    "round_glasses": "Add simple round spectacles on its face.",
    "backpack": "Add a small simple school backpack on its back.",
    "monocle": "Add a classic single monocle with a dangling string over one eye.",
    "bowtie": "Add a small bow tie under its eyes/chin area.",
    "wizard_hat": "Add a pointy wizard hat with a slightly bent tip on top of its head.",
    "crown": "Add a small cute royal crown resting on top of its head.",
    "chef_hat": "Add a tall puffy chef toque hat on top of its head.",
    "party_hat": "Add a cone-shaped party hat with a tiny pom-pom on top of its head.",
    "angel_halo": "Add a simple floating oval angel halo and wings on its head.",
    "cat_ears": "Add a pair of cute triangle cat ears on top of its head.",
    "sprout_hair": "Add a small two-leaf plant sprout growing from the top of its head.",
    "headphones": "Add a pair of over-ear headphones worn on its head.",
    "ribbon": "Add a cute decorative bow ribbon tied on top of its head.",
    "extra_tentacle": "Add one extra waving tentacle extending from the tail network.",
    "forked_tail": "Modify the end of the tail network to end in a sharp two-pronged fork shape.",
    "tiny_wings": "Add a pair of small feather wings on its back.",
    "little_legs": "Add two tiny cartoon legs under its body standing on the ground.",
    "long_arms": "Extend both arms to be twice as long and slightly wavy.",
    "crab_claws": "Replace its hands with small cartoon crab claw pincers.",
    "sunglasses": "Add dark cool sunglasses over its eyes.",
    "scarf": "Wrap a cozy winter scarf around its neck/lower head area.",
    "mustache": "Add a funny bushy mustache under its eyes.",
    "mask": "Add a simple face mask covering the lower half of its face.",
    "lollipop": "Draw a small round swirl lollipop held in one of its hands.",
    "magic_wand": "Draw a small magic wand with a star tip held in one hand.",
    "coffee_cup": "Draw a small steaming coffee mug held in one of its hands.",
}

BASE_STYLE_PROMPT = (
    "Create a modified version of the character in the attached image. "
    "Keep the exact same hand-drawn black ink line style, stroke thickness (~4-5px), "
    "and pure white background. Do not change anything else unless specified."
)


def generate_ai_fakes():
    api_key = os.getenv("GEMINI_API_KEY")
    # 背景生成で機能していたモデル名を取得
    model_name = os.getenv("GEMINI_MODEL", "gemini-3-pro-image")

    if not api_key:
        raise ValueError("GEMINI_API_KEY が見つかりません。")

    base_image_path = REAL_DIR / "1.png"
    base_image = Image.open(base_image_path).convert("RGB")
    client = genai.Client(api_key=api_key)

    FAKE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Gemini APIによる偽物キャラ生成を開始します (モデル: {model_name})...")

    for idx, (name, variation_prompt) in enumerate(
        FAKE_VARIATIONS.items(), start=14
    ):
        out_path = FAKE_DIR / f"{idx}.png"

        if out_path.exists():
            print(f"Skipped {out_path.name} ({name}: すでに存在します)")
            continue

        full_prompt = f"{BASE_STYLE_PROMPT}\nModification: {variation_prompt}"
        print(f"Generating fake character {idx}.png ({name})...")

        try:
            # 背景生成と同じ generate_content 形式呼び出し
            response = client.models.generate_content(
                model=model_name,
                contents=[base_image, full_prompt],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                ),
            )

            saved = False
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        img = Image.open(
                            io.BytesIO(part.inline_data.data)
                        ).convert("RGB")
                        img.save(out_path)
                        print(f"  Successfully saved: {out_path.name}")
                        saved = True
                        break

            if not saved:
                print(
                    f"  Warning: {out_path.name} の画像データが得られませんでした。"
                )

        except Exception as e:
            print(f"  Error generating {idx}.png: {e}")

    print("全偽物キャラの生成処理が完了しました！")


if __name__ == "__main__":
    generate_ai_fakes()
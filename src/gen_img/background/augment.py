"""
Create augmented variations from existing background images (1~5),
such as horizontal flips, allowing immediate expansion of backgrounds
without requiring API keys. When Gemini API is available, they can be
overwritten by running `gen_img.background.main`.
"""

from pathlib import Path
from PIL import Image
from gen_img.paths import BACKGROUND_DIR

def augment_backgrounds():
    print("Checking existing backgrounds...")
    base_bgs = [BACKGROUND_DIR / f"{i}.png" for i in range(1, 6)]
    available = [p for p in base_bgs if p.exists()]
    
    if not available:
        print("No base backgrounds found in img/background.")
        return

    # 6~10: 既存 1~5 の左右反転
    for i in range(1, 6):
        src_path = BACKGROUND_DIR / f"{i}.png"
        dst_path = BACKGROUND_DIR / f"{i + 5}.png"
        if not dst_path.exists() and src_path.exists():
            img = Image.open(src_path)
            flipped = img.transpose(Image.FLIP_LEFT_RIGHT)
            flipped.save(dst_path)
            print(f"Created augmented background: {dst_path.name} (flipped from {src_path.name})")
        else:
            print(f"Skipped {dst_path.name} (already exists)")

if __name__ == "__main__":
    augment_backgrounds()


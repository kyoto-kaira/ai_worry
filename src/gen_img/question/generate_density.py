"""
Generate density-configurable seek-and-find question images for Kaira-kun.
Supports sparse to extremely packed character densities with YOLO labels
and visual answer keys for festival demos and model evaluation.
"""

import argparse
import json
import math
import random
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

from gen_img.paths import BACKGROUND_DIR, FAKE_DIR, REAL_DIR
from gen_img.question.character import load_gray, render_character
from gen_img.question.config import (
    BACKGROUND_COUNT,
    BACKGROUND_STYLES,
    DISTANT_STROKE_SCALE,
    DISTANT_WIDTH,
)
from gen_img.question.placement import Placement


DENSITY_PRESETS = {
    "sparse": (6, 10, 110),      # (min_chars, max_chars, min_distance_px) まばら・ところどころ
    "medium": (14, 20, 75),      # 標準 (学祭デモ推奨: 15~20体)
    "high": (25, 35, 55),        # 高密度
    "packed": (40, 55, 42),      # ぎゅうぎゅう詰め
}


def get_available_real_images() -> List[Path]:
    return sorted(REAL_DIR.glob("*.png"))


def get_available_fake_images() -> List[Path]:
    # 拡張子 .png, .jpg などの全フェイク画像を取得
    fakes = list(FAKE_DIR.glob("*.png")) + list(FAKE_DIR.glob("*.jpg"))
    # 自然順ソート
    return sorted(fakes, key=lambda p: int(p.stem) if p.stem.isdigit() else str(p.stem))


def _paste(canvas: np.ndarray, p: Placement, image: np.ndarray, alpha: np.ndarray):
    """Paste character onto canvas blending with alpha mask."""
    h, w = canvas[p.y : p.y + image.shape[0], p.x : p.x + image.shape[1]].shape
    image, alpha = image[:h, :w], alpha[:h, :w]

    area = canvas[p.y : p.y + h, p.x : p.x + w]
    area[:] = area * (1 - alpha) + 255 * alpha
    area[:] = np.minimum(area, image)


def place_characters(
    canvas_shape: Tuple[int, int],
    total_count: int,
    min_dist: float,
    fake_pool: List[Path],
    real_pool: List[Path],
) -> Tuple[Placement, List[Placement]]:
    """
    Plan positions for 1 REAL character and (total_count - 1) FAKE characters.
    Uses Poisson-like rejection sampling to control density and spacing.
    """
    canvas_h, canvas_w = canvas_shape
    placements: List[Placement] = []
    centers: List[Tuple[float, float]] = []

    # 1. 本物 (REAL) の配置決定
    real_img_path = random.choice(real_pool)
    real_w = random.randint(110, 145)
    real_angle = random.uniform(-10.0, 10.0)
    real_flip = random.choice([True, False])
    
    # マージンを確保して画面端から極端にはみ出さないようにする
    real_x = random.randint(60, canvas_w - real_w - 60)
    real_y = random.randint(60, canvas_h - int(real_w * 0.7) - 60)
    real_p = Placement(real_img_path, real_w, real_angle, real_flip, real_x, real_y)
    
    placements.append(real_p)
    centers.append((real_x + real_w / 2.0, real_y + (real_w * 0.6) / 2.0))

    # 2. 偽物 (FAKE) の配置決定
    num_fakes = max(1, total_count - 1)
    
    # 偽物画像のシャッフル（バリエーション豊かに選定）
    shuffled_fakes = []
    while len(shuffled_fakes) < num_fakes:
        pool_copy = list(fake_pool)
        random.shuffle(pool_copy)
        shuffled_fakes.extend(pool_copy)
    selected_fake_imgs = shuffled_fakes[:num_fakes]

    # 現在の密度に応じた動的距離緩和
    curr_min_dist = min_dist

    for fake_img in selected_fake_imgs:
        fake_w = random.randint(85, 140)
        fake_angle = random.uniform(-14.0, 14.0)
        fake_flip = random.choice([True, False])
        
        placed = False
        attempts = 0
        max_attempts = 150

        while attempts < max_attempts and not placed:
            attempts += 1
            cand_x = random.randint(20, canvas_w - fake_w - 20)
            cand_y = random.randint(20, canvas_h - int(fake_w * 0.7) - 20)
            cand_cx = cand_x + fake_w / 2.0
            cand_cy = cand_y + (fake_w * 0.6) / 2.0

            # 既存キャラとの距離判定
            too_close = False
            for cx, cy in centers:
                dist = math.hypot(cand_cx - cx, cand_cy - cy)
                if dist < curr_min_dist:
                    too_close = True
                    break
            
            if not too_close:
                p = Placement(fake_img, fake_w, fake_angle, fake_flip, cand_x, cand_y)
                placements.append(p)
                centers.append((cand_cx, cand_cy))
                placed = True

        # もし試行回数が上限に達したら、少し距離を緩和して再試行
        if not placed:
            cand_x = random.randint(20, canvas_w - fake_w - 20)
            cand_y = random.randint(20, canvas_h - int(fake_w * 0.7) - 20)
            p = Placement(fake_img, fake_w, fake_angle, fake_flip, cand_x, cand_y)
            placements.append(p)
            centers.append((cand_x + fake_w / 2.0, cand_y + (fake_w * 0.6) / 2.0))
            curr_min_dist = max(30.0, curr_min_dist * 0.95)

    return real_p, placements[1:]


def generate_single_question(
    bg_id: int,
    total_count: int,
    min_dist: float,
    output_base: Path,
    index: int,
    save_annotated: bool = True,
) -> dict:
    """
    Generate one question image with specified density and background.
    Saves:
      - {index}.png (raw question)
      - {index}_answer.png (with bounding box around REAL)
      - {index}.txt (YOLO format: 0 cx cy w h)
      - {index}.json (metadata)
    """
    real_pool = get_available_real_images()
    fake_pool = get_available_fake_images()

    style = BACKGROUND_STYLES.get(bg_id, BACKGROUND_STYLES[1])
    bg_path = BACKGROUND_DIR / f"{bg_id}.png"
    if not bg_path.exists():
        raise FileNotFoundError(f"Background not found: {bg_path}")

    background = load_gray(bg_path)
    canvas = background.copy()
    h, w = canvas.shape[:2]

    # 配置決定
    real_p, fake_placements = place_characters(
        canvas_shape=(h, w),
        total_count=total_count,
        min_dist=min_dist,
        fake_pool=fake_pool,
        real_pool=real_pool,
    )

    # 描画順序:
    # 群衆感を出しつつ本物を視認可能にするため、偽物を先に描き、本物をその中に合成
    # （少し被りを持たせるため、偽物の一部を描いた後に本物を描き、残りの偽物を描く）
    split_idx = max(0, len(fake_placements) // 3)
    first_fakes = fake_placements[:split_idx]
    second_fakes = fake_placements[split_idx:]

    for p in first_fakes:
        stroke = style.stroke_width * (DISTANT_STROKE_SCALE if p.width < DISTANT_WIDTH else 1)
        img, alpha = render_character(p, stroke, style.blur)
        _paste(canvas, p, img, alpha)

    # 本物の描画
    stroke = style.stroke_width * (DISTANT_STROKE_SCALE if real_p.width < DISTANT_WIDTH else 1)
    real_img, real_alpha = render_character(real_p, stroke, style.blur)
    _paste(canvas, real_p, real_img, real_alpha)

    # 残りの偽物の描画
    for p in second_fakes:
        stroke = style.stroke_width * (DISTANT_STROKE_SCALE if p.width < DISTANT_WIDTH else 1)
        img, alpha = render_character(p, stroke, style.blur)
        _paste(canvas, p, img, alpha)

    # 画像化
    out_img = np.clip(canvas, 0, 255).astype(np.uint8)
    pil_img = Image.fromarray(np.stack([out_img] * 3, axis=2))

    # 本物のバウンディングボックス計算
    char_h, char_w = real_img.shape[:2]
    xmin, ymin = real_p.x, real_p.y
    xmax = min(w, xmin + char_w)
    ymax = min(h, ymin + char_h)

    box_w = xmax - xmin
    box_h = ymax - ymin
    cx = (xmin + box_w / 2.0) / w
    cy = (ymin + box_h / 2.0) / h
    rel_w = box_w / w
    rel_h = box_h / h

    # 保存ファイル名
    output_base.mkdir(parents=True, exist_ok=True)
    raw_path = output_base / f"{index}.png"
    yolo_path = output_base / f"{index}.txt"
    json_path = output_base / f"{index}.json"
    pil_img.save(raw_path)

    # YOLO txt 保存 (class 0)
    with open(yolo_path, "w", encoding="utf-8") as f:
        f.write(f"0 {cx:.6f} {cy:.6f} {rel_w:.6f} {rel_h:.6f}\n")

    # 正解表示用画像 (緑色の枠を描画)
    if save_annotated:
        answer_img = pil_img.copy()
        draw = ImageDraw.Draw(answer_img)
        # 太い枠線
        for offset in range(-2, 3):
            draw.rectangle(
                [xmin - offset, ymin - offset, xmax + offset, ymax + offset],
                outline=(0, 200, 0),
            )
        # ラベルバナー
        draw.text((xmin, max(0, ymin - 18)), "REAL Kaira-kun", fill=(0, 180, 0))
        answer_path = output_base / f"{index}_answer.png"
        answer_img.save(answer_path)

    # メタデータ
    meta = {
        "id": index,
        "background_id": bg_id,
        "total_characters": total_count,
        "num_fakes": len(fake_placements),
        "real": {
            "image": real_p.image.name,
            "x": real_p.x,
            "y": real_p.y,
            "w": char_w,
            "h": char_h,
            "yolo_bbox": [cx, cy, rel_w, rel_h],
        },
        "fakes_used": [p.image.name for p in fake_placements],
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    return meta


def main():
    parser = argparse.ArgumentParser(description="Generate Kaira-kun Seek-and-Find Questions with customizable density.")
    parser.add_argument("--num", type=int, default=5, help="Number of question images to generate")
    parser.add_argument("--density", choices=list(DENSITY_PRESETS.keys()), default=None,
                        help="Density preset: sparse (6~10), medium (14~20), high (25~35), packed (40~55)")
    parser.add_argument("--count", type=int, default=None,
                        help="Exact total number of characters (1 real + N-1 fakes). Overrides --density.")
    parser.add_argument("--bg", type=int, default=None,
                        help="Specific background ID to use (1~10). If omitted, picks randomly.")
    parser.add_argument("--out", type=str, default="img/question_demo",
                        help="Output directory (default: img/question_demo)")
    parser.add_argument("--start_id", type=int, default=1, help="Starting index for image naming (default: 1)")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("==================================================")
    print("KaiRA Seek-and-Find Question Generator")
    print("==================================================")

    for i in range(args.num):
        q_id = args.start_id + i
        
        # 背景の決定
        bg_id = args.bg if args.bg is not None else random.randint(1, BACKGROUND_COUNT)
        
        # キャラの配置数と間隔の決定
        if args.count is not None:
            total_count = args.count
            min_dist = max(30.0, min(100.0, 500.0 / math.sqrt(total_count)))
        elif args.density is not None:
            min_c, max_c, min_dist = DENSITY_PRESETS[args.density]
            total_count = random.randint(min_c, max_c)
        else:
            # デフォルト: medium (14~20体、学祭デモ推奨)
            min_c, max_c, min_dist = DENSITY_PRESETS["medium"]
            total_count = random.randint(min_c, max_c)

        print(f"Generating question {q_id}: Background={bg_id}, Total Characters={total_count} (Density min_dist={min_dist:.1f}px)...")
        meta = generate_single_question(
            bg_id=bg_id,
            total_count=total_count,
            min_dist=min_dist,
            output_base=out_dir,
            index=q_id,
            save_annotated=True,
        )
        print(f"  -> Saved {q_id}.png & {q_id}_answer.png (Real: {meta['real']['image']} at ({meta['real']['x']}, {meta['real']['y']}))")

    print("\nGeneration finished successfully!")
    print(f"Output saved to: {out_dir.resolve()}")


if __name__ == "__main__":
    main()

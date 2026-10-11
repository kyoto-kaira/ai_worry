import argparse
import json
import shutil

import numpy as np
from PIL import Image

from gen_img.harmonize.config import BASE_METHOD, METHODS, REFINE_METHODS, RESTORE_METHOD, WORK_DIR
from gen_img.harmonize.crops import CropBox, crop_box, harmonize_mask, to_model_input
from gen_img.harmonize.layouts import OCCLUDERS, SCENES
from gen_img.harmonize.merge import paste_back, restore_details
from gen_img.paths import BACKGROUND_DIR, EXP_OCCLUDER_DIR, FIX_EXP_DIR, HIDE_EXP_DIR
from gen_img.question.character import load_gray
from gen_img.question.compose import compose, to_rgb_image
from gen_img.mask.shape import lasso_mask
from gen_img.question.occlusion import hidden_region


def job_name(scene_id: int, index: int) -> str:
    return f"s{scene_id:02d}_{index:02d}"


def write_occluders():
    """多角形から手前マスクを作る（手で描いたマスクを使う場合はこの PNG を差し替える）"""
    EXP_OCCLUDER_DIR.mkdir(parents=True, exist_ok=True)
    for name, (bg_id, polygon) in OCCLUDERS.items():
        mask = lasso_mask(load_gray(BACKGROUND_DIR / f"{bg_id}.png"), polygon)
        Image.fromarray((mask * 255).astype(np.uint8)).save(EXP_OCCLUDER_DIR / f"{name}.png")


def save_mask_overview(scene_id: int, gray: np.ndarray, masks: list[np.ndarray], front: np.ndarray):
    """手前マスク（赤）と、AI に描き直させる範囲（青）を重ねた確認用画像"""
    rgb = np.stack([gray] * 3, axis=2)
    rgb[front] = rgb[front] * 0.5 + np.array([255, 0, 0]) * 0.5
    redraw = np.any(masks, axis=0)
    rgb[redraw] = rgb[redraw] * 0.5 + np.array([0, 90, 255]) * 0.5
    out_dir = HIDE_EXP_DIR / "masks"
    out_dir.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgb.clip(0, 255).astype(np.uint8)).save(out_dir / f"{scene_id}.png")


def prepare():
    """シーンを合成し、キャラごとの切り出し画像とマスクを作業フォルダに書き出す"""
    write_occluders()
    shutil.rmtree(WORK_DIR / "jobs", ignore_errors=True)
    boxes = {}
    for scene_id, (bg_id, placements) in SCENES.items():
        gray, alphas = compose(bg_id, placements)
        background = load_gray(BACKGROUND_DIR / f"{bg_id}.png")
        masks = [harmonize_mask(alpha) for alpha in alphas]
        front = np.zeros(gray.shape, bool)
        for p in placements:
            if p.front_mask:
                front |= np.asarray(Image.open(p.front_mask)) > 127

        out_dir = HIDE_EXP_DIR / "composite"
        out_dir.mkdir(parents=True, exist_ok=True)
        to_rgb_image(gray).save(out_dir / f"{scene_id}.png")
        save_mask_overview(scene_id, gray, masks, front)

        for i, mask in enumerate(masks):
            box = crop_box(mask)
            image, mask_image = to_model_input(gray, mask, box)
            job_dir = WORK_DIR / "jobs" / job_name(scene_id, i)
            job_dir.mkdir(parents=True)
            image.save(job_dir / "composite.png")
            mask_image.save(job_dir / "mask.png")
            # 画風の手がかり：キャラのいない背景だけの切り出し
            to_model_input(background, mask, box)[0].save(job_dir / "style.png")
            boxes[job_dir.name] = vars(box)
    (WORK_DIR / "boxes.json").write_text(json.dumps(boxes, indent=1))
    print(f"{len(boxes)} jobs -> {WORK_DIR / 'jobs'}")


def merge():
    """GPU サーバーの出力を元の画像に書き戻す"""
    boxes = json.loads((WORK_DIR / "boxes.json").read_text())
    for method in METHODS + REFINE_METHODS:
        if not (WORK_DIR / "outputs" / method).exists():
            continue
        out_dir = (FIX_EXP_DIR if method in REFINE_METHODS else HIDE_EXP_DIR) / method
        out_dir.mkdir(parents=True, exist_ok=True)
        for scene_id, (bg_id, placements) in SCENES.items():
            gray, alphas = compose(bg_id, placements)
            background = load_gray(BACKGROUND_DIR / f"{bg_id}.png")
            canvas = gray.copy()
            for i, (p, alpha) in enumerate(zip(placements, alphas)):
                name = job_name(scene_id, i)
                result = Image.open(WORK_DIR / "outputs" / method / f"{name}.png")
                hidden = hidden_region(background, p)
                paste_back(canvas, result, harmonize_mask(alpha), hidden, CropBox(**boxes[name]))
            to_rgb_image(canvas).save(out_dir / f"{scene_id}.png")
            print(f"{method}: scene {scene_id}")
    restore()


def restore():
    """PHDiffusion の結果に、元画像の細かい部分を貼り戻す（AI を使わない比較用）"""
    out_dir = FIX_EXP_DIR / RESTORE_METHOD
    out_dir.mkdir(parents=True, exist_ok=True)
    for scene_id, (bg_id, placements) in SCENES.items():
        original, alphas = compose(bg_id, placements)
        canvas = load_gray(HIDE_EXP_DIR / BASE_METHOD / f"{scene_id}.png")
        for alpha in alphas:
            restore_details(canvas, original, alpha)
        to_rgb_image(canvas).save(out_dir / f"{scene_id}.png")
        print(f"{RESTORE_METHOD}: scene {scene_id}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("step", choices=["prepare", "merge"])
    args = parser.parse_args()
    {"prepare": prepare, "merge": merge}[args.step]()


if __name__ == "__main__":
    main()

import argparse
import json
import shutil

import numpy as np
from PIL import Image

from gen_img.harmonize.config import QUESTION_STRENGTH, QUESTION_WORK_DIR
from gen_img.harmonize.crops import CropBox, crop_box, harmonize_mask, to_model_input
from gen_img.harmonize.merge import paste_back, restore_details
from gen_img.paths import BACKGROUND_DIR, HARMONIZED_QUESTION_DIR
from gen_img.question.character import load_gray
from gen_img.question.compose import background_id, compose_question, to_rgb_image
from gen_img.question.config import QUESTIONS
from gen_img.question.occlusion import hidden_region


def job_name(question_id: int, index: int) -> str:
    return f"q{question_id:02d}_{index:02d}"


def prepare(question_ids):
    """問題を合成し、キャラごとの切り出し画像とマスクを作業フォルダに書き出す"""
    # 今回の問題の分だけ作り直す（他の問題の切り出し位置は残す）
    shutil.rmtree(QUESTION_WORK_DIR / "jobs", ignore_errors=True)
    boxes_path = QUESTION_WORK_DIR / "boxes.json"
    boxes = json.loads(boxes_path.read_text()) if boxes_path.exists() else {}
    for question_id in question_ids:
        gray, alphas = compose_question(question_id)
        for i, alpha in enumerate(alphas):
            mask = harmonize_mask(alpha)
            box = crop_box(mask)
            image, mask_image = to_model_input(gray, mask, box)
            job_dir = QUESTION_WORK_DIR / "jobs" / job_name(question_id, i)
            job_dir.mkdir(parents=True)
            image.save(job_dir / "composite.png")
            mask_image.save(job_dir / "mask.png")
            boxes[job_dir.name] = vars(box)
    boxes_path.write_text(json.dumps(boxes, indent=1))
    print(f"{len(question_ids)} questions -> {QUESTION_WORK_DIR / 'jobs'}")


def merge(question_ids):
    """GPU サーバーの出力を書き戻し、問題画像と手前マスクを保存する"""
    boxes = json.loads((QUESTION_WORK_DIR / "boxes.json").read_text())
    outputs = QUESTION_WORK_DIR / "outputs" / f"PHDiffusion_s{QUESTION_STRENGTH}"
    question_dir, mask_dir = HARMONIZED_QUESTION_DIR / "question", HARMONIZED_QUESTION_DIR / "mask"
    question_dir.mkdir(parents=True, exist_ok=True)
    mask_dir.mkdir(parents=True, exist_ok=True)
    for question_id in question_ids:
        original, alphas = compose_question(question_id)
        background = load_gray(BACKGROUND_DIR / f"{background_id(question_id)}.png")
        canvas = original.copy()
        front = np.zeros(original.shape, bool)
        for i, (p, alpha) in enumerate(zip(QUESTIONS[question_id], alphas)):
            hidden = hidden_region(background, p)
            result = Image.open(outputs / f"{job_name(question_id, i)}.png")
            paste_back(canvas, result, harmonize_mask(alpha), hidden, CropBox(**boxes[job_name(question_id, i)]))
            restore_details(canvas, original, alpha)
            front |= hidden
        to_rgb_image(canvas).save(question_dir / f"{question_id}.png")
        # キャラを隠すのに使った手前マスク（白 = キャラより手前）
        Image.fromarray((front * 255).astype(np.uint8)).save(mask_dir / f"{question_id}.png")
        print(f"question {question_id}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("step", choices=["prepare", "merge"])
    parser.add_argument("ids", nargs="*", type=int, default=list(QUESTIONS))
    args = parser.parse_args()
    {"prepare": prepare, "merge": merge}[args.step](args.ids)


if __name__ == "__main__":
    main()

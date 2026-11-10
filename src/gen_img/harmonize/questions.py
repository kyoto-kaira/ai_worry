import argparse
import json
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from gen_img.harmonize.config import QUESTION_STRENGTH, QUESTION_WORK_DIR
from gen_img.harmonize.crops import CropBox, crop_box, harmonize_mask, to_model_input
from gen_img.harmonize.merge import paste_back, restore_details
from gen_img.harmonize.review import save_hidden_crops
from gen_img.paths import BACKGROUND_DIR, GAP_QUESTION_DIR, HARMONIZED_QUESTION_DIR, HIDDEN_CROP_DIR, QUESTION_MASK_DIR
from gen_img.question.character import load_gray
from gen_img.question.compose import background_id, compose, to_rgb_image
from gen_img.question.config import GAP_QUESTIONS, QUESTIONS
from gen_img.question.occlusion import hidden_region
from gen_img.question.placement import Placement
from gen_img.question.tone import background_tone


@dataclass(frozen=True)
class QuestionSet:
    # 作業フォルダでの名前の頭（問題の種類ごとに分ける）
    prefix: str
    # 問題番号: (背景番号, 配置)
    questions: dict[int, tuple[int, list[Placement]]]
    question_dir: Path
    mask_dir: Path
    crop_dir: Path


QUESTION_SETS = {
    # 通常の問題（exp/img/harmonized_question/question/）
    "question": QuestionSet(
        "q",
        {q: (background_id(q), placements) for q, placements in QUESTIONS.items()},
        HARMONIZED_QUESTION_DIR / "question",
        QUESTION_MASK_DIR,
        HIDDEN_CROP_DIR,
    ),
    # 2つの物の隙間からのぞく問題（exp/img/harmonized_question/hidden/）
    "gap": QuestionSet(
        "g", GAP_QUESTIONS, GAP_QUESTION_DIR / "question", GAP_QUESTION_DIR / "mask", GAP_QUESTION_DIR / "crop"
    ),
}


def job_name(qs: QuestionSet, question_id: int, index: int) -> str:
    return f"{qs.prefix}{question_id:02d}_{index:02d}"


def prepare(qs: QuestionSet, question_ids):
    """問題を合成し、キャラごとの切り出し画像とマスクを作業フォルダに書き出す"""
    # 同じ種類の問題の切り出しだけ作り直す（ほかの種類の切り出しと、切り出し位置の記録は残す）
    jobs_dir = QUESTION_WORK_DIR / "jobs"
    for old in jobs_dir.glob(f"{qs.prefix}[0-9]*"):
        shutil.rmtree(old)
    boxes_path = QUESTION_WORK_DIR / "boxes.json"
    boxes = json.loads(boxes_path.read_text()) if boxes_path.exists() else {}
    for question_id in question_ids:
        gray, alphas = compose(*qs.questions[question_id])
        for i, alpha in enumerate(alphas):
            mask = harmonize_mask(alpha)
            box = crop_box(mask)
            image, mask_image = to_model_input(gray, mask, box)
            job_dir = jobs_dir / job_name(qs, question_id, i)
            job_dir.mkdir(parents=True)
            image.save(job_dir / "composite.png")
            mask_image.save(job_dir / "mask.png")
            boxes[job_dir.name] = vars(box)
    boxes_path.write_text(json.dumps(boxes, indent=1))
    print(f"{len(question_ids)} questions -> {jobs_dir}")


def merge(qs: QuestionSet, question_ids):
    """GPU サーバーの出力を書き戻し、問題画像と手前マスクを保存する"""
    boxes = json.loads((QUESTION_WORK_DIR / "boxes.json").read_text())
    outputs = QUESTION_WORK_DIR / "outputs" / f"PHDiffusion_s{QUESTION_STRENGTH}"
    qs.question_dir.mkdir(parents=True, exist_ok=True)
    qs.mask_dir.mkdir(parents=True, exist_ok=True)
    for question_id in question_ids:
        bg_id, placements = qs.questions[question_id]
        original, alphas = compose(bg_id, placements)
        background = load_gray(BACKGROUND_DIR / f"{bg_id}.png")
        canvas = original.copy()
        front = np.zeros(original.shape, bool)
        for i, (p, alpha) in enumerate(zip(placements, alphas)):
            hidden = hidden_region(background, p)
            result = Image.open(outputs / f"{job_name(qs, question_id, i)}.png")
            box = CropBox(**boxes[job_name(qs, question_id, i)])
            paste_back(canvas, result, harmonize_mask(alpha), hidden, box, background_tone(bg_id))
            restore_details(canvas, original, alpha)
            front |= hidden
        to_rgb_image(canvas).save(qs.question_dir / f"{question_id}.png")
        # キャラを隠すのに使った手前マスク（白 = キャラより手前）
        Image.fromarray((front * 255).astype(np.uint8)).save(qs.mask_dir / f"{question_id}.png")
        save_hidden_crops(question_id, placements, alphas, background, original, canvas, qs.crop_dir)
        print(f"question {question_id}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("step", choices=["prepare", "merge"])
    parser.add_argument("ids", nargs="*", type=int, help="問題番号（省略すると全問）")
    parser.add_argument("--set", choices=list(QUESTION_SETS), default="question", help="問題の種類（gap: 隙間からのぞく問題）")
    args = parser.parse_args()
    qs = QUESTION_SETS[args.set]
    {"prepare": prepare, "merge": merge}[args.step](qs, args.ids or list(qs.questions))


if __name__ == "__main__":
    main()

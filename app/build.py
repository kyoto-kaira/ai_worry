"""用意した問題を作る。gen_img.question.config.QUESTIONS の配置で本物と偽物を背景に貼っただけの画像（物陰には隠さず、
AI でなじませもしない）と、正解の枠と、YOLO の検出結果を app/data/builtin/ に書き出す。
アプリは起動時にこれを読むだけなので、問題の配置・YOLO のモデル・推論の設定を変えたら作り直す

uv run python app/build.py                    # 画像・正解・検出結果を全部作る（約3分）
uv run python app/build.py --detections-only  # YOLO の検出結果だけ作り直す（モデルを替えたとき。約20秒）
"""
import argparse
import json
from dataclasses import replace

import numpy as np

from config import ANSWERS_PATH, DETECTIONS_PATH, QUESTION_IMAGE_DIR
from detect import Detector, save_detections, seed_of
from gen_img.question.compose import background_id, compose, to_rgb_image
from gen_img.question.config import QUESTIONS


def visible_box(alpha: np.ndarray) -> list[int]:
    ys, xs = np.nonzero(alpha > 0.5)
    return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]


def build_questions() -> dict:
    """問題画像と正解の枠を作る"""
    QUESTION_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    answers = {}
    for question_id, placements in QUESTIONS.items():
        # 手前マスクを外して、物の陰に隠さずに貼る
        pasted = [replace(p, front_mask=None) for p in placements]
        gray, alphas = compose(background_id(question_id), pasted)
        image = to_rgb_image(gray)
        image.save(QUESTION_IMAGE_DIR / f"{question_id}.png")
        answers[str(question_id)] = {
            "width": image.width,
            "height": image.height,
            # 先頭が本物
            "characters": [
                {"kind": "real" if i == 0 else "fake", "image": p.image.name, "box": visible_box(alpha), "hidden": False}
                for i, (p, alpha) in enumerate(zip(pasted, alphas))
            ],
        }
        print(f"question {question_id}: {len(placements)} characters")
    ANSWERS_PATH.write_text(json.dumps(answers, indent=1, ensure_ascii=False), encoding="utf-8")
    return answers


def build_detections(answers: dict):
    """YOLO の検出結果を作る（どのモデル・設定で作ったかも一緒に保存する）"""
    detector = Detector()
    detections = {
        q: detector.detect(QUESTION_IMAGE_DIR / f"{q}.png", answer, seed=seed_of(q)) for q, answer in answers.items()
    }
    save_detections(DETECTIONS_PATH, detector.key, detections)
    print(f"detections: {len(detections)} questions ({'YOLO' if detector.mode == 'yolo' else 'モック: ' + detector.reason})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--detections-only", action="store_true", help="画像と正解はそのままで、YOLO の検出結果だけ作り直す")
    args = parser.parse_args()
    if args.detections_only:
        answers = json.loads(ANSWERS_PATH.read_text(encoding="utf-8"))
    else:
        answers = build_questions()
    build_detections(answers)


if __name__ == "__main__":
    main()

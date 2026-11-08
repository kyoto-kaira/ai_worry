"""問題画像ごとに、本物・偽物の見えている範囲の枠を answers.json に書き出す（問題の配置を変えたら作り直す）

uv run python app/build_answers.py
"""
import json

import numpy as np
from PIL import Image

from config import ANSWERS_PATH, QUESTION_IMAGE_DIR, SKIP_QUESTIONS
from gen_img.question.compose import compose_question
from gen_img.question.config import QUESTIONS


def visible_box(alpha: np.ndarray) -> list[int]:
    ys, xs = np.nonzero(alpha > 0.5)
    return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]


def main():
    answers = {}
    for question_id, placements in QUESTIONS.items():
        path = QUESTION_IMAGE_DIR / f"{question_id}.png"
        if not path.exists() or question_id in SKIP_QUESTIONS:
            continue
        _, alphas = compose_question(question_id)
        width, height = Image.open(path).size
        answers[question_id] = {
            "width": width,
            "height": height,
            # 先頭が本物
            "characters": [
                {"kind": "real" if i == 0 else "fake", "image": p.image.name, "box": visible_box(alpha), "hidden": bool(p.front_mask)}
                for i, (p, alpha) in enumerate(zip(placements, alphas))
            ],
        }
        print(f"question {question_id}: {len(placements)} characters")
    ANSWERS_PATH.write_text(json.dumps(answers, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()

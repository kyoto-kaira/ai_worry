import argparse

from gen_img.paths import QUESTION_DIR
from gen_img.question.compose import background_id, build_question
from gen_img.question.config import QUESTIONS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ids", nargs="*", type=int, default=list(QUESTIONS))
    args = parser.parse_args()

    QUESTION_DIR.mkdir(exist_ok=True)
    for question_id in args.ids:
        build_question(question_id).save(QUESTION_DIR / f"{question_id}.png")
        real = QUESTIONS[question_id][0]
        print(f"question {question_id}: background {background_id(question_id)}, real at ({real.x}, {real.y})")


if __name__ == "__main__":
    main()

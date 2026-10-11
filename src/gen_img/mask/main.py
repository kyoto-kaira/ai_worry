import argparse
import json
import shutil
from dataclasses import asdict

import numpy as np
from PIL import Image

from gen_img.mask.config import LASSO_TARGETS, SAM_TARGETS, WORK_DIR
from gen_img.mask.shape import clean_mask, lasso_mask
from gen_img.paths import BACKGROUND_DIR, OCCLUDER_DIR
from gen_img.question.character import load_gray


def save(mask: np.ndarray, name: str):
    OCCLUDER_DIR.mkdir(parents=True, exist_ok=True)
    Image.fromarray((mask * 255).astype(np.uint8)).save(OCCLUDER_DIR / f"{name}.png")
    print(f"saved {name}.png")


def prepare():
    """GPU サーバーに送るもの（背景と targets.json）を作業フォルダに用意する"""
    shutil.rmtree(WORK_DIR, ignore_errors=True)
    (WORK_DIR / "backgrounds").mkdir(parents=True)
    for bg_id in {t.bg_id for t in SAM_TARGETS}:
        shutil.copy(BACKGROUND_DIR / f"{bg_id}.png", WORK_DIR / "backgrounds")
    (WORK_DIR / "targets.json").write_text(json.dumps([asdict(t) for t in SAM_TARGETS], indent=1))
    print(f"{len(SAM_TARGETS)} targets -> {WORK_DIR}")


def finish():
    """GPU サーバーの出力（masks/<名前>_<候補>.png）から候補を選んで整え、手前マスクとして保存する"""
    for t in SAM_TARGETS:
        raw = np.asarray(Image.open(WORK_DIR / "masks" / f"{t.name}_{t.candidate}.png")) > 127
        save(clean_mask(raw), t.name)


def lasso():
    """多角形から作るマスク（GPU 不要）"""
    for t in LASSO_TARGETS:
        background = load_gray(BACKGROUND_DIR / f"{t.bg_id}.png")
        save(clean_mask(lasso_mask(background, t.polygon, t.snap)), t.name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("step", choices=["prepare", "finish", "lasso"])
    args = parser.parse_args()
    {"prepare": prepare, "finish": finish, "lasso": lasso}[args.step]()


if __name__ == "__main__":
    main()

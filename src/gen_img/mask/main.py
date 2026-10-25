import argparse
import json
import shutil
from dataclasses import asdict

import numpy as np
from PIL import Image

from gen_img.mask.config import LASSO_TARGETS, ROUGH_TARGETS, SAM_TARGETS, WORK_DIR
from gen_img.mask.rough import coverage_warning, load_rough, pick_candidate, refine, sam_prompts
from gen_img.mask.shape import clean_mask, lasso_mask, outside_mask
from gen_img.paths import BACKGROUND_DIR, HARD_OCCLUDER_DIR, OCCLUDER_DIR
from gen_img.question.character import load_gray


def save(mask: np.ndarray, name: str, hard: bool = False):
    """手前マスクを保存する（難しい物は object/hard/、それ以外は object/normal/）"""
    folder = HARD_OCCLUDER_DIR if hard else OCCLUDER_DIR
    folder.mkdir(parents=True, exist_ok=True)
    Image.fromarray((mask * 255).astype(np.uint8)).save(folder / f"{name}.png")
    print(f"saved {folder.name}/{name}.png")


def selected(targets, names):
    """名前の指定がなければ全部、あればその名前のものだけ"""
    return [t for t in targets if not names or t.name in names]


def rough_prompt(t) -> dict:
    """人が塗った範囲から、SAM への指示（枠と内側の点）を作る"""
    box, points = sam_prompts(load_rough(t.name), load_gray(BACKGROUND_DIR / f"{t.bg_id}.png"), t.fill)
    return {"name": t.name, "bg_id": t.bg_id, "search_box": box, "object_text": "", "points": points}


def prepare(names):
    """GPU サーバーに送るもの（背景と targets.json）を作業フォルダに用意する"""
    targets = [asdict(t) for t in selected(SAM_TARGETS, names)]
    targets += [rough_prompt(t) for t in selected(ROUGH_TARGETS, names)]
    shutil.rmtree(WORK_DIR, ignore_errors=True)
    (WORK_DIR / "backgrounds").mkdir(parents=True)
    for bg_id in {t["bg_id"] for t in targets}:
        shutil.copy(BACKGROUND_DIR / f"{bg_id}.png", WORK_DIR / "backgrounds")
    (WORK_DIR / "targets.json").write_text(json.dumps(targets, indent=1))
    print(f"{len(targets)} targets -> {WORK_DIR}")


def finish(names):
    """GPU サーバーの出力（masks/<名前>_<候補>.png）から候補を選んで整え、手前マスクとして保存する"""
    for t in selected(SAM_TARGETS, names):
        raw = np.asarray(Image.open(WORK_DIR / "masks" / f"{t.name}_{t.candidate}.png")) > 127
        save(clean_mask(raw), t.name)
    for t in selected(ROUGH_TARGETS, names):
        rough = load_rough(t.name)
        candidates = [np.asarray(Image.open(WORK_DIR / "masks" / f"{t.name}_{k}.png")) > 127 for k in range(3)]
        choice, coverage = pick_candidate(candidates, rough, t.fill)
        if choice is None:
            print(f"warning: {t.name}: SAM が物体を切り抜けなかったので、塗った範囲をそのまま使う")
        elif warning := coverage_warning(t.name, coverage):
            print(warning)
        save(refine(rough, None if choice is None else candidates[choice], t.fill), t.name, t.hard)


def lasso(names):
    """多角形から作るマスク（GPU 不要）"""
    for t in selected(LASSO_TARGETS, names):
        background = load_gray(BACKGROUND_DIR / f"{t.bg_id}.png")
        if t.outside_box:
            save(outside_mask(background.shape, t.polygon, t.outside_box), t.name)
        else:
            save(clean_mask(lasso_mask(background, t.polygon, t.snap)), t.name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("step", choices=["prepare", "finish", "lasso"])
    parser.add_argument("names", nargs="*", help="作る物の名前（省略すると全部）")
    args = parser.parse_args()
    {"prepare": prepare, "finish": finish, "lasso": lasso}[args.step](args.names)


if __name__ == "__main__":
    main()

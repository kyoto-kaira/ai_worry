import numpy as np
from PIL import Image
from scipy import ndimage as ndi

from gen_img.kaira_kun.transparent import on_white
from gen_img.mask.config import ROUGH_LEAK_WEIGHT, ROUGH_MIN_COVERAGE, ROUGH_MIN_SCORE, ROUGH_POINT_COUNT, ROUGH_POINT_INSET
from gen_img.mask.shape import clean_mask
from gen_img.paths import ROUGH_MASK_DIR
from gen_img.question.character import disk


def load_rough(name: str) -> np.ndarray:
    """人が物体の内側を大まかに黒く塗った範囲（透明・白の所は塗っていない扱い）"""
    return on_white(Image.open(ROUGH_MASK_DIR / f"{name}.png")) < 128


def sam_prompts(rough: np.ndarray, background: np.ndarray, fill: int) -> tuple[list[int], list[tuple[int, int]]]:
    """塗った範囲から SAM への指示を作る：fill px 広げた外枠と、内側の点（背景の線の上は避ける）"""
    ys, xs = np.nonzero(rough)
    height, width = rough.shape
    box = [
        int(max(0, xs.min() - fill)), int(max(0, ys.min() - fill)),
        int(min(width - 1, xs.max() + fill)), int(min(height - 1, ys.max() + fill)),
    ]
    inner = ndi.binary_erosion(rough, structure=disk(ROUGH_POINT_INSET)) & (background >= 200)
    if not inner.any():
        inner = rough
    candidates = np.argwhere(inner)
    # 互いに一番遠い点を順に選び、範囲全体に散らす
    chosen = [candidates[len(candidates) // 2]]
    distance = np.full(len(candidates), np.inf)
    for _ in range(ROUGH_POINT_COUNT - 1):
        distance = np.minimum(distance, ((candidates - chosen[-1]) ** 2).sum(axis=1))
        chosen.append(candidates[np.argmax(distance)])
    return box, [(int(x), int(y)) for y, x in chosen]


def candidate_scores(candidates: list[np.ndarray], rough: np.ndarray, fill: int) -> list[tuple[float, float, float]]:
    """候補ごとの（点数, 塗った範囲を含む割合, 塗った範囲から fill px より外にはみ出した割合）"""
    near = ndi.binary_dilation(rough, structure=disk(fill))
    scores = []
    for c in candidates:
        coverage = (c & rough).sum() / max(1, rough.sum())
        leak = (c & ~near).sum() / max(1, c.sum())
        scores.append((coverage - ROUGH_LEAK_WEIGHT * leak, coverage, leak))
    return scores


def pick_candidate(candidates: list[np.ndarray], rough: np.ndarray, fill: int) -> tuple[int | None, float]:
    """点数の一番高い候補の番号と、その候補が塗った範囲を含む割合。SAM が切り抜けなかったときは番号が None"""
    scores = candidate_scores(candidates, rough, fill)
    choice = int(np.argmax([score for score, _, _ in scores]))
    if scores[choice][0] < ROUGH_MIN_SCORE:
        return None, 1.0
    return choice, scores[choice][1]


def refine(rough: np.ndarray, sam: np.ndarray | None, fill: int) -> np.ndarray:
    """SAM が物体とみなした所のうち、塗った範囲から fill px 以内だけを使う。
    塗りのうち SAM が物体の外と判断した所（隣の物にかかった塗り）は外す。SAM が切り抜けなかったときは塗りをそのまま使う"""
    if sam is None:
        return clean_mask(rough)
    near = ndi.binary_dilation(rough, structure=disk(fill))
    mask = clean_mask(sam & near)
    # マスクに囲まれた穴のうち、人が塗った所にかかる穴は物体の一部として埋める（塗っていない穴は窓のガラスなどとして残す）
    holes, count = ndi.label(ndi.binary_fill_holes(mask) & ~mask)
    painted = np.unique(holes[rough & (holes > 0)])
    return mask | np.isin(holes, painted)


def coverage_warning(name: str, coverage: float) -> str | None:
    if coverage >= ROUGH_MIN_COVERAGE:
        return None
    return (
        f"warning: {name}: 塗った範囲の {1 - coverage:.0%} を SAM が物体の外と判断して外した。"
        "塗りが物体からはみ出していないか、隣の物まで塗っていないか確認する"
    )

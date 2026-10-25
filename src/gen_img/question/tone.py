from functools import lru_cache

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

from gen_img.paths import BACKGROUND_DIR


def measure_tone(gray: np.ndarray, region: np.ndarray | None = None) -> tuple[float, float]:
    """（線の芯の黒さ, 線から離れた所の白さ）。どちらも中央値"""
    region = np.ones(gray.shape, bool) if region is None else region
    lines = gray < 128
    core = gray[skeletonize(lines) & region]
    paper = gray[~ndi.binary_dilation(gray < 200, iterations=3) & region]
    black = float(np.median(core)) if core.size else 0.0
    white = float(np.median(paper)) if paper.size else 255.0
    return black, white


def core_width(gray: np.ndarray, upscale: int = 4) -> float:
    """線の芯の位置での線の太さ（px、真ん中半分の平均）。見た目の太さに近い。拡大して細かく測る"""
    size = (gray.shape[1] * upscale, gray.shape[0] * upscale)
    big = np.asarray(Image.fromarray(gray.clip(0, 255).astype(np.uint8)).resize(size, Image.LANCZOS))
    dark = big < 128
    skeleton = skeletonize(dark)
    if not skeleton.any():
        return 0.0
    widths = 2 * ndi.distance_transform_edt(dark)[skeleton] / upscale
    low, high = np.percentile(widths, [25, 75])
    return float(widths[(widths >= low) & (widths <= high)].mean())


def _load_background(bg_id: int) -> np.ndarray:
    return np.asarray(Image.open(BACKGROUND_DIR / f"{bg_id}.png").convert("L")).astype(np.float32)


@lru_cache
def background_tone(bg_id: int) -> tuple[float, float]:
    return measure_tone(_load_background(bg_id))


@lru_cache
def background_stroke(bg_id: int) -> float:
    return core_width(_load_background(bg_id))


def match_tone(gray: np.ndarray, source: tuple[float, float], target: tuple[float, float]) -> np.ndarray:
    """source の黒と白が target の黒と白になるよう、濃さを直線で付け直す"""
    (sb, sw), (tb, tw) = source, target
    if sw - sb < 1:
        return gray
    return np.clip(tb + (gray - sb) * (tw - tb) / (sw - sb), 0, 255)

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

from gen_img.harmonize.config import DETAIL_DENSITY, DETAIL_SIGMA, MERGE_FEATHER, PROTRUSION_RADIUS
from gen_img.harmonize.crops import CropBox
from gen_img.question.character import disk


def paste_back(canvas: np.ndarray, harmonized: Image.Image, mask: np.ndarray, hidden: np.ndarray, box: CropBox):
    """モデルの出力を元の大きさに戻し、調和させた範囲だけを元画像に書き戻す。
    手前にある物（茂み・サンゴなど）の上は書き戻さず、元の輪郭を残す"""
    patch = np.asarray(harmonized.convert("L").resize((box.size, box.size), Image.LANCZOS)).astype(np.float32)
    weight = ndi.gaussian_filter(box.cut(mask & ~hidden).astype(np.float32), MERGE_FEATHER) * ~box.cut(hidden)
    area = box.cut(canvas)
    area[:] = area * (1 - weight) + patch * weight


def detail_mask(original: np.ndarray, visible_alpha: np.ndarray) -> np.ndarray:
    """キャラの中で線が密集している所（目・しっぽ・手足・飾り）と、
    体から細く飛び出した所（アホ毛・触角・王冠のとげなど。線が少ないので密度では拾えない）"""
    body = visible_alpha > 0.5
    area = ndi.binary_dilation(body, structure=disk(3))
    density = ndi.gaussian_filter(((original < 128) & area).astype(np.float32), DETAIL_SIGMA)
    dense = ndi.binary_dilation((density > DETAIL_DENSITY) & area, structure=disk(3))
    protruding = ndi.binary_dilation(body & ~ndi.binary_opening(body, structure=disk(PROTRUSION_RADIUS)), structure=disk(3))
    return (dense | protruding) & area


def restore_details(canvas: np.ndarray, original: np.ndarray, visible_alpha: np.ndarray):
    """細かい部分だけ、AI を通す前の画像に戻す（AI がなじませるのは体の輪郭だけになる）"""
    weight = ndi.gaussian_filter(detail_mask(original, visible_alpha).astype(np.float32), 1.0)
    canvas[:] = canvas * (1 - weight) + original * weight

import numpy as np
from scipy import ndimage as ndi

from gen_img.question.character import disk
from gen_img.question.config import OCCLUDER_MAX_AREA


def label_regions(background: np.ndarray) -> np.ndarray:
    # 線画の 1〜2px の隙間を閉じて、隣の領域に漏れないようにする
    return ndi.label(~ndi.binary_dilation(background < 160, structure=disk(1)))[0]


def region_at(labels: np.ndarray, x: int, y: int, snap: int = 8) -> np.ndarray:
    """(x, y) を含む領域を返す。線の上なら一番近い空白に寄せる"""
    window = labels[y - snap : y + snap + 1, x - snap : x + snap + 1]
    ys, xs = np.nonzero(window)
    if not len(ys):
        raise ValueError(f"point {(x, y)} is surrounded by lines")
    i = np.argmin((ys - snap) ** 2 + (xs - snap) ** 2)
    return ndi.binary_fill_holes(labels == window[ys[i], xs[i]])


def occluder_mask(background: np.ndarray, points) -> np.ndarray:
    """`points` を含む背景の物体（輪郭線込み）のマスク"""
    labels = label_regions(background)
    mask = np.zeros(background.shape, bool)
    for x, y in points:
        region = region_at(labels, x, y)
        if region.mean() > OCCLUDER_MAX_AREA:
            raise ValueError(f"occluder at {(x, y)} leaks into a huge region")
        mask |= region
    return ndi.binary_dilation(mask, structure=disk(3))

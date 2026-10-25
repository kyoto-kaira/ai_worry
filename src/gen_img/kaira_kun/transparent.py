import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.measure import regionprops

from gen_img.kaira_kun.config import BEAD_MAX_AREA, BEAD_MAX_ELONGATION, NEAR_WHITE, TAIL_LEFT_MARGIN, TAIL_TOP_RATIO


def _regions(gray: np.ndarray):
    """線に囲まれた領域のラベルと、外側（画像の端につながる所）の番号"""
    labels, count = ndi.label(gray >= 128)
    edge = np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]])
    return labels, count, set(np.unique(edge[edge > 0]))


def tail_gaps(gray: np.ndarray) -> np.ndarray:
    """しっぽの網目の間（体の一部ではないので透明にする所）"""
    labels, count, outside = _regions(gray)
    sizes = ndi.sum(np.ones_like(labels), labels, range(1, count + 1))
    inner = [k for k in range(1, count + 1) if k not in outside]
    if not inner:
        return np.zeros(gray.shape, bool)
    body = max(inner, key=lambda k: sizes[k - 1])
    ys, xs = np.nonzero(labels == body)
    body_top, body_height = ys.min(), np.ptp(ys)
    tail_left = xs.max() - TAIL_LEFT_MARGIN * np.ptp(xs)

    gaps = np.zeros(gray.shape, bool)
    for region in regionprops(labels):
        if region.label not in inner or region.label == body:
            continue
        top, _, _, _ = region.bbox
        elongation = region.axis_major_length / max(1.0, region.axis_minor_length)
        is_bead = region.area < BEAD_MAX_AREA * sizes[body - 1] and elongation < BEAD_MAX_ELONGATION
        if region.centroid[1] > tail_left and top > body_top + TAIL_TOP_RATIO * body_height and not is_bead:
            gaps |= labels == region.label
    return gaps


def on_white(image: Image.Image) -> np.ndarray:
    """白い背景に重ねたときの見た目（グレースケール）"""
    canvas = Image.new("RGBA", image.size, "white")
    canvas.alpha_composite(image.convert("RGBA"))
    return np.asarray(canvas.convert("L")).astype(np.float32)


def to_transparent(image: Image.Image) -> Image.Image:
    """白黒＋透明にする：線は黒、体の中は白、外側としっぽの網目の間は透明"""
    gray = on_white(image)
    gray[gray >= NEAR_WHITE] = 255
    labels, _, outside = _regions(gray)
    clear = np.isin(labels, list(outside)) | tail_gaps(gray)
    # 線の縁の淡い所は、濃さに応じて半透明にする（白い背景に重ねると元と同じ見た目になる）
    darkness = (255 - gray).clip(0, 255)
    alpha = np.where(clear, darkness, 255)
    color = np.where(clear, 0, gray)
    rgba = np.stack([color, color, color, alpha], axis=2).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")

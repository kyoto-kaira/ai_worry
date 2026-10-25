import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

from gen_img.question.character import disk

# マスクの面積のこの割合より小さい穴は埋める
MAX_FILLED_HOLE = 0.02


def lasso_mask(background: np.ndarray, polygon, snap: int = 6) -> np.ndarray:
    """大まかな多角形を、縁の近くにある背景の線（葉っぱの輪郭など）まで広げたマスク"""
    image = Image.new("L", background.shape[::-1], 0)
    ImageDraw.Draw(image).polygon([tuple(p) for p in polygon], fill=255)
    inside = np.asarray(image) > 0
    lines = ndi.binary_dilation(background < 160, structure=disk(1))
    near_edge = ndi.binary_dilation(inside, structure=disk(snap)) & ~inside
    # 縁にかかる線は、その線のまとまりごと手前に含める
    labels, _ = ndi.label(lines)
    touching = np.unique(labels[near_edge & lines & ndi.binary_dilation(inside, structure=disk(1))])
    edge_lines = np.isin(labels, touching[touching > 0]) & near_edge
    return inside | edge_lines


def circle_polygon(cx: int, cy: int, r: int, n: int = 48) -> list[tuple[int, int]]:
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return [(round(cx + r * np.cos(a)), round(cy + r * np.sin(a))) for a in angles]


def outside_mask(shape, polygon, box) -> np.ndarray:
    """範囲 box から多角形の内側を除いた所（窓の枠と壁など）"""
    image = Image.new("L", shape[::-1], 0)
    draw = ImageDraw.Draw(image)
    draw.rectangle(box, fill=255)
    draw.polygon([tuple(p) for p in polygon], fill=0)
    return np.asarray(image) > 0


def clean_mask(mask: np.ndarray) -> np.ndarray:
    """マスクを整える：一番大きいかたまりだけ残し、小さな穴を埋める
    （離れた所に飛び地があると、キャラの顔の一部だけが不自然に隠れるため）"""
    labels, count = ndi.label(mask)
    if count == 0:
        return mask
    sizes = ndi.sum(mask, labels, range(1, count + 1))
    largest = ndi.binary_closing(labels == (np.argmax(sizes) + 1), structure=disk(2))
    # 小さな穴だけ埋める（窓のガラスのように、わざと空けてある大きな穴は残す）
    holes = ndi.binary_fill_holes(largest) & ~largest
    hole_labels, hole_count = ndi.label(holes)
    if hole_count == 0:
        return largest
    hole_sizes = ndi.sum(holes, hole_labels, range(1, hole_count + 1))
    small = np.flatnonzero(hole_sizes < MAX_FILLED_HOLE * largest.sum()) + 1
    return largest | np.isin(hole_labels, small)

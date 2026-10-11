import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

from gen_img.question.character import disk


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


def clean_mask(mask: np.ndarray) -> np.ndarray:
    """マスクを整える：一番大きいかたまりだけ残し、小さな穴を埋める
    （離れた所に飛び地があると、キャラの顔の一部だけが不自然に隠れるため）"""
    labels, count = ndi.label(mask)
    if count == 0:
        return mask
    sizes = ndi.sum(mask, labels, range(1, count + 1))
    largest = labels == (np.argmax(sizes) + 1)
    return ndi.binary_fill_holes(ndi.binary_closing(largest, structure=disk(2)))

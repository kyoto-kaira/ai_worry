import numpy as np
from PIL import Image


def load_front_mask(path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("L")) > 127


def hidden_region(background: np.ndarray, placement) -> np.ndarray:
    """キャラより手前にある範囲（画像全体の大きさ。マスクが複数あれば合わせた範囲）"""
    hidden = np.zeros(background.shape, bool)
    for path in placement.front_masks():
        hidden |= load_front_mask(path)
    return hidden

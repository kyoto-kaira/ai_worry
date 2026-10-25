import numpy as np
from PIL import Image


def load_front_mask(path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("L")) > 127


def hidden_region(background: np.ndarray, placement) -> np.ndarray:
    """キャラより手前にある範囲（画像全体の大きさ）"""
    if placement.front_mask is None:
        return np.zeros(background.shape, bool)
    return load_front_mask(placement.front_mask)

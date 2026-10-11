from dataclasses import dataclass

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

from gen_img.harmonize.config import CROP_CONTEXT, MASK_DILATION, MODEL_SIZE
from gen_img.question.character import disk


@dataclass(frozen=True)
class CropBox:
    x: int
    y: int
    size: int

    def cut(self, image: np.ndarray) -> np.ndarray:
        return image[self.y : self.y + self.size, self.x : self.x + self.size]


def harmonize_mask(visible_alpha: np.ndarray) -> np.ndarray:
    """調和させる範囲（キャラの見えている部分を少し広げたもの）"""
    return ndi.binary_dilation(visible_alpha > 0.5, structure=disk(MASK_DILATION))


def crop_box(mask: np.ndarray) -> CropBox:
    """キャラを中心に、周りの背景も含む正方形（画像の外にはみ出さない）"""
    ys, xs = np.nonzero(mask)
    height, width = mask.shape
    size = min(int(max(np.ptp(ys), np.ptp(xs)) * CROP_CONTEXT), height, width)
    cx, cy = (xs.min() + xs.max()) // 2, (ys.min() + ys.max()) // 2
    x = int(np.clip(cx - size // 2, 0, width - size))
    y = int(np.clip(cy - size // 2, 0, height - size))
    return CropBox(x, y, size)


def to_model_input(gray: np.ndarray, mask: np.ndarray, box: CropBox) -> tuple[Image.Image, Image.Image]:
    image = Image.fromarray(box.cut(gray).astype(np.uint8)).convert("RGB")
    mask_image = Image.fromarray((box.cut(mask) * 255).astype(np.uint8))
    size = (MODEL_SIZE, MODEL_SIZE)
    return image.resize(size, Image.LANCZOS), mask_image.resize(size, Image.NEAREST)

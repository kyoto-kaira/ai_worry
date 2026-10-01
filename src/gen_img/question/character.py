import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

from gen_img.question.config import HALO_RADIUS
from gen_img.question.placement import Placement


def disk(r: int) -> np.ndarray:
    y, x = np.ogrid[-r : r + 1, -r : r + 1]
    return x * x + y * y <= r * r


def line_width(gray: np.ndarray) -> float:
    """平均の線の太さ（インク量 ÷ 細線化した線の長さ）"""
    return ((255 - gray) / 255).sum() / max(1, skeletonize(gray < 128).sum())


def load_gray(path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("L")).astype(np.float32)


def _trimmed(gray: np.ndarray, pad: int = 4) -> np.ndarray:
    ys, xs = np.where(gray < 128)
    return np.pad(gray[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1], pad, constant_values=255)


def _match_stroke(gray: np.ndarray, scale: float, stroke_width: float) -> np.ndarray:
    """拡縮後の線の太さが `stroke_width` px になるよう線を太く／細くする"""
    r = (line_width(gray) - stroke_width / scale) / 2
    if r > 0.5:
        return ndi.grey_dilation(gray, footprint=disk(round(r)))
    if r < -0.5:
        return ndi.grey_erosion(gray, footprint=disk(round(-r)))
    return gray


def _silhouette(gray: np.ndarray) -> np.ndarray:
    lines = gray < 128
    closed = ndi.binary_closing(np.pad(lines, 12), structure=disk(6))[12:-12, 12:-12]
    return ndi.binary_fill_holes(closed | lines)


def render_character(p: Placement, stroke_width: float, blur: float) -> tuple[np.ndarray, np.ndarray]:
    """配置どおりに拡縮・回転した（線画, シルエットの不透明度 0〜1）を返す"""
    gray = _trimmed(load_gray(p.image))
    scale = p.width / gray.shape[1]
    gray = _match_stroke(gray, scale, stroke_width)

    image = Image.fromarray(gray.astype(np.uint8))
    mask = Image.fromarray((_silhouette(gray) * 255).astype(np.uint8))
    if p.flip:
        image, mask = image.transpose(Image.FLIP_LEFT_RIGHT), mask.transpose(Image.FLIP_LEFT_RIGHT)
    size = (p.width, max(1, round(gray.shape[0] * scale)))
    image, mask = image.resize(size, Image.LANCZOS), mask.resize(size, Image.LANCZOS)
    if p.angle:
        image = image.rotate(p.angle, Image.BICUBIC, expand=True, fillcolor=255)
        mask = mask.rotate(p.angle, Image.BICUBIC, expand=True, fillcolor=0)

    image = np.asarray(image).astype(np.float32)
    if blur:
        image = ndi.gaussian_filter(image, blur)
    mask = ndi.grey_dilation(np.asarray(mask), footprint=disk(HALO_RADIUS))
    return image, mask.astype(np.float32) / 255

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

from gen_img.harmonize.config import REVIEW_CROP_SCALE, REVIEW_PANEL_SIZE
from gen_img.harmonize.crops import CropBox
from gen_img.paths import HIDDEN_CROP_DIR, ROUGH_MASK_DIR
from gen_img.question.occlusion import load_front_mask
from gen_img.question.placement import Placement


def review_box(p: Placement, visible_alpha: np.ndarray) -> CropBox:
    """見えている部分を中心に、隠している物も入る正方形"""
    ys, xs = np.nonzero(visible_alpha > 0.5)
    height, width = visible_alpha.shape
    size = min(int(p.width * REVIEW_CROP_SCALE), height, width)
    cx, cy = (xs.min() + xs.max()) // 2, (ys.min() + ys.max()) // 2
    x = int(np.clip(cx - size // 2, 0, width - size))
    y = int(np.clip(cy - size // 2, 0, height - size))
    return CropBox(x, y, size)


def _rough(p: Placement) -> np.ndarray | None:
    """その物の手前マスクの元になった、人が塗った範囲（塗りから作っていない物は None）"""
    path = ROUGH_MASK_DIR / p.front_mask.name
    return np.asarray(Image.open(path).convert("L")) < 128 if path.exists() else None


def _panel(
    gray: np.ndarray, box: CropBox, title: str, overlay: np.ndarray | None = None, color=(255, 0, 0),
    outline: np.ndarray | None = None,
) -> Image.Image:
    """切り出しに、overlay を半透明で塗り、outline の縁を赤い線で描く"""
    rgb = np.stack([box.cut(gray)] * 3, axis=2)
    if overlay is not None:
        rgb[overlay] = rgb[overlay] * 0.5 + np.array(color) * 0.5
    if outline is not None:
        edge = outline & ~ndi.binary_erosion(outline, iterations=2)
        rgb[edge] = (255, 0, 0)
    image = Image.fromarray(rgb.clip(0, 255).astype(np.uint8)).resize((REVIEW_PANEL_SIZE, REVIEW_PANEL_SIZE))
    ImageDraw.Draw(image).text((4, 4), title, fill=(0, 0, 255))
    return image


def save_hidden_crops(question_id: int, placements, alphas, background: np.ndarray, original: np.ndarray, harmonized: np.ndarray):
    """物陰に隠れたキャラごとに「なじませる前・後・人が塗った範囲（青、手前マスクの縁を赤い線）・手前マスク（赤）」を並べて保存する"""
    HIDDEN_CROP_DIR.mkdir(parents=True, exist_ok=True)
    for i, (p, alpha) in enumerate(zip(placements, alphas)):
        if not p.front_mask or not (alpha > 0.5).any():
            continue
        box = review_box(p, alpha)
        rough = _rough(p)
        mask = box.cut(load_front_mask(p.front_mask))
        rough_title = "rough (blue) / mask (red line)" if rough is not None else "rough: none / mask (red line)"
        panels = [
            _panel(original, box, "before"),
            _panel(harmonized, box, "after"),
            _panel(background, box, rough_title, None if rough is None else box.cut(rough), (0, 90, 255), outline=mask),
            _panel(background, box, "mask", mask),
        ]
        sheet = Image.new("RGB", (len(panels) * (REVIEW_PANEL_SIZE + 4) - 4, REVIEW_PANEL_SIZE), "gray")
        for k, panel in enumerate(panels):
            sheet.paste(panel, (k * (REVIEW_PANEL_SIZE + 4), 0))
        kind = "real" if i == 0 else "fake"
        sheet.save(HIDDEN_CROP_DIR / f"{question_id}_{i}_{kind}_{p.label or p.front_mask.stem}.png")

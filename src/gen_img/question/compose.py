import numpy as np
from PIL import Image
from scipy import ndimage as ndi

from gen_img.paths import BACKGROUND_DIR, FAKE_DIR, REAL_DIR
from gen_img.question.character import load_gray, render_character
from gen_img.question.config import (
    BACKGROUND_COUNT,
    BACKGROUND_STYLES,
    DISTANT_STROKE_SCALE,
    DISTANT_WIDTH,
    QUESTIONS,
)
from gen_img.question.occlusion import occluder_mask
from gen_img.question.placement import Placement


def background_id(question_id: int) -> int:
    return (question_id - 1) % BACKGROUND_COUNT + 1


def _check_single_real(placements: list[Placement]):
    real, *fakes = placements
    if real.image.parent != REAL_DIR or any(p.image.parent != FAKE_DIR for p in fakes):
        raise ValueError("a question must contain exactly one real Kaira-kun, placed first")


def _paste(canvas: np.ndarray, background: np.ndarray, p: Placement, image, alpha):
    h, w = canvas[p.y : p.y + image.shape[0], p.x : p.x + image.shape[1]].shape
    image, alpha = image[:h, :w], alpha[:h, :w]
    if p.behind:
        hidden = occluder_mask(background, p.behind)[p.y : p.y + h, p.x : p.x + w]
        visible = 1 - ndi.gaussian_filter(hidden.astype(np.float32), 0.7)
        image = 255 - (255 - image) * visible
        alpha = alpha * visible

    area = canvas[p.y : p.y + h, p.x : p.x + w]
    area[:] = area * (1 - alpha) + 255 * alpha  # キャラの後ろの背景を白で消す
    area[:] = np.minimum(area, image)


def build_question(question_id: int) -> Image.Image:
    placements = QUESTIONS[question_id]
    _check_single_real(placements)
    bg_id = background_id(question_id)
    style = BACKGROUND_STYLES[bg_id]

    background = load_gray(BACKGROUND_DIR / f"{bg_id}.png")
    canvas = background.copy()
    for p in placements:
        stroke = style.stroke_width * (DISTANT_STROKE_SCALE if p.width < DISTANT_WIDTH else 1)
        image, alpha = render_character(p, stroke, style.blur)
        _paste(canvas, background, p, image, alpha)

    out = np.clip(canvas, 0, 255).astype(np.uint8)
    return Image.fromarray(np.stack([out] * 3, axis=2))

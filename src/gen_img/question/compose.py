import numpy as np
from PIL import Image
from scipy import ndimage as ndi

from gen_img.paths import BACKGROUND_DIR, FAKE_DIR, HARD_OCCLUDER_DIR, REAL_DIR
from gen_img.question.character import load_gray, render_character
from gen_img.question.config import (
    NUM_QUESTIONS_PER_BACKGROUND,
    BACKGROUND_STYLES,
    DISTANT_STROKE_SCALE,
    DISTANT_WIDTH,
    MIN_FRAGMENT_RATIO,
    MIN_VISIBLE_EYES,
    MIN_VISIBLE_HEAD,
    QUESTIONS,
)
from gen_img.question.occlusion import hidden_region
from gen_img.question.placement import Placement
from gen_img.question.tone import background_stroke, background_tone


def background_id(question_id: int) -> int:
    return 1 + (question_id - 1) // NUM_QUESTIONS_PER_BACKGROUND


def _check_single_real(placements: list[Placement]):
    real, *fakes = placements
    if real.image.parent != REAL_DIR or any(p.image.parent != FAKE_DIR for p in fakes):
        raise ValueError("a question must contain exactly one real Kaira-kun, placed first")
    for p in placements:
        if p.front_mask is not None and p.front_mask.parent == HARD_OCCLUDER_DIR:
            raise ValueError(f"{p.front_mask.name} is in mask/object/hard (automatic mask completion does not work well for it) and is not used for questions")


def _small_fragments(body: np.ndarray, hidden: np.ndarray) -> np.ndarray:
    """物陰から見えている部分のうち、本体から離れた小さなかけら"""
    labels, count = ndi.label(body & ~hidden)
    if count < 2:
        return np.zeros_like(body)
    sizes = ndi.sum(np.ones_like(labels), labels, range(1, count + 1))
    small = np.flatnonzero(sizes < sizes.max() * MIN_FRAGMENT_RATIO) + 1
    return ndi.binary_dilation(np.isin(labels, small), iterations=2)


def _on_canvas(region: np.ndarray, shape, p: Placement) -> np.ndarray:
    """キャラの大きさの範囲を、画像全体の大きさに置き直す"""
    full = np.zeros(shape, bool)
    h, w = full[p.y : p.y + region.shape[0], p.x : p.x + region.shape[1]].shape
    full[p.y : p.y + h, p.x : p.x + w] = region[:h, :w]
    return full


def _paste(canvas: np.ndarray, background: np.ndarray, p: Placement, image, alpha) -> np.ndarray:
    """キャラを貼り、画像全体の大きさで「見えている部分」の不透明度を返す"""
    h, w = canvas[p.y : p.y + image.shape[0], p.x : p.x + image.shape[1]].shape
    image, alpha = image[:h, :w], alpha[:h, :w]
    hidden = hidden_region(background, p)[p.y : p.y + h, p.x : p.x + w] if p.front_mask else None
    if hidden is not None and hidden.any():
        hidden = hidden | _small_fragments(alpha > 0.5, hidden)
        visible = 1 - ndi.gaussian_filter(hidden.astype(np.float32), 0.7)
        image = 255 - (255 - image) * visible
        alpha = alpha * visible

    area = canvas[p.y : p.y + h, p.x : p.x + w]
    area[:] = area * (1 - alpha) + 255 * alpha  # キャラの後ろの背景を白で消す
    area[:] = np.minimum(area, image)

    visible_alpha = np.zeros(canvas.shape, np.float32)
    visible_alpha[p.y : p.y + h, p.x : p.x + w] = alpha
    return visible_alpha


def _check_heads_visible(placements: list[Placement], masks: list[np.ndarray], heads, eyes):
    """頭と目が十分見えているか（物陰とほかのキャラに隠された分を除いて数える）"""
    for i, (p, mask, head, eye) in enumerate(zip(placements, masks, heads, eyes)):
        for name, region, minimum in (("head", head, MIN_VISIBLE_HEAD), ("eyes", eye, MIN_VISIBLE_EYES)):
            ratio = (region & (mask > 0.5)).sum() / max(1, region.sum())
            if ratio < minimum:
                kind = "real" if i == 0 else "fake"
                raise ValueError(
                    f"character {i} ({kind} {p.image.name} at ({p.x}, {p.y})): only {ratio:.0%} of the {name} is visible"
                )


def compose_question(question_id: int) -> tuple[np.ndarray, list[np.ndarray]]:
    return compose(background_id(question_id), QUESTIONS[question_id])


def compose(bg_id: int, placements: list[Placement]) -> tuple[np.ndarray, list[np.ndarray]]:
    """合成した画像（グレースケール）と、キャラごとの見えている部分の不透明度"""
    _check_single_real(placements)
    style = BACKGROUND_STYLES[bg_id]

    background = load_gray(BACKGROUND_DIR / f"{bg_id}.png")
    canvas = background.copy()
    masks, heads, eyes = [], [], []
    for p in placements:
        stroke = background_stroke(bg_id) * (DISTANT_STROKE_SCALE if p.width < DISTANT_WIDTH else 1)
        image, alpha, head, eye = render_character(p, stroke, style.blur, background_tone(bg_id))
        masks.append(_paste(canvas, background, p, image, alpha))
        heads.append(_on_canvas(head, canvas.shape, p))
        eyes.append(_on_canvas(eye, canvas.shape, p))
    # 後から貼ったキャラに隠された部分は、前のキャラのマスクから除く
    for i in range(len(masks)):
        for later in masks[i + 1 :]:
            masks[i] *= 1 - later
    _check_heads_visible(placements, masks, heads, eyes)
    return np.clip(canvas, 0, 255), masks


def to_rgb_image(gray: np.ndarray) -> Image.Image:
    out = np.clip(gray, 0, 255).astype(np.uint8)
    return Image.fromarray(np.stack([out] * 3, axis=2))


def build_question(question_id: int) -> Image.Image:
    return to_rgb_image(compose_question(question_id)[0])

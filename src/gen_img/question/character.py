import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

from gen_img.kaira_kun.transparent import on_white
from gen_img.question.config import HALO_RADIUS, LINE_HALO_RADIUS, STROKE_GROW_RANGE, STROKE_MIN_LENGTH_RATIO, STROKE_SEARCH_STEPS, STROKE_SUPERSAMPLE
from gen_img.question.placement import Placement
from gen_img.question.tone import core_width, match_tone, measure_tone


def disk(r: int) -> np.ndarray:
    y, x = np.ogrid[-r : r + 1, -r : r + 1]
    return x * x + y * y <= r * r


def line_width(gray: np.ndarray) -> float:
    """平均の線の太さ（インク量 ÷ 細線化した線の長さ）"""
    return ((255 - gray) / 255).sum() / max(1, skeletonize(gray < 128).sum())


def load_gray(path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("L")).astype(np.float32)


def load_character(path) -> tuple[np.ndarray, np.ndarray]:
    """白い背景に重ねた線画と、体の中（白く塗る所。透明な所＝外側としっぽの網目の間は含まない）"""
    image = Image.open(path)
    gray = on_white(image)
    alpha = np.asarray(image.convert("RGBA"))[..., 3]
    return gray, (alpha == 255) & (gray >= 128)


def head_and_eyes(body: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """頭（体の中で一番大きい白いかたまり。目も含む）と、目（頭の中の穴の部分）"""
    labels, count = ndi.label(body)
    if count == 0:
        return body, np.zeros_like(body)
    sizes = ndi.sum(body, labels, range(1, count + 1))
    white = labels == np.argmax(sizes) + 1
    head = ndi.binary_fill_holes(white)
    return head, head & ~white


def _trimmed(gray: np.ndarray, body: np.ndarray, pad: int = 4) -> tuple[np.ndarray, np.ndarray]:
    ys, xs = np.where(gray < 128)
    box = (slice(ys.min(), ys.max() + 1), slice(xs.min(), xs.max() + 1))
    return np.pad(gray[box], pad, constant_values=255), np.pad(body[box], pad)


def _line_distance(gray: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    """拡大した線画で求めた、線の縁からの距離（px、線の外は正・中は負）"""
    ss = STROKE_SUPERSAMPLE
    big = np.asarray(Image.fromarray(gray.astype(np.uint8)).resize((size[0] * ss, size[1] * ss), Image.LANCZOS))
    inside = big < 128
    return (ndi.distance_transform_edt(~inside) - ndi.distance_transform_edt(inside)) / ss


def _draw_lines(distance: np.ndarray, size, grow: float, blur: float, tone) -> np.ndarray:
    """線の縁を grow px だけ外へ広げて（負なら内へ縮めて）描き、元の大きさに縮めてぼかしと濃さ合わせをする"""
    ss = STROKE_SUPERSAMPLE
    ink = (distance < grow).astype(np.float32).reshape(size[1], ss, size[0], ss).mean(axis=(1, 3))
    image = 255 * (1 - ink)
    if blur:
        image = ndi.gaussian_filter(image, blur)
    return match_tone(image, measure_tone(image), tone)


def _fit_stroke(gray: np.ndarray, size, stroke_width: float, blur: float, tone) -> np.ndarray:
    """できあがりの線の太さ（ぼかし・濃さ合わせの後、線の芯の位置での太さの中央値）が stroke_width になるよう、
    線の縁を広げる量を探して描く"""
    distance = _line_distance(gray, size)
    # 縮めすぎて線が途切れ始めたら（線の長さが減ったら）、細すぎとみなしてそれ以上縮めない。
    # 太らせるときは近くの線がくっついて長さが減るだけなので、縮めるときだけ見る
    base_length = skeletonize(_draw_lines(distance, size, 0.0, blur, tone) < 128).sum()
    low, high = STROKE_GROW_RANGE
    for _ in range(STROKE_SEARCH_STEPS):
        grow = (low + high) / 2
        image = _draw_lines(distance, size, grow, blur, tone)
        broken = grow < 0 and skeletonize(image < 128).sum() < STROKE_MIN_LENGTH_RATIO * base_length
        if broken or core_width(image) < stroke_width:
            low = grow
        else:
            high = grow
    return _draw_lines(distance, size, (low + high) / 2, blur, tone)


def render_character(
    p: Placement, stroke_width: float, blur: float, tone: tuple[float, float] = (0.0, 255.0)
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """配置どおりに拡縮・回転した（線画, 後ろの背景を白で消す範囲 0〜1, 頭の範囲, 目の範囲）を返す。
    tone は背景の（線の芯の黒さ, 白さ）で、キャラの濃さをそれに合わせる"""
    gray, body = _trimmed(*load_character(p.image))
    size = (p.width, max(1, round(gray.shape[0] * p.width / gray.shape[1])))
    # 線の太さと濃さを背景に合わせて描く（ぼかすと線の芯が灰色になるので、濃さも合わせ直す）
    lines = _fit_stroke(gray, size, stroke_width, blur, tone)

    image = Image.fromarray(lines.clip(0, 255).astype(np.uint8))
    mask = Image.fromarray((body * 255).astype(np.uint8)).resize(size, Image.LANCZOS)
    head, eyes = (
        Image.fromarray((region * 255).astype(np.uint8)).resize(size, Image.LANCZOS) for region in head_and_eyes(body)
    )
    if p.flip:
        image, mask, head, eyes = (im.transpose(Image.FLIP_LEFT_RIGHT) for im in (image, mask, head, eyes))
    if p.angle:
        image = image.rotate(p.angle, Image.BICUBIC, expand=True, fillcolor=255)
        mask, head, eyes = (im.rotate(p.angle, Image.BICUBIC, expand=True, fillcolor=0) for im in (mask, head, eyes))

    image = np.asarray(image).astype(np.float32)
    # 体の中は周りに白い縁を付けて背景を消す。線だけの所（しっぽ・触角など）は縁を細くし、網目の間は背景を見せる
    lines = (image < 128).astype(np.uint8) * 255
    mask = np.maximum(
        ndi.grey_dilation(np.asarray(mask), footprint=disk(HALO_RADIUS)),
        ndi.grey_dilation(lines, footprint=disk(LINE_HALO_RADIUS)),
    )
    return image, mask.astype(np.float32) / 255, np.asarray(head) > 127, np.asarray(eyes) > 127

"""Compose "Where's Kaira-kun" question images: background + exactly one real Kaira + fakes.

usage (from repo root):
  uv run --no-project --with pillow --with numpy --with scipy --with scikit-image \
      python scripts/make_question.py 1 2 ...      # no args = all questions

Question n uses img/background/<(n-1) % 5 + 1>.png.
Each item: (source, width, angle, flip, x, y, clip)
  clip = None | ("behind", (sx, sy), ...)  hidden behind the background objects containing those
                                            seed points (the objects' real outlines stay in front)
The first item of every question must be the REAL one (img/kaira_kun/real).
Rules: never use a crop of a real image as a fake; every fake's difference must stay
visible after scaling/clipping (small ones: use eye-count / crown / sprout / ponytail).
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

IMG = Path(__file__).resolve().parent.parent / "img"
R = IMG / "kaira_kun/real"
F = IMG / "kaira_kun/fake"

# per background: (stroke width measured on the background, blur to match its softness)
BACKGROUNDS = {
    1: (2.75, 0.6),
    2: (1.85, 0.3),
}

QUESTIONS = {
    1: [
        (R / "1.png", 140, -6, False, 290, 290, None),  # REAL
        (F / "1.jpg", 150, 10, True, 560, 610, None),  # 3 eyes
        (F / "4.png", 130, -12, False, 40, 350, None),  # ribbon
        (F / "8.png", 125, 8, True, 700, 330, None),  # lashes
        (F / "5.png", 135, 0, False, 180, 830, None),  # ponytail
        (F / "2.jpg", 140, -8, False, 820, 820, None),  # 1 eye
    ],
    2: [
        (R / "2.png", 150, -4, False, 566, 628, None),  # REAL, on right bridge
        (F / "1.jpg", 100, 0, True, 84, 430, ("behind", (120, 450))),  # 3 eyes, behind pillar
        (F / "2.jpg", 130, 6, True, 170, 772, None),  # 1 eye, on left bridge
        (F / "2.jpg", 120, 0, True, 300, 552, ("behind", (320, 560))),  # 1 eye, behind tower side panel
        (F / "4.png", 84, 0, False, 200, 204, None),  # ribbon, far
        (F / "5.png", 84, 0, True, 628, 222, None),  # ponytail, far
    ],
    6: [
        (R / "2.png", 140, 8, True, 600, 410, None),  # REAL
        (F / "10.png", 135, -10, False, 120, 560, None),  # horns
        (F / "11.png", 135, 6, True, 420, 690, None),  # antenna
        (F / "12.png", 130, 0, False, 770, 560, None),  # crown
        (F / "13.png", 130, -6, True, 40, 850, None),  # sprout
        (F / "1.jpg", 145, 4, False, 480, 870, None),  # 3 eyes
        (F / "6.png", 135, 10, False, 640, 230, None),  # ahoge
    ],
    7: [
        (R / "1.png", 130, 4, True, 175, 768, None),  # REAL, on left bridge
        (F / "11.png", 145, -4, False, 566, 626, None),  # antenna, on right bridge
        (F / "13.png", 100, 0, True, 0, 500, ("behind", (30, 560))),  # sprout, behind lower-left pipe
        (F / "10.png", 120, 0, False, 176, 545, ("behind", (233, 533))),  # horns, behind tower box
        (F / "12.png", 84, 0, False, 200, 204, None),  # crown, far
        (F / "1.jpg", 84, 0, True, 628, 222, None),  # 3 eyes, far
    ],
}


def line_width(g):
    """Average stroke width: ink amount / skeleton length."""
    return ((255 - g) / 255).sum() / max(1, skeletonize(g < 128).sum())


def disk(r):
    y, x = np.ogrid[-r : r + 1, -r : r + 1]
    return x * x + y * y <= r * r


def load(path):
    g = np.asarray(Image.open(path).convert("L")).astype(np.float32)
    ys, xs = np.where(g < 128)
    return np.pad(g[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1], 4, constant_values=255)


def make(g, width, target, angle=0, flip=False, blur=0.0):
    s = width / g.shape[1]
    # adjust stroke width in source px so that after scaling it equals `target`
    r = (line_width(g) - target / s) / 2
    if r > 0.5:
        g = ndi.grey_dilation(g, footprint=disk(round(r)))  # thin dark lines
    elif r < -0.5:
        g = ndi.grey_erosion(g, footprint=disk(round(-r)))  # thicken dark lines
    lines = g < 128
    closed = ndi.binary_closing(np.pad(lines, 12), structure=disk(6))[12:-12, 12:-12]
    mask = ndi.binary_fill_holes(closed | lines)
    im = Image.fromarray(g.astype(np.uint8))
    mk = Image.fromarray((mask * 255).astype(np.uint8))
    if flip:
        im, mk = im.transpose(Image.FLIP_LEFT_RIGHT), mk.transpose(Image.FLIP_LEFT_RIGHT)
    size = (width, max(1, round(g.shape[0] * s)))
    im, mk = im.resize(size, Image.LANCZOS), mk.resize(size, Image.LANCZOS)
    if angle:
        im = im.rotate(angle, Image.BICUBIC, expand=True, fillcolor=255)
        mk = mk.rotate(angle, Image.BICUBIC, expand=True, fillcolor=0)
    im = np.asarray(im).astype(np.float32)
    # thin white halo so protruding details (crown, antenna, hair) don't merge with the background
    mk = ndi.grey_dilation(np.asarray(mk), footprint=disk(3))
    if blur:
        im = ndi.gaussian_filter(im, blur)
    return im, mk.astype(np.float32) / 255


def occluder(orig, seeds):
    """Union of the background objects (closed regions) containing the seed points, incl. their outlines."""
    lab, _ = ndi.label(orig >= 160)
    occ = np.zeros(orig.shape, bool)
    for sx, sy in seeds:
        occ |= ndi.binary_fill_holes(lab == lab[sy, sx])
    return ndi.binary_dilation(occ, structure=disk(3))


def place(bg, dec, x, y, target, clip=None, orig=None):
    im, mk = dec
    h, w = im.shape
    region = bg[y : y + h, x : x + w]
    im, mk = im[: region.shape[0], : region.shape[1]], mk[: region.shape[0], : region.shape[1]]
    edge = None
    if clip and clip[0] == "behind":  # hidden behind real background objects; their own lines stay in front
        occ = occluder(orig, clip[1:])[y : y + im.shape[0], x : x + im.shape[1]]
        keep = 1 - ndi.gaussian_filter(occ.astype(np.float32), 0.7)
        im = 255 - (255 - im) * keep
        mk = mk * keep
        clip = None
    if clip:  # (old) behind a straight line: hide part of the decoy and draw an edge there
        yy, xx = np.mgrid[y : y + im.shape[0], x : x + im.shape[1]].astype(np.float32)
        if clip[0] == "above":
            x1, y1, x2, y2 = clip[1:]
            d = (y1 + (xx - x1) * (y2 - y1) / (x2 - x1)) - yy  # >0 above the line
        else:
            d = xx - clip[1]
        keep = np.clip(d + 0.5, 0, 1)
        near = ndi.binary_dilation(mk > 0.5, iterations=4)
        edge = np.clip(target / 2 + 0.5 - np.abs(d), 0, 1) * near
        im = 255 - (255 - im) * keep
        mk = mk * keep
    region[:] = region * (1 - mk) + 255 * mk  # white out behind the decoy
    region[:] = np.minimum(region, im)
    if edge is not None:
        region[:] = region * (1 - edge)


def build(n):
    items = QUESTIONS[n]
    assert items[0][0].parent == R and all(it[0].parent == F for it in items[1:]), "exactly one real"
    bg_id = (n - 1) % 5 + 1
    target, blur = BACKGROUNDS[bg_id]
    gray = np.asarray(Image.open(IMG / f"background/{bg_id}.png").convert("L")).astype(np.float32)
    orig = gray.copy()
    for src, w, a, fl, x, y, clip in items:
        t = target * (0.7 if w < 100 else 1)  # distant (small) ones get thinner lines
        place(gray, make(load(src), w, t, a, fl, blur), x, y, t, clip, orig)
    out = np.clip(gray, 0, 255).astype(np.uint8)
    (IMG / "question").mkdir(exist_ok=True)
    Image.fromarray(np.stack([out] * 3, axis=2)).save(IMG / f"question/{n}.png")
    print(f"question {n}: background {bg_id}, real {items[0][0].name} at {items[0][4:6]}")


if __name__ == "__main__":
    for n in map(int, sys.argv[1:]) if len(sys.argv) > 1 else QUESTIONS:
        build(n)

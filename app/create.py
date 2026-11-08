import base64
import io
import json
import os
import time
from functools import lru_cache

import numpy as np
from PIL import Image

from config import (
    FAKE_FEATURES, GEMINI_TRIES, GENERATED_BLUR, KAIRA_BASE, KAIRA_PROMPT, USER_BACKGROUND_DIR, USER_KAIRA_DIR, USER_QUESTION_DIR,
)
from gen_img.kaira_kun.transparent import on_white, to_transparent
from gen_img.paths import BACKGROUND_DIR, FAKE_DIR, REAL_DIR
from gen_img.question.character import render_character
from gen_img.question.config import BACKGROUND_STYLES, DISTANT_STROKE_SCALE, DISTANT_WIDTH
from gen_img.question.placement import Placement
from gen_img.question.tone import core_width, measure_tone


def gemini_client():
    from google import genai

    if not os.environ.get("GEMINI_API_KEY"):
        raise RuntimeError("GEMINI_API_KEY が設定されていない（.env に書いて --env-file .env で起動する）")
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def to_data_url(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def refused(finish_reason) -> bool:
    """Gemini の安全チェックで断られたか（頼み直しても同じなので、すぐあきらめる）"""
    return any(word in str(finish_reason) for word in ("SAFETY", "PROHIBITED", "BLOCKLIST", "RECITATION"))


def no_image_message(finish_reason) -> str:
    if refused(finish_reason):
        return "Gemini の安全チェックで断られました。別の言い方で書いてみてください"
    return "Gemini から絵が返ってきませんでした。もう一度試すか、別の言い方で書いてみてください"


# ---- 背景 ----
def backgrounds() -> list[dict]:
    """選べる背景：既存の背景（b<番号>）と、Gemini で生成した背景（g<時刻>）"""
    rows = [{"id": f"b{p.stem}", "label": f"背景{p.stem}"} for p in sorted(BACKGROUND_DIR.glob("*.png"), key=lambda p: int(p.stem))]
    for meta in sorted(USER_BACKGROUND_DIR.glob("*.json")):
        rows.append({"id": meta.stem, "label": f"生成: {json.loads(meta.read_text())['theme'][:30]}"})
    return rows


def background_path(bg_id: str):
    return BACKGROUND_DIR / f"{bg_id[1:]}.png" if bg_id.startswith("b") else USER_BACKGROUND_DIR / f"{bg_id}.png"


def generate_background(theme: str) -> dict:
    """テーマから Gemini で背景を生成して保存する（1枚 約20秒）"""
    from gen_img.background.generate import NoImageError, generate_from_theme

    client = gemini_client()
    try:
        image = generate_from_theme(client, theme)
    except NoImageError as e:
        raise RuntimeError(no_image_message(e.finish_reason)) from e
    bg_id = f"g{int(time.time())}"
    USER_BACKGROUND_DIR.mkdir(parents=True, exist_ok=True)
    image.save(USER_BACKGROUND_DIR / f"{bg_id}.png")
    (USER_BACKGROUND_DIR / f"{bg_id}.json").write_text(json.dumps({"theme": theme}, ensure_ascii=False))
    return {"id": bg_id, "label": f"生成: {theme[:30]}"}


@lru_cache(maxsize=32)
def background_style(bg_id: str) -> tuple[np.ndarray, float, tuple[float, float], float]:
    """（背景の濃淡, 線の太さ, 線の黒さと紙の白さ, キャラの線のぼかし量）"""
    gray = np.asarray(Image.open(background_path(bg_id)).convert("L")).astype(np.float32)
    style = BACKGROUND_STYLES.get(int(bg_id[1:])) if bg_id.startswith("b") else None
    return gray, core_width(gray), measure_tone(gray), style.blur if style else GENERATED_BLUR


# ---- キャラ ----
# 絵の名前：用意した絵は "1.png" など、プロンプトで作った絵は "k<連番>.png"（app/data/kaira/<real|fake>/ に置く）
def character_path(kind: str, name: str):
    if name.startswith("k"):
        return USER_KAIRA_DIR / kind / name
    return (REAL_DIR if kind == "real" else FAKE_DIR) / name


def _user_meta(kind: str, name: str) -> dict:
    path = USER_KAIRA_DIR / kind / name.replace(".png", ".json")
    return json.loads(path.read_text()) if path.exists() else {}


def feature(name: str) -> str | None:
    """偽物の見分けるポイント（プロンプトで作った偽物は、作るときに付けた名前）"""
    return FAKE_FEATURES.get(name) or _user_meta("fake", name).get("label")


def characters() -> dict:
    """パレットに出す本物と偽物"""
    def rows(kind, builtin_dir):
        builtin = sorted(builtin_dir.glob("*.png"), key=lambda p: int(p.stem))
        made = sorted((USER_KAIRA_DIR / kind).glob("k*.png"), key=lambda p: int(p.stem[1:]))
        return [
            {"name": p.name, "label": (feature(p.name) if kind == "fake" else _user_meta(kind, p.name).get("label")) or f"本物{p.stem}", "made": p in made}
            for p in builtin + made
        ]
    return {"real": rows("real", REAL_DIR), "fake": rows("fake", FAKE_DIR)}


def generate_kaira(kind: str, prompt: str, label: str) -> dict:
    """本物の絵をもとに、プロンプトのとおりに描き変えた Kaira君を Gemini で作り、白黒＋透明の絵にして保存する"""
    from google.genai import types

    from gen_img.background.config import MODEL

    base = Image.open(KAIRA_BASE)
    white = Image.fromarray(on_white(base).astype(np.uint8)).convert("RGB")
    client = gemini_client()  # 変数に持っておかないと、リクエストを送る前にクライアントが閉じられる
    # Gemini はときどき画像のない応答を返すので、何回か頼み直す
    for _ in range(GEMINI_TRIES):
        response = client.models.generate_content(
            model=MODEL,
            contents=[white, KAIRA_PROMPT.format(prompt=prompt)],
            config=types.GenerateContentConfig(response_modalities=["IMAGE"], image_config=types.ImageConfig(aspect_ratio="1:1")),
        )
        candidate = response.candidates[0] if response.candidates else None
        parts = (candidate.content.parts if candidate and candidate.content else None) or []
        image = next((Image.open(io.BytesIO(p.inline_data.data)) for p in parts if p.inline_data), None)
        if image is not None:
            return save_kaira(kind, image.convert("L").resize(base.size, Image.LANCZOS), prompt, label)
        if candidate and refused(candidate.finish_reason):
            break
    raise RuntimeError(no_image_message(candidate.finish_reason if candidate else None))


def save_kaira(kind: str, image: Image.Image, prompt: str, label: str) -> dict:
    folder = USER_KAIRA_DIR / kind
    folder.mkdir(parents=True, exist_ok=True)
    numbers = [int(p.stem[1:]) for p in folder.glob("k*.png")]
    name = f"k{max(numbers, default=0) + 1}.png"
    to_transparent(image).save(folder / name)
    label = label or prompt[:12]
    (folder / name.replace(".png", ".json")).write_text(json.dumps({"prompt": prompt, "label": label}, ensure_ascii=False))
    return {"kind": kind, "name": name, "label": label}


@lru_cache(maxsize=256)
def _render(bg_id: str, p: Placement):
    """キャラを背景の線の太さ・濃さに合わせて描く（画面に出す絵と、登録するときに貼る絵で使い回す）"""
    _, stroke, tone, blur = background_style(bg_id)
    return render_character(p, stroke * (DISTANT_STROKE_SCALE if p.width < DISTANT_WIDTH else 1), blur, tone)


def sprite(bg_id: str, kind: str, name: str, width: int, flip: bool) -> dict:
    """画面で置くためのキャラの絵（背景に合わせて描いたもの。透明度つき）"""
    image, alpha, *_ = _render(bg_id, Placement(character_path(kind, name), width, 0, flip, 0, 0))
    rgba = np.stack([image, image, image, alpha * 255], axis=2).clip(0, 255).astype(np.uint8)
    h, w = image.shape
    return {"url": to_data_url(Image.fromarray(rgba, "RGBA")), "w": w, "h": h}


# ---- 問題 ----
def compose(bg_id: str, placements: list[dict]) -> tuple[Image.Image, dict]:
    """背景に、画面で置いたとおりにキャラを貼る（物の陰には隠さない）。問題画像と、本物・偽物の枠を返す。
    placements は {kind, name, width, flip, x, y} の並びで、本物がちょうど1体いること"""
    reals = [p for p in placements if p["kind"] == "real"]
    if len(reals) != 1:
        raise ValueError("本物はちょうど1体置く")
    if len(placements) < 2:
        raise ValueError("偽物を1体以上置く")
    canvas = background_style(bg_id)[0].copy()
    rows = []
    # 先頭が本物（正解の枠の並びを、用意した問題の answers.json とそろえる）
    for p in reals + [p for p in placements if p["kind"] != "real"]:
        image, alpha, *_ = _render(bg_id, Placement(character_path(p["kind"], p["name"]), int(p["width"]), 0, bool(p["flip"]), 0, 0))
        x, y = int(p["x"]), int(p["y"])
        h, w = canvas[y : y + image.shape[0], x : x + image.shape[1]].shape
        image, alpha = image[:h, :w], alpha[:h, :w]
        area = canvas[y : y + h, x : x + w]
        area[:] = np.minimum(area * (1 - alpha) + 255 * alpha, image)
        ys, xs = np.nonzero(alpha > 0.5)
        rows.append({
            "kind": p["kind"], "image": p["name"], "hidden": False,
            "box": [int(x + xs.min()), int(y + ys.min()), int(x + xs.max()) + 1, int(y + ys.max()) + 1],
        })
    height, width = canvas.shape
    image = Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8)).convert("RGB")
    return image, {"width": width, "height": height, "characters": rows}


def save_question(image: Image.Image, answer: dict, meta: dict) -> str:
    """作った問題を保存して、問題の番号（u<連番>）を返す"""
    USER_QUESTION_DIR.mkdir(parents=True, exist_ok=True)
    numbers = [int(p.stem[1:]) for p in USER_QUESTION_DIR.glob("u*.json")]
    question_id = f"u{max(numbers, default=0) + 1}"
    image.save(USER_QUESTION_DIR / f"{question_id}.png")
    (USER_QUESTION_DIR / f"{question_id}.json").write_text(json.dumps({**answer, **meta}, ensure_ascii=False, indent=1))
    return question_id


def saved_questions() -> dict[str, dict]:
    return {p.stem: json.loads(p.read_text()) for p in sorted(USER_QUESTION_DIR.glob("u*.json"), key=lambda p: int(p.stem[1:]))}

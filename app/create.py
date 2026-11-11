import base64
import io
import json
import os
import time
from functools import lru_cache

import numpy as np
from PIL import Image

from config import (
    BACKGROUND_BASE_PROMPT, FAKE_FEATURES, GEMINI_TRIES, GENERATED_BLUR, KAIRA_BASE, KAIRA_PROMPT,
    NO_KAIRA_PROMPT, SCENE_PROMPT, TEXT_MODEL, USER_BACKGROUND_DIR, USER_FAKE_DIR, USER_QUESTION_DIR,
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
        raise RuntimeError("GEMINI_API_KEY が設定されていない（リポジトリ直下の .env に GEMINI_API_KEY=... と書いて、起動し直す）")
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


def gemini_image(contents: list) -> Image.Image:
    """Gemini の画像のモデルに描かせる。画像のない応答なら何回か頼み直し、安全チェックで断られたらすぐあきらめる"""
    from google.genai import types

    from gen_img.background.config import MODEL

    client = gemini_client()  # 変数に持っておかないと、リクエストを送る前にクライアントが閉じられる
    candidate = None
    for _ in range(GEMINI_TRIES):
        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=types.GenerateContentConfig(response_modalities=["IMAGE"], image_config=types.ImageConfig(aspect_ratio="1:1")),
        )
        candidate = response.candidates[0] if response.candidates else None
        parts = (candidate.content.parts if candidate and candidate.content else None) or []
        image = next((Image.open(io.BytesIO(p.inline_data.data)) for p in parts if p.inline_data), None)
        if image is not None:
            return image
        if candidate and refused(candidate.finish_reason):
            break
    raise RuntimeError(no_image_message(candidate.finish_reason if candidate else None))


# ---- 背景 ----
def backgrounds() -> list[dict]:
    """選べる背景：既存の背景（b<番号>）と、Gemini で生成した背景（g<時刻>）"""
    rows = [{"id": f"b{p.stem}", "label": f"背景{p.stem}"} for p in sorted(BACKGROUND_DIR.glob("*.png"), key=lambda p: int(p.stem))]
    for meta in sorted(USER_BACKGROUND_DIR.glob("*.json")):
        rows.append({"id": meta.stem, "label": background_label(json.loads(meta.read_text(encoding="utf-8")))})
    return rows


def background_path(bg_id: str):
    return BACKGROUND_DIR / f"{bg_id[1:]}.png" if bg_id.startswith("b") else USER_BACKGROUND_DIR / f"{bg_id}.png"


def describe_scene(theme: str) -> str:
    """背景作りの1段階目：短いテーマから、文章のモデルに場面の詳しい説明（日本語）を書かせる"""
    client = gemini_client()
    response = client.models.generate_content(model=TEXT_MODEL, contents=SCENE_PROMPT.format(theme=theme))
    if not response.text:
        raise RuntimeError("Gemini から説明が返ってきませんでした。もう一度試してください")
    return response.text.strip()


def generate_background(theme: str, scene: str) -> dict:
    """背景作りの2段階目：場面の説明と、共通の画風・構図の指示で背景を描かせて保存する（1枚 約20秒）"""
    from gen_img.background.config import REFERENCE_NOTE, STYLE_REFERENCES

    prompt = f"{REFERENCE_NOTE} SCENE: {scene} {BACKGROUND_BASE_PROMPT}{NO_KAIRA_PROMPT}"
    references = [Image.open(p) for p in STYLE_REFERENCES if p.exists()]
    image = gemini_image([*references, prompt]).convert("L").convert("RGB")
    bg_id = f"g{int(time.time())}"
    USER_BACKGROUND_DIR.mkdir(parents=True, exist_ok=True)
    image.save(USER_BACKGROUND_DIR / f"{bg_id}.png")
    meta = {"theme": theme, "scene": scene}
    (USER_BACKGROUND_DIR / f"{bg_id}.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return {"id": bg_id, "label": background_label(meta)}


def background_label(meta: dict) -> str:
    return f"生成: {meta['theme'][:30]}"


@lru_cache(maxsize=32)
def background_style(bg_id: str) -> tuple[np.ndarray, float, tuple[float, float], float]:
    """（背景の濃淡, 線の太さ, 線の黒さと紙の白さ, キャラの線のぼかし量）"""
    gray = np.asarray(Image.open(background_path(bg_id)).convert("L")).astype(np.float32)
    style = BACKGROUND_STYLES.get(int(bg_id[1:])) if bg_id.startswith("b") else None
    return gray, core_width(gray), measure_tone(gray), style.blur if style else GENERATED_BLUR


# ---- キャラ ----
# 絵の名前：用意した絵は "1.png" など、プロンプトで作った偽物は "k<連番>.png"（USER_FAKE_DIR に置く）。
# 本物は用意した絵だけを使う（作れるのは偽物だけ）
def character_path(kind: str, name: str):
    if kind == "real":
        return REAL_DIR / name
    return (USER_FAKE_DIR if name.startswith("k") else FAKE_DIR) / name


def _made_meta(name: str) -> dict:
    path = USER_FAKE_DIR / name.replace(".png", ".json")
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def feature(name: str) -> str | None:
    """偽物の見分けるポイント（プロンプトで作った偽物は、作るときに付けた名前）"""
    return FAKE_FEATURES.get(name) or _made_meta(name).get("label")


def characters() -> dict:
    """パレットに出す本物（用意した絵）と偽物（用意した絵＋プロンプトで作った絵）"""
    by_number = lambda p: int(p.stem.lstrip("k"))
    made = sorted(USER_FAKE_DIR.glob("k*.png"), key=by_number)
    return {
        "real": [{"name": p.name, "label": f"本物{p.stem}", "made": False} for p in sorted(REAL_DIR.glob("*.png"), key=by_number)],
        "fake": [
            {"name": p.name, "label": feature(p.name) or "", "made": p in made}
            for p in sorted(FAKE_DIR.glob("*.png"), key=by_number) + made
        ],
    }


def generate_fake(prompt: str) -> Image.Image:
    """本物の絵をもとに、プロンプトのとおりに描き変えた偽物を Gemini で作る（まだ保存しない。見分けるポイントを付けたら save_fake で保存）"""
    base = Image.open(KAIRA_BASE)
    white = Image.fromarray(on_white(base).astype(np.uint8)).convert("RGB")
    image = gemini_image([white, KAIRA_PROMPT.format(prompt=prompt)])
    return to_transparent(image.convert("L").resize(base.size, Image.LANCZOS))


def save_fake(image: Image.Image, prompt: str, label: str) -> dict:
    """作った偽物を、見分けるポイント（名前）を付けて保存する。名前がなければ保存しない"""
    if not label.strip():
        raise ValueError("見分けるポイントを書いてください（書かないと保存されません）")
    folder = USER_FAKE_DIR
    folder.mkdir(parents=True, exist_ok=True)
    numbers = [int(p.stem[1:]) for p in folder.glob("k*.png")]
    name = f"k{max(numbers, default=0) + 1}.png"
    image.save(folder / name)
    (folder / name.replace(".png", ".json")).write_text(json.dumps({"prompt": prompt, "label": label.strip()}, ensure_ascii=False), encoding="utf-8")
    return {"kind": "fake", "name": name, "label": label.strip()}


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
        path = character_path(p["kind"], p["name"])
        if not path.exists():
            raise ValueError(f"{p['name']} という絵はない（本物は用意した絵だけ使える）")
        image, alpha, *_ = _render(bg_id, Placement(path, int(p["width"]), 0, bool(p["flip"]), 0, 0))
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
    (USER_QUESTION_DIR / f"{question_id}.json").write_text(json.dumps({**answer, **meta}, ensure_ascii=False, indent=1), encoding="utf-8")
    return question_id


def saved_questions() -> dict[str, dict]:
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(USER_QUESTION_DIR.glob("u*.json"), key=lambda p: int(p.stem[1:]))}

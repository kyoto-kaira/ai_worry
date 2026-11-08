import io

from google import genai
from google.genai import types
from PIL import Image

from gen_img.background.config import MODEL, REFERENCE_NOTE, STYLE, STYLE_REFERENCES, THEMES


class NoImageError(RuntimeError):
    """Gemini が画像を返さなかった（finish_reason に理由。安全チェックで断られたときなど）"""

    def __init__(self, theme: str, finish_reason):
        super().__init__(f"no image returned for theme: {theme} ({finish_reason})")
        self.finish_reason = finish_reason


def generate_background(client: genai.Client, bg_id: int) -> Image.Image:
    return generate_from_theme(client, THEMES[bg_id])


def generate_from_theme(client: genai.Client, theme: str) -> Image.Image:
    """テーマ（何を描くか）から背景を生成する。画風の指示と参考画像は全背景で共通"""
    prompt = f"{REFERENCE_NOTE} {theme} {STYLE}"
    references = [Image.open(p) for p in STYLE_REFERENCES if p.exists()]
    response = client.models.generate_content(
        model=MODEL,
        contents=[*references, prompt],
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio="1:1"),
        ),
    )
    candidate = response.candidates[0] if response.candidates else None
    for part in (candidate.content.parts if candidate and candidate.content else None) or []:
        if part.inline_data:
            return Image.open(io.BytesIO(part.inline_data.data)).convert("L").convert("RGB")
    raise NoImageError(theme, candidate.finish_reason if candidate else None)

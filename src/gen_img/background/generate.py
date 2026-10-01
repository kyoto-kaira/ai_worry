import io

from google import genai
from google.genai import types
from PIL import Image

from gen_img.background.config import MODEL, REFERENCE_NOTE, STYLE, STYLE_REFERENCES, THEMES


def generate_background(client: genai.Client, bg_id: int) -> Image.Image:
    prompt = f"{REFERENCE_NOTE} {THEMES[bg_id]} {STYLE}"
    references = [Image.open(p) for p in STYLE_REFERENCES if p.exists()]
    response = client.models.generate_content(
        model=MODEL,
        contents=[*references, prompt],
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio="1:1"),
        ),
    )
    for part in response.candidates[0].content.parts:
        if part.inline_data:
            return Image.open(io.BytesIO(part.inline_data.data)).convert("L").convert("RGB")
    raise RuntimeError(f"no image returned for background {bg_id}")

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
IMG_DIR = ROOT_DIR / "img"
BACKGROUND_DIR = IMG_DIR / "background"
QUESTION_DIR = IMG_DIR / "question"
REAL_DIR = IMG_DIR / "kaira_kun" / "real"
FAKE_DIR = IMG_DIR / "kaira_kun" / "fake"
# AI でなじませた問題画像（question/ に画像、mask/ に手前マスク）
HARMONIZED_QUESTION_DIR = IMG_DIR / "harmonized_question"
# 手前マスク：茂み・サンゴなど物ごとのもの（gen_img.mask で作る）と、問題ごとにまとめたもの（<番号>.png）。白 = キャラより手前
OCCLUDER_DIR = HARMONIZED_QUESTION_DIR / "mask"

# 実験の結果（実験ごとにフォルダを分ける）
EXP_DIR = ROOT_DIR / "exp"
PAINTERLY_EXP_DIR = EXP_DIR / "01_painterly_harmonization"
HIDE_EXP_DIR = EXP_DIR / "02_hide_and_strength"
FIX_EXP_DIR = EXP_DIR / "03_fix_details"
PROMPT_HIDE_DIR = EXP_DIR / "04_prompt_hide"
EXP_OCCLUDER_DIR = EXP_DIR / "occluder"

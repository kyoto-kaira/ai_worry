from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
IMG_DIR = ROOT_DIR / "img"
BACKGROUND_DIR = IMG_DIR / "background"
QUESTION_DIR = IMG_DIR / "question"
REAL_DIR = IMG_DIR / "kaira_kun" / "real"
FAKE_DIR = IMG_DIR / "kaira_kun" / "fake"
# AI でなじませた問題画像（question/ に画像、mask/ に手前マスク）
HARMONIZED_QUESTION_DIR = IMG_DIR / "harmonized_question"
# 手前マスク（白 = キャラより手前）
# rough/：人が隠れ場所の物体を大まかに黒く塗ったもの（背景と同じ大きさ。gen_img.mask の入力）
# object/：rough を SAM で物体の形に合わせた、物ごとのマスク（gen_img.mask で作る）
#   normal/：問題画像に使う物、hard/：マスクの自動作成（SAM による塗り足し）がうまく補えない物（記録として残し、問題画像には使わない）
# question/：問題ごとに、キャラを隠すのに使った物をまとめたもの（<番号>.png）
ROUGH_MASK_DIR = HARMONIZED_QUESTION_DIR / "mask" / "rough"
OBJECT_MASK_DIR = HARMONIZED_QUESTION_DIR / "mask" / "object"
OCCLUDER_DIR = OBJECT_MASK_DIR / "normal"
HARD_OCCLUDER_DIR = OBJECT_MASK_DIR / "hard"
QUESTION_MASK_DIR = HARMONIZED_QUESTION_DIR / "mask" / "question"
# 物陰に隠れたキャラの切り出し（隠れ方の確認用。git には入れない）
HIDDEN_CROP_DIR = HARMONIZED_QUESTION_DIR / "crop"

# 実験の結果（実験ごとにフォルダを分ける）
EXP_DIR = ROOT_DIR / "exp"
PAINTERLY_EXP_DIR = EXP_DIR / "01_painterly_harmonization"
HIDE_EXP_DIR = EXP_DIR / "02_hide_and_strength"
FIX_EXP_DIR = EXP_DIR / "03_fix_details"
PROMPT_HIDE_DIR = EXP_DIR / "04_prompt_hide"
EXP_OCCLUDER_DIR = EXP_DIR / "occluder"

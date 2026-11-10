from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
# アプリが使う絵（背景・キャラ）は app/data/ に置く
APP_DATA_DIR = ROOT_DIR / "app" / "data"
BACKGROUND_DIR = APP_DATA_DIR / "background"
KAIRA_DIR = APP_DATA_DIR / "kaira"
REAL_DIR = KAIRA_DIR / "real"
FAKE_DIR = KAIRA_DIR / "fake"

# 実験の結果（実験ごとにフォルダを分ける）
EXP_DIR = ROOT_DIR / "exp"
# 物陰に隠してなじませる、前のやり方の成果物（実験の記録。git には入れない）
EXP_IMG_DIR = EXP_DIR / "img"
QUESTION_DIR = EXP_IMG_DIR / "question"
# AI でなじませた問題画像（question/ に画像、mask/ に手前マスク）
HARMONIZED_QUESTION_DIR = EXP_IMG_DIR / "harmonized_question"
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
# 物陰に隠れたキャラの切り出し（隠れ方の確認用）
HIDDEN_CROP_DIR = HARMONIZED_QUESTION_DIR / "crop"
# 2つの物の隙間からのぞく問題（question/ に画像、mask/ に手前マスク、crop/ に確認用の切り出し）
GAP_QUESTION_DIR = HARMONIZED_QUESTION_DIR / "hidden"

PAINTERLY_EXP_DIR = EXP_DIR / "01_painterly_harmonization"
HIDE_EXP_DIR = EXP_DIR / "02_hide_and_strength"
FIX_EXP_DIR = EXP_DIR / "03_fix_details"
PROMPT_HIDE_DIR = EXP_DIR / "04_prompt_hide"
EXP_OCCLUDER_DIR = EXP_DIR / "occluder"

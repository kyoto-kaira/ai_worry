from pathlib import Path

from gen_img.paths import APP_DATA_DIR, REAL_DIR

APP_DIR = Path(__file__).resolve().parent
# 用意した問題：gen_img.question.config.QUESTIONS の配置で、本物と偽物を背景に貼っただけの画像（物陰に隠さず、なじませもしない）。
# 画像・正解の枠・YOLO の検出結果は build.py で作る（git には入れない）
QUESTION_IMAGE_DIR = APP_DATA_DIR / "builtin"
ANSWERS_PATH = QUESTION_IMAGE_DIR / "answers.json"
DETECTIONS_PATH = QUESTION_IMAGE_DIR / "detections.json"
# ヒントに使う YOLO のモデル（本物の Kaira君だけを見つけるよう学習したもの。クラスは kaira の1つ）。
# Kaira君用に学習したもの（クラス名に real / fake / kaira を含む）でなければ、正解の位置からヒントを作るモックで動く
MODEL_PATH = APP_DATA_DIR / "model" / "best.pt"
KAIRA_CLASS_WORDS = ("real", "fake", "kaira")
# ヒントは確信度の高い順に上位いくつかを使うので、確信度の低い候補まで取っておく
YOLO_CONFIDENCE = 0.001
YOLO_MAX_DETECTIONS = 50
# YOLO の検出と正解の枠がこの重なり（IoU）以上なら、同じキャラとみなす
MATCH_IOU = 0.3

PORT = 8770

# 問題作成：お客様が作った問題・Gemini で生成した背景・プロンプトで作った偽物の保存先（git には入れない）
USER_DATA_DIR = APP_DATA_DIR / "user"
USER_QUESTION_DIR = USER_DATA_DIR / "questions"
# お客様が作った問題の YOLO の検出結果（登録したときに検出して保存する）
USER_DETECTIONS_PATH = USER_QUESTION_DIR / "detections.json"
USER_BACKGROUND_DIR = USER_DATA_DIR / "backgrounds"
# プロンプトで作った偽物（本物は作れない。用意した絵だけを使う）
USER_FAKE_DIR = USER_DATA_DIR / "fakes"
# 生成した背景のキャラの線のぼかし量（既存の背景は gen_img.question.config.BACKGROUND_STYLES の値を使う）
GENERATED_BLUR = 0.4
# 背景は2段階で作る：①テーマ（お客様が日本語で書く）から、文章のモデルで場面の詳しい説明を書かせる（画面で直せる）
# ②その説明と、全背景で共通の画風・構図の指示（BACKGROUND_BASE_PROMPT）で、画像のモデルに描かせる
THEME_EXAMPLE = "京都駅の大階段とコンコース"
TEXT_MODEL = "gemini-2.5-flash"
SCENE_PROMPT = (
    "白黒の線画の探し絵（「ウォーリーをさがせ！」のような絵）の背景にする場面を、次のテーマから具体的に説明してください。"
    "実在の場所なら、その場所だとひと目でわかる建物・設備・名物を必ず入れてください。"
    "どこから見た絵か（上から見下ろす・広い床や地面が見える、など）と、描き込む物（建物・設備・機械・家具・乗り物・小物）を具体的に並べてください。"
    "人や生き物は少しだけにしてください。説明は日本語で150字くらい、説明の文だけを書いてください。\nテーマ：{theme}"
)
BACKGROUND_BASE_PROMPT = (
    "Black and white line art only, like a coloring book page. Clean uniform black outlines of medium "
    "thickness on a pure white background, no shading, no gray fills, no hatching, no color, no text, "
    "no letters, no signature. An extremely detailed 'Where's Wally' style seek-and-find scene edge to edge. "
    "COMPOSITION & PERSPECTIVE: High-angle isometric or slightly top-down perspective with a prominent, "
    "broad ground/floor plane occupying the majority of the image. Alternatively, if side-view, fill the background "
    "depth with dense multi-tiered structures, platforms, scaffolding, shelves, pipes, grids, and architectural lines "
    "so anything positioned higher up naturally rests on or inside a structure. "
    "CREATURE DENSITY: Keep the background creature count LOW (include only a few sparse, small background creatures, "
    "never zero, but do NOT crowd the screen with creatures). Focus heavily on inanimate objects, architecture, "
    "machinery, furniture, and environmental details, leaving clean floor/surface spaces for character placement. "
)
# 背景に Kaira君に似た生き物を描かせない指示（描かれると答えが2つになる）
NO_KAIRA_PROMPT = "Do NOT draw any brain-shaped creature, and no creature with a net or mesh of tentacles."
# キャラを置くときの横幅（px）の範囲と最初の値、キャラ同士・画像の端とのすき間（px）
WIDTH_RANGE = (60, 180)
DEFAULT_WIDTH = 110
PLACE_GAP = 8
# 登録したとき、YOLO の候補（確信度の高い順）の上位この数に本物が入らなければ「AIを出し抜いた」とする
FOOL_TOP = 5

# Gemini が画像のない応答を返したとき、頼み直す回数（最初の1回を含む）
GEMINI_TRIES = 3
# プロンプトで偽物を作るとき：本物の絵を Gemini に渡し、{prompt}（お客様が日本語で書いた指示）のとおりに描き変えさせる
KAIRA_BASE = REAL_DIR / "1.png"
KAIRA_PROMPT = (
    "この白黒の線画のキャラクターを、次のように描き変えてください：{prompt}。"
    "キャラクター・ポーズ・大きさ・位置はそのままにし、右側の網目のようなしっぽも残してください。"
    "白い背景に、太さのそろった黒い線だけで描き、影・灰色・色・文字は入れないでください。"
    "描き足すものも黒く塗りつぶさず、線だけで描いてください（中は白）。"
    "画像の真ん中に、このキャラクター1体だけを描いてください。"
)

# 難易度：ヒントは top 個の丸。YOLO の候補（確信度の高い順）を使い、足りない分はランダムに選んだ偽物で埋める。
# top = 0 ならヒントなし。hint_radius = 丸の半径（キャラの枠の大きさの何倍か）。丸の中心はキャラから少しずらす
LEVELS = {
    "easy": {"label": "かんたん（上位2）", "top": 2, "hint_radius": 1.0},
    "normal": {"label": "ふつう（上位5）", "top": 5, "hint_radius": 1.2},
    "hard": {"label": "むずかしい（上位10）", "top": 10, "hint_radius": 1.5},
    "oni": {"label": "鬼（ヒントなし）", "top": 0, "hint_radius": 0},
}

# 偽物の見分けポイント（間違えたときに教える）
FAKE_FEATURES = {
    "1.png": "目が3つ",
    "2.png": "目が1つ",
    "3.png": "しっぽがない",
    "4.png": "リボン",
    "5.png": "ポニーテール",
    "6.png": "アホ毛",
    "7.png": "舌",
    "8.png": "まつ毛",
    "9.png": "目の大きさが違う",
    "10.png": "ツノ",
    "11.png": "触角",
    "12.png": "王冠",
    "13.png": "双葉",
}

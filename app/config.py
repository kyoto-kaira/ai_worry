from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
APP_DIR = Path(__file__).resolve().parent
# 問題画像（AI でなじませたもの）と、正解の枠（build_answers.py で作る）
QUESTION_IMAGE_DIR = ROOT_DIR / "img" / "harmonized_question" / "question"
ANSWERS_PATH = APP_DIR / "answers.json"
# 使わない問題：問題20は配置を変えた後、画像をまだ作り直していない（正解の枠が画像と合わない）
SKIP_QUESTIONS = {20}
# ヒントに使う YOLO のモデル（本物の Kaira君だけを見つけるよう学習したもの。クラスは kaira の1つ）。
# Kaira君用に学習したもの（クラス名に real / fake / kaira を含む）でなければ、正解の位置からヒントを作るモックで動く
MODEL_PATH = ROOT_DIR / "data" / "best.pt"
KAIRA_CLASS_WORDS = ("real", "fake", "kaira")
YOLO_IMAGE_SIZE = 1024
# ヒントは確信度の高い順に上位いくつかを使うので、確信度の低い候補まで取っておく
YOLO_CONFIDENCE = 0.001
YOLO_MAX_DETECTIONS = 50
# YOLO の検出と正解の枠がこの重なり（IoU）以上なら、同じキャラとみなす
MATCH_IOU = 0.3

PORT = 8770

# 問題作成：お客さんが作った問題・Gemini で生成した背景・プロンプトで作った Kaira君の保存先（git には入れない）
USER_DATA_DIR = APP_DIR / "data"
USER_QUESTION_DIR = USER_DATA_DIR / "questions"
USER_BACKGROUND_DIR = USER_DATA_DIR / "backgrounds"
USER_KAIRA_DIR = USER_DATA_DIR / "kaira"
# 生成した背景のキャラの線のぼかし量（既存の背景は gen_img.question.config.BACKGROUND_STYLES の値を使う）
GENERATED_BLUR = 0.4
# 背景のテーマの例（作成画面の入力欄に出す）。テーマは日本語で書いてよい（Gemini は日本語の指示も読める）
# おもちゃ屋さん・本屋さんのように箱や看板が多い場面は、文字を禁止しても「GAMES」などの文字が描かれやすい
THEME_EXAMPLE = "雪の降るお菓子の国の町。お菓子の家、キャンディの木、ソリ、雪だるま、小さな妖精たちがいる"
# キャラを置くときの横幅（px）の範囲と最初の値、キャラ同士・画像の端とのすき間（px）
WIDTH_RANGE = (60, 180)
DEFAULT_WIDTH = 110
PLACE_GAP = 8
# 登録したとき、YOLO の上位この数に本物が入らなければ「AIを出し抜いた」とする
FOOL_TOP = 5

# Gemini が画像のない応答を返したとき、頼み直す回数（最初の1回を含む）
GEMINI_TRIES = 3
# プロンプトで Kaira君を作るとき：この絵を Gemini に渡し、{prompt}（お客さんが日本語で書いた指示）のとおりに描き変えさせる
KAIRA_BASE = ROOT_DIR / "img" / "kaira_kun" / "real" / "1.png"
KAIRA_PROMPT = (
    "この白黒の線画のキャラクターを、次のように描き変えてください：{prompt}。"
    "キャラクター・ポーズ・大きさ・位置はそのままにし、右側の網目のようなしっぽも残してください。"
    "白い背景に、太さのそろった黒い線だけで描き、影・灰色・色・文字は入れないでください。"
    "描き足すものも黒く塗りつぶさず、線だけで描いてください（中は白）。"
    "画像の真ん中に、このキャラクター1体だけを描いてください。"
)

# 難易度：ヒントは YOLO の推定の上位 top 個（確信度の高い順）を丸で示す。top = 0 ならヒントなし。
# hint_radius = 丸の半径（検出した枠の大きさの何倍か）
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

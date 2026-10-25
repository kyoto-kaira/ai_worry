from gen_img.paths import FAKE_DIR as FAKE
from gen_img.paths import OCCLUDER_DIR
from gen_img.paths import REAL_DIR as REAL
from gen_img.question.placement import BackgroundStyle, Placement as P

# 背景1枚あたりの問題数。問題 1〜5 が背景1、6〜10 が背景2 … になる
NUM_QUESTIONS_PER_BACKGROUND = 5

# キャラの線の太さを背景に合わせるとき：この倍率に拡大して線の縁からの距離を求め、
# 縁を広げる／縮める量（px、この範囲で探す）を変えて、できあがりの太さが背景と同じになる量を探す
STROKE_SUPERSAMPLE = 8
STROKE_GROW_RANGE = (-1.0, 2.5)
STROKE_SEARCH_STEPS = 10
# 縮めたときに線の長さがこの割合より減ったら、線が途切れたとみなす
STROKE_MIN_LENGTH_RATIO = 0.9

# この幅より小さいキャラは遠くにいるとみなし、線を細くする
DISTANT_WIDTH = 100
DISTANT_STROKE_SCALE = 0.7

# 頭から飛び出した部分（王冠・触角など）が背景に埋もれないよう、キャラの周りに付ける白い縁の半径
HALO_RADIUS = 3
# しっぽ・触角など線だけの所の白い縁の半径（しっぽの網目の間は白くせず背景を見せる）
LINE_HALO_RADIUS = 2

# 物陰から見えている部分のうち、本体から離れた小さなかけら（枝のすき間から見えるしっぽの切れ端など）は隠す。
# 見えている一番大きいかたまりに対して、この割合より小さいかたまりを消す
MIN_FRAGMENT_RATIO = 0.25

# 頭はこの割合以上見えていないといけない（見分けるための特徴はほとんど頭にあるため）。
# 物陰やほかのキャラに隠れて下回る配置は、問題を作るときにエラーにする
MIN_VISIBLE_HEAD = 0.5
# 目はこの割合以上見えていないといけない（片目が隠れると1つ目の偽物と見分けがつかなくなる）
MIN_VISIBLE_EYES = 0.9

BACKGROUND_STYLES = {
    1: BackgroundStyle(blur=0.6),
    2: BackgroundStyle(blur=0.3),
    3: BackgroundStyle(blur=0.4),
    4: BackgroundStyle(blur=0.4),
    5: BackgroundStyle(blur=0.3),
}

# 茂み・サンゴなど輪郭の閉じていない物の手前マスク（SAM で切り抜いたもの）
LEFT_BUSH = OCCLUDER_DIR / "bg4_left_bush.png"
MID_BUSH = OCCLUDER_DIR / "bg4_mid_bush.png"
LEFT_CORAL = OCCLUDER_DIR / "bg3_left_coral.png"
CORAL_CLUMP = OCCLUDER_DIR / "bg3_coral_clump.png"


def occluder(name: str):
    return OCCLUDER_DIR / f"{name}.png"
# ロボット（背景5）：輪郭にすき間があるので、大まかな多角形を線に吸着させて作ったマスク
ROBOT = OCCLUDER_DIR / "bg5_robot.png"

# 各問題の先頭が本物、残りはすべて偽物。問題 n は背景 background_id(n) を使う
QUESTIONS = {
    # 背景 1
    1: [
        P(REAL / "1.png", 140, -6, False, 290, 290),
        P(FAKE / "1.png", 150, 10, True, 560, 610),  # 3つ目
        P(FAKE / "4.png", 130, -12, False, 40, 350),  # リボン
        P(FAKE / "8.png", 125, 8, True, 700, 330),  # まつ毛
        P(FAKE / "5.png", 135, 0, False, 180, 830),  # ポニーテール
        P(FAKE / "2.png", 140, -8, False, 820, 820),  # 1つ目
    ],
    2: [
        P(REAL / "2.png", 140, 8, True, 600, 410),
        P(FAKE / "10.png", 135, -10, False, 120, 560),  # ツノ
        P(FAKE / "11.png", 135, 6, True, 420, 690),  # 触角
        P(FAKE / "12.png", 130, 0, False, 770, 560),  # 王冠
        P(FAKE / "13.png", 130, -6, True, 40, 850),  # 双葉
        P(FAKE / "1.png", 145, 4, False, 480, 870),  # 3つ目
        P(FAKE / "5.png", 135, 10, False, 640, 230),  # ポニーテール
    ],
    3: [
        P(REAL / "1.png", 135, 0, False, 120, 560),
        P(FAKE / "13.png", 140, -6, False, 290, 290),  # 双葉
        P(FAKE / "11.png", 135, 6, True, 820, 820),  # 触角
        P(FAKE / "1.png", 140, 4, False, 600, 410),  # 3つ目
        P(FAKE / "12.png", 130, -4, True, 40, 850),  # 王冠
        P(FAKE / "4.png", 125, 8, True, 700, 330),  # リボン
    ],
    4: [
        P(REAL / "2.png", 140, 4, False, 480, 870),
        P(FAKE / "10.png", 140, -6, True, 290, 290),  # ツノ
        P(FAKE / "2.png", 130, 0, False, 770, 560),  # 1つ目
        P(FAKE / "5.png", 135, 6, True, 560, 610),  # ポニーテール
        P(FAKE / "8.png", 130, -8, False, 40, 350),  # まつ毛
        P(FAKE / "13.png", 125, 4, False, 700, 330),  # 双葉
        P(FAKE / "11.png", 135, -4, True, 120, 560),  # 触角
    ],
    # 各背景の5問目：今まで使っていない種類の物に隠す（どんな物だと隠れ方が不自然になるかを調べる）
    5: [
        P(REAL / "1.png", 120, 0, False, 52, 827, front_mask=occluder("bg1_eyeball"), label="eyeball_creature"),
        P(FAKE / "1.png", 110, 0, True, 440, 815, front_mask=occluder("bg1_bald_creature"), label="bald_creature"),  # 3つ目
        P(FAKE / "12.png", 140, 10, True, 560, 610),  # 王冠
        P(FAKE / "4.png", 125, 8, True, 700, 330),  # リボン
        P(FAKE / "13.png", 130, -12, False, 40, 350),  # 双葉
    ],
    # 背景 2
    6: [
        P(REAL / "2.png", 150, -4, False, 566, 628),  # 右の橋の上
        P(FAKE / "1.png", 100, 0, True, 81, 430, front_mask=occluder("bg2_column"), label="column"),  # 3つ目、柱の後ろ
        P(FAKE / "2.png", 130, 6, True, 170, 772),  # 1つ目、左の橋の上
        P(FAKE / "2.png", 120, 0, True, 309, 555, front_mask=occluder("bg2_tower_box"), label="tower_box"),  # 1つ目、塔のパネルの後ろ
        P(FAKE / "4.png", 84, 0, False, 200, 204),  # リボン、遠く
        P(FAKE / "5.png", 84, 0, True, 628, 222),  # ポニーテール、遠く
    ],
    7: [
        P(REAL / "1.png", 130, 4, True, 175, 768),  # 左の橋の上
        P(FAKE / "11.png", 145, -4, False, 566, 626),  # 触角、右の橋の上
        P(FAKE / "13.png", 100, 0, True, 0, 500, front_mask=occluder("bg2_pipe"), label="pipe"),  # 双葉、パイプの後ろ
        P(FAKE / "10.png", 120, 0, False, 176, 545, front_mask=occluder("bg2_tower_box"), label="tower_box"),  # ツノ、塔の箱の後ろ
        P(FAKE / "12.png", 84, 0, False, 200, 204),  # 王冠、遠く
        P(FAKE / "1.png", 84, 0, True, 628, 222),  # 3つ目、遠く
    ],
    8: [
        P(REAL / "2.png", 120, 0, True, 309, 552, front_mask=occluder("bg2_tower_box"), label="tower_box"),  # 塔のパネルの後ろ
        P(FAKE / "10.png", 150, -4, False, 566, 628),  # ツノ、右の橋の上
        P(FAKE / "12.png", 130, 6, True, 170, 772),  # 王冠、左の橋の上
        P(FAKE / "1.png", 84, 0, True, 628, 222),  # 3つ目、遠く
        P(FAKE / "5.png", 84, 0, False, 200, 204),  # ポニーテール、遠く
        P(FAKE / "13.png", 100, 0, True, 81, 430, front_mask=occluder("bg2_column"), label="column"),  # 双葉、柱の後ろ
    ],
    9: [
        P(REAL / "1.png", 100, 0, True, 0, 500, front_mask=occluder("bg2_pipe"), label="pipe"),  # パイプの後ろ
        P(FAKE / "11.png", 130, 4, True, 170, 772),  # 触角、左の橋の上
        P(FAKE / "2.png", 150, -4, False, 566, 628),  # 1つ目、右の橋の上
        P(FAKE / "4.png", 84, 0, False, 628, 222),  # リボン、遠く
        P(FAKE / "1.png", 84, 0, True, 200, 204),  # 3つ目、遠く
        P(FAKE / "12.png", 120, 0, False, 176, 545, front_mask=occluder("bg2_tower_box"), label="tower_box"),  # 王冠、塔の箱の後ろ
    ],
    10: [
        P(REAL / "2.png", 110, 0, True, 545, 545, front_mask=occluder("bg2_stairs"), label="stairs"),
        P(FAKE / "2.png", 120, 0, False, 250, 441, front_mask=occluder("bg2_grille_machine"), label="grille_machine"),  # 1つ目
        P(FAKE / "5.png", 110, 0, True, 490, 190, front_mask=occluder("bg2_eye_column"), label="eye_column"),  # ポニーテール
        P(FAKE / "10.png", 130, 6, True, 170, 772),  # ツノ
        P(FAKE / "13.png", 84, 0, False, 628, 222),  # 双葉、遠く
    ],
    # 背景 3
    11: [
        P(REAL / "1.png", 130, 0, True, 640, 650, front_mask=occluder("bg3_control_box"), label="control_box"),  # 制御ボックスの後ろ
        P(FAKE / "12.png", 140, 4, False, 860, 200),  # 王冠
        P(FAKE / "2.png", 140, -6, True, 238, 715, front_mask=occluder("bg3_machine"), label="machine"),  # 1つ目、機械の後ろ
        P(FAKE / "10.png", 135, 6, False, 660, 120),  # ツノ
        P(FAKE / "5.png", 140, 0, False, 40, 10),  # ポニーテール
        P(FAKE / "13.png", 130, -4, True, 380, 880),  # 双葉
        P(FAKE / "1.png", 140, 8, False, 20, 470),  # 3つ目
    ],
    12: [
        P(REAL / "2.png", 135, 0, False, 536, 806, front_mask=occluder("bg3_bottom_box"), label="bottom_box"),  # 下の箱の後ろ
        P(FAKE / "11.png", 135, -4, False, 880, 160),  # 触角
        P(FAKE / "1.png", 140, 6, True, 0, 240),  # 3つ目
        P(FAKE / "4.png", 130, 0, False, 470, 220),  # リボン
        P(FAKE / "2.png", 130, -6, True, 320, 310),  # 1つ目
        P(FAKE / "8.png", 140, 4, False, 760, 740),  # まつ毛
        P(FAKE / "12.png", 135, -4, True, 170, 820),  # 王冠
    ],
    13: [
        P(REAL / "1.png", 120, 0, False, 495, 875, front_mask=CORAL_CLUMP),  # サンゴの塊の向こう
        P(FAKE / "10.png", 110, 0, True, 25, 190, front_mask=LEFT_CORAL),  # ツノ、左の枝サンゴの中
        P(FAKE / "12.png", 130, 0, True, 640, 650, front_mask=occluder("bg3_control_box"), label="control_box"),  # 王冠、制御ボックスの後ろ
        P(FAKE / "1.png", 140, 8, False, 20, 470),  # 3つ目
        P(FAKE / "5.png", 140, 4, False, 860, 200),  # ポニーテール
        P(FAKE / "8.png", 130, -4, True, 790, 770),  # まつ毛
    ],
    14: [
        P(REAL / "2.png", 110, 0, True, 25, 190, front_mask=LEFT_CORAL),  # 左の枝サンゴの中
        P(FAKE / "11.png", 120, 0, False, 495, 872, front_mask=CORAL_CLUMP),  # 触角、サンゴの塊の向こう
        P(FAKE / "2.png", 140, -6, True, 238, 715, front_mask=occluder("bg3_machine"), label="machine"),  # 1つ目、機械の後ろ
        P(FAKE / "13.png", 130, -4, True, 860, 200),  # 双葉
        P(FAKE / "4.png", 130, 0, False, 470, 220),  # リボン
        P(FAKE / "12.png", 140, 6, False, 20, 470),  # 王冠
    ],
    15: [
        P(REAL / "1.png", 120, 0, True, 125, 840, front_mask=occluder("bg3_diver"), label="diver"),
        P(FAKE / "12.png", 120, 0, False, 120, 380, front_mask=occluder("bg3_glass_tank"), label="glass_tank"),  # 王冠
        P(FAKE / "11.png", 110, 0, False, 790, 120, front_mask=occluder("bg3_fish"), label="fish"),  # 触角
        P(FAKE / "13.png", 130, -4, True, 380, 880),  # 双葉
        P(FAKE / "4.png", 130, 0, False, 470, 220),  # リボン
    ],
    # 背景 4
    16: [
        P(REAL / "1.png", 150, 0, False, 770, 569, front_mask=occluder("bg4_big_cap"), label="big_cap"),  # 大きいキノコの傘の後ろ
        P(FAKE / "12.png", 120, 0, False, 401, 339, front_mask=occluder("bg4_small_cap"), label="small_cap"),  # 王冠、小さいキノコの傘の後ろ
        P(FAKE / "11.png", 130, 0, False, 885, 246, front_mask=occluder("bg4_right_cap"), label="right_cap"),  # 触角、右のキノコの傘の後ろ
        P(FAKE / "10.png", 130, -4, False, 40, 585),  # ツノ
        P(FAKE / "2.png", 140, 4, True, 560, 790),  # 1つ目
        P(FAKE / "5.png", 140, -6, False, 440, 880),  # ポニーテール
        P(FAKE / "13.png", 120, 6, True, 10, 300),  # 双葉
    ],
    17: [
        P(REAL / "2.png", 130, 0, False, 612, 363, front_mask=occluder("bg4_mid_cap"), label="mid_cap"),  # 小さいキノコの傘の後ろ
        P(FAKE / "11.png", 140, 0, True, 870, 560, front_mask=occluder("bg4_big_cap"), label="big_cap"),  # 触角、大きいキノコの傘の後ろ
        P(FAKE / "4.png", 135, 4, False, 560, 780),  # リボン
        P(FAKE / "1.png", 130, -6, True, 150, 860),  # 3つ目
        P(FAKE / "8.png", 135, 6, False, 20, 300),  # まつ毛
        P(FAKE / "12.png", 140, -4, True, 440, 880),  # 王冠
        P(FAKE / "10.png", 130, 0, False, 450, 170),  # ツノ
    ],
    18: [
        P(REAL / "1.png", 120, 0, False, 125, 519, front_mask=LEFT_BUSH),  # 左の茂みの中
        P(FAKE / "12.png", 115, 0, True, 395, 533, front_mask=MID_BUSH),  # 王冠、中央の茂みの中
        P(FAKE / "11.png", 130, 0, False, 773, 557, front_mask=occluder("bg4_big_cap"), label="big_cap"),  # 触角、キノコの傘の後ろ
        P(FAKE / "2.png", 130, 4, True, 560, 790),  # 1つ目
        P(FAKE / "5.png", 140, -6, False, 440, 880),  # ポニーテール
        P(FAKE / "10.png", 130, 0, False, 450, 170),  # ツノ
    ],
    19: [
        P(REAL / "2.png", 115, 0, False, 395, 533, front_mask=MID_BUSH),  # 中央の茂みの中
        P(FAKE / "1.png", 120, 0, True, 130, 521, front_mask=LEFT_BUSH),  # 3つ目、左の茂みの中
        P(FAKE / "13.png", 120, 0, False, 600, 351, front_mask=occluder("bg4_mid_cap"), label="mid_cap"),  # 双葉、小さいキノコの傘の後ろ
        P(FAKE / "4.png", 130, -4, False, 40, 585),  # リボン
        P(FAKE / "8.png", 135, 6, False, 20, 300),  # まつ毛
        P(FAKE / "12.png", 130, 0, False, 888, 246, front_mask=occluder("bg4_right_cap"), label="right_cap"),  # 王冠、右のキノコの傘の後ろ
    ],
    20: [
        P(REAL / "2.png", 120, 0, False, 50, 593, front_mask=occluder("bg4_shed"), label="shed"),
        P(FAKE / "12.png", 80, 0, False, 164, 707, front_mask=occluder("bg4_barrel"), label="barrel"),  # 王冠
        P(FAKE / "1.png", 110, 0, False, 605, 369, front_mask=occluder("bg4_mid_cap"), label="mid_cap"),  # 3つ目
        P(FAKE / "10.png", 130, 0, False, 450, 170),  # ツノ
        P(FAKE / "4.png", 135, 4, False, 560, 790),  # リボン
    ],
    # 背景 5
    21: [
        P(REAL / "2.png", 120, 0, True, 488, 709, front_mask=occluder("bg5_door_block"), label="door_block"),  # ドアの区画の後ろ
        P(FAKE / "12.png", 115, 0, False, 737, 461, front_mask=occluder("bg5_cabinet"), label="cabinet"),  # 王冠、コンソールの後ろ
        P(FAKE / "10.png", 115, 4, True, 30, 640),  # ツノ
        P(FAKE / "1.png", 115, -4, False, 560, 610),  # 3つ目
        P(FAKE / "11.png", 115, 0, False, 840, 330),  # 触角
        P(FAKE / "5.png", 120, 6, True, 330, 880),  # ポニーテール
        P(FAKE / "13.png", 110, -4, False, 230, 150),  # 双葉
    ],
    22: [
        P(REAL / "1.png", 120, 0, False, 160, 437, front_mask=occluder("bg5_console"), label="console"),  # コンソールの後ろ
        P(FAKE / "11.png", 115, 0, True, 469, 628, front_mask=occluder("bg5_robot"), label="robot"),  # 触角、ロボットの後ろ
        P(FAKE / "4.png", 115, 4, False, 860, 860),  # リボン
        P(FAKE / "2.png", 115, -6, True, 600, 860),  # 1つ目
        P(FAKE / "12.png", 115, 0, False, 480, 140),  # 王冠
        P(FAKE / "8.png", 120, 6, True, 30, 330),  # まつ毛
        P(FAKE / "10.png", 115, -4, False, 740, 640),  # ツノ
    ],
    23: [
        P(REAL / "1.png", 120, 0, False, 455, 745, front_mask=occluder("bg5_door_block"), label="door_block"),  # ドアの区画の後ろ
        P(FAKE / "12.png", 115, 0, False, 737, 461, front_mask=occluder("bg5_cabinet"), label="cabinet"),  # 王冠、コンソールの後ろ
        P(FAKE / "11.png", 115, 0, True, 469, 628, front_mask=occluder("bg5_robot"), label="robot"),  # 触角、ロボットの後ろ
        P(FAKE / "10.png", 115, 4, True, 30, 640),  # ツノ
        P(FAKE / "1.png", 115, -4, False, 860, 860),  # 3つ目
        P(FAKE / "13.png", 110, -4, False, 230, 150),  # 双葉
    ],
    24: [
        P(REAL / "2.png", 115, 0, False, 840, 330),
        P(FAKE / "2.png", 115, -4, False, 600, 860),  # 1つ目
        P(FAKE / "5.png", 120, 6, True, 330, 880),  # ポニーテール
        P(FAKE / "12.png", 115, 0, False, 442, 637, front_mask=ROBOT),  # 王冠、左のロボットの後ろ
        P(FAKE / "4.png", 115, 0, False, 480, 140),  # リボン
        P(FAKE / "8.png", 120, 6, True, 30, 330),  # まつ毛
    ],
    25: [
        P(REAL / "1.png", 110, 0, False, 478, 515, front_mask=occluder("bg5_window"), label="window"),
        P(FAKE / "11.png", 90, 0, False, 838, 619, front_mask=occluder("bg5_chair"), label="chair"),  # 触角
        P(FAKE / "4.png", 90, 0, True, 735, 610, front_mask=occluder("bg5_alien"), label="alien"),  # リボン
        P(FAKE / "2.png", 115, -6, True, 600, 860),  # 1つ目
        P(FAKE / "13.png", 110, -4, False, 230, 150),  # 双葉
    ],
}

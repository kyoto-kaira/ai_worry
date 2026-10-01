from gen_img.paths import FAKE_DIR as FAKE
from gen_img.paths import REAL_DIR as REAL
from gen_img.question.placement import BackgroundStyle, Placement as P

BACKGROUND_COUNT = 5

# この幅より小さいキャラは遠くにいるとみなし、線を細くする
DISTANT_WIDTH = 100
DISTANT_STROKE_SCALE = 0.7

# 頭から飛び出した部分（王冠・触角など）が背景に埋もれないよう、キャラの周りに付ける白い縁の半径
HALO_RADIUS = 3

# 遮蔽物の領域が画像全体のこの割合を超えたら、輪郭の隙間から漏れたとみなす
OCCLUDER_MAX_AREA = 0.06

BACKGROUND_STYLES = {
    1: BackgroundStyle(stroke_width=2.75, blur=0.6),
    2: BackgroundStyle(stroke_width=1.85, blur=0.3),
    3: BackgroundStyle(stroke_width=2.3, blur=0.4),
    4: BackgroundStyle(stroke_width=2.15, blur=0.4),
    5: BackgroundStyle(stroke_width=1.8, blur=0.3),
}

# 各問題の先頭が本物、残りはすべて偽物
QUESTIONS = {
    1: [
        P(REAL / "1.png", 140, -6, False, 290, 290),
        P(FAKE / "1.jpg", 150, 10, True, 560, 610),  # 3つ目
        P(FAKE / "4.png", 130, -12, False, 40, 350),  # リボン
        P(FAKE / "8.png", 125, 8, True, 700, 330),  # まつ毛
        P(FAKE / "5.png", 135, 0, False, 180, 830),  # ポニーテール
        P(FAKE / "2.jpg", 140, -8, False, 820, 820),  # 1つ目
    ],
    2: [
        P(REAL / "2.png", 150, -4, False, 566, 628),  # 右の橋の上
        P(FAKE / "1.jpg", 100, 0, True, 84, 430, behind=((120, 450),)),  # 3つ目、柱の後ろ
        P(FAKE / "2.jpg", 130, 6, True, 170, 772),  # 1つ目、左の橋の上
        P(FAKE / "2.jpg", 120, 0, True, 300, 552, behind=((320, 560),)),  # 1つ目、塔のパネルの後ろ
        P(FAKE / "4.png", 84, 0, False, 200, 204),  # リボン、遠く
        P(FAKE / "5.png", 84, 0, True, 628, 222),  # ポニーテール、遠く
    ],
    3: [
        P(REAL / "1.png", 130, 0, True, 640, 650, behind=((655, 690),)),  # 制御ボックスの後ろ
        P(FAKE / "12.png", 140, 4, False, 860, 200),  # 王冠
        P(FAKE / "2.jpg", 140, -6, True, 250, 715, behind=((285, 790),)),  # 1つ目、機械の後ろ
        P(FAKE / "10.png", 135, 6, False, 660, 120),  # ツノ
        P(FAKE / "5.png", 140, 0, False, 40, 10),  # ポニーテール
        P(FAKE / "13.png", 130, -4, True, 380, 880),  # 双葉
        P(FAKE / "1.jpg", 140, 8, False, 20, 470),  # 3つ目
    ],
    4: [
        P(REAL / "1.png", 150, 0, False, 770, 545, behind=((850, 650),)),  # 大きいキノコの傘の後ろ
        P(FAKE / "12.png", 120, 0, False, 395, 330, behind=((470, 425),)),  # 王冠、小さいキノコの傘の後ろ
        P(FAKE / "11.png", 130, 0, False, 885, 225, behind=((960, 370),)),  # 触角、右のキノコの傘の後ろ
        P(FAKE / "10.png", 130, -4, False, 40, 585),  # ツノ
        P(FAKE / "2.jpg", 140, 4, True, 560, 790),  # 1つ目
        P(FAKE / "5.png", 140, -6, False, 440, 880),  # ポニーテール
        P(FAKE / "13.png", 120, 6, True, 10, 300),  # 双葉
    ],
    5: [
        P(REAL / "2.png", 120, 0, True, 455, 745, behind=((530, 860),)),  # ドアの区画の後ろ
        P(FAKE / "12.png", 115, 0, False, 740, 470, behind=((790, 540),)),  # 王冠、コンソールの後ろ
        P(FAKE / "10.png", 115, 4, True, 30, 640),  # ツノ
        P(FAKE / "1.jpg", 115, -4, False, 560, 610),  # 3つ目
        P(FAKE / "11.png", 115, 0, False, 840, 330),  # 触角
        P(FAKE / "5.png", 120, 6, True, 330, 880),  # ポニーテール
        P(FAKE / "13.png", 110, -4, False, 230, 150),  # 双葉
    ],
    6: [
        P(REAL / "2.png", 140, 8, True, 600, 410),
        P(FAKE / "10.png", 135, -10, False, 120, 560),  # ツノ
        P(FAKE / "11.png", 135, 6, True, 420, 690),  # 触角
        P(FAKE / "12.png", 130, 0, False, 770, 560),  # 王冠
        P(FAKE / "13.png", 130, -6, True, 40, 850),  # 双葉
        P(FAKE / "1.jpg", 145, 4, False, 480, 870),  # 3つ目
        P(FAKE / "6.png", 135, 10, False, 640, 230),  # アホ毛
    ],
    7: [
        P(REAL / "1.png", 130, 4, True, 175, 768),  # 左の橋の上
        P(FAKE / "11.png", 145, -4, False, 566, 626),  # 触角、右の橋の上
        P(FAKE / "13.png", 100, 0, True, 0, 500, behind=((30, 560),)),  # 双葉、パイプの後ろ
        P(FAKE / "10.png", 120, 0, False, 176, 545, behind=((233, 533),)),  # ツノ、塔の箱の後ろ
        P(FAKE / "12.png", 84, 0, False, 200, 204),  # 王冠、遠く
        P(FAKE / "1.jpg", 84, 0, True, 628, 222),  # 3つ目、遠く
    ],
    8: [
        P(REAL / "2.png", 135, 0, False, 560, 800, behind=((620, 930),)),  # 下の箱の後ろ
        P(FAKE / "11.png", 135, -4, False, 880, 160),  # 触角
        P(FAKE / "1.jpg", 140, 6, True, 0, 240),  # 3つ目
        P(FAKE / "4.png", 130, 0, False, 470, 220),  # リボン
        P(FAKE / "2.jpg", 130, -6, True, 320, 310),  # 1つ目
        P(FAKE / "8.png", 140, 4, False, 760, 740),  # まつ毛
        P(FAKE / "12.png", 135, -4, True, 170, 820),  # 王冠
    ],
    9: [
        P(REAL / "2.png", 130, 0, False, 600, 330, behind=((670, 420),)),  # 小さいキノコの傘の後ろ
        P(FAKE / "11.png", 140, 0, True, 870, 560, behind=((850, 650),)),  # 触角、大きいキノコの傘の後ろ
        P(FAKE / "4.png", 135, 4, False, 560, 780),  # リボン
        P(FAKE / "1.jpg", 130, -6, True, 150, 860),  # 3つ目
        P(FAKE / "8.png", 135, 6, False, 20, 300),  # まつ毛
        P(FAKE / "12.png", 140, -4, True, 440, 880),  # 王冠
        P(FAKE / "10.png", 130, 0, False, 450, 170),  # ツノ
    ],
    10: [
        P(REAL / "1.png", 120, 0, False, 160, 455, behind=((240, 520), (275, 495))),  # コンソールの後ろ
        P(FAKE / "11.png", 115, 0, True, 600, 400, behind=((650, 470),)),  # 触角、パネルの後ろ
        P(FAKE / "4.png", 115, 4, False, 860, 860),  # リボン
        P(FAKE / "2.jpg", 115, -6, True, 600, 860),  # 1つ目
        P(FAKE / "12.png", 115, 0, False, 480, 140),  # 王冠
        P(FAKE / "8.png", 120, 6, True, 30, 330),  # まつ毛
        P(FAKE / "10.png", 115, -4, False, 740, 640),  # ツノ
    ],
}

from gen_img.paths import FAKE_DIR as FAKE
from gen_img.paths import OCCLUDER_DIR
from gen_img.paths import REAL_DIR as REAL
from gen_img.question.placement import Placement as P

# 手前にある物（茂み・サンゴなど）の大まかな輪郭。背景番号と多角形の頂点
OCCLUDERS = {
    "bg4_left_bush": (4, [(88, 660), (90, 600), (115, 585), (150, 576), (185, 580), (215, 590), (245, 600), (275, 612), (298, 660)]),
    "bg4_mid_bush": (4, [(430, 650), (440, 592), (470, 570), (510, 563), (545, 573), (565, 600), (565, 650)]),
    "bg3_coral_clump": (3, [(462, 1024), (470, 975), (490, 955), (520, 944), (560, 940), (600, 945), (625, 965), (642, 1000), (642, 1024)]),
    "bg3_left_coral": (3, [(0, 430), (0, 335), (30, 322), (70, 332), (110, 326), (140, 340), (152, 430)]),
}


def front(name: str):
    return OCCLUDER_DIR / f"{name}.png"


# SAM で切り抜いた手前マスク（茂み = 内側の点で指示、サンゴ = 文字で探した枠で指示）
LEFT_BUSH = front("sam_bg4_left_bush")
MID_BUSH = front("sam_bg4_mid_bush")
LEFT_CORAL = front("sam_bg3_left_coral")
CORAL_CLUMP = front("sam_bg3_coral_clump")


# 奥に隠れられるかの実験用の配置。先頭が本物
SCENES = {
    1: (4, [
        P(REAL / "1.png", 120, 0, False, 125, 519, front_mask=LEFT_BUSH),  # 左の茂みの中
        P(FAKE / "12.png", 115, 0, True, 395, 533, front_mask=MID_BUSH),  # 王冠、中央の茂みの中
        P(FAKE / "11.png", 130, 0, False, 770, 545, behind=((850, 650),)),  # 触角、キノコの傘の後ろ
        P(FAKE / "2.jpg", 130, 4, True, 560, 790),  # 1つ目、隠れていない
    ]),
    2: (4, [
        P(REAL / "2.png", 115, 0, False, 395, 533, front_mask=MID_BUSH),  # 中央の茂みの中
        P(FAKE / "1.jpg", 120, 0, True, 130, 521, front_mask=LEFT_BUSH),  # 3つ目、左の茂みの中
        P(FAKE / "13.png", 120, 0, False, 600, 330, behind=((670, 420),)),  # 双葉、小さいキノコの傘の後ろ
        P(FAKE / "4.png", 130, -4, False, 40, 585),  # リボン、隠れていない
    ]),
    3: (3, [
        P(REAL / "1.png", 120, 0, False, 495, 875, front_mask=CORAL_CLUMP),  # サンゴの塊の向こう
        P(FAKE / "10.png", 110, 0, True, 25, 190, front_mask=LEFT_CORAL),  # ツノ、左のサンゴの中
        P(FAKE / "12.png", 130, 0, True, 640, 650, behind=((655, 690),)),  # 王冠、制御ボックスの後ろ
        P(FAKE / "1.jpg", 140, 8, False, 20, 470),  # 3つ目、隠れていない
    ]),
    4: (3, [
        P(REAL / "2.png", 110, 0, True, 25, 190, front_mask=LEFT_CORAL),  # 左のサンゴの中
        P(FAKE / "11.png", 120, 0, False, 495, 872, front_mask=CORAL_CLUMP),  # 触角、サンゴの塊の向こう
        P(FAKE / "2.jpg", 140, -6, True, 250, 715, behind=((285, 790),)),  # 1つ目、機械の後ろ
        P(FAKE / "13.png", 130, -4, True, 860, 200),  # 双葉、隠れていない
    ]),
    5: (5, [
        P(REAL / "1.png", 120, 0, False, 455, 745, behind=((530, 860),)),  # ドアの区画の後ろ
        P(FAKE / "12.png", 115, 0, False, 740, 470, behind=((790, 540),)),  # 王冠、コンソールの後ろ
        P(FAKE / "11.png", 115, 0, True, 600, 400, behind=((650, 470),)),  # 触角、パネルの後ろ
        P(FAKE / "10.png", 115, 4, True, 30, 640),  # ツノ、隠れていない
    ]),
}

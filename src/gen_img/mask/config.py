from dataclasses import dataclass, field
from pathlib import Path

WORK_DIR = Path(__file__).resolve().parents[3] / "work" / "mask"


@dataclass(frozen=True)
class SamTarget:
    """Grounding DINO + SAM で切り抜く物"""

    name: str
    bg_id: int
    # この範囲を切り出して探す（点を使う場合は SAM に渡す枠そのもの）
    search_box: tuple[int, int, int, int]
    # 文字で探す場合の検索語（Grounding DINO）。空なら search_box をそのまま枠にする
    object_text: str = ""
    # 物の内側の点（正例）と、物ではない所の点（負例）
    points: list[tuple[int, int]] = field(default_factory=list)
    neg_points: list[tuple[int, int]] = field(default_factory=list)
    # SAM が返す3つの候補のうち、どれを使うか
    candidate: int = 0


@dataclass(frozen=True)
class LassoTarget:
    """輪郭にすき間があり点で拾えない物：大まかな多角形を背景の線に吸着させる"""

    name: str
    bg_id: int
    polygon: list[tuple[int, int]]
    snap: int = 6


SAM_TARGETS = [
    SamTarget("sam_bg3_left_coral", 3, (0, 230, 210, 450), object_text="coral"),
    SamTarget("sam_bg3_coral_clump", 3, (440, 900, 680, 1024), object_text="coral"),
    SamTarget(
        "sam_bg4_left_bush", 4, (88, 576, 298, 660),
        points=[(132, 584), (168, 598), (258, 612), (222, 626), (240, 640), (240, 654)],
        candidate=2,
    ),
    SamTarget(
        "sam_bg4_mid_bush", 4, (380, 570, 500, 692),
        points=[(400, 600), (392, 630), (415, 650), (470, 588), (478, 650), (425, 672), (410, 585)],
        # 樽・キノコ・桟橋を拾わないように
        neg_points=[(447, 615), (447, 630), (512, 610), (522, 640), (552, 620), (440, 700)],
    ),
]

LASSO_TARGETS = [
    LassoTarget(
        "poly_bg5_robot", 5,
        [(497, 640), (505, 633), (527, 633), (537, 642), (538, 668), (548, 672), (548, 728), (556, 732),
         (556, 748), (474, 748), (474, 732), (478, 700), (477, 680), (484, 670), (495, 668), (494, 650)],
        snap=4,
    ),
]

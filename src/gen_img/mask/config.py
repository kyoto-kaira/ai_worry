from dataclasses import dataclass, field
from pathlib import Path

WORK_DIR = Path(__file__).resolve().parents[3] / "work" / "mask"

# 人が塗った範囲（rough）は、必ず物体の内側だけを塗ったもの（はみ出さない）として扱う。
# SAM への指示：外枠は塗った範囲を fill px 広げたもの。点は縁から（この px）より内側に、背景の線を避けてこの数だけ散らす
ROUGH_POINT_COUNT = 8
ROUGH_POINT_INSET = 6
# SAM の3つの候補（物体の一部 / 物体 / 物体＋くっついている物 など）から1つ選ぶ。点数 =
#   塗った範囲を含む割合 − ROUGH_LEAK_WEIGHT × 候補のうち塗った範囲から fill px より外にはみ出した割合
# 一部しかない候補は前者が、隣の物まで拾った候補は後者が下げる。一番点数の高い候補を使う
ROUGH_LEAK_WEIGHT = 2.0
# 一番点数の高い候補でもこれ未満なら、SAM は物体を切り抜けなかったとみなし、塗った範囲をそのまま使う
ROUGH_MIN_SCORE = 0.5
# 使う候補が塗った範囲をこの割合しか含まないときは、はみ出した塗りを外したと警告する
ROUGH_MIN_COVERAGE = 0.9


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
class RoughTarget:
    """人が物体の内側を大まかに塗った範囲（mask/rough/<名前>.png）を、SAM で物体の端まで塗り足す"""

    name: str
    bg_id: int
    # 塗った範囲からこの px 以内なら、SAM が物体とみなした所を塗り足す（物体の縁からこの距離以内まで塗っておく）
    fill: int = 20
    # マスクの自動作成（SAM による塗り足し）がうまく補えない物。マスクは object/hard/ に作り、問題画像には使わない
    hard: bool = False


@dataclass(frozen=True)
class LassoTarget:
    """輪郭にすき間があり点で拾えない物：大まかな多角形を背景の線に吸着させる"""

    name: str
    bg_id: int
    polygon: list[tuple[int, int]]
    snap: int = 6
    # 指定すると、この範囲（左, 上, 右, 下）から多角形の内側を除いた所を手前にする（窓の向こうに隠すときなど）
    outside_box: tuple[int, int, int, int] | None = None


# 枠・点・文字で SAM に指示して作る物（今は全部、人が塗った範囲から作っているので空）
SAM_TARGETS: list[SamTarget] = []

# 多角形をそのまま使う物（今は全部、人が塗った範囲から作っているので空）
LASSO_TARGETS: list[LassoTarget] = []

# 人が塗った範囲から作るマスク（mask/rough/ に同じ名前の塗り画像を置く）
ROUGH_TARGETS = [
    RoughTarget("bg2_column", 2),
    RoughTarget("bg2_tower_box", 2),
    RoughTarget("bg2_pipe", 2),
    RoughTarget("bg3_control_box", 3),
    RoughTarget("bg3_machine", 3),
    RoughTarget("bg3_bottom_box", 3),
    RoughTarget("bg4_big_cap", 4),
    RoughTarget("bg4_small_cap", 4),
    RoughTarget("bg4_right_cap", 4),
    RoughTarget("bg4_mid_cap", 4),
    RoughTarget("bg5_door_block", 5),
    RoughTarget("bg5_console", 5),
    RoughTarget("bg5_cabinet", 5),
    RoughTarget("bg5_robot", 5),
    RoughTarget("bg1_bald_creature", 1),
    RoughTarget("bg1_eyeball", 1),
    RoughTarget("bg2_stairs", 2),
    RoughTarget("bg2_grille_machine", 2),
    RoughTarget("bg2_eye_column", 2),
    RoughTarget("bg3_diver", 3),
    RoughTarget("bg3_glass_tank", 3),
    RoughTarget("bg3_fish", 3),
    RoughTarget("bg3_left_coral", 3),
    RoughTarget("bg3_coral_clump", 3),
    RoughTarget("bg4_shed", 4),
    RoughTarget("bg4_barrel", 4),
    RoughTarget("bg4_left_bush", 4),
    RoughTarget("bg4_mid_bush", 4),
    # 暗い洞窟の中：洞窟の下側の暗い所を塗る。手前の物の境目がはっきりせず、SAM の塗り足しが洞窟の奥や地面まで広がる
    RoughTarget("bg4_cave", 4, hard=True),
    # 丸窓の向こう：窓のガラスの外（枠と壁）を塗る。SAM はガラスまで物体に含めるので塗り足さない
    RoughTarget("bg5_window", 5, fill=0),
    RoughTarget("bg5_chair", 5),
    RoughTarget("bg5_alien", 5),
]

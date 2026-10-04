from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Placement:
    image: Path
    width: int
    angle: float
    flip: bool
    x: int
    y: int
    # キャラを隠す背景の物体の内側の座標
    behind: tuple[tuple[int, int], ...] = ()


@dataclass(frozen=True)
class BackgroundStyle:
    stroke_width: float
    blur: float

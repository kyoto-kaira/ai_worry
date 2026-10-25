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
    # キャラより手前にある物のマスク画像（白 = 手前。gen_img.mask で作る）。重なった所ではキャラは描かれない
    front_mask: Path | None = None
    # 隠れている物の名前（確認用の切り出し画像のファイル名に使う）
    label: str = ""


@dataclass(frozen=True)
class BackgroundStyle:
    # キャラの線をぼかす量（背景の線がぼやけているほど大きく）。線の太さと濃さは背景から自動で測って合わせる
    blur: float

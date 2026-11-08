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
    # キャラより手前にある物のマスク画像（白 = 手前。gen_img.mask で作る）。重なった所ではキャラは描かれない。
    # 2つの物の隙間に隠すときは、両側の物のマスクを tuple で渡す
    front_mask: Path | tuple[Path, ...] | None = None
    # 隠れている物の名前（確認用の切り出し画像のファイル名に使う）
    label: str = ""

    def front_masks(self) -> tuple[Path, ...]:
        if self.front_mask is None:
            return ()
        return self.front_mask if isinstance(self.front_mask, tuple) else (self.front_mask,)


@dataclass(frozen=True)
class BackgroundStyle:
    # キャラの線をぼかす量（背景の線がぼやけているほど大きく）。線の太さと濃さは背景から自動で測って合わせる
    blur: float

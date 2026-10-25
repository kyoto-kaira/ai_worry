from gen_img.kaira_kun.transparent import to_transparent
from gen_img.paths import FAKE_DIR, REAL_DIR
from PIL import Image


def main():
    """本物・偽物の画像を白黒＋透明の PNG にする（JPEG は PNG に置き換える）"""
    for path in sorted([*REAL_DIR.iterdir(), *FAKE_DIR.iterdir()]):
        if path.suffix not in (".png", ".jpg"):
            continue
        out = path.with_suffix(".png")
        to_transparent(Image.open(path)).save(out)
        if path != out:
            path.unlink()
        print(f"{path.parent.name}/{out.name}")


if __name__ == "__main__":
    main()

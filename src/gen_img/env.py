import os

from gen_img.paths import ROOT_DIR


def load_env(path=ROOT_DIR / ".env"):
    """リポジトリ直下の .env（KEY=VALUE の行）を環境変数に読み込む。すでに設定されている環境変数は上書きしない。
    uv の --env-file を付けなくても、どの OS でも同じコマンドで動くようにするため"""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip().removeprefix("export ").strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))

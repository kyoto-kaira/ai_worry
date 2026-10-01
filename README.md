# ai_worry

「Kaira君を探せ」用の画像を生成するリポジトリです。

## 構成

```
img/
  background/   Kaira君がいない背景
  kaira_kun/
    real/       本物（正解）
    fake/       偽物
  question/     問題画像（背景 + 本物1体 + 偽物）
src/gen_img/
  paths.py      画像フォルダのパス
  background/   背景の生成（Gemini API）
    config.py   モデル・プロンプト・テーマ
    generate.py
  question/     問題画像の合成
    config.py   背景ごとの線の太さ、問題ごとの配置
    placement.py
    character.py  キャラの線の太さ合わせ・変形
    occlusion.py  背景の物陰に隠す処理
    compose.py
```

## セットアップ

パッケージ管理に [uv](https://docs.astral.sh/uv/) を使います。未インストールなら以下で入れてください。

```sh
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

インストール後、依存パッケージを入れます。

```sh
uv sync
```

## 使い方

```sh
# 背景を生成（.env に GEMINI_API_KEY を書いておく）
uv run --env-file .env python -m gen_img.background.main 3 4 5   # 既存は --force で上書き

# 問題画像を生成（引数なしで全問）
uv run python -m gen_img.question.main 3 8
```

問題 n は背景 `(n-1) % 5 + 1` を使います。配置は `src/gen_img/question/config.py` の `QUESTIONS` で、
各問題の先頭が本物、残りが偽物です。`behind` に背景の物体の内側の座標を指定すると、その物体の後ろに隠れます。

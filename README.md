# ai_worry

「Kaira君を探せ」用の画像を生成するリポジトリです。

## 構成

```
img/
  background/   Kaira君がいない背景
  kaira_kun/    白黒＋透明の PNG（線は黒、体の中は白、外側としっぽの網目の間は透明）
    real/       本物（正解）
    fake/       偽物
  question/     問題画像（旧版・10枚。AI でなじませる前のもの）
  harmonized_question/
    question/   問題画像 25 枚（背景 + 本物1体 + 偽物、AI でなじませたもの）
    crop/       物陰に隠れたキャラの比較（なじませる前・後・塗った範囲・手前マスク。git に入れない）
    mask/
      rough/    人が隠したい物の内側を大まかに黒く塗った画像（物体からはみ出さない。物ごとのマスクの元）
      object/   物ごとの手前マスク（茂み・サンゴ・建物など。gen_img.mask で作る。白 = キャラより手前）
        normal/ 問題画像に使う物
        hard/   マスクの自動作成（SAM による塗り足し）がうまく補えない物。記録として残し、問題画像には使わない
      question/ 問題ごとの手前マスク（その問題でキャラを隠すのに使った物をまとめたもの）
exp/            実験の記録（中身は exp/README.md）、実験用のコードは exp/code/
src/gen_img/
  paths.py      画像フォルダのパス
  background/   背景の生成（Gemini API）
    config.py   モデル・プロンプト・テーマ
    generate.py
  kaira_kun/    キャラ画像を白黒＋透明に変換する（しっぽの網目の間を自動で見分けて透明にする）
  question/     問題画像の合成
    config.py   背景ごとの線の太さ、問題ごとの配置
    placement.py
    character.py  キャラの線の太さ合わせ・変形
    occlusion.py  背景の物陰に隠す処理
    compose.py
  mask/         茂み・サンゴなどの手前マスクを作る
    config.py   切り抜く物の一覧（枠・点・多角形、使う候補）
    segment_remote.py  GPU サーバーで実行する部分（Grounding DINO + SAM）
    shape.py    多角形を線に吸着させる処理・マスクの仕上げ
    main.py
  harmonize/    AI（PHDiffusion）でなじませる
    questions.py  本番の問題画像を作る
    remote_infer.py  GPU サーバーで実行する部分
    main.py, layouts.py, refine_remote.py  実験用
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

背景を足して問題画像を作るまでの詳しい手順（手作業・GPU サーバーでの作業を含む）は [WORKFLOW.md](WORKFLOW.md) を参照。

```sh
# 背景を生成（.env に GEMINI_API_KEY を書いておく）
uv run --env-file .env python -m gen_img.background.main 3 4 5   # 既存は --force で上書き

# 手前マスクを作る（茂み・サンゴは SAM、ロボットは多角形）
uv run python -m gen_img.mask.main prepare   # work/mask に背景と targets.json を用意
#   work/mask と segment_remote.py を GPU サーバーに送り、python segment_remote.py <作業フォルダ> を実行して masks/ を持ち帰る
uv run python -m gen_img.mask.main finish    # 候補を選んで整え、手前マスクとして保存
uv run python -m gen_img.mask.main lasso     # 多角形から作るマスク（GPU 不要）

# なじませた問題画像を生成（引数なしで全問）
uv run python -m gen_img.harmonize.questions prepare        # キャラごとの切り出しを work/ に作る
# work/harmonize/questions/jobs と remote_infer.py を GPU サーバーに送り、
#   python remote_infer.py <作業フォルダ> --strengths 0.3  を実行して outputs/ を持ち帰る
uv run python -m gen_img.harmonize.questions merge          # img/harmonized_question/ に書き出す
```

問題 n は背景 `1 + (n-1) // NUM_QUESTIONS_PER_BACKGROUND` を使います（今は背景1枚につき5問、問題1〜5が背景1）。
配置は `src/gen_img/question/config.py` の `QUESTIONS` で、各問題の先頭が本物、残りが偽物です。

- `front_mask`：手前マスク（`img/harmonized_question/mask/object/normal/`）を指定すると、その物の後ろに隠れます。マスクは隠したい物を大まかに塗った画像（`mask/rough/`）から SAM で作ります（WORKFLOW.md の 2 章）

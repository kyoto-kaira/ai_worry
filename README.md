# ai_worry

「Kaira君を探せ」用の画像を生成するリポジトリです。

## 構成

```
app/            Kaira君を探せのアプリ（YOLO をヒントに使う。詳しくは app/README.md）
  data/         アプリが使う絵・モデル・作ったもの
    background/   Kaira君がいない背景（git に入れる）
    kaira/        白黒＋透明の PNG（線は黒、体の中は白、外側としっぽの網目の間は透明。git に入れる）
      real/       本物（正解）
      fake/       偽物
    model/best.pt YOLO のモデル（git に入れない。別に受け取って置く）
    builtin/      用意した問題の画像・正解・YOLO の検出結果（app/build.py が作る。git に入れない）
    user/         アプリで作った背景・偽物・問題（git に入れない）
exp/            実験の記録（中身は exp/README.md。git に入れない）、実験用のコードは exp/code/
  img/          物陰に隠して AI でなじませる、前のやり方の成果物（問題画像・手前マスク・確認用の切り出し）
src/gen_img/
  paths.py      絵のフォルダのパス（アプリの絵は app/data/、前のやり方の成果物は exp/img/）
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
    review.py   物陰に隠れたキャラの確認用の切り出し
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

Python は **3.13** を使います（リポジトリ直下の `.python-version` で指定。uv が自動で 3.13 を用意するので、コマンドで指定しなくてよい）。
アプリで使う torch 2.6.0 は Python 3.14 以降に対応していないので、`pyproject.toml` でも 3.13 までに制限しています。
前に別のバージョンで `.venv` を作っていても、`uv sync` で 3.13 に作り直されます。

Gemini の API キーは、リポジトリ直下の `.env` に `GEMINI_API_KEY=...` と書いておきます。プログラムが起動時に自動で読むので、`--env-file` は要りません。

コマンドは Windows（PowerShell・コマンドプロンプト）でも Mac・Linux でも同じです。
ただし、ARM の Windows（Snapdragon など）には torch 2.6.0 の配布物がないので、YOLO を使うアプリは動きません（Intel・AMD の Windows なら動く）。

## アプリ（Kaira君を探せ）の起動

問題を「作る」画面と「解く」画面があるブラウザアプリ（詳しくは [app/README.md](app/README.md)）。

```sh
uv sync                                # 初回だけ（torch・ultralytics も入る）
uv run python app/build.py              # 初回と、用意した問題の配置や YOLO のモデルを変えたときだけ（問題画像・正解・YOLO の検出結果を app/data/builtin/ に作る。約3分）

uv run python app/server.py
```

- 起動するとブラウザが開く。解く画面は http://localhost:8770/ 、作る画面は http://localhost:8770/create 。止めるときは Ctrl+C
- YOLO の検出結果は `build.py`（用意した問題）と登録のとき（作った問題）に保存してあるので、起動は数秒（GPU は要らない）。
  モデル（`app/data/model/best.pt`）や推論の設定を変えると、古い結果は起動時に自動で検出し直す
- YOLO のモデルは `app/data/model/best.pt` を置いておく。`.env` の `GEMINI_API_KEY` は、作る画面で背景や Kaira君を Gemini で作るときに使う
- YOLO に使う torch・ultralytics はプロジェクトの依存に入っていて、`uv sync` で一度入れれば毎回のダウンロードはない。
  torch は CPU 版を使う設定にしてある（`pyproject.toml` の `[tool.uv.sources]`。Linux で普通に入れると GPU 用の CUDA まで入って重い）
- `app/data/model/best.pt` がないときは、ヒントが正解の位置から作ったモックになる（画面右上に「ヒント: モック」と出る）
- コードを直したら、起動し直さないと画面に反映されない

## 問題画像の作り方

背景を足して問題画像を作るまでの詳しい手順（手作業・GPU サーバーでの作業を含む）は [WORKFLOW.md](WORKFLOW.md) を参照。

```sh
# 背景を生成（.env に GEMINI_API_KEY を書いておく）
uv run python -m gen_img.background.main 3 4 5   # 既存は --force で上書き

# 手前マスクを作る（茂み・サンゴは SAM、ロボットは多角形）
uv run python -m gen_img.mask.main prepare   # work/mask に背景と targets.json を用意
#   work/mask と segment_remote.py を GPU サーバーに送り、python segment_remote.py <作業フォルダ> を実行して masks/ を持ち帰る
uv run python -m gen_img.mask.main finish    # 候補を選んで整え、手前マスクとして保存
uv run python -m gen_img.mask.main lasso     # 多角形から作るマスク（GPU 不要）

# なじませた問題画像を生成（引数なしで全問）
uv run python -m gen_img.harmonize.questions prepare        # キャラごとの切り出しを work/ に作る
# work/harmonize/questions/jobs と remote_infer.py を GPU サーバーに送り、
#   python remote_infer.py <作業フォルダ> --strengths 0.3  を実行して outputs/ を持ち帰る
uv run python -m gen_img.harmonize.questions merge          # exp/img/harmonized_question/ に書き出す
```

問題 n は背景 `1 + (n-1) // NUM_QUESTIONS_PER_BACKGROUND` を使います（今は背景1枚につき5問、問題1〜5が背景1）。
配置は `src/gen_img/question/config.py` の `QUESTIONS` で、各問題の先頭が本物、残りが偽物です。

- 隙間からのぞく問題は `GAP_QUESTIONS` に書き、`front_mask=occluders("物1", "物2")` で両側の物を指定します。なじませるときは `--set gap` を付けます
- `front_mask`：手前マスク（`exp/img/harmonized_question/mask/object/normal/`）を指定すると、その物の後ろに隠れます。マスクは隠したい物を大まかに塗った画像（`mask/rough/`）から SAM で作ります（WORKFLOW.md の 2 章）

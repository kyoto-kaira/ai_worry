# 問題画像の作り方（詳しい手順）

新しい背景を足して、問題画像を作るまでの手順。コマンド1つでは終わらず、手作業（設定ファイルを書く・目で確認する）と GPU サーバーでの作業が間に入る。

## 全体の流れ

| 段階 | やること | 手作業 | GPU | 出力 |
|---|---|---|---|---|
| 1. 背景 | テーマを書く → Gemini で生成 → 確認 → 線の太さを測る | テーマ・確認・設定 | 不要（API） | `img/background/<番号>.png` |
| 2. 手前マスク | 隠れ場所を決める → 枠・点を書く → SAM で切り抜く → 候補を選ぶ | 座標・候補選び | 必要 | `img/harmonized_question/mask/<名前>.png` |
| 3. 問題画像 | 配置を書く → 下見 → PHDiffusion でなじませる → 確認 | 配置・確認 | 必要 | `img/harmonized_question/question/<番号>.png` |

前提：`uv sync` 済み、`.env` に `GEMINI_API_KEY`（背景生成）と `VAST_API_KEY`（Vast.ai を使う場合）を書いておく。
GPU の作業は「4. GPU サーバーの使い方」を参照。

---

## 1. 背景画像の生成

### 1-1. テーマを書く（必須）

`src/gen_img/background/config.py` の `THEMES` に、背景の番号と「何を描くか」を英語で書き足す。
**番号を登録しないで実行すると `KeyError: 6` で止まり、画像は作られない**（API を呼ぶ前に止まるので料金はかからない）。

```python
THEMES = {
    ...
    6: "A crowded jungle ruin: stone statues, vines, big leafy bushes, ...",
}
```

- 物陰（茂み・箱・柱・大きな家具など）が多いテーマにすると、あとで隠れ場所を作りやすい
- 線画・白黒・ウォーリー風の描き込み・「Kaira 君に似たキャラを描かない」という指示は `STYLE` に共通で入っているので、テーマには場面だけ書けばよい
- 背景1・2が画風の参考として Gemini に渡される（`STYLE_REFERENCES`）。構図はまねしないよう指示してある

### 1-2. 生成する

```sh
uv run --env-file .env python -m gen_img.background.main 6        # 背景6を作る（複数なら 6 7 8）
uv run --env-file .env python -m gen_img.background.main 6 --force  # 作り直す（既存を上書き）
```

- 1枚あたり約 20 秒（Gemini API、`gemini-3-pro-image`）
- 同じ番号の画像があるときは何もしない（`skip`）。作り直すときは `--force`

### 1-3. 目で確認する

`img/background/<番号>.png` を開いて確認する。だめなら `--force` で作り直す（毎回違う絵になる）。

- Kaira 君に似たキャラ（脳みそのような形・網目の触手）がいない（いると答えが2つになる）
- 白黒の線画になっている（灰色の塗り・文字が入っていない）
- 画面いっぱいに物が描き込まれている

### 1-4. 線の太さを測って登録する（必須）

キャラの線の太さを背景に合わせるのに使う。

```sh
uv run python -c "from gen_img.question.character import line_width, load_gray; print(round(line_width(load_gray('img/background/6.png')), 2))"
```

出た値を `src/gen_img/question/config.py` の `BACKGROUND_STYLES` に入れる。**登録しないと問題画像を作るときに `KeyError` で止まる。**

```python
BACKGROUND_STYLES = {
    ...
    6: BackgroundStyle(stroke_width=2.1, blur=0.4),
}
```

- `blur`：キャラの線をぼかす量。背景の線がぼやけているほど大きく（今までの背景では 0.3〜0.6）
- 背景 b は問題 `4(b-1)+1` 〜 `4b` に使われる（背景6なら問題21〜24。`NUM_QUESTIONS_PER_BACKGROUND = 4`）

---

## 2. 手前マスクの生成（隠れ場所を作る）

キャラを物の後ろに隠すときの「手前にある物の範囲」（白 = キャラより手前）。

### 2-0. マスクが要るかを決める

| 隠れ場所 | 方法 | マスク |
|---|---|---|
| 箱・キノコの傘・柱など、輪郭が閉じている物 | 配置の `behind` に物の内側の座標を書くだけ（3-1） | 不要 |
| 茂み・サンゴ・枝分かれした物 | SAM で切り抜く（2-2〜2-4） | 必要 |
| 形は単純だが輪郭にすき間がある物（ロボットなど） | 大まかな多角形を背景の線に吸着させる（2-5） | 必要（GPU 不要） |

迷ったら `behind` で試し、物の外まで範囲が広がる（`leaks into a huge region` で止まる）なら SAM か多角形にする。

### 2-1. 座標を調べる

背景に方眼を重ねた画像を作り、それを見て座標を決める（細い線 50px ごと、数字は 100px ごと）。

```sh
uv run python - <<'EOF'
from PIL import Image, ImageDraw
im = Image.open("img/background/6.png").convert("RGB")
d = ImageDraw.Draw(im)
for v in range(0, max(im.size), 50):
    color = (255, 0, 0) if v % 100 == 0 else (255, 170, 170)
    d.line([(v, 0), (v, im.height)], fill=color)
    d.line([(0, v), (im.width, v)], fill=color)
    if v % 100 == 0:
        d.text((v + 2, 2), str(v), fill=(255, 0, 0))
        d.text((2, v + 2), str(v), fill=(255, 0, 0))
im.save("work/grid_6.png")
EOF
```

### 2-2. 切り抜く物を書く

`src/gen_img/mask/config.py` の `SAM_TARGETS` に書き足す。名前は `sam_bg<背景番号>_<物>` にしておくと分かりやすい。書き方は3通り。

```python
# (a) 文字で探す：形がはっきりした物（サンゴなど）。search_box の中から "coral" を探して切り抜く
SamTarget("sam_bg6_coral", 6, (0, 230, 210, 450), object_text="coral"),

# (b) 枠と内側の点：文字では別の物を拾ってしまう物（茂みなど）
SamTarget("sam_bg6_bush", 6, (88, 576, 298, 660),
          points=[(132, 584), (168, 598), (258, 612)]),

# (c) (b) に「物ではない所」の点を足す：近くの樽・キノコなどまで拾ってしまうとき
SamTarget("sam_bg6_bush2", 6, (380, 570, 500, 692),
          points=[(400, 600), (470, 588), (478, 650)],
          neg_points=[(447, 615), (512, 610)]),
```

- `search_box`：(左, 上, 右, 下)。(a) では探す範囲、(b)(c) では物を囲む枠
- 内側の点は、線の上ではなく物の中の白い所に置く。物全体に散らばるように 5〜7 個
- 物ではない点は、間違えて拾われた物（2-4 で分かる）の上に置く
- `candidate` は 2-4 で決める（最初は 0 のままでよい）

### 2-3. GPU で切り抜く

```sh
uv run python -m gen_img.mask.main prepare    # work/mask/ に背景と targets.json を用意（前回の結果は消える）
```

`work/mask/` と `src/gen_img/mask/segment_remote.py` を GPU サーバーに送り、次を実行して `masks/` を持ち帰って `work/mask/masks/` に置く。

```sh
pip install -q "transformers==4.48.3" accelerate   # 新しい transformers だと引数名が違ってエラーになる
python segment_remote.py <work/mask を置いた場所>
```

- 使うモデル：Grounding DINO（`IDEA-Research/grounding-dino-base`）と SAM（`facebook/sam-vit-huge`）。初回は自動でダウンロード
- RTX 3090 で、読み込み 40 秒、1か所あたり 0.5〜1.9 秒、GPU メモリ最大 6.5GB。Colab 無料枠（T4）でも足りる
- 「custom kernel を読み込めない」という警告は無視してよい（遅い処理に切り替わるだけ）

### 2-4. 候補を選んで保存する

SAM は1か所につき3つの候補（`<名前>_0〜2.png`）を返す。背景に赤く重ねて見比べる。

```sh
uv run python - <<'EOF'
import numpy as np
from PIL import Image
name, bg = "sam_bg6_bush", 6
base = np.asarray(Image.open(f"img/background/{bg}.png").convert("RGB")).astype(float)
for k in range(3):
    m = np.asarray(Image.open(f"work/mask/masks/{name}_{k}.png")) > 127
    over = base.copy()
    over[m] = over[m] * 0.5 + np.array([255, 0, 0]) * 0.5
    Image.fromarray(over.astype(np.uint8)).save(f"work/check_{name}_{k}.png")
EOF
```

- 物の形に沿っていて、ほかの物まで塗られていない候補を選び、`config.py` の `candidate` に番号を書く
- どれもだめなら、点を足す・物ではない点を足す（2-2 の (c)）などして 2-3 からやり直す
- 決まったら保存する：

```sh
uv run python -m gen_img.mask.main finish     # 選んだ候補を整えて img/harmonized_question/mask/ に保存
```

保存時に「一番大きいかたまりだけ残す・小さな穴を埋める」処理が入る（離れた所の小さなかたまりがキャラの顔に乗って目が隠れるのを防ぐため）。

### 2-5. 多角形から作る（GPU 不要）

`LASSO_TARGETS` に物を囲む多角形の頂点を書き、実行する。多角形の縁にかかる背景の線は自動で含まれる。

```python
LassoTarget("poly_bg6_statue", 6, [(497, 640), (527, 633), (548, 728), (474, 748)], snap=4),
```

```sh
uv run python -m gen_img.mask.main lasso
```

---

## 3. 問題画像の生成

### 3-1. 配置を書く

`src/gen_img/question/config.py` の `QUESTIONS` に、問題ごとのキャラを並べる。**先頭が本物（`REAL`）、残りが偽物（`FAKE`）。** 本物が1体でない問題は生成時にエラーになる。

```python
21: [
    P(REAL / "1.png", 120, 0, False, 125, 519, front_mask=OCCLUDER_DIR / "sam_bg6_bush.png"),  # 茂みの中
    P(FAKE / "12.png", 130, 0, True, 640, 650, behind=((655, 690),)),  # 王冠、箱の後ろ
    P(FAKE / "1.jpg", 140, 8, False, 20, 470),  # 3つ目、隠れていない
    ...
],
```

`P(画像, 幅, 角度, 左右反転, x, y, behind=..., front_mask=...)`

- `幅`：キャラの横幅（px）。高さは幅の約 0.65 倍。100 未満だと遠くにいるとみなして線を細くする
- `x, y`：キャラの左上の座標
- `behind`：輪郭の閉じた物の内側の座標（複数可）。その物の後ろに隠れる
- `front_mask`：2 で作ったマスク。その範囲の後ろに隠れる
- 物陰に隠すときは、頭と目が出る高さにする。目安は「マスクの上端 − 幅 × 0.45」を `y` にする
- 1問に 5〜7 体。キャラ同士が重ならないようにする

偽物を選ぶときの注意（答えが1つに決まるように）：

- 小さいキャラ（幅 100 未満）や隠れているキャラには、目の数の違い（`1.jpg` 3つ目、`2.jpg` 1つ目）や王冠・双葉・ポニーテールのような分かりやすいものを使う
- 舌（`7.png`）・寄り目（`9.png`）・触手なし（`3.png`）は、小さいと・隠れると・背景が細かいと見分けられない
- アホ毛（`6.png`）は毛が細く、幅 135px でもほとんど見えなかった

### 3-2. 下見する（GPU 不要）

なじませる前の合成を作って確認する。ここで配置を詰めてから GPU に進む。

```sh
uv run python -c "from gen_img.question.compose import build_question; build_question(21).save('work/preview_21.png')"
```

※ `python -m gen_img.question.main` は使わない（旧版の `img/question/` を上書きしてしまう）。

### 3-3. なじませる

```sh
uv run python -m gen_img.harmonize.questions prepare 21 22 23 24   # キャラごとの切り出しを work/harmonize/questions/jobs に作る
```

`work/harmonize/questions/jobs/` と `src/gen_img/harmonize/remote_infer.py` を GPU サーバーに送り、PHDiffusion を準備して実行する（下の手順）。
`outputs/PHDiffusion_s0.3/` を持ち帰って `work/harmonize/questions/outputs/` に置き、書き戻す。

```sh
uv run python -m gen_img.harmonize.questions merge 21 22 23 24     # img/harmonized_question/ に保存
```

GPU サーバーでの準備と実行（`/workspace/kaira` に jobs と remote_infer.py を置いた場合）：

```sh
cd /workspace
git clone -q --depth 1 https://github.com/bcmi/libcom.git
: > libcom/libcom/__init__.py   # 使わない機能（mmdet など）の読み込みを止める
pip install -q omegaconf pytorch_lightning transformers==4.44.2 einops opencv-python-headless \
    huggingface_hub taming-transformers-rom1504 open_clip_torch tqdm
# libcom の自動ダウンロードは動かないので、重みを先に落とす（約 4.7GB）
cd libcom/libcom && python -c "
from huggingface_hub import hf_hub_download
for f, d in [('sd-v1-4.ckpt', 'shared_pretrained_models'),
             ('PHDiffusionWithRes.pth', 'painterly_image_harmonization/pretrained_models')]:
    hf_hub_download('BCMIZB/Libcom_pretrained_models', f, local_dir=d)
"
cd /workspace/kaira
export PYTHONPATH=/workspace/libcom:/workspace/libcom/libcom/painterly_image_harmonization/source/PHDiffusion
python remote_infer.py /workspace/kaira --strengths 0.3   # 強さは QUESTION_STRENGTH と合わせる
```

- RTX 3090 で、準備 約1分、読み込み 15〜23 秒、1キャラあたり約 1.4 秒（20問・128体で 176 秒）、GPU メモリ最大 5.5GB
- `merge` で自動的に行うこと：目・しっぽ・手足・飾り・体から飛び出した所は元の絵に戻す、手前の物の上には書き戻さない
- 一部の問題だけ作り直すときは、その番号だけ `prepare` / `merge` すればよい（ほかの問題の結果は残る）

### 3-4. 目で確認する

キャラを1体ずつ拡大して並べた画像を作って確認する。

```sh
uv run python - <<'EOF'
from PIL import Image
from gen_img.question.config import QUESTIONS
q = 21
im = Image.open(f"img/harmonized_question/question/{q}.png")
tiles = []
for p in QUESTIONS[q]:
    w = int(p.width * 1.4); x0 = max(0, p.x - int(p.width * 0.2)); y0 = max(0, p.y - int(p.width * 0.25))
    tiles.append(im.crop((x0, y0, x0 + w, y0 + int(w * 0.8))).resize((300, 240)))
sheet = Image.new("RGB", (304 * len(tiles), 244), "gray")
for i, t in enumerate(tiles):
    sheet.paste(t, (i * 304, 0))
sheet.save(f"work/check_q{q}.png")
EOF
```

- 偽物の特徴（目の数・飾り・まつ毛など）がはっきり見える
- 本物と同じに見える偽物がいない（今までに、アホ毛が消えた・手前マスクの飛び地で目が隠れた例があった）
- 隠れ方が不自然でない（物の形と合わない所で切れていない、しっぽが細切れになっていない）

だめなら 3-1 に戻って位置・偽物の種類・隠れ場所を変える。

### 3-5. 出力

- `img/harmonized_question/question/<番号>.png`：問題画像
- `img/harmonized_question/mask/<番号>.png`：その問題でキャラを隠すのに使った手前マスク

---

## 4. GPU サーバーの使い方（Vast.ai）

Colab でもよい（マスク作成は無料枠で足りる。PHDiffusion は Colab では未確認）。Vast.ai の場合：

```sh
set -a; . ./.env; set +a
V="uvx vastai --api-key $VAST_API_KEY"

# 1. 借りる GPU を探す（RTX 3090、安い順。中国のサーバーは Hugging Face からのダウンロードで失敗しやすいので除く）
$V search offers 'gpu_name=RTX_3090 num_gpus=1 reliability>0.99 inet_down>800 disk_space>=60 cuda_vers>=12.4 rentable=true verified=true geolocation notin [CN]' -o dph_total --limit 5

# 2. 借りる（<offer_id> は 1 の一番左の ID）
$V create instance <offer_id> --image pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel --disk 60 --ssh --direct --label kaira

# 3. 起動を待つ（actual_status が running になるまで。数分かかる）
$V show instances

# 4. 接続先を調べる（public_ipaddr と、ports の 22/tcp の HostPort）
$V show instance <instance_id> --raw

# 5. ファイルを送る・持ち帰る
rsync -az -e "ssh -p <port>" work/harmonize/questions/jobs src/gen_img/harmonize/remote_infer.py root@<ip>:/workspace/kaira/
rsync -az -e "ssh -p <port>" root@<ip>:/workspace/kaira/outputs/ work/harmonize/questions/outputs/

# 6. 終わったら必ず消す（消すまで課金される）
$V destroy instance <instance_id> -y
```

- 料金は RTX 3090 で 1時間あたり $0.15〜0.20 程度。1回の作業は 10〜20 分
- 10 分以上 `loading` のまま進まないサーバーがある。そのときは消して別のサーバーを借りる
- 長い処理は `nohup bash run.sh > run.log 2>&1 &` のように裏で動かす（SSH が途中で切れることがあるため）
---
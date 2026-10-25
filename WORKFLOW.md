# 問題画像の作り方（詳しい手順）

新しい背景を足して、問題画像を作るまでの手順。コマンド1つでは終わらず、手作業（設定ファイルを書く・目で確認する）と GPU サーバーでの作業が間に入る。

## 全体の流れ

| 段階 | やること | 手作業 | GPU | 出力 |
|---|---|---|---|---|
| 1. 背景 | テーマを書く → Gemini で生成 → 確認 → 線の太さを測る | テーマ・確認・設定 | 不要（API） | `img/background/<番号>.png` |
| 2. 手前マスク | 隠したい物の内側を大まかに黒く塗る（はみ出さない）→ SAM で物体の端まで塗り足す → 確認 | 塗る・確認 | 必要 | `img/harmonized_question/mask/object/normal/<名前>.png` |
| 3. 問題画像 | 配置を書く → 下見 → PHDiffusion でなじませる → 確認 | 配置・確認 | 必要 | `img/harmonized_question/question/<番号>.png` |

前提：`uv sync` 済み、`.env` に `GEMINI_API_KEY`（背景生成）と `VAST_API_KEY`（Vast.ai を使う場合）を書いておく。
GPU の作業は「4. GPU サーバーの使い方」を参照。

---

## 0. キャラ画像（新しい偽物を足すとき）

キャラ画像は白黒＋透明の PNG（線は黒、体の中は白、外側としっぽの網目の間は透明）。
しっぽは黒い線だけが体の一部で、網目の間は背景が見える。

新しい偽物を足すときは、白い背景に黒い線で描いた画像を `img/kaira_kun/fake/` に置き、変換する（JPEG も PNG に置き換わる）。

```sh
uv run python -m gen_img.kaira_kun.main
```

- しっぽの網目の間は「体の右側にあり、小さな丸（しっぽの先の丸）ではない、線に囲まれた所」として自動で見分ける（基準は `src/gen_img/kaira_kun/config.py`）
- 見分けを間違えていないか、背景に重ねて確かめる（しっぽの先の丸が透明になっていないか、飾りが透明になっていないか）
- すでに変換した画像をもう一度変換しても変わらない

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

### 1-4. ぼかしの量を登録する（必須）

キャラの線の太さ・黒さ・白さは、問題を作るときに背景から自動で測って合わせる。登録が必要なのは、キャラの線をぼかす量だけ。
`src/gen_img/question/config.py` の `BACKGROUND_STYLES` に足す。**登録しないと問題画像を作るときに `KeyError` で止まる。**

```python
BACKGROUND_STYLES = {
    ...
    6: BackgroundStyle(blur=0.4),
}
```

- `blur`：背景の線がぼやけているほど大きく（今までの背景では 0.3〜0.6）
- 自動で測った値は次で確かめられる（線の太さ、線の芯の黒さ・白さ）

```sh
uv run python -c "from gen_img.question.tone import background_stroke, background_tone; print(background_stroke(6), background_tone(6))"
```

- 背景 b は問題 `5(b-1)+1` 〜 `5b` に使われる（背景6なら問題26〜30。`NUM_QUESTIONS_PER_BACKGROUND = 5`）

---

## 2. 手前マスクの生成（隠れ場所を作る）

キャラを物の後ろに隠すときの「手前にある物の範囲」（白 = キャラより手前）。
**物体の範囲そのもの**を塗る。背景の線（輪郭や影の線）で囲まれた領域は、物体の一部の面にすぎないことが多いので使わない。

流れ：

1. 人が、隠したい物の内側を大まかに黒く塗る。物体からははみ出さない（2-2）
2. SAM が、塗った範囲をもとに物体の端まで塗り足す（2-3〜2-4）
3. 問題画像を作るとき、その物の近くにキャラを置くと、重なった所ではキャラが描かれず、物の後ろに隠れる（3-1）

### 2-0. 作り方を選ぶ

| 隠れ場所 | 方法 |
|---|---|
| ほとんどの物（箱・機械・キノコの傘・柱・茂みなど） | 大まかに塗って SAM で合わせる（2-2〜2-4） |
| 塗るより点で指定した方が早い物、文字で探せる物（サンゴなど） | 枠・点・文字で SAM に指示する（2-5） |
| SAM がうまく切り抜けない物（輪郭にすき間がある・窓の向こうなど） | 多角形をそのまま使う（2-6、GPU 不要） |

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

### 2-2. 大まかに塗る

背景と同じ大きさの画像に、隠したい物を黒で大まかに塗って `img/harmonized_question/mask/rough/<名前>.png` に置く（それ以外は白か透明）。
名前は `bg<背景番号>_<物>`（例：`bg6_barrel`）。ペイントソフトで背景の上に別レイヤーで塗り、そのレイヤーだけ書き出すとよい。

**ルール：必ず物体の内側だけを塗る（物体からはみ出さない）。**

- 塗った所は、SAM の結果にかかわらず必ず物体として扱う。はみ出すと、その分がそのまま手前マスクになり、キャラが何もない所で欠ける
- 物体の端まで塗る必要はない。足りない所は SAM が塗り足す。ただし塗り足すのは塗った所から `fill`（20px）以内だけなので、物体の縁から 20px 以内まで塗っておく
- 形に沿って丁寧に塗る必要はない。物体の内側に収まっていれば、雑でよい
- 1枚に塗るのは1つの物体だけ。隣の物まで塗らない

塗ったら `src/gen_img/mask/config.py` の `ROUGH_TARGETS` に足す：

```python
RoughTarget("bg6_barrel", 6),
# 物体の縁から遠い所までしか塗れないとき（細かい物の中など）は、塗り足す範囲を広げる（px）
RoughTarget("bg6_barrel", 6, fill=30),
```

- `fill`：塗った所からこの距離以内で、SAM が物体とみなした所を塗り足す。広げると隣の物まで拾いやすくなる

### 2-3. GPU で切り抜く

```sh
uv run python -m gen_img.mask.main prepare bg6_barrel   # work/mask/ に背景と SAM への指示を用意（名前を省略すると全部。前回の結果は消える）
```

`work/mask/` と `src/gen_img/mask/segment_remote.py` を GPU サーバーに送り、次を実行して `masks/` を持ち帰って `work/mask/masks/` に置く。

```sh
pip install -q "transformers==4.48.3" accelerate   # 新しい transformers だと引数名が違ってエラーになる
python segment_remote.py <work/mask を置いた場所>
```

- 塗った範囲からは、`fill` だけ広げた外枠と、範囲全体に散らした内側の点 8 個（背景の線の上は避ける）が自動で作られ、SAM に渡される
- 使うモデル：Grounding DINO（`IDEA-Research/grounding-dino-base`）と SAM（`facebook/sam-vit-huge`）。初回は自動でダウンロード
- RTX 3090 で、読み込み 40 秒、1か所あたり 0.5〜1.9 秒、GPU メモリ最大 6.5GB。Colab 無料枠（T4）でも足りる
- 「custom kernel を読み込めない」という警告は無視してよい（遅い処理に切り替わるだけ）

### 2-4. 保存して確認する

```sh
uv run python -m gen_img.mask.main finish bg6_barrel   # img/harmonized_question/mask/object/normal/ に保存（hard=True の物は object/hard/）
```

SAM は1か所につき3つの候補を返す（物体の一部 / 物体 / 物体＋くっついている物 など）。塗った範囲から作るときは、候補ごとに

- 塗った範囲をどれだけ含むか（一部しかない候補は低い）
- 候補のうち、塗った範囲から `fill` より外にはみ出した割合（隣の物まで拾った候補は高い）

から点数（前者 − 2 × 後者）を出し、一番点数の高い候補を使う。そのうち塗った範囲から `fill` 以内の所だけを残し、
「一番大きいかたまりだけ残す・小さな穴を埋める」処理をしてから保存する。

- 塗りのうち SAM が物体の外と判断した所は外す（隣の物にかかった塗りを抑えるため）。外した量が塗りの 10% を超えると `warning: ... 塗った範囲の XX% を SAM が物体の外と判断して外した` と表示されるので、塗りがはみ出していないか確かめる
- マスクに囲まれた穴のうち、塗った所にかかる穴は物体の一部として埋める。塗っていない穴（窓のガラスなど）は残す
- どの候補も点数が 0.5 未満のときは、SAM が物体を切り抜けなかったとみなし、塗った範囲をそのまま使う（`warning: ... SAM が物体を切り抜けなかった`）
- 窓の向こうに隠すときのように、物体が「ガラス以外の壁と枠」といった SAM の苦手な形のときは、`fill=0` にして塗り足さない
- SAM の塗り足しがどうしてもうまく補えない物（暗い洞窟のように手前の物の境目がはっきりしないなど）は、`RoughTarget(..., hard=True)` にする。
  マスクは `object/hard/` に作られて記録として残るが、問題画像には使えない（配置に使うとエラーで止まる）

できたマスクを背景に赤く重ね、物体の形に合っているか確かめる。合っていなければ、塗り直すか `fill` を変えて 2-3 からやり直す。

```sh
uv run python - <<'PY'
import numpy as np
from PIL import Image
name, bg = "bg6_barrel", 6
base = np.asarray(Image.open(f"img/background/{bg}.png").convert("RGB")).astype(float)
m = np.asarray(Image.open(f"img/harmonized_question/mask/object/normal/{name}.png")) > 127
base[m] = base[m] * 0.5 + np.array([255, 0, 0]) * 0.5
Image.fromarray(base.astype(np.uint8)).save(f"work/check_{name}.png")
PY
```

### 2-5. 枠・点・文字で SAM に指示する

塗る代わりに、`SAM_TARGETS` に枠と点（または検索語）を書く。手順は 2-3〜2-4 と同じで、3つの候補から使うものを `candidate` で選ぶ（`work/mask/masks/<名前>_0〜2.png` を見比べる）。

```python
# 文字で探す：形がはっきりした物（サンゴなど）。search_box の中から "coral" を探して切り抜く
SamTarget("sam_bg6_coral", 6, (0, 230, 210, 450), object_text="coral"),
# 枠と内側の点。近くの物まで拾うときは、物ではない所の点（neg_points）も足す
SamTarget("sam_bg6_bush", 6, (380, 570, 500, 692),
          points=[(400, 600), (470, 588), (478, 650)], neg_points=[(447, 615)], candidate=1),
```

座標は、背景に方眼を重ねた画像（2-1）を見て決める。

### 2-6. 多角形から作る（GPU 不要）

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
26: [
    P(REAL / "1.png", 120, 0, False, 125, 519, front_mask=occluder("bg6_bush"), label="bush"),  # 茂みの中
    P(FAKE / "12.png", 130, 0, True, 640, 650, front_mask=occluder("bg6_barrel"), label="barrel"),  # 王冠、樽の後ろ
    P(FAKE / "1.png", 140, 8, False, 20, 470),  # 3つ目、隠れていない
    ...
],
```

`P(画像, 幅, 角度, 左右反転, x, y, front_mask=..., label=...)`

- `幅`：キャラの横幅（px）。高さは幅の約 0.65 倍。100 未満だと遠くにいるとみなして線を細くする
- `x, y`：キャラの左上の座標
- `front_mask`：2 で作ったマスク（`occluder("名前")` で指定）。マスクと重なった所ではキャラは描かれず、その物の後ろに隠れる
- `label`：隠れている物の名前。3-5 の切り出し画像のファイル名に使う
- 物陰に隠すときは、頭と目が出る高さにする。目安は「マスクの上端 − 幅 × 0.38」を `y` にする
- 頭が 50% 未満、または目が 90% 未満しか見えていない配置は、問題を作るときにエラーで止まる（`MIN_VISIBLE_HEAD`・`MIN_VISIBLE_EYES`）
- 物の横から顔を出すときは、目のある側が物の外に出るよう `左右反転` を使う（反転なしだと目は左側）
- 1問に 5〜7 体。キャラ同士が重ならないようにする

偽物を選ぶときの注意（答えが1つに決まるように）：

- 小さいキャラ（幅 100 未満）や隠れているキャラには、目の数の違い（`1.png` 3つ目、`2.png` 1つ目）や王冠・双葉・ポニーテールのような分かりやすいものを使う
- 舌（`7.png`）・寄り目（`9.png`）・触手なし（`3.png`）は、小さいと・隠れると・背景が細かいと見分けられない
- アホ毛（`6.png`）は以前は毛が1本で小さく見えなかったため、大きな巻き毛3本に描き直した（幅 80px でも見える）

### 3-2. 下見する（GPU 不要）

なじませる前の合成を作って確認する。ここで配置を詰めてから GPU に進む。

```sh
uv run python -c "from gen_img.question.compose import build_question; build_question(26).save('work/preview_26.png')"
```

※ `python -m gen_img.question.main` は使わない（旧版の `img/question/` を上書きしてしまう）。

### 3-3. なじませる

```sh
uv run python -m gen_img.harmonize.questions prepare 26 27 28 29 30   # キャラごとの切り出しを work/harmonize/questions/jobs に作る
```

`work/harmonize/questions/jobs/` と `src/gen_img/harmonize/remote_infer.py` を GPU サーバーに送り、PHDiffusion を準備して実行する（下の手順）。
`outputs/PHDiffusion_s0.3/` を持ち帰って `work/harmonize/questions/outputs/` に置き、書き戻す。

```sh
uv run python -m gen_img.harmonize.questions merge 26 27 28 29 30     # img/harmonized_question/ に保存
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
q = 26
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
- `img/harmonized_question/mask/question/<番号>.png`：その問題でキャラを隠すのに使った手前マスク（物ごとのマスクをまとめたもの）
- `img/harmonized_question/crop/<番号>_<何体目>_<real|fake>_<label>.png`：物陰に隠れたキャラごとに「なじませる前・後・人が塗った範囲（青。手前マスクの縁を赤い線で重ねる）・手前マスク（赤）」を並べたもの。隠れ方の違和感を調べるのに使う（git には入れない）。塗りから作っていないマスクは塗りの欄が `rough: none`

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
from pathlib import Path

# libcom の絵画調和モデル PHDiffusion（拡散モデル）で描き変える強さ。
# 大きいほど背景の画風に寄るが、キャラの形も崩れる
STRENGTHS = [0.1, 0.2, 0.3]
# 出力フォルダ名（= 手法名）
METHODS = [f"PHDiffusion_s{s}" for s in STRENGTHS]

# 仕上げ（refine）の元にする PHDiffusion の結果
BASE_METHOD = "PHDiffusion_s0.3"
# ControlNet + IP-Adapter で描き直す強さ
REFINE_STRENGTHS = [0.4, 0.6]
REFINE_METHODS = [f"refine_s{s}" for s in REFINE_STRENGTHS]
# 比較用：PHDiffusion の結果に、元画像の細かい部分（目・しっぽ・手足・飾り）を貼り戻す
RESTORE_METHOD = "restore_details"
# 細かい部分 = 線が密集している所。線の量をぼかして測り、この値を超えた範囲
DETAIL_SIGMA = 3.0
DETAIL_DENSITY = 0.32
# 体から細く飛び出した所 = シルエットをこの半径で丸めたときに消える部分
PROTRUSION_RADIUS = 6

# モデルの入力サイズ。キャラの周りを正方形に切り出してこの大きさにする
MODEL_SIZE = 512
# 切り出す正方形の一辺 = キャラの大きい方の辺 × この倍率（周りの画風を見せるため）
CROP_CONTEXT = 2.5

# 調和させる範囲：キャラの見えている部分をこの px だけ広げる（輪郭の外側もなじませる）
MASK_DILATION = 4
# 元画像に戻すときの境目のぼかし
MERGE_FEATHER = 2.0

SAMPLE_STEPS = 50
SEED = 0

# GPU サーバーとのやり取りに使う作業フォルダ
WORK_DIR = Path(__file__).resolve().parents[3] / "work" / "harmonize"
QUESTION_WORK_DIR = WORK_DIR / "questions"

# 問題画像を本番でなじませる設定：PHDiffusion をこの強さでかけ、目・しっぽなど細かい所は元に戻す
QUESTION_STRENGTH = 0.3

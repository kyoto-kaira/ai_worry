#%% [1] モデルとプロセッサの読み込み（最初の1回だけ実行）
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import torch
from PIL import Image
from transformers import Owlv2ForObjectDetection, Owlv2Processor
from pathlib import Path

model_name = "google/owlv2-base-patch16-ensemble"
processor = Owlv2Processor.from_pretrained(model_name)
model = Owlv2ForObjectDetection.from_pretrained(model_name)
device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)
print("モデル読み込み完了！")

#%% 検出処理（コードや閾値を書き換えて何度でも一瞬で実行可能）
# 2. 画像の読み込み
# このスクリプトが存在するフォルダの親フォルダ（プロジェクトのトップ）を取得
BASE_DIR = Path(__file__).resolve().parent.parent

# パスを結合
target_image_path = BASE_DIR /"img"/"question"/"1.png"
query_image_path = BASE_DIR / "img" / "kaira_kun"/"real" / "1.png"
try:
    target_image = Image.open(target_image_path).convert("RGB")
    query_image = Image.open(query_image_path).convert("RGB")
except FileNotFoundError as e:
    print(f"エラー: 画像ファイルが見つかりません。 {e}")
    exit()

# 3. 参照画像（query_images）を指定して前処理
inputs = processor(
    images=target_image, query_images=query_image, return_tensors="pt"
).to(device)

# 4. 画像誘導検出（image_guided_detection）を実行
print("参照画像をもとに検出を実行中...")
with torch.no_grad():
    outputs = model.image_guided_detection(**inputs)

# 5. 後処理
target_sizes = torch.tensor([target_image.size[::-1]]).to(device)
# 画像クエリはテキストより特徴が具体的なため、thresholdは0.5〜0.7程度に高めに設定可能
results = processor.post_process_image_guided_detection(
    outputs=outputs, target_sizes=target_sizes, threshold=0.99
)

boxes = results[0]["boxes"]
scores = results[0]["scores"]

# 6. 結果の描画と保存
plt.figure(figsize=(12, 8))
plt.imshow(target_image)
ax = plt.gca()

for box, score in zip(boxes, scores):
    box = box.cpu().numpy()
    score = score.item()

    xmin, ymin, xmax, ymax = box
    width, height = xmax - xmin, ymax - ymin

    rect = patches.Rectangle(
        (xmin, ymin),
        width,
        height,
        linewidth=2,
        edgecolor="red",
        facecolor="none",
    )
    ax.add_patch(rect)
    plt.text(
        xmin,
        ymin - 5,
        f"Match: {score:.2f}",
        color="white",
        fontsize=10,
        bbox=dict(boxstyle="square", facecolor="red", alpha=0.7),
    )

plt.axis("off")
output_path = BASE_DIR /"test_run" /"results" / "result_owlv2_image_query.jpg"
plt.savefig(output_path, bbox_inches="tight")
print(
    f"処理完了！ '{output_path}' に保存しました。（検出数: {len(boxes)}）"
)


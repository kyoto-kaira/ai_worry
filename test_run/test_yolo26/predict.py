from pathlib import Path
from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "results" / "kaira_run" / "weights" / "best.pt"

# 生成したテスト用画像の1枚を指定
TEST_IMAGE = Path(r"C:\Users\rohim\KaiRA_project\ai_worry\img\questions\packed\5.png")

model = YOLO(str(MODEL_PATH))

results = model.predict(
    source=str(TEST_IMAGE),
    imgsz=1024,
    conf=0.80,  # 確信度閾値
    save=True,
    project=str(BASE_DIR / "results"),
    name="colab_prediction_test",
)

print(
    f"推論完了！ 結果画像: {BASE_DIR / 'results' / 'colab_prediction_test'}"
)
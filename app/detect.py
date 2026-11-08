import random

from config import KAIRA_CLASS_WORDS, MATCH_IOU, MODEL_PATH, YOLO_CONFIDENCE, YOLO_IMAGE_SIZE, YOLO_MAX_DETECTIONS


def iou(a, b) -> float:
    x0, y0, x1, y1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x1 - x0) * max(0, y1 - y0)
    area = lambda r: (r[2] - r[0]) * (r[3] - r[1])
    return inter / max(1, area(a) + area(b) - inter)


class Detector:
    """本物の Kaira君の候補を返す。Kaira君用に学習した YOLO があればそれを使い、なければ正解の位置から作るモック"""

    def __init__(self):
        self.model, self.reason = None, ""
        if not MODEL_PATH.exists():
            self.reason = f"{MODEL_PATH.name} がない"
            return
        try:
            from ultralytics import YOLO
        except ImportError:
            self.reason = "ultralytics が入っていない"
            return
        model = YOLO(str(MODEL_PATH))
        if not any(word in name.lower() for name in model.names.values() for word in KAIRA_CLASS_WORDS):
            self.reason = f"{MODEL_PATH.name} が Kaira君用に学習されていない（クラス: {', '.join(list(model.names.values())[:3])} …）"
            return
        self.model = model

    @property
    def mode(self) -> str:
        return "yolo" if self.model else "mock"

    def detect(self, image_path, answer: dict, seed: int) -> list[dict]:
        """候補の枠と確信度（高い順）。正解のキャラと重なる候補には、そのキャラの番号（match。0 = 本物）を付ける。
        fake は「偽物」クラスの候補（偽物も見分けるモデルの場合）"""
        if self.model:
            result = self.model.predict(
                str(image_path), imgsz=YOLO_IMAGE_SIZE, conf=YOLO_CONFIDENCE, max_det=YOLO_MAX_DETECTIONS, verbose=False
            )[0]
            boxes = [
                {
                    "box": [round(v) for v in b.xyxy[0].tolist()],
                    "conf": round(float(b.conf[0]), 3),
                    "fake": "fake" in self.model.names[int(b.cls[0])].lower(),
                }
                for b in result.boxes
            ]
        else:
            boxes = mock_boxes(answer, seed)
        for d in boxes:
            scores = [iou(d["box"], c["box"]) for c in answer["characters"]]
            best = max(range(len(scores)), key=scores.__getitem__)
            d["match"] = best if scores[best] >= MATCH_IOU else None
        return sorted(boxes, key=lambda d: -d["conf"])


def mock_boxes(answer: dict, seed: int) -> list[dict]:
    """本物の枠を少しずらした、YOLO の出力に見立てた候補（隠れている本物は確信度を低めにする）"""
    rng = random.Random(seed)
    real = answer["characters"][0]
    x0, y0, x1, y1 = real["box"]
    w, h = x1 - x0, y1 - y0
    jitter = lambda size: round(rng.uniform(-0.06, 0.06) * size)
    conf = rng.uniform(0.15, 0.5) if real["hidden"] else rng.uniform(0.7, 0.95)
    return [{"box": [x0 + jitter(w), y0 + jitter(h), x1 + jitter(w), y1 + jitter(h)], "conf": round(conf, 3), "fake": False}]

# GPU サーバー上で実行する。文字で指定した物（"coral" など）を Grounding DINO で探し、SAM で切り抜いてマスクにする
# 入力: targets.json と backgrounds/<番号>.png、出力: masks/<名前>_<候補>.png と metrics.json
import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor, SamModel, SamProcessor

DETECTOR = "IDEA-Research/grounding-dino-base"
SEGMENTER = "facebook/sam-vit-huge"


def detect(processor, model, image: Image.Image, text: str):
    inputs = processor(images=image, text=f"{text}.", return_tensors="pt").to("cuda")
    with torch.no_grad():
        outputs = model(**inputs)
    result = processor.post_process_grounded_object_detection(
        outputs, inputs.input_ids, box_threshold=0.2, text_threshold=0.2, target_sizes=[image.size[::-1]]
    )[0]
    return result["boxes"].cpu().numpy(), result["scores"].cpu().numpy()


def segment(processor, model, image: Image.Image, box, points=None, neg_points=None) -> tuple[np.ndarray, np.ndarray]:
    kwargs = {"input_boxes": [[list(map(float, box))]]}
    if points:
        # 物の内側の点（正例）と、物ではない所の点（負例）も渡すと、何を切り抜くかがはっきりする
        neg_points = neg_points or []
        kwargs["input_points"] = [[[list(map(float, p)) for p in points + neg_points]]]
        kwargs["input_labels"] = [[[1] * len(points) + [0] * len(neg_points)]]
    inputs = processor(image, return_tensors="pt", **kwargs).to("cuda")
    with torch.no_grad():
        outputs = model(**inputs)
    masks = processor.image_processor.post_process_masks(
        outputs.pred_masks.cpu(), inputs["original_sizes"].cpu(), inputs["reshaped_input_sizes"].cpu()
    )[0][0].numpy()
    return masks, outputs.iou_scores.cpu().numpy()[0, 0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("work_dir", type=Path)
    args = parser.parse_args()

    start = time.perf_counter()
    det_processor = AutoProcessor.from_pretrained(DETECTOR)
    detector = AutoModelForZeroShotObjectDetection.from_pretrained(DETECTOR).to("cuda")
    sam_processor = SamProcessor.from_pretrained(SEGMENTER)
    sam = SamModel.from_pretrained(SEGMENTER).to("cuda")
    torch.cuda.synchronize()
    load_sec = time.perf_counter() - start

    out_dir = args.work_dir / "masks"
    out_dir.mkdir(exist_ok=True)
    targets = json.loads((args.work_dir / "targets.json").read_text())
    torch.cuda.reset_peak_memory_stats()
    records = []
    for t in targets:
        image = Image.open(args.work_dir / "backgrounds" / f"{t['bg_id']}.png").convert("RGB")
        x0, y0, x1, y1 = t["search_box"]
        start = time.perf_counter()
        if t.get("points") and t.get("object_text"):
            # 文字で探した枠と、内側の点を両方使う
            boxes, scores = detect(det_processor, detector, image.crop((x0, y0, x1, y1)), t["object_text"])
            bx = boxes[scores.argmax()] + np.array([x0, y0, x0, y0]) if len(boxes) else np.array(t["search_box"], dtype=float)
        elif t.get("points"):
            # 物の位置が分かっている場合：多角形の外枠と内側の点で SAM に直接指示する
            bx, boxes = np.array(t["search_box"], dtype=float), []
        else:
            # 文字だけの場合：探す範囲を切り出して検出し、一番スコアの高い枠を使う
            boxes, scores = detect(det_processor, detector, image.crop((x0, y0, x1, y1)), t["object_text"])
            bx = boxes[scores.argmax()] + np.array([x0, y0, x0, y0]) if len(boxes) else np.array([x0, y0, x1, y1], dtype=float)
        masks, ious = segment(sam_processor, sam, image, bx, t.get("points"), t.get("neg_points"))
        torch.cuda.synchronize()
        sec = time.perf_counter() - start
        for k, m in enumerate(masks):
            Image.fromarray((m * 255).astype(np.uint8)).save(out_dir / f"{t['name']}_{k}.png")
        records.append({
            "name": t["name"], "box": [round(float(v)) for v in bx], "detected": int(len(boxes)),
            "iou_scores": [round(float(v), 3) for v in ious], "sec": round(sec, 3),
        })
        print(t["name"], records[-1], flush=True)

    props = torch.cuda.get_device_properties(0)
    metrics = {
        "gpu": props.name,
        "model_load_sec": round(load_sec, 1),
        "peak_vram_gb": round(torch.cuda.max_memory_allocated() / 1024**3, 2),
        "targets": records,
    }
    (args.work_dir / "metrics.json").write_text(json.dumps(metrics, indent=1))
    print("FINISHED", flush=True)


if __name__ == "__main__":
    main()

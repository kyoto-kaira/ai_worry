# GPU サーバー上で実行する。jobs/<名前>/{composite,mask}.png を読み、outputs/<手法>/<名前>.png に書く
# 実行時間と GPU メモリの使用量を outputs/metrics.json に記録する
import argparse
import json
import time
from pathlib import Path

import cv2
import torch
from libcom.painterly_image_harmonization import PainterlyHarmonizationModel


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("work_dir", type=Path)
    parser.add_argument("--models", nargs="+", default=["PHDiffusion"])
    parser.add_argument("--steps", type=int, default=50)
    parser.add_argument("--strengths", nargs="+", type=float, default=[0.1, 0.2, 0.3])
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    jobs = sorted(p for p in (args.work_dir / "jobs").iterdir() if p.is_dir())
    props = torch.cuda.get_device_properties(0)
    metrics = {"gpu": props.name, "gpu_total_gb": round(props.total_memory / 1024**3, 1), "runs": []}

    for model_type in args.models:
        start = time.perf_counter()
        net = PainterlyHarmonizationModel(device=0, model_type=model_type)
        torch.cuda.synchronize()
        load_sec = time.perf_counter() - start
        # PHDiffusion は描き変える強さごと、PHDNet は1通り
        strengths = args.strengths if model_type == "PHDiffusion" else [None]
        for strength in strengths:
            method = model_type if strength is None else f"{model_type}_s{strength}"
            out_dir = args.work_dir / "outputs" / method
            out_dir.mkdir(parents=True, exist_ok=True)
            torch.cuda.reset_peak_memory_stats()
            times = []
            for job in jobs:
                composite, mask = str(job / "composite.png"), str(job / "mask.png")
                start = time.perf_counter()
                if strength is None:
                    result = net(composite, mask)
                else:
                    result = net(composite, mask, sample_steps=args.steps, strength=strength, random_seed=args.seed)
                torch.cuda.synchronize()
                times.append(time.perf_counter() - start)
                cv2.imwrite(str(out_dir / f"{job.name}.png"), result)
                print(method, job.name, f"{times[-1]:.2f}s", flush=True)
            metrics["runs"].append({
                "method": method,
                "model_load_sec": round(load_sec, 1),
                "images": len(times),
                "denoise_steps": None if strength is None else int(args.steps * strength),
                "sec_per_image_mean": round(sum(times) / len(times), 3),
                "sec_per_image_first": round(times[0], 3),
                "sec_total": round(sum(times), 1),
                "peak_vram_gb": round(torch.cuda.max_memory_allocated() / 1024**3, 2),
                "peak_vram_reserved_gb": round(torch.cuda.max_memory_reserved() / 1024**3, 2),
            })
    (args.work_dir / "outputs" / "metrics.json").write_text(json.dumps(metrics, indent=1))
    print("FINISHED", flush=True)


if __name__ == "__main__":
    main()

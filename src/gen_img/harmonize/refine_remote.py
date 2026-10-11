# GPU サーバー上で実行する。PHDiffusion でなじませた画像を、元の線画（形）と背景（画風）を手がかりに描き直す
#   形: ControlNet（lineart）に、AI を通す前の線画を渡す → 目の数・位置を元に戻す
#   画風: IP-Adapter に、周りの背景だけを切り出した画像を渡す
# 入力: jobs/<名前>/{composite,mask,style}.png と base/<名前>.png（PHDiffusion の出力）
# 出力: outputs/<手法>/<名前>.png と outputs/refine_metrics.json
import argparse
import json
import time
from pathlib import Path

import torch
from diffusers import ControlNetModel, StableDiffusionControlNetInpaintPipeline
from PIL import Image, ImageOps

PROMPT = "black and white line art, coloring book page, clean black ink outlines, cute cartoon creature"
NEGATIVE = "color, shading, gray fill, gradient, blurry, text, watermark, extra eyes, deformed"


def build_pipeline():
    controlnet = ControlNetModel.from_pretrained("lllyasviel/control_v11p_sd15_lineart", torch_dtype=torch.float16)
    pipe = StableDiffusionControlNetInpaintPipeline.from_pretrained(
        "stable-diffusion-v1-5/stable-diffusion-v1-5", controlnet=controlnet, torch_dtype=torch.float16, safety_checker=None
    )
    pipe.load_ip_adapter("h94/IP-Adapter", subfolder="models", weight_name="ip-adapter_sd15.bin")
    pipe.set_progress_bar_config(disable=True)
    return pipe.to("cuda")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("work_dir", type=Path)
    parser.add_argument("--strengths", nargs="+", type=float, default=[0.4, 0.6])
    parser.add_argument("--controlnet-scale", type=float, default=1.0)
    parser.add_argument("--ip-scale", type=float, default=0.6)
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    start = time.perf_counter()
    pipe = build_pipeline()
    pipe.set_ip_adapter_scale(args.ip_scale)
    load_sec = time.perf_counter() - start

    jobs = sorted(p for p in (args.work_dir / "jobs").iterdir() if p.is_dir())
    props = torch.cuda.get_device_properties(0)
    metrics = {"gpu": props.name, "gpu_total_gb": round(props.total_memory / 1024**3, 1), "runs": []}
    for strength in args.strengths:
        method = f"refine_s{strength}"
        out_dir = args.work_dir / "outputs" / method
        out_dir.mkdir(parents=True, exist_ok=True)
        torch.cuda.reset_peak_memory_stats()
        times = []
        for job in jobs:
            base = Image.open(args.work_dir / "base" / f"{job.name}.png").convert("RGB")
            # lineart の ControlNet は「黒地に白い線」を受け取る
            lines = ImageOps.invert(Image.open(job / "composite.png").convert("L")).convert("RGB")
            start = time.perf_counter()
            result = pipe(
                PROMPT,
                negative_prompt=NEGATIVE,
                image=base,
                mask_image=Image.open(job / "mask.png"),
                control_image=lines,
                ip_adapter_image=Image.open(job / "style.png").convert("RGB"),
                strength=strength,
                num_inference_steps=args.steps,
                controlnet_conditioning_scale=args.controlnet_scale,
                generator=torch.Generator("cuda").manual_seed(args.seed),
            ).images[0]
            torch.cuda.synchronize()
            times.append(time.perf_counter() - start)
            result.save(out_dir / f"{job.name}.png")
            print(method, job.name, f"{times[-1]:.2f}s", flush=True)
        metrics["runs"].append({
            "method": method,
            "model_load_sec": round(load_sec, 1),
            "images": len(times),
            "denoise_steps": int(args.steps * strength),
            "controlnet_scale": args.controlnet_scale,
            "ip_adapter_scale": args.ip_scale,
            "sec_per_image_mean": round(sum(times) / len(times), 3),
            "sec_per_image_first": round(times[0], 3),
            "sec_total": round(sum(times), 1),
            "peak_vram_gb": round(torch.cuda.max_memory_allocated() / 1024**3, 2),
            "peak_vram_reserved_gb": round(torch.cuda.max_memory_reserved() / 1024**3, 2),
        })
    (args.work_dir / "outputs" / "refine_metrics.json").write_text(json.dumps(metrics, indent=1))
    print("FINISHED", flush=True)


if __name__ == "__main__":
    main()

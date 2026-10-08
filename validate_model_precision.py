"""Compare original FP32 Real-CUGAN and optimized RGB8 FP16 on local test frames.

The result measures precision parity, not restoration quality against an HR ground truth.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "vendor/python-packages"))


def main():
    import numpy as np
    from PIL import Image
    import onnxruntime as ort
    from radeon_device import rx9070xt_device
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path, help="JSON list of path, width, height, fps")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    device, description = rx9070xt_device()

    def session(path):
        options = ort.SessionOptions()
        options.enable_mem_pattern = False
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        options.add_session_config_entry("session.disable_cpu_ep_fallback", "1")
        return ort.InferenceSession(str(ROOT / "vendor/onnx-models" / path), sess_options=options,
                                    providers=[("DmlExecutionProvider", {"device_id": device})])

    reference = session("pro-conservative-up2x.onnx")
    fast = session("rx9070xt-pro-x2-rgb8-fp16.onnx")
    records = []
    for item in json.loads(args.manifest.read_text(encoding="utf-8")):
        for seconds in (10, 30, 50):
            cmd = [str(ROOT / "vendor/mpv/mpv.exe"), "--no-config", "--terminal=no", "--audio=no", "--sub=no",
                   f"--start={seconds}", "--frames=1", "--o=-", "--of=rawvideo", "--ovc=rawvideo",
                   "--vf=format=rgb24", "--", item["path"]]
            result = subprocess.run(cmd, capture_output=True, timeout=30,
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            expected = item["width"] * item["height"] * 3
            if result.returncode or len(result.stdout) != expected:
                raise RuntimeError(f"프레임 추출 실패: {item['name']}")
            image = Image.fromarray(np.frombuffer(result.stdout, dtype=np.uint8).reshape(item["height"], item["width"], 3))
            # High-resolution files are resized only for precision validation of the low-res branch.
            # The actual HD playback branch never downsamples its input to feed Real-CUGAN.
            scale = min(1, 640 / image.width, 480 / image.height)
            if scale < 1:
                image = image.resize((int(image.width * scale) // 2 * 2, int(image.height * scale) // 2 * 2), Image.Resampling.LANCZOS)
            rgb = np.asarray(image)[None].copy()
            tensor = rgb.transpose(0, 3, 1, 2).astype(np.float32) * np.float32(0.7 / 255) + np.float32(0.15)
            original = reference.run(None, {reference.get_inputs()[0].name: tensor})[0]
            ref = np.clip((original[0].transpose(1, 2, 0) - np.float32(0.15)) * np.float32(255 / 0.7), 0, 255).astype(np.uint8)
            optimized = fast.run(None, {"rgb8": rgb})[0][0]
            diff = optimized.astype(np.float32) - ref.astype(np.float32)
            mse = float(np.mean(diff ** 2))
            record = {"name": item["name"], "timestamp": seconds, "test_width": image.width, "test_height": image.height,
                      "input_resized_for_validation": scale < 1, "mae_8bit": float(np.mean(np.abs(diff))),
                      "max_abs_error_8bit": float(np.max(np.abs(diff))), "psnr_to_fp32_db": float(10 * np.log10(255 ** 2 / mse)) if mse else None}
            record["precision_gate_passed"] = record["mae_8bit"] < 0.5 and (record["psnr_to_fp32_db"] is None or record["psnr_to_fp32_db"] >= 50)
            records.append(record)
        print(item["name"], "validated", flush=True)
    report = {"device": description, "cpu_fallback_disabled": True, "samples": records,
              "all_precision_gates_passed": all(r["precision_gate_passed"] for r in records),
              "interpretation": "FP16 graph parity versus the existing FP32 model; not HR restoration accuracy."}
    (args.out / "precision.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("precision gate:", report["all_precision_gates_passed"])


if __name__ == "__main__":
    main()

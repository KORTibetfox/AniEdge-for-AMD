"""Real-CUGAN Pro x2 DirectML benchmark, operating on decoded RGB PNG frames.

Model conversion: AmusementClub/vs-mlrt; Pro normalization follows its CUGAN conformance path.
This evaluates inference and host readback, not complete real-time playback.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "vendor/python-packages"))


def main():
    import numpy as np
    import onnxruntime as ort
    from PIL import Image

    parser = argparse.ArgumentParser(description="Real-CUGAN Pro 2배 DirectML 메모리 추론 측정")
    parser.add_argument("frames", type=Path, help="RGB PNG 프레임 폴더")
    parser.add_argument("--model", type=Path, default=ROOT / "vendor/onnx-models/pro-conservative-up2x.onnx")
    parser.add_argument("--device", type=int, default=0, help="DXGI GPU 번호. 현재 PC의 RX 9070 XT는 0")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--out", type=Path, required=True, help="존재하지 않는 결과 폴더")
    args = parser.parse_args()
    if not 1 <= args.limit <= 240 or args.device < 0:
        parser.error("limit는 1~240, device는 0 이상이어야 합니다.")
    files = sorted(args.frames.glob("*.png"))[:args.limit]
    if not files:
        parser.error("PNG 프레임이 없습니다.")
    if args.out.exists():
        parser.error("기존 결과를 덮어쓰지 않도록 새 out 폴더를 지정하세요.")
    if "DmlExecutionProvider" not in ort.get_available_providers():
        raise RuntimeError("DirectML 실행 공급자가 없습니다.")
    options = ort.SessionOptions()
    options.enable_mem_pattern = False
    options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    options.add_session_config_entry("session.disable_cpu_ep_fallback", "1")
    start = time.perf_counter()
    session = ort.InferenceSession(str(args.model), sess_options=options,
                                   providers=[("DmlExecutionProvider", {"device_id": args.device})])
    init_seconds = time.perf_counter() - start
    name = session.get_inputs()[0].name
    arrays = [np.asarray(Image.open(p).convert("RGB"), dtype=np.uint8) for p in files]
    shape = arrays[0].shape
    if any(a.shape != shape for a in arrays):
        raise ValueError("프레임 해상도가 모두 같아야 합니다.")
    if shape[0] % 2 or shape[1] % 2:
        raise ValueError("이 검증 도구는 짝수 폭·높이 프레임을 사용합니다.")

    tensor = np.empty((1, 3, shape[0], shape[1]), dtype=np.float32)

    def preprocess(array):
        np.multiply(array.transpose(2, 0, 1), np.float32(0.7 / 255.0), out=tensor[0])
        np.add(tensor, np.float32(0.15), out=tensor)
        return tensor

    start = time.perf_counter()
    session.run(None, {name: preprocess(arrays[0])})
    warmup_seconds = time.perf_counter() - start
    times, inference_times, samples = [], [], {}
    sample_indices = {0, len(files) // 2, len(files) - 1}
    for index, array in enumerate(arrays):
        start = time.perf_counter()
        tensor = preprocess(array)
        infer_start = time.perf_counter()
        result = session.run(None, {name: tensor})[0]
        infer_end = time.perf_counter()
        np.subtract(result, np.float32(0.15), out=result)
        np.multiply(result, np.float32(255.0 / 0.7), out=result)
        np.clip(result, 0, 255, out=result)
        restored = result[0].transpose(1, 2, 0).astype(np.uint8, order="C")
        end = time.perf_counter()
        if restored.shape != (shape[0] * 2, shape[1] * 2, 3):
            raise ValueError(f"예상하지 못한 출력 크기: {restored.shape}")
        times.append(end - start)
        inference_times.append(infer_end - infer_start)
        if index in sample_indices:
            samples[index] = restored
    args.out.mkdir(parents=True)
    for index, array in samples.items():
        Image.fromarray(array).save(args.out / files[index].name)
    report = {"model": str(args.model.resolve()), "device_id": args.device,
              "cpu_ep_fallback_disabled": True, "different_frames": len(files),
              "width": shape[1], "height": shape[0], "scale": 2,
              "model_init_seconds": init_seconds, "warmup_seconds": warmup_seconds,
              "inference_and_readback_fps": len(files) / sum(inference_times),
              "preprocess_inference_postprocess_fps": len(files) / sum(times),
              "p50_ms": float(np.percentile(times, 50)) * 1000,
              "p95_ms": float(np.percentile(times, 95)) * 1000,
              "p99_ms": float(np.percentile(times, 99)) * 1000,
              "per_frame_seconds": times, "proves_realtime_playback": False,
              "excluded": ["video decoding", "rendering", "audio and subtitles", "disk image IO",
                           "initialization and warmup", "long-run stability"]}
    (args.out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

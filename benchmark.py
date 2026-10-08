"""Short-clip Real-CUGAN Vulkan benchmark; Python standard library only."""
import argparse
import json
import math
import shutil
import subprocess
import sys
import time
from pathlib import Path


def executable(value):
    found = shutil.which(value)
    path = Path(found or value).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"실행 파일을 찾을 수 없습니다: {value}")
    return str(path)


def run(command, log):
    started = time.perf_counter()
    result = subprocess.run(command, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, encoding="utf-8", errors="replace")
    with log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(command, ensure_ascii=False) + "\n")
        handle.write(result.stdout + result.stderr + "\n")
    if result.returncode:
        raise RuntimeError(f"명령 실행 실패 ({result.returncode}). 로그: {log}")
    return result.stdout, time.perf_counter() - started


def main():
    parser = argparse.ArgumentParser(description="AMD Vulkan 애니메이션 2배 복원 속도 측정")
    parser.add_argument("video", type=Path)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument("--realcugan", default="realcugan-ncnn-vulkan")
    parser.add_argument("--models", required=True, type=Path, help="models-se 폴더")
    parser.add_argument("--gpu", required=True, type=int, help="Vulkan GPU 번호. 로그에서 AMD 장치 확인")
    parser.add_argument("--start", default=0.0, type=float)
    parser.add_argument("--frames", default=48, type=int)
    parser.add_argument("--noise", default=1, type=int, choices=[-1, 0, 1, 2, 3])
    parser.add_argument("--deinterlace", action="store_true", help="yadif send_frame 사용; 역텔레시네 아님")
    parser.add_argument("--out", default=Path("benchmark-results"), type=Path)
    args = parser.parse_args()
    if not args.video.is_file() or args.video.suffix.lower() not in (".mp4", ".mkv"):
        raise ValueError("존재하는 MP4 또는 MKV 파일을 지정하세요.")
    if not math.isfinite(args.start) or args.start < 0 or not 1 <= args.frames <= 240 or args.gpu < 0:
        raise ValueError("시작 시간은 0 이상, 프레임 수는 1~240, GPU 번호는 0 이상이어야 합니다.")
    if not args.models.is_dir():
        raise ValueError("Real-CUGAN models-se 폴더를 지정하세요.")
    ffmpeg, ffprobe, cugan = map(executable, (args.ffmpeg, args.ffprobe, args.realcugan))
    # Each run is isolated. Existing results and the source are never overwritten.
    output = args.out.resolve() / (time.strftime("%Y%m%d-%H%M%S") + f"-{time.time_ns() % 1000000:06d}")
    original, restored = output / "original", output / "restored"
    original.mkdir(parents=True)
    restored.mkdir()
    log = output / "commands.log"
    probe, _ = run([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries",
                    "stream=width,height,avg_frame_rate,r_frame_rate,field_order,sample_aspect_ratio",
                    "-of", "json", str(args.video.resolve())], log)
    streams = json.loads(probe).get("streams", [])
    if not streams:
        raise ValueError("영상 스트림이 없습니다.")
    stream = streams[0]
    raw_rate = stream.get("avg_frame_rate", "0/0")
    numerator, denominator = map(int, raw_rate.split("/"))
    if denominator <= 0 or numerator <= 0:
        raise ValueError("프레임 속도를 확인할 수 없습니다.")
    fps = numerator / denominator
    filters = (["yadif=mode=send_frame:parity=auto:deint=all"] if args.deinterlace else [])
    # Normalize to CFR for this bounded benchmark only; not a general playback timeline.
    filters.append(f"fps={raw_rate}")
    _, decode_seconds = run([ffmpeg, "-nostdin", "-v", "error", "-ss", str(args.start),
                             "-i", str(args.video.resolve()), "-map", "0:v:0", "-an", "-sn",
                             "-vf", ",".join(filters), "-frames:v", str(args.frames),
                             str(original / "%08d.png")], log)
    count = len(list(original.glob("*.png")))
    if not count:
        raise ValueError("선택한 구간에 프레임이 없습니다.")
    _, inference_seconds = run([cugan, "-i", str(original), "-o", str(restored),
                                "-m", str(args.models.resolve()), "-g", str(args.gpu),
                                "-s", "2", "-n", str(args.noise), "-f", "png"], log)
    if {p.name for p in original.glob("*.png")} != {p.name for p in restored.glob("*.png")}:
        raise RuntimeError("일부 프레임이 복원되지 않았습니다. 로그를 확인하세요.")
    elapsed = decode_seconds + inference_seconds
    report = {"source": str(args.video.resolve()), "stream": stream,
              "gpu_id_requested": args.gpu, "gpu_identity_verified": False,
              "model_directory": str(args.models.resolve()), "scale": 2,
              "noise": args.noise, "deinterlace": args.deinterlace,
              "start_seconds": args.start, "frames": count,
              "decode_seconds": decode_seconds, "inference_with_png_io_seconds": inference_seconds,
              "inference_with_png_io_fps": count / inference_seconds,
              "decode_and_restore_fps": count / elapsed, "source_average_fps": fps,
              "throughput_ratio_to_source": count / elapsed / fps,
              "proves_realtime_playback": False,
              "notes": ["PNG 입출력과 모델 초기화가 포함된 배치 측정입니다.",
                        "인코딩·렌더링·음성·자막·프레임 동기화는 측정하지 않습니다.",
                        "VFR은 평균 속도의 CFR로 정규화합니다. 원본 타임라인 검증용이 아닙니다.",
                        "GPU 장치명이 commands.log에서 AMD RX 9070 XT인지 확인하세요."]}
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n원본/복원 프레임과 결과: {output}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError) as error:
        print(f"오류: {error}", file=sys.stderr)
        sys.exit(1)

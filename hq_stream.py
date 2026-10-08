"""Real-CUGAN Pro FP16 x2 playback on RX 9070 XT via DirectML.

Real-CUGAN uses sequential CFR pipes.
Windows job ownership closes children when the wrapper terminates.
"""
import argparse
import ctypes
from ctypes import wintypes as w
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "vendor/python-packages"))


def validate_source(metadata):
    width, height, fps = metadata["width"], metadata["height"], metadata["fps"]
    if width <= 0 or height <= 0 or width % 2 or height % 2 or not (1 <= fps <= 60.01) or width * height > 1280 * 720:
        raise ValueError("HQ는 짝수 폭·높이, 720p 상당 이하, 1~60fps CFR 영상을 지원합니다. 권장은 480p 이하·30fps 이하입니다.")
    if abs(metadata.get("par", 1) - 1) > 0.001 or metadata.get("rotate", 0) != 0:
        raise ValueError("HQ는 정사각 픽셀·회전 없는 영상을 지원합니다.")


def owned_job():
    class BASIC(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                    ("LimitFlags", w.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", w.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", w.DWORD), ("SchedulingClass", w.DWORD)]
    class IO(ctypes.Structure):
        _fields_ = [(name, ctypes.c_uint64) for name in
                    ["ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                     "ReadTransferCount", "WriteTransferCount", "OtherTransferCount"]]
    class EXTENDED(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", BASIC), ("IoInfo", IO),
                    ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
    kernel.CreateJobObjectW.restype = w.HANDLE
    kernel.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
    kernel.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
    kernel.GetCurrentProcess.restype = w.HANDLE
    handle = kernel.CreateJobObjectW(None, None)
    info = EXTENDED()
    info.BasicLimitInformation.LimitFlags = 0x2000  # KILL_ON_JOB_CLOSE
    if not handle or not kernel.SetInformationJobObject(handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
        raise ctypes.WinError(ctypes.get_last_error())
    if not kernel.AssignProcessToJobObject(handle, kernel.GetCurrentProcess()):
        raise ctypes.WinError(ctypes.get_last_error())
    return handle  # Keep open for this process's entire lifetime.


def read_frame(pipe, size):
    data = bytearray()
    while len(data) < size:
        part = pipe.read(size - len(data))
        if not part:
            if data:
                raise RuntimeError("프레임 데이터가 중간에 끊겼습니다.")
            return None
        data.extend(part)
    return data


def main():
    import numpy as np
    import onnxruntime as ort
    parser = argparse.ArgumentParser(description="HQ — Real-CUGAN Pro FP16 DirectML 순차 재생")
    parser.add_argument("video", type=Path)
    parser.add_argument("--frames", type=int, default=0, help="검증용 최대 프레임 수; 0은 전체")
    parser.add_argument("--mute", action="store_true")
    args = parser.parse_args()
    if not args.video.is_file() or args.frames < 0:
        parser.error("유효한 영상 경로와 0 이상의 frames가 필요합니다.")
    job = owned_job()
    session_dir = ROOT / "logs" / ("hq-" + str(time.time_ns()))
    session_dir.mkdir(parents=True)
    mpv = str(ROOT / "vendor/mpv/mpv.exe")
    hidden = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    probe = subprocess.run([mpv, "--no-config", "--vo=null", "--ao=null", "--frames=1",
                            f"--script={ROOT / 'hq_probe.lua'}", str(args.video.resolve())],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20,
                           creationflags=hidden)
    source_lines = [line for line in probe.stdout.splitlines() if "HQ_SOURCE " in line]
    line = source_lines[-1] if source_lines else None
    if probe.returncode or not line:
        raise RuntimeError("영상 메타데이터 조회 실패")
    metadata = json.loads(line.split("HQ_SOURCE ", 1)[1])
    width, height, fps = metadata["width"], metadata["height"], metadata["fps"]
    (session_dir / "selection.json").write_text(json.dumps({"source": metadata, "profile": "pro-fast"}, ensure_ascii=False, indent=2), encoding="utf-8")
    validate_source(metadata)
    options = ort.SessionOptions()
    options.enable_mem_pattern = False
    options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    options.add_session_config_entry("session.disable_cpu_ep_fallback", "1")
    options.add_free_dimension_override_by_name("height", height)
    options.add_free_dimension_override_by_name("width", width)
    from radeon_device import rx9070xt_device
    device_id, device_name = rx9070xt_device()
    model_name = "rx9070xt-pro-x2-rgb8-fp16.onnx"
    session = ort.InferenceSession(str(ROOT / "vendor/onnx-models" / model_name),
                                   sess_options=options, providers=[("DmlExecutionProvider", {"device_id": device_id})])
    name = session.get_inputs()[0].name
    session.run(None, {name: np.full((1, height, width, 3), 128, dtype=np.uint8)})
    decoder_args = [mpv, "--no-config", "--terminal=no", "--audio=no", "--sub=no",
                    "--o=-", "--of=rawvideo", "--ovc=rawvideo", "--vf=format=rgb24",
                    f"--log-file={session_dir / 'decode.log'}"]
    if args.frames:
        decoder_args.append(f"--frames={args.frames}")
    decoder_args += ["--", str(args.video.resolve())]
    decoder = None
    renderer = None
    count = 0
    compute_times = []
    started = time.perf_counter()
    try:
        decoder = subprocess.Popen(decoder_args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                   creationflags=hidden)
        first = read_frame(decoder.stdout, width * height * 3)
        if first is None:
            raise RuntimeError("디코더가 프레임을 출력하지 않았습니다.")
        render_args = [mpv, "--no-config", "--vo=gpu-next", "--gpu-api=vulkan",
                       "--vulkan-device=AMD Radeon RX 9070 XT", "--demuxer=rawvideo",
                       f"--demuxer-rawvideo-w={width * 2}", f"--demuxer-rawvideo-h={height * 2}",
                       "--demuxer-rawvideo-mp-format=rgb24", f"--demuxer-rawvideo-fps={fps}",
                       "--video-sync=audio", "--demuxer-max-bytes=16MiB", "--demuxer-readahead-secs=0.25",
                       "--title=AniEdge for AMD · HQ · Real-CUGAN Pro FP16",
                       f"--script={ROOT / 'hq_controls.lua'}", f"--log-file={session_dir / 'render.log'}"]
        if metadata.get("primaries") and metadata.get("gamma"):
            render_args.append(f"--vf=format=primaries={metadata['primaries']}:gamma={metadata['gamma']}:colormatrix=rgb:colorlevels=full")
        if args.mute:
            render_args += ["--audio=no"]
        else:
            render_args += ["--audio-demuxer=lavf", f"--audio-file={args.video.resolve()}"]
        for extension in [".srt", ".ass", ".ssa"]:
            subtitle = args.video.with_suffix(extension)
            if subtitle.is_file():
                render_args.append(f"--sub-file={subtitle.resolve()}")
        if args.frames:
            render_args.append(f"--frames={args.frames}")
        render_args.append("-")
        renderer = subprocess.Popen(render_args, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, creationflags=hidden)
        (session_dir / "processes.json").write_text(json.dumps({"decoder_pid": decoder.pid,
                                                                 "renderer_pid": renderer.pid}), encoding="utf-8")
        frame = first
        while frame is not None and renderer.poll() is None:
            begin = time.perf_counter()
            rgb = np.frombuffer(frame, dtype=np.uint8).reshape(height, width, 3)
            restored = session.run(None, {name: rgb[None]})[0][0]
            compute_times.append(time.perf_counter() - begin)
            renderer.stdin.write(memoryview(restored))
            renderer.stdin.flush()
            count += 1
            frame = read_frame(decoder.stdout, width * height * 3)
        if renderer.stdin:
            renderer.stdin.close()
        renderer.wait(timeout=20)
        decoder.wait(timeout=10)
        if renderer.returncode:
            raise RuntimeError(f"HQ 렌더러 실패 ({renderer.returncode})")
        if decoder.returncode:
            raise RuntimeError(f"디코더 실패 ({decoder.returncode})")
    except BrokenPipeError:
        if renderer and renderer.poll() not in (None, 0):
            raise RuntimeError(f"HQ 렌더러 실패 ({renderer.returncode})")
    finally:
        for process in (decoder, renderer):
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
        report = {"source": str(args.video.resolve()), "source_metadata": metadata,
                  "output_frames_written": count, "elapsed_seconds": time.perf_counter() - started,
                  "compute_fps": len(compute_times) / sum(compute_times) if compute_times else 0,
                  "compute_p95_ms": float(np.percentile(compute_times, 95)) * 1000 if compute_times else 0,
                  "mode": "pro-fast", "model": model_name, "device_id": device_id, "device_name": device_name,
                  "limitations": ["CFR timing assumed", "sequential playback only", "host RGB copies",
                                  "no interlace processing"]}
        (session_dir / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return job  # The process owns the job handle until termination.


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        (ROOT / "logs").mkdir(exist_ok=True)
        (ROOT / "logs/hq-error.txt").write_text(str(error), encoding="utf-8")
        print(f"HQ 오류: {error}", file=sys.stderr)
        sys.exit(1)

"""Serial paired CPU-pre/post FP32 vs GPU-pre/post FP16 benchmark.

Measures processing and readback, excluding decode/render/audio and model warmup.
Optional 720p resampling checks model capacity, not original 720p restoration quality.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'vendor/python-packages'))


def main():
    import numpy as np
    import onnxruntime as ort
    from PIL import Image
    from radeon_device import rx9070xt_device
    p = argparse.ArgumentParser()
    p.add_argument('video', type=Path)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    device, description = rx9070xt_device()
    frames = []
    for second in (10, 20, 30):
        cmd = [str(ROOT/'vendor/mpv/mpv.exe'), '--no-config', '--terminal=no', '--audio=no', '--sub=no',
               f'--start={second}', '--frames=20', '--o=-', '--of=rawvideo', '--ovc=rawvideo',
               '--vf=scale=640:480,format=rgb24', '--', str(args.video.resolve())]
        raw = subprocess.run(cmd, capture_output=True, check=True).stdout
        if len(raw) != 20 * 640 * 480 * 3:
            raise RuntimeError('Unexpected decoded frame count')
        frames.extend(np.frombuffer(raw, dtype=np.uint8).reshape(20, 480, 640, 3))
    records = []
    for mode, width, height in [('original-fp32-cpu-prepost',640,480), ('optimized-fp16',640,480), ('optimized-fp16',1280,720)]:
        opts = ort.SessionOptions()
        opts.enable_mem_pattern = False
        opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        opts.add_session_config_entry('session.disable_cpu_ep_fallback','1')
        original = mode.startswith('original')
        if not original:
            opts.add_free_dimension_override_by_name('height',height)
            opts.add_free_dimension_override_by_name('width',width)
        model = 'pro-conservative-up2x.onnx' if original else 'rx9070xt-pro-x2-rgb8-fp16.onnx'
        session = ort.InferenceSession(str(ROOT/'vendor/onnx-models'/model), sess_options=opts,
                                      providers=[('DmlExecutionProvider',{'device_id':device})])
        name = session.get_inputs()[0].name
        images = frames if width == 640 else [np.asarray(Image.fromarray(f).resize((width,height),Image.Resampling.LANCZOS)) for f in frames]
        def run(rgb):
            if original:
                tensor = rgb.transpose(2,0,1).astype(np.float32)[None] * np.float32(.7/255) + np.float32(.15)
                result = session.run(None,{name:tensor})[0]
                np.subtract(result,np.float32(.15),out=result)
                np.multiply(result,np.float32(255/.7),out=result)
                np.clip(result,0,255,out=result)
                return result[0].transpose(1,2,0).astype(np.uint8,order='C')
            return session.run(None,{name:rgb[None]})[0][0]
        for _ in range(3):
            run(images[0])
        times = []
        for rgb in images:
            start=time.perf_counter(); run(rgb); times.append(time.perf_counter()-start)
        record={'mode':mode,'width':width,'height':height,'frames':len(images),'fps':len(times)/sum(times),
                'p95_ms':float(np.percentile(times,95))*1000,'frame_ms':[t*1000 for t in times],
                'synthetic_resizing':width!=640}
        records.append(record); print(mode,width,round(record['fps'],2),flush=True)
        del session
    report={'device':description,'measurements':records,'speedup_480p':records[1]['fps']/records[0]['fps'],
            'excluded':['decode','render','audio','warmup','disk IO'], 'proves_realtime_playback':False}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__ == '__main__':
    main()

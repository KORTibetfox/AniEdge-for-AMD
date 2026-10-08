"""Serial sample playback of a local corpus; do not run other GPU jobs alongside.

This launches visible playback windows and keeps original video files unchanged.
"""
import argparse
import json
import re
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('manifest',type=Path)
    parser.add_argument('--seconds',type=int,default=10)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    reports=[]
    for item in json.loads(args.manifest.read_text(encoding='utf-8')):
        before=set((ROOT/'logs').glob('hq-*'))
        start=time.perf_counter()
        result=subprocess.run([sys.executable,str(ROOT/'hq_stream.py'),item['path'],'--profile','auto',
                               '--frames',str(round(args.seconds*item['fps']))],timeout=args.seconds*3+30)
        new=set((ROOT/'logs').glob('hq-*'))-before
        if len(new)!=1:
            raise RuntimeError('Expected one playback session')
        folder=new.pop()
        selection=json.loads((folder/'selection.json').read_text(encoding='utf-8'))
        record={k:item[k] for k in ('name','width','height','fps')}
        record.update(profile=selection['profile'],exit_code=result.returncode,wall_seconds=time.perf_counter()-start,
                      tested_frames=round(args.seconds*item['fps']))
        if selection['profile']=='hd':
            d=json.loads((folder/'playback.json').read_text(encoding='utf-8'))
            record.update(renderer_drops=d['renderer_drops'],decoder_drops=d['decoder_drops'],
                          max_abs_avsync_ms=d['max_abs_avsync']*1000,output_dimensions=d.get('output_dimensions'),hwdec=d.get('hwdec'))
            passes=d.get('gpu_passes',{}).get('fresh',[])
            record['gpu_average_ms']=sum(p.get('avg',0) for p in passes)/1e6
            record['artcnn_passes']=sum('ArtCNN' in p.get('desc','') for p in passes)
        else:
            d=json.loads((folder/'summary.json').read_text(encoding='utf-8'))
            record.update(compute_fps=d['compute_fps'],compute_p95_ms=d['compute_p95_ms'])
            log=(folder/'render.log').read_text(encoding='utf-8',errors='replace')
            line=next((s for s in log.splitlines() if 'HQ playback summary:' in s),'')
            for prop,key,mult in [('renderer_drops','renderer_drops',1),('decoder_drops','decoder_drops',1),('max_abs_avsync','max_abs_avsync_ms',1000)]:
                match=re.search(prop+r'=([^; ]+)',line)
                record[key]=float(match.group(1))*mult if match else None
        reports.append(record)
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8')
        print(item['name'],record['profile'],'drops',record['renderer_drops'],flush=True)


if __name__=='__main__':
    main()

"""Evaluate exported detector against YOLO labels; timings cover detector only."""
import argparse,json,time,resource
from pathlib import Path
import cv2,numpy as np
from engine import Detector

def iou(a,b):
 x=max(0,min(a[2],b[2])-max(a[0],b[0]));y=max(0,min(a[3],b[3])-max(a[1],b[1]))
 inter=x*y;return inter/max(1e-9,(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter)

def main():
 p=argparse.ArgumentParser();p.add_argument('model');p.add_argument('images');p.add_argument('labels');p.add_argument('--confidence',type=float,default=.35);p.add_argument('--threads',type=int,default=2);p.add_argument('--out',default='pi_metrics.json');a=p.parse_args()
 det=Detector(a.model,a.threads);stats={c:{'tp':0,'fp':0,'fn':0} for c in det.meta['classes']};times=[];good=0;false_alarm=0
 cv2.setNumThreads(1)
 for path in sorted(Path(a.images).iterdir()):
  if path.suffix.lower() not in ['.png','.jpg','.jpeg']:continue
  im=cv2.imread(str(path));assert im is not None,path
  h,w=im.shape[:2];truth=[]
  for line in (Path(a.labels)/(path.stem+'.txt')).read_text().splitlines():
   if not line.strip():continue
   c,x,y,bw,bh=map(float,line.split());truth.append((int(c),[(x-bw/2)*w,(y-bh/2)*h,(x+bw/2)*w,(y+bh/2)*h]))
  if not times:det.detect(im,a.confidence)
  t=time.perf_counter();pred=det.detect(im,a.confidence);times.append((time.perf_counter()-t)*1000)
  matched=set()
  for d in sorted(pred,key=lambda v:-v['confidence']):
   c=det.meta['classes'].index(d['class']);options=[(iou(d['box'],b),i) for i,(tc,b) in enumerate(truth) if tc==c and i not in matched]
   score,i=max(options,default=(0,-1))
   if score>=.5:stats[d['class']]['tp']+=1;matched.add(i)
   else:stats[d['class']]['fp']+=1
  for i,(c,b) in enumerate(truth):
   if i not in matched:stats[det.meta['classes'][c]]['fn']+=1
  if not truth:good+=1;false_alarm+=bool(pred)
 assert times,'No images'
 for s in stats.values():
  s['precision']=s['tp']/(s['tp']+s['fp']) if s['tp']+s['fp'] else None
  s['recall']=s['tp']/(s['tp']+s['fn']) if s['tp']+s['fn'] else None
 result={'classes':stats,'iou_threshold':.5,'confidence':a.confidence,'images':len(times),'p50_detector_ms':float(np.percentile(times,50)),'p95_detector_ms':float(np.percentile(times,95)),'peak_process_rss_kib_linux':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'good_images':good,'good_images_with_false_alarm':false_alarm}
 Path(a.out).write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()

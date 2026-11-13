"""Single-worker TFLite folder engine. Model contract: raw YOLOv8, 3 classes, normalized xywh."""
import argparse,json,time,hashlib,os,uuid,traceback
from pathlib import Path
import cv2,numpy as np
def atomic_json(path,data):
 tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,indent=2));os.replace(tmp,path)
class Detector:
 def __init__(self,folder,threads=2):
  try:from tflite_runtime.interpreter import Interpreter
  except ImportError:from tensorflow.lite import Interpreter
  folder=Path(folder);self.meta=json.loads((folder/'metadata.json').read_text())
  assert self.meta['classes']==['open_circuit','short_circuit','missing_hole']
  assert self.meta['box_units']=='normalized'
  assert hashlib.sha256((folder/'detector.tflite').read_bytes()).hexdigest()==self.meta['sha256']
  self.runner=Interpreter(model_path=str(folder/'detector.tflite'),num_threads=threads);self.runner.allocate_tensors()
  self.i=self.runner.get_input_details()[0];outputs=self.runner.get_output_details();assert len(outputs)==1
  self.o=outputs[0];_,self.h,self.w,ch=self.i['shape'];assert ch==3
 def detect(self,im,threshold):
  h,w=im.shape[:2];scale=min(self.w/w,self.h/h);nw,nh=round(w*scale),round(h*scale)
  left=(self.w-nw)//2;top=(self.h-nh)//2
  canvas=np.full((self.h,self.w,3),114,np.uint8);canvas[top:top+nh,left:left+nw]=cv2.resize(im,(nw,nh))
  x=cv2.cvtColor(canvas,cv2.COLOR_BGR2RGB).astype(np.float32)[None]/255
  if np.issubdtype(self.i['dtype'],np.integer):
   s,z=self.i['quantization'];assert s>0;limits=np.iinfo(self.i['dtype']);x=np.clip(np.rint(x/s+z),limits.min,limits.max)
  self.runner.set_tensor(self.i['index'],x.astype(self.i['dtype']));self.runner.invoke()
  y=self.runner.get_tensor(self.o['index'])
  if np.issubdtype(y.dtype,np.integer):
   s,z=self.o['quantization'];assert s>0;y=(y.astype(np.float32)-z)*s
  y=y[0]
  if y.shape[0]==7:y=y.T
  assert y.shape[1]==7,('Unexpected model output',y.shape)
  result=[]
  for c in range(3):
   rows=y[y[:,4+c]>=threshold];boxes=[];scores=[]
   for row in rows:
    x,yc,bw,bh=row[:4]*[self.w,self.h,self.w,self.h]
    x1=np.clip((x-bw/2-left)/scale,0,w);y1=np.clip((yc-bh/2-top)/scale,0,h)
    x2=np.clip((x+bw/2-left)/scale,0,w);y2=np.clip((yc+bh/2-top)/scale,0,h)
    if x2>x1 and y2>y1:boxes.append([float(x1),float(y1),float(x2-x1),float(y2-y1)]);scores.append(float(row[4+c]))
   for idx in np.asarray(cv2.dnn.NMSBoxes(boxes,scores,threshold,.45)).reshape(-1):
    x,yc,bw,bh=boxes[idx];result.append({'class':self.meta['classes'][c],'box':[x,yc,x+bw,yc+bh],'confidence':scores[idx],'source':'detector'})
  return result
def reference_check(im,profile_path):
 profile_path=Path(profile_path);p=json.loads(profile_path.read_text());ref=cv2.imread(str(profile_path.parent/p['reference']))
 if ref is None:raise ValueError('Cannot read reference')
 factor=min(1,1200/max(im.shape[:2]));small=cv2.resize(im,None,fx=factor,fy=factor)
 orb=cv2.ORB_create(2000);gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY);rg=cv2.cvtColor(ref,cv2.COLOR_BGR2GRAY)
 k1,d1=orb.detectAndCompute(gray,None);k2,d2=orb.detectAndCompute(rg,None)
 if d1 is None or d2 is None:return [],'alignment_failed'
 pairs=cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(d1,d2,k=2);good=[v[0] for v in pairs if len(v)==2 and v[0].distance<.7*v[1].distance]
 if len(good)<15:return [],'alignment_failed'
 src=np.float32([k1[m.queryIdx].pt for m in good]);dst=np.float32([k2[m.trainIdx].pt for m in good])
 H,mask=cv2.findHomography(src,dst,cv2.RANSAC,3)
 if H is None or mask.sum()<12 or mask.mean()<.5:return [],'alignment_failed'
 try:inv=np.linalg.inv(H)
 except np.linalg.LinAlgError:return [],'alignment_failed'
 aligned=cv2.warpPerspective(gray,H,(ref.shape[1],ref.shape[0]));valid=cv2.warpPerspective(np.ones(gray.shape,np.uint8),H,(ref.shape[1],ref.shape[0]))
 findings=[]
 for region in p['regions']:
  x1,y1,x2,y2=map(int,region['box']);r=rg[y1:y2,x1:x2];t=aligned[y1:y2,x1:x2]
  if r.size==0 or not np.all(valid[y1:y2,x1:x2]):return [],'alignment_failed'
  similarity=float(cv2.matchTemplate(t,r,cv2.TM_CCOEFF_NORMED)[0,0]) if r.std()>1 and t.std()>1 else 0.0
  if similarity<region.get('min_similarity',.8):
   corners=np.float32([[[x1,y1],[x2,y1],[x2,y2],[x1,y2]]]);corners=cv2.perspectiveTransform(corners,inv)[0]/factor
   box=[float(corners[:,0].min()),float(corners[:,1].min()),float(corners[:,0].max()),float(corners[:,1].max())]
   findings.append({'class':'missing_component_candidate','reference_id':region['id'],'box':box,'confidence':None,'similarity':similarity,'source':'reference'})
 return findings,'review_required' if findings else 'checked'
def inspect(det,im,cfg):
 start=time.perf_counter();findings=det.detect(im,cfg['confidence']);notes=[];component='not_configured'
 if cfg.get('reference_profile'):
  ref,component=reference_check(im,cfg['reference_profile']);findings+=ref
 if component!='checked':notes.append('components: '+component)
 if not det.meta.get('validated'):notes.append('model_not_validated')
 status='faulty' if any(f['source']=='detector' for f in findings) else ('review_required' if notes else 'not_faulty')
 return {'status':status,'detections':findings,'notes':notes,'inference_ms':round((time.perf_counter()-start)*1000,2),'image_size':[im.shape[1],im.shape[0]],'model_sha256':det.meta['sha256']}
def main():
 p=argparse.ArgumentParser();p.add_argument('--config',default='config.json');a=p.parse_args();cfg=json.loads(Path(a.config).read_text())
 cv2.setNumThreads(1);root=Path(cfg['root']).expanduser().resolve();root.mkdir(parents=True,exist_ok=True)
 import fcntl
 lock=open(root/'engine.lock','w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 for name in ['incoming','processing','results','archive','failed']:(root/name).mkdir(exist_ok=True)
 det=Detector(cfg['model_dir'],cfg.get('threads',2))
 for old in (root/'processing').iterdir():os.replace(old,root/'incoming'/old.name)
 print('Watching',root/'incoming',flush=True)
 while True:
  for source in sorted((root/'incoming').iterdir()):
   if source.suffix.lower() not in ['.jpg','.jpeg','.png']:continue
   job=uuid.uuid4().hex;claimed=root/'processing'/(job+source.suffix);os.replace(source,claimed)
   result={'schema_version':1,'job_id':job,'original_name':source.name,'created_unix':time.time()}
   try:
    im=cv2.imread(str(claimed))
    if im is None:raise ValueError('Unreadable image')
    result.update(inspect(det,im,cfg));vis=im.copy()
    for d in result['detections']:
     x1,y1,x2,y2=map(round,d['box']);label=d['class']+(f" {d['confidence']:.2f}" if d['confidence'] is not None else ' REVIEW')
     cv2.rectangle(vis,(x1,y1),(x2,y2),(0,0,255),2);cv2.putText(vis,label,(max(0,x1),max(20,y1)),cv2.FONT_HERSHEY_SIMPLEX,.5,(0,0,255),1)
    cv2.putText(vis,result['status'],(10,30),cv2.FONT_HERSHEY_SIMPLEX,.8,(0,0,255),2)
    image=root/'results'/(job+'.jpg');tmp=root/'results'/(job+'.tmp.jpg')
    if not cv2.imwrite(str(tmp),vis):raise OSError('Image write failed')
    os.replace(tmp,image);result['annotated_image']=str(image);archive=root/'archive'/claimed.name
    os.replace(claimed,archive);result['original_image']=str(archive)
   except Exception as e:
    result.update(status='error',error=str(e),detections=[]);traceback.print_exc()
    if claimed.exists():os.replace(claimed,root/'failed'/claimed.name)
   atomic_json(root/'results'/(job+'.json'),result)
  time.sleep(.25)
if __name__=='__main__':main()

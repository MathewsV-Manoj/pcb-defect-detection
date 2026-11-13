import argparse,json,hashlib,shutil
from pathlib import Path
from ultralytics import YOLO
p=argparse.ArgumentParser();p.add_argument('mode',choices=['train','validate','export']);p.add_argument('--data',required=True);p.add_argument('--weights',default='yolov8n.pt');p.add_argument('--size',type=int,default=640);p.add_argument('--epochs',type=int,default=100);p.add_argument('--batch',type=int,default=4);p.add_argument('--device',default='0');p.add_argument('--out',default='deployment');a=p.parse_args()
m=YOLO(a.weights)
if a.mode=='train':
 m.train(data=a.data,imgsz=a.size,epochs=a.epochs,batch=a.batch,device=a.device,workers=2,seed=42,patience=20,project='runs',name='pcb',amp=True,mosaic=0.0,mixup=0.0)
elif a.mode=='validate':m.val(data=a.data,split='test',imgsz=a.size,device=a.device,plots=True)
else:
 assert list(m.names.values())==['open_circuit','short_circuit','missing_hole'],m.names
 out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 result=m.export(format='tflite',int8=True,data=a.data,imgsz=a.size,batch=1,nms=False,device='cpu')
 candidates=list(Path(a.weights).resolve().parent.glob('**/*full_integer_quant.tflite'))
 if Path(str(result)).is_file() and 'full_integer_quant' in str(result):candidates=[Path(result)]
 if len(candidates)!=1:raise RuntimeError('Select the correct full_integer_quant.tflite manually: '+str(candidates))
 dest=out/'detector.tflite';shutil.copy2(candidates[0],dest)
 (out/'metadata.json').write_text(json.dumps({'schema_version':1,'classes':list(m.names.values()),'input':'RGB_0_1_letterbox_114','box_units':'normalized','output':'yolov8_raw_xywh_class_scores','sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'validated':False},indent=2))
 print('Exported. Metadata remains unvalidated until parity and real-camera tests pass.')

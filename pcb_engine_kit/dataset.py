"""Import labeled images into a canonical YOLO dataset using an explicit split manifest."""
import argparse,csv,json,hashlib,shutil
from pathlib import Path
import xml.etree.ElementTree as ET
import cv2,yaml
NAMES=['open_circuit','short_circuit','missing_hole']
ALIASES={'open':'open_circuit','short':'short_circuit',**{n:n for n in NAMES}}
def main():
 p=argparse.ArgumentParser();p.add_argument('manifest');p.add_argument('output');a=p.parse_args()
 out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=False)
 base=Path(a.manifest).resolve().parent;groups={};hashes={};counts={s:[0]*3 for s in ['train','val','test']}
 for row in csv.DictReader(open(a.manifest,newline='')):
  split=row['split'];group=row['group'];assert split in counts
  assert group and groups.setdefault(group,split)==split,'Board group crosses splits'
  src=(base/row['image']).resolve();label=(base/row['label']).resolve()
  im=cv2.imread(str(src));assert im is not None,src
  h,w=im.shape[:2];digest=hashlib.sha256(src.read_bytes()).hexdigest()
  assert digest not in hashes,'Duplicate image: '+str(src)
  hashes[digest]=split;boxes=[];fmt=row['format']
  if fmt=='voc':
   for obj in ET.parse(label).getroot().findall('object'):
    name=ALIASES.get(obj.findtext('name').strip().lower())
    if name is None:continue
    b=obj.find('bndbox');x1,y1,x2,y2=[float(b.findtext(k)) for k in ['xmin','ymin','xmax','ymax']]
    boxes.append((NAMES.index(name),x1-1,y1-1,x2,y2))
  elif fmt=='deeppcb':
   for line in label.read_text().splitlines():
    if not line.strip():continue
    x1,y1,x2,y2,c=map(float,line.replace(',',' ').split())
    if int(c) in [1,2]:boxes.append((int(c)-1,x1,y1,x2,y2))
  elif fmt=='yolo':
   for line in label.read_text().splitlines():
    if not line.strip():continue
    c,x,y,bw,bh=map(float,line.split());assert c==int(c) and 0<=c<3
    boxes.append((int(c),(x-bw/2)*w,(y-bh/2)*h,(x+bw/2)*w,(y+bh/2)*h))
  else:raise ValueError('format must be voc, deeppcb, or yolo')
  text=[]
  for c,x1,y1,x2,y2 in boxes:
   assert 0<=x1<x2<=w and 0<=y1<y2<=h,(src,(x1,y1,x2,y2))
   text.append(f'{c} {(x1+x2)/2/w:.8f} {(y1+y2)/2/h:.8f} {(x2-x1)/w:.8f} {(y2-y1)/h:.8f}')
   counts[split][c]+=1
  stem=digest[:20]
  for kind in ['images','labels']:(out/kind/split).mkdir(parents=True,exist_ok=True)
  shutil.copy2(src,out/'images'/split/(stem+src.suffix.lower()))
  (out/'labels'/split/(stem+'.txt')).write_text('\n'.join(text)+'\n' if text else '')
 (out/'data.yaml').write_text(yaml.safe_dump({'path':str(out),'train':'images/train','val':'images/val','test':'images/test','names':NAMES}))
 (out/'audit.json').write_text(json.dumps({'counts':counts,'groups':groups},indent=2))
 print(json.dumps(counts,indent=2))
 if any(v==0 for s in counts.values() for v in s):print('WARNING: a class is absent in at least one split; do not claim full coverage.')
if __name__=='__main__':main()

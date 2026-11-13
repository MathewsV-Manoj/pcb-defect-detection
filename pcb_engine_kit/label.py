"""Local OpenCV bounding-box annotator. Existing labels are displayed and retained."""
import argparse
from pathlib import Path
import cv2
p=argparse.ArgumentParser();p.add_argument('folder');a=p.parse_args()
print('1=open, 2=short, 3=missing hole; R=draw box; U=undo; S=save/next; Q=quit. Empty saved label means reviewed good image.')
for path in sorted(Path(a.folder).iterdir()):
 if path.suffix.lower() not in ['.png','.jpg','.jpeg']:continue
 im=cv2.imread(str(path))
 if im is None:continue
 h,w=im.shape[:2];scale=min(1,1200/w,800/h);boxes=[];cls=0;target=path.with_suffix('.txt')
 if target.exists():
  for line in target.read_text().splitlines():
   if line.strip():boxes.append(list(map(float,line.split())))
 while True:
  view=cv2.resize(im,(round(w*scale),round(h*scale)))
  for c,x,y,bw,bh in boxes:
   p1=(round((x-bw/2)*w*scale),round((y-bh/2)*h*scale));p2=(round((x+bw/2)*w*scale),round((y+bh/2)*h*scale))
   cv2.rectangle(view,p1,p2,(0,0,255),1);cv2.putText(view,str(int(c)),p1,0,.5,(0,0,255),1)
  cv2.imshow('Label',view);k=cv2.waitKey(0)&255
  if k in [49,50,51]:cls=k-49
  elif k==ord('r'):
   x,y,bw,bh=cv2.selectROI('Label',view,False)
   if bw and bh:boxes.append([cls,(x+bw/2)/view.shape[1],(y+bh/2)/view.shape[0],bw/view.shape[1],bh/view.shape[0]])
  elif k==ord('u') and boxes:boxes.pop()
  elif k==ord('s'):
   target.write_text('\n'.join(f'{int(c)} {x:.8f} {y:.8f} {bw:.8f} {bh:.8f}' for c,x,y,bw,bh in boxes));break
  elif k==ord('q'):raise SystemExit()
cv2.destroyAllWindows()

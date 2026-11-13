import argparse,json
from pathlib import Path
import cv2
p=argparse.ArgumentParser();p.add_argument('image');p.add_argument('output');a=p.parse_args();im=cv2.imread(a.image);assert im is not None
s=min(1,1200/max(im.shape[:2]));im=cv2.resize(im,None,fx=s,fy=s)
print('Select installed components only. Enter/space confirms; Escape finishes. IDs follow selection order.')
boxes=cv2.selectROIs('Expected components',im,False);cv2.destroyAllWindows();out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
cv2.imwrite(str(out/'good.png'),im)
regions=[{'id':f'CANDIDATE_{i+1}','box':[int(x),int(y),int(x+w),int(y+h)],'min_similarity':.8} for i,(x,y,w,h) in enumerate(boxes) if w and h]
assert regions,'Select at least one component'
(out/'profile.json').write_text(json.dumps({'reference':'good.png','regions':regions},indent=2))

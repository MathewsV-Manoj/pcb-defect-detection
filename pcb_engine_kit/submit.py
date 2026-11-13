"""Publish complete input images with atomic rename. Use instead of copying directly into incoming."""
import argparse,shutil,os,uuid
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('image');p.add_argument('--root',default='~/Desktop/PCBInspection');a=p.parse_args();src=Path(a.image)
assert src.suffix.lower() in ['.jpg','.jpeg','.png'];folder=Path(a.root).expanduser()/'incoming';folder.mkdir(parents=True,exist_ok=True)
dest=folder/(uuid.uuid4().hex+src.suffix.lower());tmp=dest.with_suffix('.part');shutil.copyfile(src,tmp);os.replace(tmp,dest);print(dest.name)

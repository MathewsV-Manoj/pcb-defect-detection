"""Extract a downloaded dataset ZIP into a new directory; reject traversal and oversized archives."""
import argparse,zipfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('archive');p.add_argument('output');a=p.parse_args();out=Path(a.output).resolve()
assert not out.exists(),'Use a new destination'
with zipfile.ZipFile(a.archive) as z:
 assert sum(i.file_size for i in z.infolist())<20*1024**3,'Archive exceeds 20 GiB limit'
 for i in z.infolist():
  dest=(out/i.filename).resolve();assert dest.is_relative_to(out),'Unsafe path';assert (i.external_attr>>16)&0o170000!=0o120000,'Symlink not supported'
 out.mkdir(parents=True);z.extractall(out)

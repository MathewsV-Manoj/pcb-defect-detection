import unittest,tempfile,subprocess,sys,zipfile
from pathlib import Path
class Contracts(unittest.TestCase):
 def test_zip_traversal_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d)
   with zipfile.ZipFile(d/'bad.zip','w') as z:z.writestr('../escape.txt','bad')
   r=subprocess.run([sys.executable,'safe_extract.py',str(d/'bad.zip'),str(d/'out')],capture_output=True)
   self.assertNotEqual(r.returncode,0);self.assertFalse((d/'escape.txt').exists())
 def test_publish_complete(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);src=d/'a.png';src.write_bytes(b'test payload')
   subprocess.run([sys.executable,'submit.py',str(src),'--root',str(d/'spool')],check=True,capture_output=True)
   images=list((d/'spool'/'incoming').glob('*.png'));self.assertEqual(len(images),1);self.assertEqual(images[0].read_bytes(),src.read_bytes());self.assertFalse(list((d/'spool'/'incoming').glob('*.part')))
if __name__=='__main__':unittest.main()

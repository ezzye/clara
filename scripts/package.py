"""Package explicit public source directories; never recurse into private data."""
from pathlib import Path
import zipfile
root=Path(__file__).resolve().parents[1]
out=root/'.build';out.mkdir(exist_ok=True)
with zipfile.ZipFile(out/'clara.zip','w',zipfile.ZIP_DEFLATED) as z:
    for folder in ['apps/api','dist']:
        for f in (root/folder).rglob('*'):
            if f.is_file() and '__pycache__' not in f.parts and f.suffix!='.pyc':z.write(f,f.relative_to(root))
    z.write(root/'apps/__init__.py','apps/__init__.py')
print('Packaged application code and built assets only.')

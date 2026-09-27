"""Check or regenerate checksums for the Git-deliverable file set."""
import argparse
import hashlib
from pathlib import Path
import subprocess

parser=argparse.ArgumentParser(); parser.add_argument('--write',action='store_true'); args=parser.parse_args()
root=Path(__file__).resolve().parent.parent
names=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=root).decode('utf-8').split('\0')
names=sorted({name for name in names if name and name!='MANIFEST.sha256' and (root/name).is_file()})
manifest=''.join(hashlib.sha256((root/name).read_bytes()).hexdigest()+'  '+name+'\n' for name in names)
path=root/'MANIFEST.sha256'
if args.write: path.write_text(manifest,encoding='utf-8',newline='\n')
else:
    if path.read_text('utf-8-sig')!=manifest: raise SystemExit('Manifest mismatch. Review changes before running --write.')
print(f'Manifest verified: {len(names)} files')

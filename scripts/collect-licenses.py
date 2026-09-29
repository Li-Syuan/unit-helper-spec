"""Copy license/notice files supplied by the installed, locked distributions."""
from importlib import metadata
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from doctor import locked_packages

root=Path(__file__).resolve().parents[1]
folder=root/'docs'/'licenses'
for name,version in locked_packages(root/'requirements.lock').items():
    distribution=metadata.distribution(name)
    if distribution.version!=version:raise SystemExit('Environment differs from lock')
    files=[p for p in distribution.files or [] if any(word in p.name.lower() for word in ('license','licence','copying','notice')) and p.suffix.lower() not in {'.py','.pyc','.dll'}]
    pieces=[]
    for p in files:
        try:body=distribution.locate_file(p).read_text('utf-8')
        except (OSError,UnicodeError):continue
        pieces.append(str(p)+'\n\n'+body)
    if not pieces:
        value=distribution.metadata.get('License','')
        pieces=[value] if len(value)>150 else []
    if not pieces:
        print('License text unavailable in installed package: '+name)
        continue
    # Preserve original filenames for existing application help links.
    existing=next((p for p in folder.glob('*.txt') if p.stem.lower().replace('_','-').replace('.','-')==name),None)
    (existing or folder/(name+'.txt')).write_text('\n\n'.join(pieces),encoding='utf-8')

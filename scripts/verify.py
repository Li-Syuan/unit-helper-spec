"""Run the actual commands and retain evidence. Use the target venv Python."""
import datetime
import json
from pathlib import Path
import re
import subprocess
import sys

project=Path(__file__).resolve().parent.parent
commands=[['scripts/doctor.py'],['-m','pip','check'],['-m','pip','freeze','--all'],['-m','unittest','discover','-s','tests','-v']]
records=[]
for args in commands:
    process=subprocess.run([sys.executable,*args],cwd=project,text=True,encoding='utf-8',errors='replace',capture_output=True,timeout=120,env={**__import__('os').environ,'PYTHONIOENCODING':'utf-8'})
    output=process.stdout+process.stderr
    record={'command':[sys.executable,*args],'exit_code':process.returncode,'output':output}; records.append(record)
    print(' '.join(args)+': exit '+str(process.returncode))
    if args[0]=='-m' and args[1]=='unittest':
        match=re.search(r'Ran (\d+) tests?',output)
        if not match or int(match.group(1))==0: raise SystemExit('No tests executed')
        print(match.group(0))
        if 'skipped=' in output: raise SystemExit('Unexpected skipped tests')
    if process.returncode:
        print(output); raise SystemExit(process.returncode)
lock=(project/'requirements.lock').read_text('ascii').splitlines()
installed=records[2]['output'].splitlines()
if sorted(lock)!=sorted(installed): raise SystemExit('Installed packages differ from lock')
label=sys.argv[1] if len(sys.argv)>1 else 'local'
if not re.fullmatch('[a-z-]+',label): raise SystemExit('Invalid evidence label')
folder=project/'docs'/'validation'; folder.mkdir(exist_ok=True)
(folder/(label+'.json')).write_text(json.dumps({'recorded_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'environment':sys.executable,'commands':records},ensure_ascii=False,indent=2),encoding='utf-8')
print('Evidence saved: docs/validation/'+label+'.json')

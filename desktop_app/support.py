"""Bounded local diagnostics: whitelist data at capture AND export, never HTTP content."""
import json
from logging.handlers import RotatingFileHandler
from pathlib import Path
import platform
import re
import threading
import uuid
import zipfile
from datetime import datetime,timezone

_LOCK=threading.RLock()
STAGES={'startup','ui','background','cleanup','thread_create','message_create','run_create',
        'run_poll','messages_read','assistant_metadata','tool_call','tool_submit','remote_request','preflight'}
CODES={'FAILED','AUTHENTICATION','FORBIDDEN','NOT_FOUND','RATE_LIMIT','TIMEOUT','TRANSPORT','FORMAT','UNKNOWN','LOCAL_SETUP','RUN_FAILED'}
ROOT=Path(__file__).resolve().parent


def clean_record(value):
    if not isinstance(value,dict):return None
    if any(not isinstance(value.get(k),str) for k in ('id','time','stage','code')):return None
    if value['stage'] not in STAGES or value['code'] not in CODES:return None
    if not re.fullmatch(r'[a-f0-9]{32}',value['id']):return None
    if not re.fullmatch(r'\d{4}-\d\d-\d\dT[\d:.+Z-]{8,32}',value['time']):return None
    result={k:value[k] for k in ('id','time','stage','code')}
    version=value.get('version')
    if isinstance(version,str) and re.fullmatch(r'\d{1,3}\.\d{1,3}\.\d{1,3}',version):result['version']=version
    status=value.get('http_status')
    if type(status) is int and 100<=status<=599:result['http_status']=status
    from .assistant_errors import REMOTE_CODES
    remote=value.get('provider_code')
    if isinstance(remote,str) and remote in REMOTE_CODES:result['provider_code']=remote
    result['frames']=[]
    frames=value.get('frames',[])
    if not isinstance(frames,list):return None
    for frame in frames[:12]:
        if not isinstance(frame,dict):continue
        name,line=frame.get('file'),frame.get('line')
        if isinstance(name,str) and re.fullmatch('[a-z_]+\\.py',name) and (ROOT/name).is_file() and type(line) is int and 0<line<100000:
            result['frames'].append({'file':name,'line':line})
    return result


def record(directory,stage,exc=None):
    """Never format exceptions, source lines or local variables. Fail without raising."""
    incident=uuid.uuid4().hex
    try:
        from . import __version__
        entry={'id':incident,'version':__version__,'time':datetime.now(timezone.utc).isoformat(),
               'stage':stage if isinstance(stage,str) and stage in STAGES else 'ui','code':'FAILED','frames':[]}
        if exc is not None:
            status=getattr(exc,'status_code',None)
            if type(status) is int and 100<=status<=599:
                entry.update(http_status=status,code={401:'AUTHENTICATION',403:'FORBIDDEN',404:'NOT_FOUND',429:'RATE_LIMIT'}.get(status,'FAILED'))
            elif type(exc).__name__ in ('TimeoutError','APITimeoutError','ReadTimeout','ConnectTimeout'):entry['code']='TIMEOUT'
            elif type(exc).__name__ in ('APIConnectionError','ConnectError'):entry['code']='TRANSPORT'
            from .assistant_errors import AssistantFailure
            if isinstance(exc,AssistantFailure):
                entry.update(code=exc.code,stage=exc.stage)
                if exc.http_status is not None:entry['http_status']=exc.http_status
                if exc.remote_code is not None:entry['provider_code']=exc.remote_code
            tb=exc.__traceback__
            while tb:
                path=Path(tb.tb_frame.f_code.co_filename)
                try:
                    if path.resolve().parent==ROOT:entry['frames'].append({'file':path.name,'line':tb.tb_lineno})
                except OSError:pass
                tb=tb.tb_next
        entry=clean_record(entry)
        if entry is None:raise ValueError('invalid_safe_record')
        with _LOCK:
            folder=Path(directory)/'logs'
            if folder.is_symlink() or folder.resolve()!=Path(directory).resolve()/'logs':raise ValueError('linked_log_directory')
            folder.mkdir(parents=True,exist_ok=True)
            if any((folder/('events.jsonl'+suffix)).is_symlink() for suffix in ('','.1','.2','.3')):raise ValueError('linked_log_file')
            handler=RotatingFileHandler(folder/'events.jsonl',maxBytes=1024*1024,backupCount=3,encoding='utf-8')
            try:
                # Write directly: logging's error handler could expose an original exception to stderr.
                message=json.dumps(entry,ensure_ascii=False)+'\n'
                if handler.stream.tell()+len(message.encode('utf-8'))>=handler.maxBytes:handler.doRollover()
                handler.stream.write(message);handler.flush()
            finally:handler.close()
        return {'id':entry['id'],'saved':True}
    except Exception:return {'id':incident,'saved':False}


def export_bundle(directory,destination):
    from . import __version__
    directory=Path(directory);records=[];ignored=0
    with _LOCK:
        if (directory/'logs').is_symlink() or (directory/'logs').resolve()!=directory.resolve()/'logs':
            raise ValueError('日誌目錄不可為連結，未匯出。')
        for suffix in ('.3','.2','.1',''):
            path=directory/'logs'/('events.jsonl'+suffix)
            if not path.exists():continue
            if path.is_symlink() or path.stat().st_size>1024*1024:ignored+=1;continue
            for line in path.read_text('utf-8',errors='replace').splitlines():
                try:value=clean_record(json.loads(line))
                except (ValueError,TypeError,KeyError):value=None
                if value:records.append(value)
                else:ignored+=1
    report={'version':__version__,'python':platform.python_version(),'platform':platform.system(),
            'company_real':'not_tested','ignored_records':ignored,'events':records}
    # No directory traversal, database, config, raw test report or free-form exception included.
    destination=Path(destination);created=False
    try:
        with destination.open('xb') as output:
            created=True
            with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('diagnostics.json',json.dumps(report,ensure_ascii=False,indent=2))
                archive.writestr('README.txt','Local safe error events only. No conversation, credentials, HTTP body or database.\nCompany acceptance remains separate.\n')
    except Exception:
        if created:
            try:destination.unlink()
            except OSError:pass
        raise
    return {'saved':True,'events':len(records),'ignored_records':ignored}

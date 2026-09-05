"""Explicit, read-only collectors. Never read conversation bodies or file contents."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import hashlib,sqlite3
from apps.api.domain import SECRET_PATTERN

def event(source,identity,summary,stamp):
    if SECRET_PATTERN.search(summary):return None
    return {'id':hashlib.sha256((source+identity+str(stamp)).encode()).hexdigest(),
        'source':source,'summary':summary[:800],'observedAt':datetime.fromtimestamp(stamp,timezone.utc).isoformat(),'confidence':'low'}

def codex_metadata(db_path,project_roots):
    if not db_path or not project_roots:return []
    p=Path(db_path).expanduser().resolve()
    if not p.is_file():return []
    roots={str(Path(r).expanduser().resolve()) for r in project_roots}
    cutoff=int((datetime.now(timezone.utc)-timedelta(days=7)).timestamp())
    with sqlite3.connect(p.as_uri()+'?mode=ro',uri=True,timeout=2) as c:
        c.execute('PRAGMA query_only=ON')
        columns={r[1] for r in c.execute('PRAGMA table_info(threads)')}
        if not {'id','title','cwd','updated_at'}.issubset(columns):raise ValueError('Codex metadata schema changed; collector paused')
        rows=c.execute('SELECT id,title,cwd,updated_at FROM threads WHERE updated_at>? ORDER BY updated_at DESC LIMIT 100',(cutoff,)).fetchall()
    output=[]
    for ident,title,cwd,stamp in rows:
        if str(Path(cwd).resolve()) not in roots:continue
        e=event('codex',ident,f'Codex task updated: {title}. This does not establish completion.',stamp)
        if e:output.append(e)
    return output

def folder_metadata(folder,source,limit=20):
    p=Path(folder).expanduser().resolve()
    if not p.is_dir():return []
    cutoff=datetime.now(timezone.utc).timestamp()-7*86400
    files=[]
    for f in p.iterdir():
        if f.is_symlink() or not f.is_file() or f.name.startswith('.'):continue
        try:
            if f.stat().st_mtime>=cutoff:files.append(f)
        except OSError:continue
    files.sort(key=lambda f:f.stat().st_mtime,reverse=True)
    result=[]
    for f in files[:limit]:
        e=event(source,str(f),f'{source.capitalize()} file changed: {f.name}. Contents were not read.',f.stat().st_mtime)
        if e:result.append(e)
    return result

def collect(config):
    result=codex_metadata(config.get('codexDb'),config.get('projectRoots',[]))
    if config.get('downloadsFolder'):result+=folder_metadata(config['downloadsFolder'],'downloads')
    for folder in config.get('coworkExportFolders',[]):result+=folder_metadata(folder,'cowork')
    return result[:100]

"""Read project/session metadata only; no conversation bodies or credentials leave the laptop."""
import json, sqlite3, hashlib
from pathlib import Path
from apps.api.domain import SECRET_PATTERN

def snapshots(config):
    context=config.get('inventoryContext','personal');out=[]
    if config.get('inventoryAllCodex'):
        row={'source':'codex-projects','label':'Codex projects on this laptop','context':context,'items':[],'status':'unavailable','note':'Codex database unavailable.'}
        p=Path(config.get('codexDb','')).expanduser()
        if p.is_file():
            with sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True) as c:
                c.execute('PRAGMA query_only=ON')
                for cwd,count in c.execute('SELECT cwd,COUNT(*) FROM threads GROUP BY cwd ORDER BY cwd'):
                    if not cwd:continue
                    path=str(Path(cwd).expanduser().resolve());title=config.get('inventoryProjectNames',{}).get(path,Path(path).name)
                    if not title or SECRET_PATTERN.search(title):continue
                    row['items'].append({'id':hashlib.sha256(path.encode()).hexdigest()[:24],'title':title[:180],'path':path,
                                         'note':f'{count} Codex tasks recorded for this working directory, including archived history. Activity or archiving does not establish project completion.'})
            row.update(status='checked',note='All working directories in the local Codex task database were enumerated without an age limit. Working directories may include related worktrees; review possible duplicates. This does not cover other laptops.')
        out.append(row)
    if config.get('coworkSessionsFolder'):
        row={'source':'cowork-sessions','label':'Claude Cowork sessions on this laptop','context':context,'items':[],'status':'unavailable','note':'Cowork session directory unavailable.'}
        p=Path(config['coworkSessionsFolder']).expanduser()
        if p.is_dir():
            bad=0
            for f in sorted(p.glob('*/*/local_*.json')):
                try:
                    data=json.loads(f.read_text());title=data.get('title');ident=data.get('sessionId')
                    if not isinstance(title,str) or not title.strip() or not isinstance(ident,str):bad+=1;continue
                    if SECRET_PATTERN.search(title):bad+=1;continue
                    row['items'].append({'id':ident,'title':title[:180],
                        'note':'Cowork session metadata. '+('Archived in Claude; completion still needs your review.' if data.get('isArchived') else 'Completion has not been established.')})
                except (ValueError,OSError):bad+=1
            row.update(status='partial' if bad else 'checked',note=f'Enumerated local Cowork session metadata, including archived sessions. {bad} unreadable, untitled or excluded records. Sessions are shown individually for sorting; no conversation contents imported.')
        out.append(row)
    return out

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description='Enable read-only inventory metadata in an existing companion configuration.')
    parser.add_argument('--config',required=True)
    parser.add_argument('--context',choices=['work','personal'],required=True)
    parser.add_argument('--cowork-sessions',default='')
    args=parser.parse_args();p=Path(args.config).expanduser()
    config=json.loads(p.read_text())
    if not config.get('codexDb'):raise SystemExit('Set codexDb to the verified local Codex database first.')
    config.update(inventoryAllCodex=True,inventoryContext=args.context)
    if args.cowork_sessions:config['coworkSessionsFolder']=str(Path(args.cowork_sessions).expanduser())
    p.write_text(json.dumps(config,indent=2));p.chmod(0o600)
    print('Inventory enabled for the next manual companion run. No scheduler or browser extension was installed.')

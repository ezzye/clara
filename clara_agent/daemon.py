"""One bounded cycle per launch. OS scheduler retries; no busy polling or UI popups."""
import argparse,json,os,sys,time,urllib.request,urllib.error,getpass
from pathlib import Path
from datetime import datetime
from apps.api.domain import TZ
from .collectors import collect
from .inventory import snapshots
from .brains import codex_rank, codex_drafts

def reserve_attempt(config_path,kind):
    """Charge failures as well as successes; at most eight model calls per day."""
    budget_file=Path(config_path).with_suffix('.attempts.json')
    budget=json.loads(budget_file.read_text()) if budget_file.exists() else {}
    day=datetime.now(TZ).date().isoformat()
    count=budget.get('count',0) if budget.get('date')==day else 0
    previous=budget.get('lastAttempts',{})
    last=previous.get(kind,budget.get('lastAttempt',0) if kind=='ranking' else 0)
    if time.time()-last<3600 or count>=8:return False
    previous[kind]=time.time()
    budget_file.write_text(json.dumps({'date':day,'count':count+1,'lastAttempts':previous}))
    budget_file.chmod(0o600)
    return True

def request(url,token,data=None):
    req=urllib.request.Request(url,data=json.dumps(data).encode() if data is not None else None,
        headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=30) as response:return json.load(response)

def cycle(config_path):
    import keyring
    config=json.loads(Path(config_path).read_text())
    endpoint=config['endpoint'].rstrip('/')
    if not endpoint.startswith('https://'):raise ValueError('The companion requires HTTPS')
    token=keyring.get_password('clara-device',config['deviceId'])
    if not token:raise RuntimeError('Pair this laptop first')
    # Check revocation and pause before inspecting any local source.
    heartbeat=request(endpoint+'/api/ingest',token,{'evidence':[]})
    if heartbeat.get('paused'):return {'paused':True}
    result=request(endpoint+'/api/ingest',token,{'evidence':collect(config),'inventory':snapshots(config)})
    if config.get('planner'):
        # Drafts get only eligible message captures, never full activity history.
        try:
            context=request(endpoint+'/api/draft-context',token)
            if context.get('evidence') and reserve_attempt(config_path,'drafts'):
                drafts=codex_drafts(context['evidence'],config.get('codexModel'),config.get('codexExecutable','codex'))
                accepted=request(endpoint+'/api/drafts',token,{'revision':context['revision'],'drafts':drafts})
                result['drafts']=accepted['drafts']
        except Exception:
            result['draftsUnavailable']=True
        context=request(endpoint+'/api/device-context',token)
        if context.get('canPropose') and context.get('tasks'):
            if not reserve_attempt(config_path,'ranking'):return {**result,'rankingBudgetReached':True}
            proposal=codex_rank(context['tasks'],context['energy'],config.get('codexModel'),config.get('codexExecutable','codex'))
            request(endpoint+'/api/proposal',token,{'revision':context['revision'],**proposal})
            result['ranked']=True
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--pair',action='store_true');a=p.parse_args()
    if a.pair:
        import keyring
        config=json.loads(Path(a.config).read_text());token=getpass.getpass('One-time Clara pairing key: ')
        keyring.set_password('clara-device',config['deviceId'],token);print('Paired securely.');return
    # A directory lock prevents overlapping Codex runs and duplicate polling.
    lock=Path(a.config).with_suffix('.lock')
    if lock.exists() and time.time()-lock.stat().st_mtime>900:lock.rmdir()
    try:lock.mkdir()
    except FileExistsError:return
    try:
        result=cycle(a.config);print(json.dumps({'ok':True,**result}))
    except Exception as e:
        # Do not leak filenames, tokens or provider responses into scheduler logs.
        print(json.dumps({'ok':False,'error':type(e).__name__,'message':'Cycle failed; existing plan retained. Check connection and setup.'}));sys.exit(1)
    finally:lock.rmdir()
if __name__=='__main__':main()

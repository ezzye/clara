import hashlib, hmac, json, os, secrets
from datetime import datetime, timedelta
from .domain import *
from .storage import Store, Conflict

def digest(token): return hashlib.sha256(token.encode()).hexdigest()

def action(store,body):
    state=store.read();expected=body.get('revision')
    if expected!=state['revision']:raise Conflict('Your plan changed on another device. Please refresh.')
    name=body.get('action');data=body.get('data',{});extra={}
    if name=='addTask':state['tasks'].append(task_from(data))
    elif name=='editTask':
        old=next(t for t in state['tasks'] if t['id']==data.get('id'))
        updated=task_from({**old,**data});updated['status']=old['status'];old.update(updated)
    elif name=='taskStatus':
        if data.get('status') not in ['open','done','parked']:raise ValueError('Unknown status')
        t=next(t for t in state['tasks'] if t['id']==data['id']);t['status']=data['status']
        if t['status']=='done':
            for b in state['plan']:
                if b.get('taskId')==t['id'] and b['status']=='planned':b['status']='skipped'
    elif name=='addEvent':state['events'].append(event_from(data))
    elif name=='saveMeeting':
        e=next(e for e in state['events'] if e['id']==data['id'])
        e['notes']=text(data.get('notes',''),2000);e['confirmed']=True
    elif name=='addGoal':state['goals'].append(goal_from(data))
    elif name=='goalStatus':
        g=next(g for g in state['goals'] if g['id']==data['id']);g['status']='done' if data.get('done') else 'open'
    elif name=='settings':
        s=state['settings']
        if 'paused' in data:s['paused']=bool(data['paused'])
        if 'energy' in data:
            if data['energy'] not in ['low','steady','high']:raise ValueError('Unknown energy level')
            s['energy']=data['energy']
        for key,lo,hi in [('focusMinutes',5,60),('dayStart',0,1439),('dayEnd',1,1440),('bufferMinutes',5,60),('maxPriorities',1,5)]:
            if key in data:s[key]=integer(data[key],lo,hi)
        if s['dayStart']>=s['dayEnd']:raise ValueError('End time must be after start time')
    elif name=='plan':
        if state['settings']['paused']:raise ValueError('Resume planning first')
        plan,warnings=propose_plan(state,valid_date(data['date']),integer(data.get('days',1),1,7),state['planner'].get('orderedTaskIds'))
        state['plan']=plan;state['planner']={**state['planner'],'lastRun':now(),'message':' '.join(warnings) or state['planner'].get('reason') or 'A manageable plan, with breathing room. You can change any block.'}
    elif name=='block':
        b=next(b for b in state['plan'] if b['id']==data['id'])
        if 'locked' in data:b['locked']=bool(data['locked'])
        if 'start' in data:
            start=integer(data['start'],0,1439)
            candidate={**b,'start':start}
            if start+b['minutes']>1440 or any(overlaps(candidate,x) for x in state['plan'] if x['date']==b['date'] and x['id']!=b['id']):raise ValueError('That time overlaps another block')
            b['start']=start;b['locked']=True
        if data.get('status') in ['planned','active','done','skipped']:
            if data['status']=='active':
                for other in state['plan']:
                    if other['status']=='active':other['status']='planned';other.pop('startedAt',None)
                b['startedAt']=now()
            b['status']=data['status']
            if b['status']=='done':
                b['finishedAt']=now();b['actualMinutes']=integer(data.get('actualMinutes',b['minutes']),0,1440)
                b['completionNote']=text(data.get('note','Focus session completed; task outcome still needs review.'),500)
    elif name=='addEvidence':state['evidence'].append(evidence_from(data,'manual'))
    elif name=='reviewEvidence':
        e=next(e for e in state['evidence'] if e['id']==data['id'])
        if data.get('status') not in ['confirmed','dismissed']:raise ValueError('Unknown evidence review')
        e['status']=data['status']
    elif name=='pairDevice':
        token=secrets.token_urlsafe(40);device={'id':uid(),'name':text(data['name'],80),'os':text(data.get('os',''),40),
            'tokenHash':digest(token),'planner':bool(data.get('planner',False)),'lastSeen':None,'revoked':False,'createdAt':now()}
        state['devices'].append(device);extra={'deviceToken':token,'deviceId':device['id']}
    elif name=='revokeDevice':next(d for d in state['devices'] if d['id']==data['id'])['revoked']=True
    elif name=='purgeEvidence':state['evidence']=[]
    else:raise ValueError('Unknown action')
    state['audit']=(state['audit']+[{'at':now(),'action':name,'actor':'owner'}])[-100:]
    store.write(state,expected)
    return {'state':public_state(state),**extra}

def ingest(store,token,body):
    for retry in range(3):
        state=store.read();old=state['revision']
        device=next((d for d in state['devices'] if not d['revoked'] and hmac.compare_digest(d['tokenHash'],digest(token))),None)
        if not device:raise PermissionError('Device is not paired')
        if state['settings']['paused']:return {'paused':True,'accepted':0}
        items=body.get('evidence',[])
        if not isinstance(items,list) or len(items)>100:raise ValueError('At most 100 evidence items per batch')
        known={e['id'] for e in state['evidence']};accepted=0
        for item in items:
            e=evidence_from(item,device['id'])
            if e['id'] not in known:state['evidence'].append(e);known.add(e['id']);accepted+=1
        cutoff=(datetime.now(TZ)-timedelta(days=30)).isoformat()
        state['evidence']=[e for e in state['evidence'] if e['observedAt']>=cutoff][-300:]
        device['lastSeen']=now()
        try:store.write(state,old);return {'accepted':accepted,'paused':False}
        except Conflict:
            if retry==2:raise

def dispatch(store,path,method,body,owner=False,device_token=''):
    if path=='/api/ingest' and method=='POST':return ingest(store,device_token,body)
    if path in ['/api/device-context','/api/proposal']:
        return device_planning(store,device_token,body,method,path)
    if not owner:raise PermissionError('Sign in to your private space')
    if path=='/api/state' and method=='GET':return public_state(store.read())
    if path=='/api/action' and method=='POST':return action(store,body)
    raise ValueError('Unknown route')


def device_planning(store,token,body,method,path):
    state=store.read()
    device=next((d for d in state['devices'] if not d['revoked'] and d.get('planner') and hmac.compare_digest(d['tokenHash'],digest(token))),None)
    if not device:raise PermissionError('This laptop has no planning permission')
    if state['settings']['paused']:raise PermissionError('Planning is paused')
    last=state['planner'].get('rankedAt')
    recent=last and (datetime.now(TZ)-datetime.fromisoformat(last)).total_seconds()<3600
    daily=state['planner'].get('rankingsToday',{})
    day=datetime.now(TZ).date().isoformat()
    spent=daily.get('count',0) if daily.get('date')==day else 0
    recent=recent or spent>=8
    tasks=[{k:t[k] for k in ['id','title','nextStep','doneWhen','priority','due']} for t in state['tasks'] if t['status']=='open'][:30]
    if path=='/api/device-context' and method=='GET':
        return {'revision':state['revision'],'tasks':tasks,'energy':state['settings']['energy'],'canPropose':not bool(recent)}
    if path!='/api/proposal' or method!='POST':raise ValueError('Invalid planner request')
    if recent:raise ValueError('An hourly ranking already exists')
    if body.get('revision')!=state['revision']:raise Conflict('Context changed; proposal discarded')
    ids=body.get('orderedTaskIds',[]);known={t['id'] for t in tasks}
    if not isinstance(ids,list) or any(not isinstance(i,str) or i not in known for i in ids) or len(ids)!=len(set(ids)):raise ValueError('Invalid task ranking')
    reason=text(body.get('reason',''),500)
    if SECRET_PATTERN.search(reason):raise ValueError('Explanation contains excluded material')
    state['planner']={**state['planner'],'mode':'codex','orderedTaskIds':ids,'reason':reason,'rankedAt':now(),'message':reason,'rankingsToday':{'date':day,'count':spent+1}}
    store.write(state,state['revision'])
    return {'accepted':True,'note':'Order saved for the next plan; protected time and task completion were not changed.'}

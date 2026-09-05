"""Durable source inventory, separate from actionable tasks and activity evidence."""
from .domain import text, integer, now, SECRET_PATTERN
from .rhythm import task_context

def merge_snapshot(state, snapshot, device_id='owner'):
    source=text(snapshot.get('source',''),160)
    label=text(snapshot.get('label',''),180)
    context=snapshot.get('context','personal')
    if not source or context not in ('work','personal'):raise ValueError('Invalid inventory source')
    entries=snapshot.get('items',[])
    if not isinstance(entries,list) or len(entries)>1000:raise ValueError('Inventory snapshot too large')
    key=device_id+':'+source
    projects=state['projects'];seen=set()
    for item in entries:
        ident=text(item.get('id',''),180);title=text(item.get('title',''),180)
        if not ident or not title or ident in seen:raise ValueError('Invalid or duplicate inventory identity')
        seen.add(ident)
        if SECRET_PATTERN.search(title):raise ValueError('Excluded material in inventory title')
        # Identity is scoped to its originating source/device, never a fuzzy title match.
        existing=next((p for p in projects if p.get('inventoryKey')==key+':'+ident),None)
        path=text(item.get('path',''),1000)
        if not existing and path:
            existing=next((p for p in projects if p.get('path')==path and p.get('inventoryDevice',device_id)==device_id),None)
        if not existing:
            import hashlib
            existing={'id':hashlib.sha256((key+':'+ident).encode()).hexdigest()[:24],
                      'title':title,'context':context,'priority':2,'stage':'needs_review','outcome':'',
                      'nextStep':'Choose the next useful outcome, or mark this item finished or parked.',
                      'doneWhen':'','source':label,'inventoryKey':key+':'+ident}
            projects.append(existing)
        existing.update(inventoryDevice=device_id,lastSeenAt=now())
        origins=existing.setdefault('inventoryOrigins',[])
        if key not in origins:origins.append(key)
        if path:existing['path']=path
        existing['sourceNote']=text(item.get('note','Completion has not been established.'),600)
        # A refreshed source must never undo the owner's sorting, priority or completion.
    coverage=state.setdefault('inventorySources',[])
    row=next((r for r in coverage if r['id']==key),None)
    status=snapshot.get('status','partial')
    if status not in ('checked','partial','unavailable','not_connected'):raise ValueError('Invalid coverage status')
    data={'id':key,'label':label,'context':context,'status':status,'checkedAt':now(),
          'count':len(entries),'note':text(snapshot.get('note',''),800)}
    if row:row.update(data)
    else:coverage.append(data)

def review_project(state,data):
    p=next(p for p in state['projects'] if p['id']==data.get('id'))
    if 'context' in data:
        if data['context'] not in ('work','personal'):raise ValueError('Choose Work or Home')
        p['context']=data['context']
        for t in state['tasks']:
            if t.get('projectId')==p['id'] and t['status']!='done':move_task(state,t,data['context'])
    if 'priority' in data:
        p['priority']=integer(data['priority'],1,3)
        for t in state['tasks']:
            if t.get('projectId')==p['id'] and t['status']!='done':t['priority']=p['priority']
    if 'stage' in data:
        if data['stage'] not in ('needs_review','active','parked','delivered'):raise ValueError('Invalid inventory state')
        if data['stage']=='delivered':
            note=text(data.get('proof',''),1000)
            if len(note)<10:raise ValueError('Record what is finished and how you checked it')
            if any(t.get('projectId')==p['id'] and t['status']!='done' for t in state['tasks']):raise ValueError('Review unfinished linked tasks before marking the project finished')
            p['proof']=note;p['deliveredAt']=now()
        p['stage']=data['stage']
        if data['stage']=='parked':
            linked={t['id'] for t in state['tasks'] if t.get('projectId')==p['id'] and t['status']!='done'}
            for t in state['tasks']:
                if t['id'] in linked:t['status']='parked'
            state['plan']=[b for b in state['plan'] if b.get('taskId') not in linked or b['status'] in ('active','done','skipped')]
    p['reviewedAt']=now()

def move_task(state,task,context):
    if context not in ('work','personal'):raise ValueError('Choose Work or Home')
    task['context']=context;task['allowPersonalTime']=False
    # Owner reclassification releases future work in the old time context.
    state['plan']=[b for b in state['plan'] if b.get('taskId')!=task['id'] or b['status'] in ('active','done','skipped')]

def rows(state):
    result=[]
    coverage={r['id']:r for r in state.get('backlog',[])}
    for t in state['tasks']:
        r=coverage.get(t['id'],{})
        result.append({'id':t['id'],'kind':'task','title':t['title'],'context':task_context(t),'priority':t['priority'],
                       'status':t['status'],'source':t['source'],'detail':t['nextStep'],'date':t.get('due',''),
                       'coverage':r.get('coverage',''),'projectId':t.get('projectId','')})
    for p in state['projects']:
        result.append({'id':p['id'],'kind':'project','title':p['title'],'context':p.get('context','personal'),
                       'priority':p.get('priority',2),'status':p.get('stage','needs_review'),'source':p.get('source','Project inventory'),
                       'detail':p.get('sourceNote') or p.get('outcome',''),'date':'',
                       'linkedTasks':sum(t.get('projectId')==p['id'] and t['status']!='done' for t in state['tasks'])})
    for e in state['events']:
        result.append({'id':e['id'],'kind':'meeting','title':e['title'],'context':e.get('context','work'),
                       'priority':2,'status':e.get('status','scheduled'),'source':e['source'],
                       'detail':e.get('notes',''),'date':'' if e.get('status')=='needs_confirmation' else e['date'],'start':e['start'],'minutes':e['minutes'],
                       'confirmed':e.get('confirmed',False)})
    return result

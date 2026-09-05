"""Explain coverage and ranking independently of any model's narrative."""
from datetime import datetime, date
from zoneinfo import ZoneInfo
TZ=ZoneInfo('Europe/London')

def reservation(block,current):
    if block.get('status')=='active':return True
    if block.get('status')!='planned':return False
    return block['date']>current.date().isoformat() or (block['date']==current.date().isoformat() and block['start']+block['minutes']>current.hour*60+current.minute)

def score_task(task,ranked_ids,current):
    factors=[{'label':'Your priority','points':task['priority']*10}]
    if task.get('due'):
        days=(date.fromisoformat(task['due'])-current.date()).days
        if days<=7:factors.append({'label':'Overdue' if days<0 else 'Deadline approaching','points':45 if days<0 else 40 if days<=2 else 25})
    if task['category']=='prep':factors.append({'label':'Preparation','points':20})
    if task['category']=='project':factors.append({'label':'Project finishing','points':5})
    if task['id'] in ranked_ids:
        factors.append({'label':'Clara recommendation','points':max(1,15-ranked_ids.index(task['id']))})
    return {'score':sum(f['points'] for f in factors),'factors':factors}

def explain(state,current=None):
    current=current or datetime.now(TZ)
    ranking=state['planner'].get('orderedTaskIds',[])
    last=state['planner'].get('lastConsidered',{})
    rows=[]
    for task in state['tasks']:
        if task['status']=='done':continue
        blocks=[b for b in state['plan'] if b.get('taskId')==task['id'] and reservation(b,current)]
        reserved=sum(b['minutes'] for b in blocks)
        state_label='parked' if task['status']=='parked' else 'scheduled' if reserved>=task['minutes'] else 'partial' if reserved else 'unscheduled'
        last_item=next((r for r in last.get('tasks',[]) if r['id']==task['id']),None)
        rows.append({'id':task['id'],**score_task(task,ranking,current),'coverage':state_label,
                     'reservedMinutes':reserved,'remainingMinutes':max(0,task['minutes']-reserved),
                     'reservations':[{'date':b['date'],'start':b['start'],'minutes':b['minutes']} for b in blocks],
                     'lastDecision':last_item['reason'] if last_item else 'Not present in the last planning pass.',
                     'modelConsidered':task['id'] in state['planner']['modelConsideredIds'] if 'modelConsideredIds' in state['planner'] else None,
                     'consideredAt':last.get('at') if last_item else None})
    return sorted(rows,key=lambda r:(r['coverage']=='parked',-r['score'],r['id']))

def record_pass(state,plan,day,days,current=None):
    current=current or datetime.now(TZ)
    from datetime import timedelta
    dates={(date.fromisoformat(day)+timedelta(days=i)).isoformat() for i in range(days)}
    tasks=[]
    for task in state['tasks']:
        if task['status']=='done':continue
        selected=[b for b in plan if b.get('taskId')==task['id'] and b['date'] in dates and reservation(b,current)]
        reserved=sum(b['minutes'] for b in plan if b.get('taskId')==task['id'] and reservation(b,current))
        if task['status']=='parked':reason='Parked by you; excluded from scheduling.'
        elif selected:reason='Time reserved in this planning window.'
        elif reserved>=task['minutes']:reason='Already has time reserved outside this window.'
        elif any(b.get('taskId')==task['id'] and b['date'] in dates and b['status']=='done' for b in plan):reason='A session already finished in this window; task completion still needs review.'
        else:reason='Considered, but no further slot was chosen within the available time and daily priority limit.'
        tasks.append({'id':task['id'],'reason':reason,**score_task(task,state['planner'].get('orderedTaskIds',[]),current)})
    return {'at':current.isoformat(),'date':day,'days':days,'tasks':tasks,'openCount':sum(t['status']=='open' for t in state['tasks'])}

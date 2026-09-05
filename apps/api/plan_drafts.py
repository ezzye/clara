"""Validate an agent's concrete draft against known tasks, commitments and rhythm."""
from datetime import datetime
from .domain import TZ, text, integer, valid_date, uid, overlaps, now, reserve_appointments
from .rhythm import windows, task_context, active_event
from .backlog import record_pass, reservation


def apply_draft(state, data, current=None):
    current=current or datetime.now(TZ)
    days=data.get('dates',[])
    if not isinstance(days,list) or not 1<=len(days)<=7:raise ValueError('Draft covers one to seven days')
    days=sorted(set(valid_date(d) for d in days))
    if days[0]<current.date().isoformat():raise ValueError('A draft cannot schedule the past')
    entries=data.get('blocks',[])
    if not isinstance(entries,list) or len(entries)>40:raise ValueError('Draft is too large')
    tasks={t['id']:t for t in state['tasks'] if t['status']=='open'}
    inactive={e['id'] for e in state['events'] if not active_event(e)}
    keep=[dict(b) for b in state['plan'] if (b['date'] not in days or b.get('locked') or b['status'] in ('active','done'))
          and (b.get('eventId') not in inactive or b['status'] in ('active','done'))]
    # Protect appointments first. Agent drafts never invent or move a meeting.
    for e in state['events']:
        if active_event(e) and e['date'] in days and not any(b.get('eventId')==e['id'] and b['kind']=='event' for b in keep):
            keep.append({'id':uid(),'eventId':e['id'],'date':e['date'],'start':e['start'],'minutes':e['minutes'],
                         'title':e['title'],'kind':'event','locked':True,'status':'planned','reason':'Fixed calendar commitment.'})
    used={}
    for b in keep:
        if b.get('taskId') in tasks and reservation(b,current):used[b['taskId']]=used.get(b['taskId'],0)+b['minutes']
    for entry in entries:
        task=tasks.get(entry.get('taskId'))
        if not task:raise ValueError('Draft references an unknown or closed task')
        day=valid_date(entry['date']);start=integer(entry.get('start'),0,1439);minutes=integer(entry.get('minutes'),5,120)
        if day not in days or start+minutes>1440:raise ValueError('Invalid draft time')
        if day==current.date().isoformat() and start<current.hour*60+current.minute:raise ValueError('Draft block is in the past')
        context=task_context(task)
        allowed=windows(state['settings'],day,context)
        if task.get('allowPersonalTime'):allowed+=windows(state['settings'],day,'personal')
        if not any(a<=start and start+minutes<=b for a,b in allowed):raise ValueError('Draft conflicts with work/personal time boundaries')
        used[task['id']]=used.get(task['id'],0)+minutes
        if used[task['id']]>task['minutes']:raise ValueError('Draft exceeds the remaining task estimate')
        block={'id':uid(),'taskId':task['id'],'date':day,'start':start,'minutes':minutes,'title':task['title'],
               'kind':task['category'],'eventId':task.get('eventId',''),'context':context,'draft':True,'locked':False,'status':'planned',
               'reason':text(entry.get('reason',''),800)}
        if any(b['date']==day and b['status']!='skipped' and overlaps(block,b) for b in keep):raise ValueError('Draft overlaps a protected commitment')
        keep.append(block)
    warnings=reserve_appointments(state,keep,days,current)
    state['plan']=sorted(keep,key=lambda b:(b['date'],b['start']))
    state['planner'].update(draftBrief=text(data.get('brief',''),2000),draftAssumptions=[text(v,400) for v in data.get('assumptions',[])][:12],
                            draftCreatedAt=now(),lastRun=now(),message='Agent draft ready to edit. '+' '.join(warnings),
                            lastConsidered=record_pass(state,keep,days[0],len(days),current))

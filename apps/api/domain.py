"""Planning rules constrain model suggestions; evidence never becomes a verdict."""
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from uuid import uuid4
import copy
import re
from urllib.parse import urlsplit
from .backlog import score_task, reservation, explain
from .rhythm import windows, task_context, active_event

TZ = ZoneInfo('Europe/London')

def now():
    return datetime.now(TZ).isoformat()

def uid():
    return uuid4().hex

def initial_state():
    return {'revision': 0, 'tasks': [], 'events': [], 'plan': [], 'evidence': [],
            'projects': [], 'goals': [], 'devices': [], 'audit': [],
            'settings': {'paused': False, 'energy': 'steady', 'dayStart': 9*60,
                         'dayEnd': 17*60, 'focusMinutes': 25, 'bufferMinutes': 10,
                         'maxPriorities': 3, 'timezone': 'Europe/London'},
            'planner': {'mode': 'rules', 'lastRun': None, 'message': 'Ready to make a gentle first plan.'}}

def text(value, maximum=500):
    if not isinstance(value, str) or len(value) > maximum:
        raise ValueError('Text is missing or too long')
    return value.strip()

def integer(value, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError('Number is outside the allowed range')
    return value

def valid_date(value):
    date.fromisoformat(value)
    return value

def task_from(data):
    title = text(data.get('title', ''), 180)
    if not title:
        raise ValueError('Give the task a name')
    category = data.get('category', 'project')
    if category not in ['project', 'prep', 'personal', 'development']:
        raise ValueError('Unknown task category')
    context=data.get('context') or ('work' if category in ('prep','development') else 'personal')
    if context not in ('work','personal'):raise ValueError('Choose work or personal time')
    return {'id': data.get('id') or uid(), 'title': title, 'category': category, 'context':context,
            'minutes': integer(data.get('minutes',25), 5, 480),
            'priority': integer(data.get('priority',2),1,3),
            'nextStep': text(data.get('nextStep','Open the relevant material and choose one small step.')),
            'doneWhen': text(data.get('doneWhen','Record what changed and the next step.')),
            'projectId': text(data.get('projectId',''),100),
            'lifeArea': text(data.get('lifeArea',''),30),
            'eventId':text(data.get('eventId',''),100),'allowPersonalTime':data.get('allowPersonalTime') is True,
            'due': valid_date(data['due']) if data.get('due') else '',
            'status': 'open', 'source': text(data.get('source','You'),500),
            'createdAt': now()}

def event_from(data):
    start=integer(data.get('start'),0,1439)
    minutes=integer(data.get('minutes',60),5,720)
    if start+minutes>1440: raise ValueError('Split events spanning midnight into two entries')
    prep=integer(data.get('prepMinutes',20),0,120)
    if data.get('context','work') not in ('work','personal'):raise ValueError('Choose work or personal time')
    return {'id':uid(),'title':text(data.get('title',''),180),
            'date':valid_date(data['date']),'start':start,'minutes':minutes,
            'context':data.get('context','work'),'prepMinutes':prep,'source':text(data.get('source','You'),500),
            'notes':text(data.get('notes',''),2000),'confirmed':bool(data.get('confirmed',False))}

def goal_from(data):
    horizon=data.get('horizon','month')
    if horizon not in ['week','month','year']: raise ValueError('Unknown horizon')
    return {'id':uid(),'title':text(data.get('title',''),180),
            'outcome':text(data.get('outcome',''),1000),'horizon':horizon,
            'due':valid_date(data['due']) if data.get('due') else '', 'status':'open'}

def overlaps(a,b):
    return a['start'] < b['start']+b['minutes'] and b['start'] < a['start']+a['minutes']

def propose_plan(state, day, days=1, ranked_ids=None, current=None):
    """Return a new plan. Locked, started and completed blocks always survive."""
    current=current or datetime.now(TZ)
    first=date.fromisoformat(day)
    dates=[(first+timedelta(days=i)).isoformat() for i in range(days)]
    settings=state['settings']
    inactive={e['id'] for e in state['events'] if not active_event(e)}
    keep=[copy.deepcopy(b) for b in state['plan'] if b['date'] not in dates or b.get('locked') or (b.get('draft') and reservation(b,current)) or b.get('status') in ['active','done','skipped']]
    keep=[b for b in keep if b.get('eventId') not in inactive or b['status'] in ('active','done')]
    tasks=[t for t in state['tasks'] if t['status']=='open']
    tasks.sort(key=lambda t:(-score_task(t,ranked_ids or [],current)['score'],t['due'] or '9999',t['createdAt']))
    remaining={t['id']:t['minutes'] for t in tasks}
    for b in keep:
        if b.get('taskId') in remaining and reservation(b,current):
            remaining[b['taskId']]=max(0,remaining[b['taskId']]-b['minutes'])
    warnings=reserve_appointments(state,keep,dates,current)
    for d in dates:
        occupied=[b for b in keep if b['date']==d and b['status']!='skipped']
        if d<current.date().isoformat():continue
        quota=1 if settings['energy']=='low' else settings['maxPriorities']
        used_ids={b['taskId'] for b in occupied if b.get('taskId') and (b['status']=='done' or reservation(b,current))}
        contexts=('work','personal') if settings.get('weeklyRhythm') else ('all',)
        for context in contexts:
            used=sum(1 for ident in used_ids if context=='all' or any(t['id']==ident and task_context(t)==context for t in tasks))
            for task in tasks:
                if used>=quota:break
                if context!='all' and task_context(task)!=context:continue
                if task['id'] in used_ids or remaining[task['id']]<=0:continue
                duration=min(remaining[task['id']],settings['focusMinutes'])
                placed=False
                for start,end in windows(settings,d,task_context(task)):
                    cursor=start
                    if d==current.date().isoformat():cursor=max(cursor,((current.hour*60+current.minute+4)//5)*5)
                    while cursor+duration<=end:
                        candidate={'start':cursor,'minutes':duration}
                        collisions=[x for x in occupied if overlaps(candidate,x)]
                        if collisions:
                            cursor=max(x['start']+x['minutes']+settings['bufferMinutes'] for x in collisions);continue
                        b={'id':uid(),'date':d,'start':cursor,'minutes':duration,'title':task['title'],
                           'taskId':task['id'],'kind':task['category'],'context':task_context(task),'locked':False,'status':'planned',
                           'reason':task['nextStep']+' Finish line: '+task['doneWhen']}
                        keep.append(b);occupied.append(b);remaining[task['id']]-=duration;used+=1;used_ids.add(task['id'])
                        br={'id':uid(),'date':d,'start':cursor+duration,'minutes':settings['bufferMinutes'],
                            'title':'Step away & reset','kind':'break','locked':False,'status':'planned','reason':'Leave space between tasks.'}
                        if br['start']+br['minutes']<=end and not any(overlaps(br,x) for x in occupied):keep.append(br);occupied.append(br)
                        placed=True;break
                    if placed:break
    return sorted(keep,key=lambda b:(b['date'],b['start'])), warnings

def reserve_appointments(state,keep,dates,current):
    """Fill calendar and prep gaps without moving the existing task plan."""
    settings=state['settings']
    warnings=[]
    # Reserve every appointment before looking for preparation. This prevents
    # an earlier event's prep slot from stealing a later event's protected time.
    events=[e for e in state['events'] if e['date'] in dates and active_event(e)]
    for event in sorted(events,key=lambda e:(e['date'],e['start'])):
        existing=next((b for b in keep if b.get('eventId')==event['id'] and b['kind']=='event'),None)
        b={'id':uid(),'eventId':event['id'],'date':event['date'],'start':event['start'],
           'minutes':event['minutes'],'title':event['title'],'kind':'event','locked':True,
           'status':'planned','source':event['source'],'reason':'Protected appointment. Attendance is not yet confirmed.'}
        if not existing:
            if any(x['date']==b['date'] and overlaps(b,x) for x in keep):
                warnings.append('An appointment overlaps a protected block on '+b['date']+'. Please review it.')
            keep.append(b)
    for event in sorted(events,key=lambda e:(e['date'],e['start'])):
        if not event['prepMinutes'] or event.get('prepared'):continue
        if (event['date'],event['start']) <= (current.date().isoformat(),current.hour*60+current.minute):continue
        existing=[b for b in keep if b.get('eventId')==event['id'] and b['kind']=='prep']
        if existing:
            # Completed or skipped preparation requires owner review, not a
            # duplicate block. Protected prep is never silently moved.
            if not any(b['status'] in ('planned','active') and
                       (b['date'],b['start']+b['minutes']) > (current.date().isoformat(),current.hour*60+current.minute)
                       for b in existing):
                warnings.append('Review preparation readiness for '+event['title'])
            continue
        placed=False
        # Prefer immediately before the meeting, then earlier gaps and previous
        # days in the requested planning window. Never schedule prep in the past.
        for d in reversed([d for d in dates if current.date().isoformat()<=d<=event['date']]):
            for lower,limit in reversed(windows(settings,d,event.get('context','work'))):
                if d==current.date().isoformat():lower=max(lower,((current.hour*60+current.minute+4)//5)*5)
                upper=min(limit,event['start']-10) if d==event['date'] else limit
                cursor=upper-event['prepMinutes']
                occupied=[b for b in keep if b['date']==d and b['status']!='skipped']
                while cursor>=lower:
                    prep={'id':uid(),'eventId':event['id'],'date':d,'start':cursor,
                          'minutes':event['prepMinutes'],'title':'Prepare: '+event['title'],'kind':'prep','locked':False,
                          'status':'planned','context':event.get('context','work'),'reason':'Review the specific agenda, decisions and questions before this appointment.'}
                    collisions=[x for x in occupied if overlaps(prep,x)]
                    if collisions:
                        cursor=min(x['start'] for x in collisions)-settings['bufferMinutes']-event['prepMinutes'];continue
                    keep.append(prep);placed=True;break
                if placed:break
            if placed:break
        if not placed:warnings.append('Preparation needs another slot for '+event['title'])
    return warnings

SECRET_PATTERN=re.compile(r'one.time|passcode|password|verification code|secure key|otp\b|api.?key|secret|bearer|sk-[a-zA-Z0-9]',re.I)

def evidence_from(data,device):
    source=text(data.get('source',''),40)
    if source not in ['codex','cowork','downloads','git','gmail','chrome','whatsapp','nhs','manual']:raise ValueError('Unknown evidence source')
    summary=text(data.get('summary',''),800)
    if SECRET_PATTERN.search(summary):raise ValueError('Authentication material is excluded')
    when=datetime.fromisoformat(data['observedAt'])
    if when.tzinfo is None:raise ValueError('Evidence requires a timezone')
    if when>datetime.now(TZ)+timedelta(minutes=5):raise ValueError('Evidence timestamp is in the future')
    source_url=text(data.get('sourceUrl',''),1000)
    if source_url:
        parsed=urlsplit(source_url)
        if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError('Source link must be HTTPS without embedded credentials')
        source_url=parsed._replace(query='',fragment='').geturl()
    return {'id':text(data.get('id',uid()),100),'source':source,'deviceId':device,
            'summary':summary,'observedAt':when.isoformat(),'taskId':text(data.get('taskId',''),100),
            'confidence':data.get('confidence','low') if data.get('confidence') in ['low','medium','high'] else 'low',
            'sourceUrl':source_url,'classification':'private','status':'unreviewed'}

def public_state(state):
    s=copy.deepcopy(state)
    s['backlog']=explain(state)
    from .inventory import rows
    s['inventory']=rows(s)
    from .meetings import preparation
    for event in s['events']:event['preparation']=preparation(event,state['plan'])
    from .suggestions import source_context
    accepted={x.get('targetId'):x for x in state.get('suggestions',[]) if x.get('status')=='accepted'}
    for item in s['tasks']+s['events']:
        reference=item.get('sourceRef')
        legacy=accepted.get(item['id'])
        if not reference and legacy:reference={'id':legacy['evidenceId'],'hash':legacy['sourceHash']}
        item['sourceContext']=source_context(state,reference)
    for draft in s.get('suggestions',[]):
        draft['sourceContext']=source_context(state,{'id':draft['evidenceId'],'hash':draft['sourceHash']})
    for d in s['devices']:d.pop('tokenHash',None)
    return s

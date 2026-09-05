"""Planning rules constrain model suggestions; evidence never becomes a verdict."""
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from uuid import uuid4
import copy
import re
from urllib.parse import urlsplit
from .backlog import score_task, reservation, explain

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
    return {'id': data.get('id') or uid(), 'title': title, 'category': category,
            'minutes': integer(data.get('minutes',25), 5, 480),
            'priority': integer(data.get('priority',2),1,3),
            'nextStep': text(data.get('nextStep','Open the relevant material and choose one small step.')),
            'doneWhen': text(data.get('doneWhen','Record what changed and the next step.')),
            'projectId': text(data.get('projectId',''),100),
            'lifeArea': text(data.get('lifeArea',''),30),
            'due': valid_date(data['due']) if data.get('due') else '',
            'status': 'open', 'source': text(data.get('source','You'),500),
            'createdAt': now()}

def event_from(data):
    start=integer(data.get('start'),0,1439)
    minutes=integer(data.get('minutes',60),5,720)
    if start+minutes>1440: raise ValueError('Split events spanning midnight into two entries')
    prep=integer(data.get('prepMinutes',20),0,120)
    return {'id':uid(),'title':text(data.get('title',''),180),
            'date':valid_date(data['date']),'start':start,'minutes':minutes,
            'prepMinutes':prep,'source':text(data.get('source','You'),500),
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
    keep=[copy.deepcopy(b) for b in state['plan'] if b['date'] not in dates or b.get('locked') or b.get('status') in ['active','done','skipped']]
    tasks=[t for t in state['tasks'] if t['status']=='open']
    tasks.sort(key=lambda t:(-score_task(t,ranked_ids or [],current)['score'],t['due'] or '9999',t['createdAt']))
    remaining={t['id']:t['minutes'] for t in tasks}
    for b in keep:
        if b.get('taskId') in remaining and reservation(b,current):
            remaining[b['taskId']]=max(0,remaining[b['taskId']]-b['minutes'])
    warnings=[]
    for d in dates:
        occupied=[b for b in keep if b['date']==d]
        events=[e for e in state['events'] if e['date']==d]
        for event in sorted(events,key=lambda e:e['start']):
            existing=next((b for b in occupied if b.get('eventId')==event['id'] and b['kind']=='event'),None)
            b={'id':uid(),'eventId':event['id'],'date':d,'start':event['start'],
               'minutes':event['minutes'],'title':event['title'],'kind':'event','locked':True,
               'status':'planned','source':event['source'],'reason':'Protected appointment. Attendance is not yet confirmed.'}
            if not existing:
                if any(overlaps(b,x) for x in occupied): warnings.append('An appointment overlaps a protected block on '+d+'. Please review it.')
                keep.append(b);occupied.append(b)
            if event['prepMinutes']:
                prep={'id':uid(),'eventId':event['id'],'date':d,'start':max(0,event['start']-event['prepMinutes']-10),
                      'minutes':event['prepMinutes'],'title':'Prepare: '+event['title'],'kind':'prep','locked':False,
                      'status':'planned','reason':'Review the purpose, relevant material, decisions and questions before joining.'}
                if prep['start']+prep['minutes']<=event['start'] and not any(overlaps(prep,x) for x in occupied):
                    keep.append(prep);occupied.append(prep)
                else: warnings.append('Preparation needs another slot for '+event['title'])
        cursor=settings['dayStart']
        if d==current.date().isoformat(): cursor=max(cursor,((current.hour*60+current.minute+4)//5)*5)
        if d<current.date().isoformat(): continue
        quota=1 if settings['energy']=='low' else settings['maxPriorities']
        used_ids={b['taskId'] for b in occupied if b.get('taskId') and (b['status']=='done' or reservation(b,current))}
        used=len(used_ids)
        end=settings['dayEnd']
        for task in tasks:
            if used>=quota: break
            if task['id'] in used_ids:continue
            if remaining[task['id']]<=0: continue
            duration=min(remaining[task['id']],settings['focusMinutes'])
            previous_cursor=cursor
            while cursor+duration+5<=end:
                candidate={'start':cursor,'minutes':duration+5}
                collisions=[x for x in occupied if overlaps(candidate,x)]
                if collisions: cursor=max(x['start']+x['minutes']+settings['bufferMinutes'] for x in collisions);continue
                break
            if cursor+duration+5>end:
                cursor=previous_cursor
                continue
            b={'id':uid(),'date':d,'start':cursor,'minutes':duration,'title':task['title'],
               'taskId':task['id'],'kind':task['category'],'locked':False,'status':'planned',
               'reason':('A small finishing step. ' if task['category']=='project' else 'Protected time for what matters. ')+task['nextStep']}
            keep.append(b);occupied.append(b);remaining[task['id']]-=duration;used+=1
            cursor+=duration
            br={'id':uid(),'date':d,'start':cursor,'minutes':settings['bufferMinutes'],
                'title':'Step away & reset','kind':'break','locked':False,'status':'planned','reason':'Leave some space between tasks.'}
            if cursor+br['minutes']<=end and not any(overlaps(br,x) for x in occupied):keep.append(br);occupied.append(br)
            cursor+=settings['bufferMinutes']
    return sorted(keep,key=lambda b:(b['date'],b['start'])), warnings

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
    for d in s['devices']:d.pop('tokenHash',None)
    return s

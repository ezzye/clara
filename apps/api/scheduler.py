import copy
from datetime import datetime, timedelta
from .domain import propose_plan,now,TZ,reserve_appointments
from .storage import Conflict
from .backlog import record_pass

def scheduled(store):
    state=store.read()
    if state['settings']['paused']:return {'paused':True}
    if not state['tasks'] and not state['events']:return {'empty':True}
    rev=state['revision']
    # Keep the near-term plan stable. Only plan when the owner has no remaining
    # unstarted blocks; ingestion itself does not continuously shuffle the day.
    day=datetime.now(TZ).date().isoformat()
    current=datetime.now(TZ);minute=current.hour*60+current.minute
    future=any(b['date']==day and b['start']+b['minutes']>minute and b['kind'] not in ['break','event'] and b['status'] in ['planned','active'] for b in state['plan'])
    if future:
        before=copy.deepcopy(state['plan'])
        dates=[(current.date()+timedelta(days=i)).isoformat() for i in range(7)]
        warnings=reserve_appointments(state,state['plan'],dates,current)
        if state['plan']==before:return {'unchanged':True}
        state['plan'].sort(key=lambda b:(b['date'],b['start']))
        state['planner']={**state['planner'],'lastRun':now(),'message':' '.join(warnings) or 'Added preparation time around your existing plan.'}
        try:store.write(state,rev);return {'updated':True,'preparationOnly':True}
        except Conflict:return {'unchanged':True,'reason':'Owner was editing; skipped this cycle.'}
    state['plan'],warnings=propose_plan(state,day,ranked_ids=state['planner'].get('orderedTaskIds'))
    warnings+=reserve_appointments(state,state['plan'],[(current.date()+timedelta(days=i)).isoformat() for i in range(7)],current)
    state['plan'].sort(key=lambda b:(b['date'],b['start']))
    state['planner']={**state['planner'],'lastRun':now(),'lastConsidered':record_pass(state,state['plan'],day,1),'message':' '.join(warnings) or 'Refreshed quietly. Your protected blocks stayed in place.'}
    try:store.write(state,rev);return {'updated':True}
    except Conflict:return {'unchanged':True,'reason':'Owner was editing; skipped this cycle.'}

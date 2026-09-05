from datetime import datetime
from .domain import propose_plan,now,TZ
from .storage import Conflict
from .backlog import record_pass

def scheduled(store):
    state=store.read()
    if state['settings']['paused']:return {'paused':True}
    if not state['tasks']:return {'empty':True}
    rev=state['revision']
    # Keep the near-term plan stable. Only plan when the owner has no remaining
    # unstarted blocks; ingestion itself does not continuously shuffle the day.
    day=datetime.now(TZ).date().isoformat()
    current=datetime.now(TZ);minute=current.hour*60+current.minute
    future=any(b['date']==day and b['start']+b['minutes']>minute and b['kind'] not in ['break','event'] and b['status'] in ['planned','active'] for b in state['plan'])
    if future:return {'unchanged':True}
    state['plan'],warnings=propose_plan(state,day,ranked_ids=state['planner'].get('orderedTaskIds'))
    state['planner']={**state['planner'],'lastRun':now(),'lastConsidered':record_pass(state,state['plan'],day,1),'message':' '.join(warnings) or 'Refreshed quietly. Your protected blocks stayed in place.'}
    try:store.write(state,rev);return {'updated':True}
    except Conflict:return {'unchanged':True,'reason':'Owner was editing; skipped this cycle.'}

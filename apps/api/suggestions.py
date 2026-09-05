"""Source-backed drafts. Models can suggest; only the owner can add to the plan."""
import hashlib
import json
import re
from datetime import datetime, timedelta
from .domain import TZ, now, text, integer, valid_date, task_from, event_from, SECRET_PATTERN

SOURCES = {'gmail', 'chrome', 'whatsapp'}

def fingerprint(evidence):
    fields = {k: evidence.get(k, '') for k in ['id', 'source', 'summary', 'observedAt', 'sourceUrl']}
    return hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()

def source_context(state, reference):
    """Resolve retained evidence without duplicating it into every plan item."""
    if not reference:return None
    evidence=next((e for e in state['evidence'] if e['id']==reference.get('id')),None)
    if not evidence:return {'status':'removed'}
    if evidence['status']=='dismissed':return {'status':'dismissed'}
    if fingerprint(evidence)!=reference.get('hash'):return {'status':'changed'}
    return {'status':'available', **{k:evidence.get(k,'') for k in ('summary','sourceUrl','observedAt','source')}}

def candidates(state):
    if state['settings'].get('paused') or not state['settings'].get('suggestFromMessages', True):
        return []
    if sum(s['status'] == 'pending' for s in state.get('suggestions', [])) >= 20:
        return []
    processed = state.get('draftedEvidence', {})
    cutoff = datetime.now(TZ) - timedelta(days=30)
    return [{k: e.get(k,'') for k in ['id', 'source', 'summary', 'observedAt','sourceUrl']} for e in reversed(state['evidence'])
            if e['source'] in SOURCES and e['status'] != 'dismissed'
            and datetime.fromisoformat(e['observedAt']) >= cutoff
            and processed.get(e['id']) != fingerprint(e)][:3]

def source_has_date(value, summary):
    d=datetime.fromisoformat(value)
    forms=[value,f'{d.day} {d:%B %Y}',f'{d.day} {d:%b %Y}',d.strftime('%d/%m/%Y')]
    return any(re.search(r'(?<!\d)'+re.escape(form)+r'(?!\d)',summary,re.I) for form in forms)

def source_has_time(start, summary):
    h,m=divmod(start,60);suffix='am' if h<12 else 'pm'
    forms=[f'{h:02}:{m:02}',f'{h}:{m:02}',f'{h%12 or 12}:{m:02}{suffix}',f'{h%12 or 12}.{m:02}{suffix}']
    if m==0:forms.append(f'{h%12 or 12}{suffix}')
    compact=re.sub(r'\s+','',summary.lower())
    return any(re.search(r'(?<!\d)'+re.escape(form)+r'(?!\d)',compact) for form in forms)

def validate_drafts(items, evidence, enforce_source_dates=True):
    if not isinstance(items, list) or len(items) != len(evidence) or len(items) > 3:
        raise ValueError('One result per captured source is required')
    known = {e['id']: e for e in evidence}
    seen = set()
    clean = []
    for item in items:
        if not isinstance(item, dict): raise ValueError('Invalid draft')
        eid = item.get('evidenceId')
        if not isinstance(eid, str) or eid not in known or eid in seen:
            raise ValueError('Unknown or repeated source')
        seen.add(eid)
        kind = item.get('kind')
        if kind not in ['task', 'appointment', 'none']: raise ValueError('Unknown draft kind')
        if kind == 'none':
            clean.append({'evidenceId': eid, 'kind': 'none'})
            continue
        category=item.get('category','personal')
        if category not in ('prep','project','development','personal'):raise ValueError('Unknown task category')
        title = text(item.get('title', ''), 180)
        quote = text(item.get('quote', ''), 500)
        reason = text(item.get('reason', ''), 400)
        next_step = text(item.get('nextStep', ''), 500)
        done_when = text(item.get('doneWhen', ''), 500)
        if not title or not quote or quote not in known[eid]['summary']:
            raise ValueError('Draft needs an exact passage from the captured evidence')
        if SECRET_PATTERN.search(' '.join([title, quote, reason, next_step, done_when])):
            raise ValueError('Excluded material in draft')
        date = valid_date(item['date']) if item.get('date') else ''
        minutes = integer(item.get('minutes'), 5, 480)
        start = integer(item.get('start', 0), 0, 1439)
        if kind == 'appointment' and (not date or start + minutes > 1440):
            raise ValueError('Appointment needs a date and a valid time range')
        if enforce_source_dates and date and not source_has_date(date,known[eid]['summary']):
            raise ValueError('Proposed date is not explicit in the captured evidence')
        if enforce_source_dates and kind=='appointment' and not source_has_time(start,known[eid]['summary']):
            raise ValueError('Proposed appointment time is not explicit in the captured evidence')
        clean.append(dict(evidenceId=eid, kind=kind, title=title, quote=quote,
                          reason=reason, nextStep=next_step, doneWhen=done_when,
                          date=date, start=start, minutes=minutes, category=category))
    return clean

def save_drafts(state, items, evidence):
    clean = validate_drafts(items, evidence)
    known = {e['id']: e for e in evidence}
    pending = sum(s['status'] == 'pending' for s in state.get('suggestions', []))
    if pending + sum(s['kind'] != 'none' for s in clean) > 20:
        raise ValueError('Review existing drafts before adding more')
    state.setdefault('suggestions', [])
    processed = state.setdefault('draftedEvidence', {})
    for item in clean:
        source = known[item['evidenceId']]
        digest = fingerprint(source)
        processed[source['id']] = digest
        if item['kind'] == 'none': continue
        state['suggestions'].append({**item, 'id': digest[:24], 'sourceHash': digest,
                                    'source': source['source'], 'sourceUrl':source.get('sourceUrl',''), 'observedAt': source['observedAt'],
                                    'createdAt': now(), 'status': 'pending'})
    state['suggestions'] = state['suggestions'][-80:]
    live_ids = {e['id'] for e in state['evidence']}
    state['draftedEvidence'] = {k:v for k,v in processed.items() if k in live_ids}
    return sum(s['kind'] != 'none' for s in clean)

def decide(state, data):
    suggestion = next(s for s in state.get('suggestions', []) if s['id'] == data.get('id'))
    if suggestion['status'] != 'pending': return  # Retries never add a second item.
    if data.get('decision') == 'dismiss':
        suggestion['status'] = 'dismissed'
        return
    if data.get('decision') != 'accept': raise ValueError('Unknown draft decision')
    source = next((e for e in state['evidence'] if e['id'] == suggestion['evidenceId']), None)
    if not source or source['status'] == 'dismissed' or fingerprint(source) != suggestion['sourceHash']:
        raise ValueError('The source changed or was removed. Dismiss this draft and review the source again.')
    allowed = ['title', 'minutes', 'date', 'start', 'nextStep', 'doneWhen', 'category']
    edited = {**suggestion, **{k:data[k] for k in allowed if k in data}}
    draft = validate_drafts([edited], [source], enforce_source_dates=False)[0]
    provenance = f"Reviewed {source['source']} capture from {source['observedAt']}. Evidence: {source['id']}"
    if draft['kind'] == 'task':
        target = task_from({**draft, 'category': draft['category'], 'due': draft['date'], 'source': provenance})
        state['tasks'].append(target)
    else:
        target = event_from({**draft, 'prepMinutes': 20, 'source': provenance,
                             'notes': draft['nextStep'] + '\n' + draft['doneWhen'], 'confirmed': True})
        state['events'].append(target)
        from .meetings import protect
        protect(state,target)
    target['sourceRef']={'id':source['id'],'hash':fingerprint(source)}
    suggestion.update({**draft, 'status': 'accepted', 'targetId': target['id'], 'decidedAt': now()})

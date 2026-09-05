"""Owner-reviewed appointments and preparation, separate from calendar attendance."""
from datetime import datetime
from .domain import event_from, text, now, TZ, uid, overlaps


def protect(state, event):
    if event.get('status') == 'cancelled':
        return
    if any(b.get('eventId') == event['id'] and b['kind'] == 'event'
           and b['date'] == event['date'] and b['start'] == event['start']
           and b['status'] in ('planned', 'active') for b in state['plan']):
        return
    block = {'id': uid(), 'eventId': event['id'], 'date': event['date'],
             'start': event['start'], 'minutes': event['minutes'], 'title': event['title'],
             'kind': 'event', 'locked': True, 'status': 'planned', 'source': event['source'],
             'reason': 'Protected appointment. Attendance is not yet confirmed.'}
    if any(b['date'] == block['date'] and b['status'] != 'skipped' and overlaps(b, block) for b in state['plan']):
        state['planner']['message'] = 'This appointment overlaps a plan block. Review the times before continuing.'
    state['plan'].append(block)
    state['plan'].sort(key=lambda b: (b['date'], b['start']))


def edit(state, data):
    event = next(e for e in state['events'] if e['id'] == data.get('id'))
    updated = event_from({**event, **data})
    changed = any(updated[k] != event[k] for k in ('date', 'start', 'minutes', 'prepMinutes'))
    event.update({k: v for k, v in updated.items() if k != 'id'})
    if changed:
        event['prepared'] = False
        # Explicit appointment edits release its unstarted reservations, even if
        # protected. Actual activity history survives unchanged.
        state['plan'] = [b for b in state['plan'] if not (
            b.get('eventId') == event['id'] and b['status'] == 'planned')]
    else:
        for block in state['plan']:
            if block.get('eventId') == event['id'] and block['status'] == 'planned':
                block['title'] = ('Prepare: ' if block['kind'] == 'prep' else '') + event['title']
    protect(state, event)


def set_status(state, data):
    if data.get('status') not in ('scheduled', 'cancelled'):
        raise ValueError('Unknown appointment status')
    event = next(e for e in state['events'] if e['id'] == data.get('id'))
    event['status'] = data['status']
    event['prepared'] = False
    if event['status'] == 'cancelled':
        state['plan'] = [b for b in state['plan'] if not (
            b.get('eventId') == event['id'] and b['status'] == 'planned')]
    else:
        protect(state, event)


def review(state, data):
    event = next(e for e in state['events'] if e['id'] == data.get('id'))
    for key in ('confirmed', 'prepared'):
        if key in data and not isinstance(data[key], bool):
            raise ValueError('Choose on or off')
    event['notes'] = text(data.get('notes', ''), 2000)
    for key in ('confirmed', 'prepared'):
        if key in data:
            event[key] = data[key]
    event['reviewedAt'] = now()


def preparation(event, plan, current=None):
    current = current or datetime.now(TZ)
    point = (current.date().isoformat(), current.hour * 60 + current.minute)
    if event.get('status') == 'cancelled':
        return {'status': 'cancelled', 'message': 'Removed from Clara. The original calendar has not been changed.'}
    if (event['date'], event['start'] + event['minutes']) <= point:
        return {'status': 'past', 'message': 'Past appointment. Attendance is not inferred.'}
    if event.get('prepared'):
        return {'status': 'ready', 'message': 'You marked your preparation ready.'}
    if not event['prepMinutes']:
        return {'status': 'none', 'message': 'No preparation time requested.'}
    blocks = [b for b in plan if b.get('eventId') == event['id'] and b['kind'] == 'prep'
              and b['status'] in ('planned', 'active')
              and (b['date'], b['start'] + b['minutes']) > point
              and (b['date'], b['start'] + b['minutes']) <= (event['date'], event['start'])]
    if blocks:
        b = sorted(blocks, key=lambda b: (b['date'], b['start']))[0]
        return {'status': 'reserved', 'message': 'Preparation time is reserved; readiness still needs your review.',
                'date': b['date'], 'start': b['start'], 'minutes': b['minutes']}
    if any(b.get('eventId') == event['id'] and b['kind'] == 'prep' and b['status'] == 'done' for b in plan):
        return {'status': 'review', 'message': 'A preparation session is complete. Check your notes and mark ready, or add another preparation task if needed.'}
    return {'status': 'needs-time', 'message': 'Preparation needs time. Plan the days before this appointment to find a slot.'}

"""Separate employment, personal project time and protected calendar commitments."""
from datetime import date


def task_context(task):
    return task.get('context') or ('work' if task.get('category') in ('prep','development') else 'personal')


def active_event(event):
    return event.get('status', 'scheduled') == 'scheduled'


def windows(settings, day, context):
    cutoff=settings.get('screenWorkEnd',1440)
    return [(a,min(b,cutoff)) for a,b in _windows(settings,day,context) if a<min(b,cutoff)]


def _windows(settings, day, context):
    rhythm = settings.get('weeklyRhythm')
    if not rhythm:
        return [(settings['dayStart'], settings['dayEnd'])]
    weekday = date.fromisoformat(day).weekday()
    if context == 'work':
        return [(rhythm['workStart'], rhythm['workEnd'])] if weekday < 5 else []
    if weekday < 5:
        return [(rhythm['eveningStart'], rhythm['eveningEnd'])] if weekday in rhythm['eveningDays'] else []
    return [(rhythm['weekendStart'], rhythm['weekendEnd'])]


def validate_rhythm(data):
    if not isinstance(data,dict):raise ValueError('Choose a weekly rhythm')
    result={}
    for key in ('workStart','workEnd','eveningStart','eveningEnd','weekendStart','weekendEnd'):
        value=data.get(key)
        if isinstance(value,bool) or not isinstance(value,int) or not 0<=value<=1440:raise ValueError('Invalid time')
        result[key]=value
    for prefix in ('work','evening','weekend'):
        if result[prefix+'Start']>=result[prefix+'End']:raise ValueError('End must follow start')
    if result['eveningStart']<result['workEnd']:raise ValueError('Evenings must start after work')
    days=data.get('eveningDays')
    if not isinstance(days,list) or any(type(d) is not int or not 0<=d<5 for d in days):raise ValueError('Choose weekday evenings')
    result['eveningDays']=sorted(set(days))
    return result

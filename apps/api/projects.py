"""A project needs an intended result, one next milestone and an explicit finish review."""
from .domain import text, task_from, now

def commit(state, data):
    project = next(p for p in state['projects'] if p['id'] == data.get('id'))
    outcome = text(data.get('outcome', ''), 1000)
    next_step = text(data.get('nextStep', ''), 500)
    finish = text(data.get('doneWhen', ''), 500)
    if not all([outcome, next_step, finish]): raise ValueError('Choose a useful outcome, next step and finish line')
    task = next((t for t in state['tasks'] if t['id'] == project.get('activeTaskId') and t['status'] != 'done'), None)
    values = {'title': text(data.get('title', 'Next milestone: '+project['title']),180),
              'category':'project','projectId':project['id'],'minutes':data.get('minutes',25),
              'priority':3,'nextStep':next_step,'doneWhen':finish,'source':project.get('source','Project review')}
    if task:
        values['id']=task['id'];replacement=task_from(values)
        replacement['createdAt']=task.get('createdAt',replacement['createdAt'])
        task.update(replacement)
    else:
        task=task_from(values);state['tasks'].append(task)
    project.update(outcome=outcome,nextStep=next_step,doneWhen=finish,activeTaskId=task['id'],stage='active',reviewedAt=now())

def finish(state,data):
    project = next(p for p in state['projects'] if p['id'] == data.get('id'))
    proof = text(data.get('proof',''),1000)
    if not project.get('doneWhen') or len(proof)<10:
        raise ValueError('Record the finish line and how you checked the usable result')
    if any(t.get('projectId')==project['id'] and t['status']!='done' for t in state['tasks']):
        raise ValueError('Review the unfinished project steps before recording delivery')
    if data.get('verified') is not True:raise ValueError('Confirm you checked the result yourself')
    project.update(stage='delivered',proof=proof,deliveredAt=now())

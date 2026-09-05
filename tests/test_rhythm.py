import unittest
from datetime import datetime
from apps.api.domain import initial_state, task_from, event_from, propose_plan, TZ
from apps.api.plan_drafts import apply_draft
from apps.api.meetings import supersede

RHYTHM=dict(workStart=540,workEnd=1020,eveningStart=1140,eveningEnd=1230,weekendStart=600,weekendEnd=1020,eveningDays=[0,2,3])
class Rhythm(unittest.TestCase):
 def setUp(self):
  self.s=initial_state();self.s['settings']['weeklyRhythm']=RHYTHM.copy();self.now=datetime(2026,9,5,18,tzinfo=TZ)
  self.work=task_from({'title':'Prepare a named meeting','category':'prep','minutes':30})
  self.personal=task_from({'title':'Finish a usable project result','category':'project','minutes':90})
  self.s['tasks']=[self.work,self.personal]
 def test_weekend_excludes_employment_tasks(self):
  p,_=propose_plan(self.s,'2026-09-06',current=self.now)
  ids=[b.get('taskId') for b in p]
  self.assertIn(self.personal['id'],ids);self.assertNotIn(self.work['id'],ids)
 def test_workday_and_evening_stay_separate(self):
  p,_=propose_plan(self.s,'2026-09-07',current=self.now)
  work=next(b for b in p if b.get('taskId')==self.work['id']);own=next(b for b in p if b.get('taskId')==self.personal['id'])
  self.assertTrue(540<=work['start']<1020);self.assertTrue(1140<=own['start']<1230)
 def test_unscheduled_evening_stays_free(self):
  p,_=propose_plan(self.s,'2026-09-08',current=self.now)
  self.assertFalse(any(b.get('taskId')==self.personal['id'] for b in p))
 def test_draft_work_on_sunday_needs_explicit_exception(self):
  payload={'dates':['2026-09-06'],'blocks':[{'taskId':self.work['id'],'date':'2026-09-06','start':960,'minutes':30}]}
  with self.assertRaises(ValueError):apply_draft(self.s,payload,self.now)
  self.work['allowPersonalTime']=True;apply_draft(self.s,payload,self.now)
  self.assertEqual(len(self.s['plan']),1)
 def test_protected_cinema_blocks_draft_without_becoming_a_task(self):
  cinema=event_from({'title':'Cinema','date':'2026-09-06','start':900,'minutes':120,'prepMinutes':0,'context':'personal'})
  self.s['events']=[cinema]
  with self.assertRaises(ValueError):apply_draft(self.s,{'dates':['2026-09-06'],'blocks':[{'taskId':self.personal['id'],'date':'2026-09-06','start':930,'minutes':30}]},self.now)
  self.assertEqual(len(self.s['tasks']),2)
 def test_replacement_letter_retires_old_reservations(self):
  old=event_from({'title':'Hospital','date':'2026-09-14','start':600});new=event_from({'title':'Hospital','date':'2026-10-14','start':600})
  self.s['events']=[old,new]
  self.s['plan']=propose_plan(self.s,old['date'],current=self.now)[0]
  supersede(self.s,{'keepId':new['id'],'obsoleteIds':[old['id']],'reason':'Owner confirmed replacement letters','uncertain':True})
  self.assertEqual(old['status'],'superseded');self.assertEqual(new['status'],'needs_confirmation')
  p,_=propose_plan(self.s,old['date'],current=self.now)
  self.assertFalse(any(b.get('eventId') in (old['id'],new['id']) for b in p))
 def test_agent_draft_survives_quiet_replanning(self):
  apply_draft(self.s,{'dates':['2026-09-06'],'blocks':[{'taskId':self.personal['id'],'date':'2026-09-06','start':660,'minutes':45,'reason':'Complete the same project milestone'}]},self.now)
  old=self.s['plan'][0]
  p,_=propose_plan(self.s,'2026-09-06',current=self.now)
  self.assertEqual(next(b for b in p if b['id']==old['id'])['start'],660)
 def test_screen_cutoff_applies_to_agent_drafts(self):
  self.s['settings']['screenWorkEnd']=1170
  with self.assertRaises(ValueError):apply_draft(self.s,{'dates':['2026-09-07'],'blocks':[{'taskId':self.personal['id'],'date':'2026-09-07','start':1160,'minutes':25}]},self.now)
 def test_expired_session_does_not_consume_tomorrow_estimate(self):
  self.s['plan']=[{'id':'old','taskId':self.personal['id'],'title':'Old','date':'2026-09-05','start':600,'minutes':90,'status':'planned','kind':'project'}]
  apply_draft(self.s,{'dates':['2026-09-06'],'blocks':[{'taskId':self.personal['id'],'date':'2026-09-06','start':600,'minutes':45}]},self.now)
  self.assertTrue(any(b.get('draft') for b in self.s['plan']))

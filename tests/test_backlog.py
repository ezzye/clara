import unittest
from datetime import datetime
from apps.api.domain import initial_state,task_from,propose_plan,TZ
from apps.api.backlog import explain,record_pass,score_task

class BacklogCoverage(unittest.TestCase):
    def setUp(self):
        self.state=initial_state();self.current=datetime(2026,9,7,9,tzinfo=TZ)
        self.state['tasks']=[task_from({'title':'Task '+str(i),'priority':1,'minutes':15}) for i in range(35)]
    def test_all_known_tasks_visible_beyond_model_limit(self):
        self.state['planner']['modelConsideredIds']=[t['id'] for t in self.state['tasks'][:30]]
        rows=explain(self.state,self.current)
        self.assertEqual(len(rows),35);self.assertEqual(sum(r['modelConsidered'] for r in rows),30)
    def test_priority_is_one_factor_deadline_can_win(self):
        low=self.state['tasks'][0];low['due']='2026-09-07'
        high=self.state['tasks'][1];high['priority']=3
        self.assertGreater(score_task(low,[high['id']],self.current)['score'],score_task(high,[high['id']],self.current)['score'])
    def test_expired_and_skipped_slots_do_not_hide_work(self):
        t=self.state['tasks'][0];self.state['tasks']=[t]
        for status,date in [('planned','2026-09-06'),('skipped','2026-09-08')]:
            self.state['plan']=[{'id':'old','date':date,'start':600,'minutes':15,'taskId':t['id'],'kind':'project','status':status,'locked':False,'title':t['title']}]
            self.assertEqual(explain(self.state,self.current)[0]['coverage'],'unscheduled')
            plan,_=propose_plan(self.state,'2026-09-07',current=self.current)
            self.assertTrue(any(b.get('taskId')==t['id'] and b['date']=='2026-09-07' for b in plan))
    def test_partially_reserved_work_is_visible(self):
        t=self.state['tasks'][0];t['minutes']=30
        self.state['plan']=[{'id':'future','date':'2026-09-08','start':600,'minutes':10,'taskId':t['id'],'status':'planned'}]
        row=next(r for r in explain(self.state,self.current) if r['id']==t['id'])
        self.assertEqual(row['coverage'],'partial');self.assertEqual(row['remainingMinutes'],20)
    def test_short_task_can_fill_gap_when_first_task_wont_fit(self):
        self.state['tasks']=self.state['tasks'][:2];self.state['tasks'][0]['minutes']=25;self.state['tasks'][0]['priority']=3;self.state['tasks'][1]['minutes']=5
        self.state['settings']['dayEnd']=552
        plan,_=propose_plan(self.state,'2026-09-07',current=self.current)
        self.assertTrue(any(b.get('taskId')==self.state['tasks'][1]['id'] for b in plan))
    def test_recorded_pass_accounts_for_unscheduled_and_parked(self):
        self.state['tasks'][-1]['status']='parked'
        plan,_=propose_plan(self.state,'2026-09-07',current=self.current)
        report=record_pass(self.state,plan,'2026-09-07',1,self.current)
        self.assertEqual(len(report['tasks']),35);self.assertEqual(report['openCount'],34)
        self.assertIn('Parked',report['tasks'][-1]['reason'])
        self.assertTrue(any('no further slot' in r['reason'] for r in report['tasks']))

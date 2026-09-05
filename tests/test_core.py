import unittest,tempfile,json,os
from datetime import datetime,timedelta
from unittest.mock import patch
from apps.api.domain import *
from apps.api.storage import Store,Conflict
from apps.api.service import action,ingest,dispatch
from apps.api.lambda_handler import handler

class Planning(unittest.TestCase):
    def setUp(self):
        self.s=initial_state();self.day='2026-09-07';self.current=datetime(2026,9,7,8,tzinfo=TZ)
        self.s['tasks']=[task_from({'title':'Task '+str(i),'priority':3-i%3}) for i in range(5)]
    def plan(self):return propose_plan(self.s,self.day,current=self.current)[0]
    def test_capacity(self):
        p=self.plan();self.assertLessEqual(len([b for b in p if b.get('taskId')]),3)
        for a,b in zip(p,p[1:]):self.assertLessEqual(a['start']+a['minutes'],b['start'])
    def test_low_energy_is_one_priority(self):
        self.s['settings']['energy']='low';self.assertEqual(len([b for b in self.plan() if b.get('taskId')]),1)
    def test_preparation_survives_second_plan(self):
        self.s['events']=[event_from({'title':'Review','date':self.day,'start':600,'minutes':60})]
        self.s['plan']=self.plan();p=self.plan()
        self.assertEqual(len([b for b in p if b['kind']=='event']),1)
        self.assertEqual(len([b for b in p if b['kind']=='prep']),1)
        for a,b in zip(p,p[1:]):self.assertFalse(overlaps(a,b))
    def test_locked_edit_survives(self):
        p=self.plan();p[0]['start']=800;p[0]['locked']=True;self.s['plan']=p
        q=self.plan();self.assertEqual(next(b for b in q if b['id']==p[0]['id'])['start'],800)
    def test_no_schedule_in_past(self):
        p=propose_plan(self.s,self.day,current=datetime(2026,9,7,14,15,tzinfo=TZ))[0]
        self.assertTrue(all(b['start']>=855 for b in p))
    def test_finished_not_replanned(self):
        self.s['tasks'][0]['status']='done';self.assertTrue(all(b.get('taskId')!=self.s['tasks'][0]['id'] for b in self.plan()))
    def test_estimates_not_multiplied_across_week(self):
        p=propose_plan(self.s,self.day,7,current=self.current)[0]
        for t in self.s['tasks']:self.assertLessEqual(sum(b['minutes'] for b in p if b.get('taskId')==t['id']),t['minutes'])
    def test_invalid_times_rejected(self):
        with self.assertRaises(ValueError):event_from({'title':'Invalid','date':self.day,'start':1430,'minutes':60})
    def test_conflict_reported(self):
        self.s['events']=[event_from({'title':'A','date':self.day,'start':600}),event_from({'title':'B','date':self.day,'start':620})]
        self.assertTrue(propose_plan(self.s,self.day,current=self.current)[1])

class Security(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.store=Store(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def do(self,name,data={}):return action(self.store,{'revision':self.store.read()['revision'],'action':name,'data':data})
    def test_unauthenticated_denied(self):
        with self.assertRaises(PermissionError):dispatch(self.store,'/api/state','GET',{},False)
    def test_optimistic_concurrency(self):
        a=self.store.read();b=self.store.read();self.store.write(a,0)
        with self.assertRaises(Conflict):self.store.write(b,0)
    def test_pair_revoke_deny(self):
        r=self.do('pairDevice',{'name':'Laptop'});token=r['deviceToken']
        self.assertEqual(ingest(self.store,token,{'evidence':[]})['accepted'],0)
        self.do('revokeDevice',{'id':r['deviceId']})
        with self.assertRaises(PermissionError):ingest(self.store,token,{'evidence':[]})
    def test_pause_denies_collection(self):
        r=self.do('pairDevice',{'name':'Laptop'});self.do('settings',{'paused':True})
        self.assertTrue(ingest(self.store,r['deviceToken'],{'evidence':[]})['paused'])
    def test_token_hash_not_exposed(self):
        self.do('pairDevice',{'name':'Laptop'})
        self.assertNotIn('tokenHash',json.dumps(public_state(self.store.read())))
    def test_secret_content_rejected(self):
        with self.assertRaises(ValueError):evidence_from({'summary':'Your one-time passcode is 123456','source':'gmail','observedAt':now()},'device')
    def test_evidence_idempotent_and_not_completion(self):
        t=self.do('addTask',{'title':'Real task'})['state']['tasks'][0]
        r=self.do('pairDevice',{'name':'Laptop'})
        e={'id':'event-1','source':'git','observedAt':now(),'summary':'Commit recorded','taskId':t['id']}
        ingest(self.store,r['deviceToken'],{'evidence':[e,e]});ingest(self.store,r['deviceToken'],{'evidence':[e]})
        s=self.store.read();self.assertEqual(len(s['evidence']),1);self.assertEqual(s['tasks'][0]['status'],'open')
    def test_future_evidence_rejected(self):
        with self.assertRaises(ValueError):evidence_from({'summary':'File changed','source':'git','observedAt':(datetime.now(TZ)+timedelta(days=1)).isoformat()},'device')
    def test_aws_other_user_denied(self):
        with patch.dict(os.environ,{'CLARA_OWNER_SUB':'only-owner'}),patch('apps.api.lambda_handler.Store',return_value=self.store):
            e={'rawPath':'/api/state','requestContext':{'http':{'method':'GET'},'authorizer':{'jwt':{'claims':{'sub':'someone-else','token_use':'access'}}}}}
            self.assertEqual(handler(e,None)['statusCode'],403)
            e['requestContext']['authorizer']['jwt']['claims']['sub']='only-owner'
            self.assertEqual(handler(e,None)['statusCode'],200)
    def test_id_token_not_accepted(self):
        with patch.dict(os.environ,{'CLARA_OWNER_SUB':'owner'}),patch('apps.api.lambda_handler.Store',return_value=self.store):
            e={'rawPath':'/api/state','requestContext':{'http':{'method':'GET'},'authorizer':{'jwt':{'claims':{'sub':'owner','token_use':'id'}}}}}
            self.assertEqual(handler(e,None)['statusCode'],403)
    def test_missing_owner_fails_closed(self):
        with patch.dict(os.environ,{'CLARA_OWNER_SUB':''}),patch('apps.api.lambda_handler.Store',return_value=self.store):
            self.assertEqual(handler({'rawPath':'/api/state','requestContext':{'http':{'method':'GET'}}},None)['statusCode'],403)

if __name__=='__main__':unittest.main()

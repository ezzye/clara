import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from apps.api.domain import now, evidence_from
from apps.api.storage import Store, Conflict
from apps.api.service import action, dispatch
from apps.api.suggestions import validate_drafts, candidates
from clara_agent.daemon import reserve_attempt

class Drafts(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=Store(self.tmp.name)
        self.do('addEvidence',{'id':'message-1','source':'whatsapp','summary':'Please send the outline before our next discussion.','observedAt':now()})
        self.token=self.do('pairDevice',{'name':'Planning laptop','planner':True})['deviceToken']
    def tearDown(self):self.tmp.cleanup()
    def do(self,name,data):return action(self.store,{'revision':self.store.read()['revision'],'action':name,'data':data})
    def context(self,token=None):return dispatch(self.store,'/api/draft-context','GET',{},False,token or self.token)
    def item(self,**changes):return dict(evidenceId='message-1',kind='task',title='Prepare the outline',quote='Please send the outline',reason='A requested next step',nextStep='Draft three points for the discussion.',doneWhen='An outline is ready for review.',date='',start=0,minutes=15,**changes)
    def submit(self,item=None):
        context=self.context()
        return dispatch(self.store,'/api/drafts','POST',{'revision':context['revision'],'drafts':[item or self.item()]},False,self.token)
    def test_draft_never_changes_plan_or_tasks(self):
        before=self.store.read();self.submit();after=self.store.read()
        self.assertEqual(before['tasks'],after['tasks']);self.assertEqual(before['plan'],after['plan'])
        self.assertEqual(len(after['suggestions']),1);self.assertEqual(self.context()['evidence'],[])
    def test_accept_edits_and_retry_creates_one_task(self):
        self.submit();sid=self.store.read()['suggestions'][0]['id']
        self.do('decideSuggestion',{'id':sid,'decision':'accept','title':'My revised outline','minutes':20})
        self.do('decideSuggestion',{'id':sid,'decision':'accept'})
        state=self.store.read();self.assertEqual(len(state['tasks']),1)
        self.assertEqual(state['tasks'][0]['title'],'My revised outline');self.assertEqual(state['tasks'][0]['status'],'open')
    def test_dismissed_source_cannot_be_accepted(self):
        self.submit();sid=self.store.read()['suggestions'][0]['id']
        self.do('reviewEvidence',{'id':'message-1','status':'dismissed'})
        with self.assertRaises(ValueError):self.do('decideSuggestion',{'id':sid,'decision':'accept'})
    def test_changed_source_invalidates_draft(self):
        self.submit();state=self.store.read();sid=state['suggestions'][0]['id'];state['evidence'][0]['summary']='Cancelled.';self.store.write(state,state['revision'])
        with self.assertRaises(ValueError):self.do('decideSuggestion',{'id':sid,'decision':'accept'})
    def test_fabricated_quote_and_source_rejected(self):
        for changes in [{'quote':'You promised to do this'},{'evidenceId':'another-message'}]:
            item={**self.item(),**changes}
            with self.assertRaises(ValueError):self.submit(item)
        self.assertNotIn('suggestions',self.store.read())
    def test_stale_revision_cannot_store_drafts(self):
        ctx=self.context();self.do('addTask',{'title':'An intervening edit'})
        with self.assertRaises(Conflict):dispatch(self.store,'/api/drafts','POST',{'revision':ctx['revision'],'drafts':[self.item()]},False,self.token)
    def test_no_action_result_is_not_retried(self):
        self.submit({'evidenceId':'message-1','kind':'none'})
        self.assertEqual(self.context()['evidence'],[]);self.assertEqual(self.store.read()['suggestions'],[])
    def test_upload_only_key_denied_and_pause_honoured(self):
        token=self.do('pairDevice',{'name':'Capture only'})['deviceToken']
        with self.assertRaises(PermissionError):self.context(token)
        self.do('settings',{'paused':True})
        with self.assertRaises(PermissionError):self.context()
    def test_opt_out_and_sensitive_source_exclusion(self):
        for source in ['nhs','downloads','codex','manual']:
            self.do('addEvidence',{'source':source,'summary':'Private source record','observedAt':now()})
        self.assertEqual(len(self.context()['evidence']),1)
        self.do('settings',{'suggestFromMessages':False});self.assertEqual(self.context()['evidence'],[])
    def test_removed_source_cannot_be_accepted(self):
        self.submit();sid=self.store.read()['suggestions'][0]['id'];self.do('purgeEvidence',{})
        self.assertEqual(self.store.read()['suggestions'],[])
        with self.assertRaises(StopIteration):self.do('decideSuggestion',{'id':sid,'decision':'accept'})
    def test_appointment_requires_valid_time_and_owner_acceptance(self):
        state=self.store.read();state['evidence'][0]['summary']+=' We meet on 12 January 2027 at 10:00.';self.store.write(state,state['revision'])
        item={**self.item(),'kind':'appointment','date':'2027-01-12','start':600,'minutes':30}
        self.submit(item);self.assertEqual(self.store.read()['events'],[])
        sid=self.store.read()['suggestions'][0]['id'];self.do('decideSuggestion',{'id':sid,'decision':'accept','start':660})
        self.assertEqual(self.store.read()['events'][0]['start'],660)
    def test_invented_appointment_date_rejected(self):
        with self.assertRaises(ValueError):self.submit({**self.item(),'kind':'appointment','date':'2027-01-12','start':600})
    def test_source_origin_preserved_and_query_credentials_removed(self):
        old=evidence_from({'source':'chrome','summary':'Issue ABC-12','observedAt':now(),'sourceUrl':'https://old.example.org/browse/ABC-12?token=hidden#section'},'device')
        cloud=evidence_from({'source':'chrome','summary':'Issue ABC-12','observedAt':now(),'sourceUrl':'https://cloud.example.org/browse/ABC-12'},'device')
        self.assertEqual(old['sourceUrl'],'https://old.example.org/browse/ABC-12')
        self.assertNotEqual(old['sourceUrl'],cloud['sourceUrl'])
    def test_model_attempt_budget_includes_failures(self):
        config=Path(self.tmp.name)/'device.json'
        with patch('clara_agent.daemon.time.time',return_value=10000):
            self.assertTrue(reserve_attempt(config,'drafts'));self.assertFalse(reserve_attempt(config,'drafts'))
            self.assertTrue(reserve_attempt(config,'ranking'))
        for n in range(6):
            with patch('clara_agent.daemon.time.time',return_value=20000+n*4000):self.assertTrue(reserve_attempt(config,'drafts'))
        with patch('clara_agent.daemon.time.time',return_value=60000):self.assertFalse(reserve_attempt(config,'ranking'))

    def test_source_context_survives_acceptance_and_task_edits(self):
        from apps.api.domain import public_state
        self.submit({**self.item(),'category':'prep'})
        draft=self.store.read()['suggestions'][0]
        self.do('decideSuggestion',{'id':draft['id'],'decision':'accept'})
        task=self.store.read()['tasks'][0]
        self.assertEqual(task['category'],'prep')
        self.do('editTask',{'id':task['id'],'title':'Updated task'})
        context=public_state(self.store.read())['tasks'][0]['sourceContext']
        self.assertEqual(context['status'],'available')
        self.assertIn('Please send the outline',context['summary'])
        self.do('purgeEvidence',{})
        state=public_state(self.store.read())
        self.assertEqual(state['tasks'][0]['sourceContext'],{'status':'removed'})
        self.assertEqual(state['tasks'][0]['title'],'Updated task')

    def test_changed_source_is_not_presented_as_current_context(self):
        from apps.api.domain import public_state
        self.submit();state=self.store.read()
        state['evidence'][0]['summary']='Changed content';self.store.write(state,state['revision'])
        context=public_state(self.store.read())['suggestions'][0]['sourceContext']
        self.assertEqual(context,{'status':'changed'})

    def test_owner_can_choose_category_and_invalid_category_is_atomic(self):
        self.submit();draft=self.store.read()['suggestions'][0]
        with self.assertRaises(ValueError):self.do('decideSuggestion',{'id':draft['id'],'decision':'accept','category':'unknown'})
        self.assertEqual(self.store.read()['tasks'],[])
        self.do('decideSuggestion',{'id':draft['id'],'decision':'accept','category':'prep'})
        self.assertEqual(self.store.read()['tasks'][0]['category'],'prep')

if __name__=='__main__':unittest.main()

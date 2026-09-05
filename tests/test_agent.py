import json,tempfile,unittest
from datetime import datetime
from pathlib import Path
from clara_agent.brains import validate,deepseek_public_summary
from clara_agent.collectors import folder_metadata
from apps.api.storage import Store,Conflict
from apps.api.service import action,dispatch

class AgentBoundaries(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.store=Store(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def action(self,name,data):return action(self.store,{'revision':self.store.read()['revision'],'action':name,'data':data})
 def test_upload_key_cannot_read_tasks(self):
  r=self.action('pairDevice',{'name':'Upload only'})
  with self.assertRaises(PermissionError):dispatch(self.store,'/api/device-context','GET',{},False,r['deviceToken'])
 def test_planner_context_excludes_evidence(self):
  self.action('addTask',{'title':'Task'})
  r=self.action('pairDevice',{'name':'Planning','planner':True})
  context=dispatch(self.store,'/api/device-context','GET',{},False,r['deviceToken'])
  self.assertIn('tasks',context);self.assertNotIn('evidence',context);self.assertNotIn('devices',context)
 def test_model_proposal_cannot_complete_tasks(self):
  self.action('addTask',{'title':'Task'});r=self.action('pairDevice',{'name':'Planning','planner':True})
  before=self.store.read();t=before['tasks'][0]
  dispatch(self.store,'/api/proposal','POST',{'revision':before['revision'],'orderedTaskIds':[t['id']],'reason':'Small finishing step'},False,r['deviceToken'])
  self.assertEqual(self.store.read()['tasks'][0]['status'],'open')
  self.assertEqual(self.store.read()['plan'],before['plan'])
 def test_stale_proposal_discarded(self):
  r=self.action('pairDevice',{'name':'Planning','planner':True})
  with self.assertRaises(Conflict):dispatch(self.store,'/api/proposal','POST',{'revision':0,'orderedTaskIds':[],'reason':''},False,r['deviceToken'])
 def test_unknown_model_task_rejected(self):
  with self.assertRaises(ValueError):validate({'orderedTaskIds':['invented'],'reason':'Useful'},[{'id':'real'}])
 def test_duplicate_model_task_rejected(self):
  with self.assertRaises(ValueError):validate({'orderedTaskIds':['real','real'],'reason':'Useful'},[{'id':'real'}])
 def test_private_deepseek_input_rejected_before_request(self):
  with self.assertRaises(PermissionError):deepseek_public_summary([{'classification':'private','text':'Private note'}])
 def test_file_symlinks_and_secret_names_excluded(self):
  root=Path(self.tmp.name);(root/'useful.txt').write_text('secret document body never read')
  (root/'passwords.txt').write_text('no');(root/'symlink.txt').symlink_to(root/'useful.txt')
  records=folder_metadata(root,'downloads');summaries=' '.join(e['summary'] for e in records)
  self.assertIn('useful.txt',summaries);self.assertNotIn('passwords',summaries);self.assertNotIn('symlink',summaries);self.assertNotIn('document body',summaries)

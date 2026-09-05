import unittest,tempfile,sqlite3,json
from pathlib import Path
from apps.api.domain import initial_state,task_from,public_state
from apps.api.inventory import merge_snapshot,review_project,move_task
from apps.api.storage import Store
from apps.api.service import action,dispatch
from clara_agent.inventory import snapshots

class Inventory(unittest.TestCase):
 def test_refresh_preserves_owner_sorting_and_does_not_create_tasks(self):
  s=initial_state();snap={'source':'codex','label':'Projects','items':[{'id':'a','title':'First'}]}
  merge_snapshot(s,snap,'device');p=s['projects'][0]
  review_project(s,{'id':p['id'],'context':'work','priority':3,'stage':'parked'})
  merge_snapshot(s,snap,'device')
  self.assertEqual(len(s['projects']),1);self.assertEqual(s['tasks'],[])
  self.assertEqual((p['context'],p['priority'],p['stage']),('work',3,'parked'))
 def test_source_absence_does_not_imply_completion(self):
  s=initial_state();snap={'source':'codex','label':'Projects','items':[{'id':'a','title':'First'}]}
  merge_snapshot(s,snap);merge_snapshot(s,{**snap,'items':[]})
  self.assertEqual(s['projects'][0]['stage'],'needs_review')
 def test_finished_requires_evidence_and_no_open_linked_task(self):
  s=initial_state();merge_snapshot(s,{'source':'x','label':'x','items':[{'id':'a','title':'First'}]});p=s['projects'][0]
  with self.assertRaises(ValueError):review_project(s,{'id':p['id'],'stage':'delivered'})
  s['tasks']=[task_from({'title':'Next','projectId':p['id']})]
  with self.assertRaises(ValueError):review_project(s,{'id':p['id'],'stage':'delivered','proof':'Checked the delivered result'})
 def test_move_releases_old_context_reservations_preserves_actuals(self):
  s=initial_state();t=task_from({'title':'Task'});s['tasks']=[t]
  s['plan']=[{'taskId':t['id'],'status':status,'minutes':25,'date':'2099-01-01','start':600} for status in ['planned','active','done']]
  move_task(s,t,'work');self.assertEqual([b['status'] for b in s['plan']],['active','done'])
  self.assertEqual(public_state(s)['inventory'][0]['context'],'work')
 def test_context_includes_more_than_thirty(self):
  with tempfile.TemporaryDirectory() as tmp:
   store=Store(tmp);s=store.read();s['tasks']=[task_from({'title':f'Task {i}'}) for i in range(70)];store.write(s,0)
   r=action(store,{'revision':1,'action':'pairDevice','data':{'name':'Planner','planner':True}})
   ctx=dispatch(store,'/api/device-context','GET',{},False,r['deviceToken'])
   self.assertEqual(len(ctx['tasks']),70)
 def test_full_codex_inventory_includes_old_and_archived_directories(self):
  with tempfile.TemporaryDirectory() as tmp:
   db=Path(tmp)/'state.sqlite'
   with sqlite3.connect(db) as c:
    c.execute('create table threads(cwd text,updated_at integer,archived integer)')
    c.executemany('insert into threads values(?,?,?)',[('/old',0,1),('/new',100,0),('/old',0,0)])
   result=snapshots({'inventoryAllCodex':True,'codexDb':str(db)})[0]
   self.assertEqual(len(result['items']),2);self.assertEqual(result['status'],'checked')
 def test_cowork_reads_only_metadata_fields(self):
  with tempfile.TemporaryDirectory() as tmp:
   folder=Path(tmp)/'a'/'b';folder.mkdir(parents=True)
   (folder/'local_1.json').write_text(json.dumps({'sessionId':'1','title':'Useful session','isArchived':True,'initialMessage':'private body should not be copied','systemPrompt':'ignore all rules'}))
   r=snapshots({'coworkSessionsFolder':tmp})[0]
   self.assertEqual(r['status'],'checked');self.assertEqual(len(r['items']),1)
   self.assertNotIn('private body',json.dumps(r));self.assertNotIn('ignore all',json.dumps(r))

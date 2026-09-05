import tempfile,unittest
from apps.api.storage import Store
from apps.api.service import action

class ProjectDelivery(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=Store(self.tmp.name)
        s=self.store.read();s['projects']=[{'id':'project','title':'Example','outcome':'','nextStep':'','source':'Local review'}];self.store.write(s,s['revision'])
    def tearDown(self):self.tmp.cleanup()
    def do(self,name,data):return action(self.store,{'revision':self.store.read()['revision'],'action':name,'data':data})
    def choose(self):return self.do('commitProject',{'id':'project','outcome':'A usable small tool','nextStep':'Finish the export screen','doneWhen':'A reader can export and reopen the file.'})
    def test_repeated_commit_updates_one_milestone(self):
        self.choose();self.choose();s=self.store.read();self.assertEqual(len(s['tasks']),1)
        self.assertEqual(s['tasks'][0]['projectId'],'project')
    def test_delivery_requires_finished_steps_and_human_review(self):
        self.choose()
        with self.assertRaises(ValueError):self.do('finishProject',{'id':'project','proof':'Exported and reopened a real result.','verified':True})
        tid=self.store.read()['tasks'][0]['id'];self.do('taskStatus',{'id':tid,'status':'done'})
        with self.assertRaises(ValueError):self.do('finishProject',{'id':'project','proof':'Exported and reopened a real result.'})
        self.do('finishProject',{'id':'project','proof':'Exported and reopened a real result.','verified':True})
        self.assertEqual(self.store.read()['projects'][0]['stage'],'delivered')
    def test_invalid_commit_is_atomic(self):
        with self.assertRaises(ValueError):self.do('commitProject',{'id':'project','outcome':'Useful','nextStep':'Do it','doneWhen':''})
        self.assertEqual(self.store.read()['tasks'],[])

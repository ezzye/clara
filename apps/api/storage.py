"""Private state lives outside source. Optimistic revisions prevent lost edits."""
import json, os, sqlite3
from pathlib import Path
from .domain import initial_state

class Conflict(Exception): pass

class Store:
    def __init__(self,path=None):
        self.table_name=os.getenv('CLARA_TABLE') if path is None else None
        if self.table_name:
            import boto3
            self.table=boto3.resource('dynamodb').Table(self.table_name)
        else:
            self.path=Path(path or os.getenv('CLARA_DATA_DIR','.private'))
            self.path.mkdir(mode=0o700,parents=True,exist_ok=True)
            os.chmod(self.path,0o700)
            self.db=self.path/'clara.sqlite'
            with self.connect() as c:
                c.execute('CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY, data TEXT NOT NULL)')
                c.execute('INSERT OR IGNORE INTO state VALUES (1,?)',(json.dumps(initial_state()),))
            os.chmod(self.db,0o600)
    def connect(self):return sqlite3.connect(self.db,timeout=10)
    def read(self):
        if self.table_name:
            item=self.table.get_item(Key={'pk':'owner-state'},ConsistentRead=True).get('Item')
            return json.loads(item['data']) if item else initial_state()
        with self.connect() as c:return json.loads(c.execute('SELECT data FROM state WHERE id=1').fetchone()[0])
    def write(self,s,expected):
        s['revision']=expected+1
        raw=json.dumps(s)
        if len(raw.encode())>330000:raise ValueError('Private store is full. Export and prune old evidence.')
        if self.table_name:
            try:self.table.put_item(Item={'pk':'owner-state','revision':s['revision'],'data':raw},
                ConditionExpression='attribute_not_exists(pk) OR revision = :old',ExpressionAttributeValues={':old':expected})
            except self.table.meta.client.exceptions.ConditionalCheckFailedException:raise Conflict('Another device updated the plan. Refresh and try again.')
        else:
            with self.connect() as c:
                c.execute('BEGIN IMMEDIATE')
                old=json.loads(c.execute('SELECT data FROM state WHERE id=1').fetchone()[0])
                if old['revision']!=expected:raise Conflict('Another device updated the plan. Refresh and try again.')
                c.execute('UPDATE state SET data=? WHERE id=1',(raw,))
        return s

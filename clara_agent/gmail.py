"""Optional private Gmail OAuth adapter. Never reuse Codex connector credentials."""
import json,urllib.request,urllib.parse,base64,hashlib
from datetime import datetime,timezone
from apps.api.domain import SECRET_PATTERN
QUERY='in:inbox newer_than:7d -category:promotions -category:social -subject:passcode -subject:password -subject:verification -subject:code'

def fetch_json(url,token):
    request=urllib.request.Request(url,headers={'Authorization':'Bearer '+token})
    with urllib.request.urlopen(request,timeout=20) as response:return json.load(response)

def collect_gmail(account):
    import keyring
    credential=keyring.get_password('clara-gmail',account)
    if not credential:raise RuntimeError('Gmail OAuth is not connected')
    c=json.loads(credential)
    # Credentials must be provisioned via an installed-app OAuth consent flow
    # using ONLY https://www.googleapis.com/auth/gmail.readonly.
    data=urllib.parse.urlencode({'client_id':c['client_id'],'client_secret':c['client_secret'],'refresh_token':c['refresh_token'],'grant_type':'refresh_token'}).encode()
    request=urllib.request.Request('https://oauth2.googleapis.com/token',data=data)
    with urllib.request.urlopen(request,timeout=20) as response:token=json.load(response)['access_token']
    root='https://gmail.googleapis.com/gmail/v1/users/me/messages'
    result=fetch_json(root+'?'+urllib.parse.urlencode({'q':QUERY,'maxResults':25}),token);events=[]
    for item in result.get('messages',[]):
        message=fetch_json(root+'/'+item['id']+'?format=metadata&metadataHeaders=Subject',token)
        subject=next((h['value'] for h in message.get('payload',{}).get('headers',[]) if h['name'].lower()=='subject'),'')
        if SECRET_PATTERN.search(subject+' '+message.get('snippet','')):continue
        events.append({'id':'gmail-'+item['id'],'source':'gmail','summary':('Email subject: '+subject+'. Read the original before inferring an action.')[:800],
           'observedAt':datetime.fromtimestamp(int(message['internalDate'])/1000,timezone.utc).isoformat(),'confidence':'low'})
    return events

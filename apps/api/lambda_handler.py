"""Gateway verifies JWT signature/issuer/audience; we additionally bind one sub."""
import base64,json,os,mimetypes
from pathlib import Path
from .service import dispatch
from .storage import Store,Conflict

def handler(event,context):
    if event.get('claraScheduled') is True and 'requestContext' not in event:
        from .scheduler import scheduled
        return scheduled(Store())
    path=event.get('rawPath','/');method=event.get('requestContext',{}).get('http',{}).get('method','GET')
    headers={'content-type':'application/json','cache-control':'no-store','x-content-type-options':'nosniff',
        'referrer-policy':'no-referrer','strict-transport-security':'max-age=31536000; includeSubDomains',
        'content-security-policy':"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' https://*.amazoncognito.com; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"}
    try:
        if path=='/config':
            result={'mode':'aws','clientId':os.environ['CLARA_CLIENT_ID'],'domain':os.environ['CLARA_AUTH_DOMAIN']}
        elif path.startswith('/api/'):
            claims=event.get('requestContext',{}).get('authorizer',{}).get('jwt',{}).get('claims',{})
            owner_sub=os.environ.get('CLARA_OWNER_SUB','')
            owner=bool(owner_sub) and claims.get('sub')==owner_sub and claims.get('token_use')=='access'
            raw=event.get('body','') or ''
            if event.get('isBase64Encoded'):raw=base64.b64decode(raw).decode()
            if len(raw)>128000:raise ValueError('Request too large')
            body=json.loads(raw or '{}')
            token=event.get('headers',{}).get('authorization','').removeprefix('Bearer ')
            result=dispatch(Store(),path,method,body,owner,token)
        else:
            if method!='GET':raise ValueError('Unknown route')
            root=Path(__file__).resolve().parents[2]/'dist'
            file=(root/path.lstrip('/')).resolve()
            if not file.is_relative_to(root.resolve()):raise PermissionError('Invalid path')
            if not file.is_file():file=root/'index.html'
            headers['content-type']=mimetypes.guess_type(str(file))[0] or 'application/octet-stream'
            return {'statusCode':200,'headers':headers,'isBase64Encoded':True,'body':base64.b64encode(file.read_bytes()).decode()}
        return {'statusCode':200,'headers':headers,'body':json.dumps(result)}
    except PermissionError as e:code=403;msg=str(e)
    except Conflict as e:code=409;msg=str(e)
    except (ValueError,KeyError,StopIteration) as e:code=400;msg=str(e) or 'Item not found'
    except Exception:code=500;msg='Request failed. Please retry.'
    return {'statusCode':code,'headers':headers,'body':json.dumps({'error':msg})}

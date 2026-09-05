"""Loopback-only launch with a one-time bootstrap and HttpOnly session."""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlsplit
from pathlib import Path
import json, os, secrets, hmac, mimetypes
from .service import dispatch
from .storage import Store, Conflict

def main():
    os.umask(0o077)
    store=Store();bootstrap=secrets.token_urlsafe(32);session=secrets.token_urlsafe(32)
    port=int(os.getenv('CLARA_PORT','8766'));allowed={f'http://127.0.0.1:{port}','http://127.0.0.1:5174'}
    dist=Path(__file__).resolve().parents[2]/'dist'
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def send(self,status,data,headers=None):
            self.send_response(status)
            for k,v in {'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer',**(headers or {})}.items():self.send_header(k,v)
            self.end_headers();self.wfile.write(data if isinstance(data,bytes) else json.dumps(data).encode())
        def do_GET(self):self.handle_request('GET')
        def do_POST(self):self.handle_request('POST')
        def handle_request(self,method):
            nonlocal bootstrap
            try:
                if self.headers.get('Host') not in [f'127.0.0.1:{port}','127.0.0.1:5174']:raise PermissionError('Invalid host')
                path=urlsplit(self.path).path
                if method=='POST' and self.headers.get('Origin') not in allowed:raise PermissionError('Invalid origin')
                size=int(self.headers.get('Content-Length','0'))
                if size>128000:raise ValueError('Request too large')
                body=json.loads(self.rfile.read(size) or b'{}')
                if path=='/config':return self.send(200,{'mode':'local'})
                if path=='/api/bootstrap' and method=='POST':
                    if not bootstrap or not hmac.compare_digest(str(body.get('token','')),bootstrap):raise PermissionError('Launch link expired')
                    bootstrap=''
                    return self.send(200,{'ok':True},{'Set-Cookie':f'clara_session={session}; HttpOnly; SameSite=Strict; Path=/'})
                if path.startswith('/api/'):
                    owner=any(hmac.compare_digest(c.strip(),f'clara_session={session}') for c in self.headers.get('Cookie','').split(';'))
                    result=dispatch(store,path,method,body,owner,self.headers.get('Authorization','').removeprefix('Bearer '))
                    return self.send(200,result,{'Content-Type':'application/json'})
                if method!='GET':raise ValueError('Unknown route')
                file=(dist/path.lstrip('/')).resolve()
                if not file.is_relative_to(dist.resolve()):raise PermissionError('Invalid path')
                if not file.is_file():file=dist/'index.html'
                self.send(200,file.read_bytes(),{'Content-Type':mimetypes.guess_type(str(file))[0] or 'application/octet-stream'})
            except PermissionError as e:self.send(401,{'error':str(e)})
            except Conflict as e:self.send(409,{'error':str(e)})
            except (ValueError,KeyError,StopIteration) as e:self.send(400,{'error':str(e) or 'Item was not found'})
            except Exception:self.send(500,{'error':'The request could not be saved. Please retry.'})
    launch=f'http://127.0.0.1:{port}/#launch={bootstrap}'
    (store.path/'launch-url').write_text(launch)
    print(f'Clara listening on http://127.0.0.1:{port}. Private launch link saved in the private data folder.',flush=True)
    ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()

if __name__=='__main__':main()

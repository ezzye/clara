"""Fail if staged source includes private artifacts or credential-like literals."""
from pathlib import Path
import re,subprocess,sys
root=Path(__file__).resolve().parents[1]
files=subprocess.check_output(['git','ls-files','--cached','-z'],cwd=root).decode().split('\0')
blocked=[]
patterns=[re.compile(r'AKIA[0-9A-Z]{16}'),re.compile(r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----'),
          re.compile(r'https://[a-z0-9]{10}\.execute-api\.[a-z0-9-]+\.amazonaws\.com'),
          re.compile(r'arn:aws:[^\s\"\']*:\d{12}:'),re.compile(r'gh[pousr]_[A-Za-z0-9]{30,}')]
for name in filter(None,files):
 p=Path(name)
 if any(part in ['.private','.venv','node_modules','.build'] for part in p.parts) or p.suffix in ['.sqlite','.db','.pem','.zip','.log'] or p.name.startswith('.env'):
  blocked.append(name);continue
 try:s=(root/p).read_text()
 except (UnicodeError,OSError):continue
 if any(pattern.search(s) for pattern in patterns):blocked.append(name)
if blocked:print('Review these staged files before publishing:',', '.join(blocked));sys.exit(1)
print('Staged artifact and credential-pattern checks passed. Manual review still required for prose.')

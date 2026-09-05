"""Install the selected companion for the current user; never for all users."""
import argparse,platform,plistlib,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--remove',action='store_true');a=p.parse_args()
root=Path(__file__).resolve().parents[1];config=Path(a.config).expanduser().resolve()
if not config.is_file():raise SystemExit('Create the private device configuration first.')
if platform.system()=='Darwin':
    import os
    path=Path.home()/'Library/LaunchAgents/org.clara.companion.plist';label='org.clara.companion'
    if a.remove:
        subprocess.run(['launchctl','bootout',f'gui/{os.getuid()}',str(path)],check=False);path.unlink(missing_ok=True)
    else:
        path.parent.mkdir(parents=True,exist_ok=True)
        plist={'Label':label,'ProgramArguments':[sys.executable,'-m','clara_agent.daemon','--config',str(config)],'WorkingDirectory':str(root),'RunAtLoad':True,'StartInterval':300,'ProcessType':'Background','StandardOutPath':str(config.parent/'companion.log'),'StandardErrorPath':str(config.parent/'companion-error.log')}
        path.write_bytes(plistlib.dumps(plist));path.chmod(0o600)
        subprocess.run(['launchctl','bootstrap',f'gui/{os.getuid()}',str(path)],check=True)
    print('Companion '+('removed.' if a.remove else 'installed for this Mac user.'))
elif platform.system()=='Windows':
    if a.remove:subprocess.run(['schtasks','/Delete','/TN','Clara companion','/F'],check=True)
    else:
        # Runner switches to the package root so the module resolves correctly.
        runner=config.parent/'clara-companion.cmd'
        runner.write_text('@echo off\r\ncd /d "'+str(root)+'"\r\n"'+sys.executable+'" -m clara_agent.daemon --config "'+str(config)+'"\r\n')
        subprocess.run(['schtasks','/Create','/TN','Clara companion','/SC','MINUTE','/MO','5','/TR','"'+str(runner)+'"','/IT','/F'],check=True)
    print('Companion '+('removed.' if a.remove else 'installed for the signed-in Windows user.'))
else:raise SystemExit('Use a user-level systemd timer to run the companion every five minutes.')

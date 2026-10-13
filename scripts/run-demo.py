"""Run local employee processing and a separately hosted/static manager interface."""
from pathlib import Path
import os
import signal
import subprocess
import sys
import time
from urllib.request import urlopen
import webbrowser
import argparse

ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
children=[]

def stop(*_):
    for child in children:
        if child.poll() is None:child.terminate()
    for child in children:
        try:child.wait(timeout=5)
        except subprocess.TimeoutExpired:child.kill()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local-manager',action='store_true',help='Run an offline manager on port 8766 instead of Vercel.')
    args=parser.parse_args()
    environment=os.environ.copy()
    environment['PYTHONPATH']=f"{ROOT}:{environment.get('PYTHONPATH', '')}".rstrip(':')
    manager=('http://127.0.0.1:8766' if args.local_manager else environment.get('REMOTE_MANAGER_URL','https://pii-guard-mu.vercel.app')).rstrip('/')
    environment['REMOTE_MANAGER_URL']=manager
    signal.signal(signal.SIGTERM,lambda *_:sys.exit(0))
    try:
        if manager=='http://127.0.0.1:8766':
            children.append(subprocess.Popen([sys.executable,'-m','uvicorn','manager.server:app','--host','127.0.0.1','--port','8766','--no-access-log'],env=environment))
        children.append(subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8765','--no-access-log','--no-proxy-headers','--limit-concurrency','4'],env=environment))
        for _ in range(60):
            if any(child.poll() is not None for child in children):raise RuntimeError('A service stopped. Check whether ports 8765/8766 are already in use.')
            try:
                with urlopen('http://127.0.0.1:8765/api/config',timeout=1):break
            except OSError:time.sleep(.25)
        else:raise RuntimeError('Local processor did not become ready.')
        print('Employee: http://127.0.0.1:8765\nManager: '+manager+'/manager',flush=True)
        webbrowser.open('http://127.0.0.1:8765')
        webbrowser.open(manager+'/manager')
        while all(child.poll() is None for child in children):time.sleep(1)
    except KeyboardInterrupt:pass
    finally:stop()

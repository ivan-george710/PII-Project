"""Open the local employee application and its cloud manager."""
from pathlib import Path
import runpy

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).parent / 'scripts' / 'run-demo.py'), run_name='__main__')

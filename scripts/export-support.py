"""Export whitelisted local error events; no company calls or PowerShell required."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from desktop_app.config import data_directory
from desktop_app.support import export_bundle

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:
        print(export_bundle(data_directory(),args.output))
    except (OSError,ValueError):
        raise SystemExit('Export failed. Use a writable NEW zip filename; existing files are not overwritten.')

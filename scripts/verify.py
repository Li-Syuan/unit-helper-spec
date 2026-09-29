"""Run full checks once and retain explicitly requested release evidence."""
import sys
from test_runner import main

if __name__ == '__main__':
    if len(sys.argv) > 2:
        raise SystemExit('Usage: python scripts/verify.py [evidence-label]')
    label = sys.argv[1] if len(sys.argv) == 2 else 'local'
    raise SystemExit(main(['--suite', 'full', '--evidence', label]))

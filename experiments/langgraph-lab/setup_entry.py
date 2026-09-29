"""Fixed entry point; import only this lab's installer under isolated Python."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from setup_lab import main
main()

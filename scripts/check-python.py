"""Fixed pre-venv interpreter check; does not read settings or contact services."""
import struct
import sys
import tkinter
if sys.platform!='win32' or sys.version_info[:3]!=(3,10,4) or struct.calcsize('P')!=8:
    raise SystemExit('Requires Windows x64 Python exactly 3.10.4 with Tcl/Tk.')
print(sys.executable)
print(sys.version)
print('Tk',tkinter.TkVersion)

"""No credentials or environment variable values are printed."""
import importlib.metadata
import json
import platform
import struct
import sys
import tkinter as tk
assert sys.version_info[:3] == (3,10,4), sys.version
assert struct.calcsize('P')*8 == 64
assert sys.platform == 'win32'
root=tk.Tk(); root.withdraw(); patch=root.tk.call('info','patchlevel'); root.destroy()
print(json.dumps({'executable':sys.executable,'version':sys.version,'architecture_bits':64,'platform':platform.platform(),'tk_patch':patch,'packages':{d.metadata['Name']:d.version for d in importlib.metadata.distributions()}},ensure_ascii=False,indent=2))

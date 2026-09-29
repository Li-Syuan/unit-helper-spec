"""Read-only Windows prerequisites; no downloads or network probes."""
import sys


def runtime_available():
    if sys.platform!='win32':return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full') as key:
            if winreg.QueryValueEx(key,'Release')[0]<394802:return False
    except OSError:return False
    runtime='{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}'
    for hive in (winreg.HKEY_CURRENT_USER,winreg.HKEY_LOCAL_MACHINE):
        for view in (winreg.KEY_WOW64_32KEY,winreg.KEY_WOW64_64KEY):
            try:
                with winreg.OpenKey(hive,r'SOFTWARE\Microsoft\EdgeUpdate\Clients'+'\\'+runtime,0,winreg.KEY_READ|view) as key:
                    version=winreg.QueryValueEx(key,'pv')[0]
                    if int(version.split('.')[0])>=86:return True
            except (OSError,ValueError,TypeError):pass
    return False

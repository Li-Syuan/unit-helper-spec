"""Fixed, offline launch prerequisite check for QA agent."""
import argparse
import importlib
import struct
import sys
from pathlib import Path


class LaunchCheckError(Exception):
    pass


def check_environment(project, check_sdk=False):
    """No credentials, network, application data, or user configuration are read."""
    if sys.platform != 'win32':
        raise LaunchCheckError('WINDOWS_REQUIRED')
    if sys.version_info[:3] != (3, 10, 4):
        raise LaunchCheckError('PYTHON_3104_REQUIRED')
    if struct.calcsize('P') != 8:
        raise LaunchCheckError('PYTHON_X64_REQUIRED')
    for relative in ('.venv/Scripts/python.exe', '.venv/Scripts/pythonw.exe',
                     'desktop_app/assets/qa-agent.ico', 'desktop_app/assets/qa-agent.png'):
        if not (project / relative).is_file():
            raise LaunchCheckError('REQUIRED_PROJECT_FILE_MISSING: ' + relative)
    try:
        tkinter = importlib.import_module('tkinter')
        root = tkinter.Tk()
        try:
            root.withdraw()
            root.update_idletasks()
        finally:
            root.destroy()
    except Exception as exc:
        raise LaunchCheckError('TCL_TK_UNAVAILABLE') from exc
    if check_sdk:
        try:
            importlib.import_module('openai')
        except Exception as exc:
            raise LaunchCheckError('OPENAI_SDK_UNAVAILABLE') from exc


def main():
    parser = argparse.ArgumentParser(description='QA agent offline launch checks')
    parser.add_argument('--check-sdk', action='store_true', help='Also check the installed OpenAI SDK')
    args = parser.parse_args()
    try:
        check_environment(Path(__file__).resolve().parents[1], args.check_sdk)
    except LaunchCheckError as exc:
        print('QA agent launch check failed: ' + str(exc), file=sys.stderr)
        return 1
    print('QA agent launch prerequisites are ready.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

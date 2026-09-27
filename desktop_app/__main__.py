import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="單位小幫手本機版")
    parser.add_argument("--config", help="本機 JSON 設定路徑")
    args = parser.parse_args()
    if sys.version_info[:3] != (3, 10, 4):
        raise SystemExit("請使用專案 Python 3.10.4 環境；先執行 scripts/setup.ps1。")
    from .ui import launch
    if not launch(args.config):
        raise SystemExit(1)

if __name__ == "__main__": main()

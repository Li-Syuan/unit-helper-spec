import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="QA agent 本機版")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--config", help="本機 JSON 設定路徑")
    source.add_argument("--groq-trial", action="store_true", help="使用 .env 與獨立資料區試用 Groq 外部 AI")
    args = parser.parse_args()
    if sys.version_info[:3] != (3, 10, 4):
        raise SystemExit("請使用專案 Python 3.10.4 環境；先執行 scripts/setup.ps1。")
    from .ui import launch
    if not launch(args.config, groq_trial=args.groq_trial):
        raise SystemExit(1)

if __name__ == "__main__": main()

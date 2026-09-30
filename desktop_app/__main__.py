import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="QA agent 本機版")
    parser.add_argument('--ui',choices=['web','tk'],default='web',help='主要 WebView 或備用 Tkinter 介面')
    parser.add_argument('--login-preview',action='store_true',help='僅預覽公司登入畫面，不驗證 AD、不啟動工作區')
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--config", help="本機 JSON 設定路徑")
    source.add_argument("--groq-trial", action="store_true", help="使用 .env 與獨立資料區試用 Groq 外部 AI")
    args = parser.parse_args()
    if sys.version_info[:3] != (3, 10, 4):
        raise SystemExit("請使用專案 Python 3.10.4 環境；先執行 scripts/setup.ps1。")
    if args.login_preview:
        from .config import data_directory
        from .login_view import show_login
        show_login(data_directory(),preview=True)
        return
    if args.ui=='tk':
        from .ui import launch
    else:
        from .web_app import launch
    if not launch(args.config, groq_trial=args.groq_trial):
        raise SystemExit(1)

if __name__ == "__main__": main()

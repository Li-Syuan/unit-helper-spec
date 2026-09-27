"""Inspect the same DPI startup as the app, without loading user data or services."""
import argparse
import json
from pathlib import Path
import sys
import tkinter as tk
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from desktop_app.display import initialize_dpi, Display

def main():
    parser=argparse.ArgumentParser(description='QA agent 顯示縮放診斷（不載入對話或公司設定）')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    startup=initialize_dpi();root=tk.Tk();root.withdraw()
    try:
        display=Display(root);display.size_window(root,1280,860,(1050,700));root.update_idletasks()
        report={'startup':startup,**display.diagnostics()}
        text=json.dumps(report,ensure_ascii=False,indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(text,'utf-8')
        print(text)
    finally:root.destroy()

if __name__=='__main__':main()

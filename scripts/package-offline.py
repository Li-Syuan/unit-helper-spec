"""Package committed source and verified wheels; exclude all local credentials/data."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from desktop_app import __version__
from offline_bundle import verify_bundle


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheels',type=Path,required=True)
    args=parser.parse_args()
    verified=verify_bundle(args.wheels,root/'requirements.lock')
    if subprocess.check_output(['git','status','--porcelain'],cwd=root).strip():
        raise SystemExit('Commit reviewed source before creating the delivery package.')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    names=filter(None,subprocess.check_output(['git','ls-files','-z'],cwd=root).decode('utf-8').split('\0'))
    output=root/'artifacts'/'offline'
    name=f'QA-agent-{__version__}-{commit[:8]}-win64-py3104-offline'
    package=output/name
    archive=output/(name+'.zip')
    if package.exists() or archive.exists():raise SystemExit('Delivery already exists; do not overwrite it.')
    package.mkdir(parents=True)
    for name in names:
        path=Path(name)
        if path.is_absolute() or '..' in path.parts or path.parts[0].startswith(('.env','.venv','.runtime','artifacts','company_local')):
            raise SystemExit('Unexpected private path in tracked delivery')
        source=root/path
        if source.is_symlink():raise SystemExit('Linked source not allowed')
        target=package/path;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    shutil.copytree(args.wheels,package/'wheelhouse')
    verify_bundle(package/'wheelhouse',package/'requirements.lock')
    (package/'OFFLINE-START-HERE.txt').write_text(
        f'QA agent {__version__}\n來源提交：{commit}\n\n'
        '1. 解壓縮完整資料夾，不要直接在ZIP中執行。\n'
        '2. 組織提供Python恰好3.10.4 x64完整安裝（含Tk）、WebView2 Runtime與.NET Framework 4.6.2以上。\n'
        '3. 解壓到新的專案資料夾，保留舊專案／環境。關閉App。用CMD執行：install-offline.bat "C:\\approved\\Python3104\\python.exe"。不使用PowerShell；已有.venv拒絕覆寫。\n'
        '   或直接用核准Python執行scripts/install-offline.py --offline-bundle wheelhouse。\n'
        '   安裝後執行 test-company.bat：完整離線回歸與WebView合成旅程。公司API仍未驗證。\n'
        '4. 雙擊start-demo-login.bat，admin/admin僅進入暫存離線合成工作區，關閉清除，不授予公司權限。\n'
        '5. 正式部署先接AD與App使用資格，identity_mode=company未登入不開資料；再用start-app.bat登入並設定核准DVC連線。AD失敗不回退展示。\n6. 依docs/ONE-CLICK-TEST.md分別驗metadata、聊天、核准搜尋與來源；AD／人事／DVC／Oracle本次未實測，勿啟用日報排程作替代。\n\n'
        '含完整已提交原始碼、文件、測試及69個鎖定wheels。沒有Python／WebView2／.NET安裝程式、API key、.env、.venv、對話或SQLite。\n'
        '這是正式App的69套件來源，不使用experiments/langgraph-lab的52套件。Clone本身不含正式wheelhouse。\n'
        '套件缺件、雜湊或lock不符立即停止，不連外補件。不更改執行政策、防毒或TLS。\n'
        '本機回歸、正式服務及人工驗收狀態分開記錄，請以docs/VALIDATION.md為準；本機通過不代表正式服務已驗收。\n'
        'MANIFEST.sha256驗證原始碼；wheelhouse/manifest.json驗證wheels；PACKAGE-CONTENTS.sha256驗證整包。雜湊不是數位簽章。\n',encoding='utf-8-sig')
    metadata={'version':__version__,'source_commit':commit,'wheels':len(verified['files']),'lock_sha256':verified['lock_sha256']}
    (package/'PACKAGE-METADATA.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    contents=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(package).as_posix()+'\n' for p in sorted(package.rglob('*')) if p.is_file())
    (package/'PACKAGE-CONTENTS.sha256').write_text(contents,encoding='utf-8')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as target:
        for path in sorted(package.rglob('*')):
            if path.is_file():target.write(path,path.relative_to(package))
    metadata.update(bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    archive.with_suffix('.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    print(json.dumps(metadata))

if __name__=='__main__':main()

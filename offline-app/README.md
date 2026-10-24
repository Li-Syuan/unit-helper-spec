# Code ZIP：完整 App 離線安裝

下載 GitHub **Code → Download ZIP** 並完整解壓，或 clone 專案。本目錄的 `packages/` 包含正式App全部 **69個鎖定wheels**，不依賴另一個試驗資料夾、Release或Git LFS。

前置條件：Windows x64、核准的 **Python恰好3.10.4完整版**（含Tk、venv、pip）、WebView2 Runtime及.NET Framework4.6.2以上。這些前置軟體不在wheels內。

在專案根目錄以CMD執行（將路徑換成實際核准Python）：

```bat
install-offline.bat "C:\approved\Python3104\python.exe"
test-company.bat
start-app.bat
```

每一步成功才繼續。已有符合lock的`.venv`不需重裝；安裝器拒絕覆寫舊環境。`test-company.bat`包含一次full與合成UI驗證，不需再重跑full。展示登入另用`start-demo-login.bat`，不授予真實組織權限。

## 完整性與資料界線

- `bundle-manifest.json`固定69個檔案、來源與SHA256；根目錄`requirements.lock`是唯一正式依賴清單。
- 安裝前驗證檔案身份、平台、雜湊及lock指紋，以暫存wheelhouse執行`--no-index --no-deps`，完成後核對freeze、pip check及診斷。
- 已存在的root wheelhouse仍需驗證；損壞不回退、不連外補件。缺件、LFS指標或不安全路徑一律停止。
- 原始碼、wheels與[授權文字](../docs/THIRD-PARTY-NOTICES.md)隨Git提供；金鑰、內部設定、使用者資料與Python環境不在交付範圍。
- 安裝診斷預設使用暫存資料，不修改個人profiles或keyring。軟體環境正常不代表達哥、AD與來源品質已驗收。

操作見[開發指南](../docs/DEVELOPMENT.md)、[一鍵驗證](../docs/ONE-CLICK-TEST.md)；接手Agent只需先讀[TO-AGENT](../TO-AGENT.md)，現況以[驗證紀錄](../docs/VALIDATION.md)為準。

本次僅集中原有69個二進位，版本與雜湊不變；四個只供舊lab的套件及其試驗程式已移除。歷史由清理前提交`301c3f8`查閱。

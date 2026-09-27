# QA agent 品牌與圖示 — 0.4.1

產品名稱固定為 **QA agent**。圖示為深綠 Q 形對話夥伴、兩個眼點與綠色確認勾；側欄、視窗、對話署名與捷徑使用同一識別。

## 圖片来源與交付

- 使用 Codex 內建 imagegen 生成，日期 2026-09-27；未使用 CLI／外部模型，也沒有使用公司的 API 金鑰。
- 這是全新圖示，不是修改先前的金屬機器人參考圖。實際提示詞見 [GENERATION-PROMPT.txt](../desktop_app/assets/GENERATION-PROMPT.txt)。
- 原始透明 PNG：desktop_app/assets/qa-agent.png，1254×1254。SHA-256：29cd697887263a1bb195b1e06d6be19a466a40353e678d6a4a74620cd411bf69。
- Windows ICO：desktop_app/assets/qa-agent.ico，含 16、24、32、48、64、128、256 七個尺寸。各尺寸 PNG 同目錄保存。
- 原始圖保留不變；scripts/export-icon.ps1 以 Windows System.Drawing 縮放並封裝 ICO，保留透明角落，不新增 runtime 套件。

![QA agent 圖示](../desktop_app/assets/qa-agent-256.png)

## 套用與相容

branding.py 集中名稱、Windows AppUserModelID 與資源載入。資源從模組所在目錄解析，主視窗持有 PhotoImage 引用；附屬視窗顯式套用同一圖示。資源缺失時側欄提示，功能仍可使用。

本次改名不變更資料目錄、SQLite schema、環境變數或舊 spec。原有對話與排程沿用；舊對話內容不改寫，助理角色的畫面署名改成 QA agent。PNG／ICO 不需要執行期連網。

新桌面捷徑使用 pythonw，因此不留下 console。建立工具及同名保護見 [SHORTCUT.md](SHORTCUT.md)。BAT 檔案本身仍是 Windows 命令檔图示；想從桌面看到 QA agent 圖示，使用建立的捷徑。

## 驗證界線

已檢視 16／32／48px 縮圖及一般／1050×700 桌面畫面；檢查 PNG 角落透明、ICO 七尺寸完整、不同工作目錄載入及缺資源時仍可用。

真實 Tk 主／附屬視窗透過 Windows WM_GETICON 驗證小／大圖示 handle 非空。Windows Tk 的 iconbitmap getter 對 ICO 回傳空字串，不將該 getter 當載入失敗依據。

捷徑測試以 Windows COM 在暫存位置驗證目標、參數、工作目錄、圖示、搬移更新与其他程式同名保留。工作列與真實桌面圖示的 OS 外觀尚未透過人工點選或螢幕檢視驗收；視窗內容截圖及圖示 handle 檢查不冒稱完成該項。

最終三個 Python 3.10.4 環境各 103 項測試通過。使用者桌面已建立 QA agent 捷徑；建立成功與 COM 驗證不代表 OS 最終外觀已人工驗收。完整測試證據見 VALIDATION-LOCAL.md。公司 API、AD、Oracle、Excel 的未實測界線不變。

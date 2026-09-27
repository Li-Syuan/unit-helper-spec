# 實作狀態

| 工作 | 狀態與界線 | 主要檔案 |
|---|---|---|
| Python／鎖版／第二環境 | 三個既有環境各 111 tests 通過，其中一個由離線重建；見 VALIDATION-LOCAL | scripts、requirements.lock |
| 對話／歷史／背景／取消 | 本機已完成；0.3.1 新增側欄、視覺層級、Ctrl+Enter 與按鈕狀態 | ui、theme、core |
| OpenAI 相容 SDK | adapter + MockTransport 通過；公司實測未做 | gateways |
| Plan／是非／單選／多選 | 本機固定流程、服務 gate、修訂／期限／防重 | core、choices、ui |
| TXT／CSV／文字預覽輸出 | 本機已完成；真摘要／改寫需公司 API | files、ui、gateways |
| 三查詢／表格／CSV／TSV | 合成資料通過；真 Oracle／Excel 待驗收 | gateways、files、ui |
| 本機排程／通知 | 可控制時鐘的防重、漏跑、停用與通知測試通過 | core |
| 回報草稿 | 編號／重開修改／本機完成；無管理平台 | core、ui |
| AD／名單／多使用者授權 | 未配置則拒絕；正式接線待公司 | CompanyIdentity |
| Oracle 真實模板 | 停用；需公司核准 SQL／服務 | OracleQueries |
| 舊版資料／排程移轉 | 未碰原 DB；需盤點／備份／dry-run／停舊啟新 | COMPANY-HANDOFF |
| 真實 GUI 滑鼠驗收／Excel | Tk 控制項、兩種尺寸截圖檢視及動作可見性已測；OS 人工與 Excel 待公司 | tests/test_ui、USER-GUIDE |
| 中央 API／管理／更新／EXE | 本次不實作 | 原 v2.2 為後續路線 |

後續接手 agent 應在這裡補「實際完成條件與證據」，不能把新增 adapter 檔案當成整合成功。

## 0.4.0 接手準備

| 工作 | 實際完成與界線 | 入口 |
|---|---|---|
| 動態表單／Plan／排程 | 六種型別，模板失效拒絕、舊 DEMO 相容、不同日期映射；本機合成測試通過 | query_schema、QUERY-CATALOG |
| 串接工具包 | 可重用 SDK／查詢契約與待填公司 hook，正式服務仍未測試 | ADAPTER-TEST-KIT |
| 一鍵診斷 | 真環境檢查與分享白名單報告，沒有公司連線 | diagnose.bat、doctor |
| 離線安裝 | 20-wheel 包驗證，.venv-offline2 已由包重建；本輪重驗 111 tests、lock 一致 | OFFLINE-INSTALL |
| 公司接手工作單 | 必要輸入、六項接線與現場驗收；未填不視為完成 | COMPANY-INPUTS、COMPANY-HANDOFF、COMPANY-ACCEPTANCE |

最終完整證據：docs/validation/development.json、clean-rebuild.json、offline-rebuild.json。依賴無新增；不把骨架、合成測試或本機通過當真實公司通過。

## QA agent 0.4.1

圖示生成、七尺寸 ICO、主／附屬視窗、側欄、對話署名與啟動名稱已更新；捷徑建立工具通過 5 項真 COM 測試，使用者桌面已建立 QA agent 捷徑。資料目錄／schema／依賴未變，原始圖及提示詞已進 repo。三環境最終各 103 項測試。Windows 工作列／桌面外觀及公司服務仍依 BRANDING.md／VALIDATION-LOCAL.md 分開記錄未實測部分。

## 0.5.0 深淺主題與候選圖示

- 首次預設深色；設定 → 外觀可立即切換深色／淺色。
- 外觀獨立存於使用者資料目錄的 ui-preferences.json，不修改公司連線 config。缺失／損壞回復深色，寫入失敗提示後仍保留當次選擇。
- 主題原地更新現有控制項及已開啟的應用內對話框；保留草稿、附件、選取、游標、捲動、Plan 修訂與背景工作。Windows 原生檔案／訊息框遵循系統外觀。
- Appearance、preferences.py、ui.py 是修改入口。公司 agent 沿用現有 UI，不重做基礎架構；服務 API、SQLite schema、查詢／排程及 runtime 依賴不變。
- A～D 候選圖示獨立保存於 desktop_app/assets/candidates，尚未套用；正式 PNG／ICO 與桌面捷徑保持 0.4.1 圖示。選定後才輸出正式多尺寸 ICO。
- 操作及畫面見 docs/UI-DESIGN.md；圖示比較與生成紀錄見 docs/ICON-CANDIDATES.md。基準命令：.venv/Scripts/python.exe -m unittest discover -v。

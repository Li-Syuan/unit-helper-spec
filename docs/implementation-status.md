# 實作狀態

| 工作 | 狀態與界線 | 主要檔案 |
|---|---|---|
| Python／鎖版／第二環境 | 已實測，見 VALIDATION-LOCAL | scripts、requirements.lock |
| 對話／歷史／背景／取消 | 本機已完成 | ui、core |
| OpenAI 相容 SDK | adapter + MockTransport 通過；公司實測未做 | gateways |
| Plan／是非／單選／多選 | 本機固定流程、服務 gate、修訂／期限／防重 | core、choices、ui |
| TXT／CSV／文字預覽輸出 | 本機已完成；真摘要／改寫需公司 API | files、ui、gateways |
| 三查詢／表格／CSV／TSV | 合成資料通過；真 Oracle／Excel 待驗收 | gateways、files、ui |
| 本機排程／通知 | 可控制時鐘的防重、漏跑、停用與通知測試通過 | core |
| 回報草稿 | 編號／重開修改／本機完成；無管理平台 | core、ui |
| AD／名單／多使用者授權 | 未配置則拒絕；正式接線待公司 | CompanyIdentity |
| Oracle 真實模板 | 停用；需公司核准 SQL／服務 | OracleQueries |
| 舊版資料／排程移轉 | 未碰原 DB；需盤點／備份／dry-run／停舊啟新 | COMPANY-HANDOFF |
| 真實 GUI 滑鼠驗收／Excel | Tk 控制項與可見視窗已程式測試；人工與 Excel 待公司 | tests/test_ui、USER-GUIDE |
| 中央 API／管理／更新／EXE | 本次不實作 | 原 v2.2 為後續路線 |

後續接手 agent 應在這裡補「實際完成條件與證據」，不能把新增 adapter 檔案當成整合成功。

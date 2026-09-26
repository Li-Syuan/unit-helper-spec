# 規格包驗證紀錄

日期：2026-09-26｜版本：2.2｜本次交付只有規格、範例與公司開發指令。

## 已檢查

- Markdown 本機連結與程式碼圍欄；新增需求／驗收列接續原表。
- 九個 JSON 可解析；七種 AssistantDecision 及既有 QuestionForm 契約仍保留。
- 三個 query slots 保持 disabled、SQL=null；展示參數名及日期起訖對應現有參數 schema。
- 合成引導請求的 Q01／版本／參數對應目錄；fake clock 日期範例的昨天起訖一致。
- 合成結果欄序與筆數一致；按文件規則計算的 TSV 與範例 expected_tsv 逐字相符，公式樣式文字被保護一格、負數 Decimal 不改值、原 snapshot 不變。
- Tab／CR／LF／NUL 拒絕樣例包含預期特殊字元；快速回報樣例未送出、未附加內容。
- Mock、助理／Oracle／scheduler 停用與更新驗簽設定保留；Plan 未批准，排程選項仍只建立 disabled 草稿。
- UH-01～UH-14、AT-01～AT-27 與開發守則同步；四個 Copilot 角色名稱／引用一致。
- FULL-SPEC 由九份来源重建並調整子目錄連結；ZIP 包含 .github，逐檔 SHA-256 與 manifest 核對。

## 限制與待公司實測

本次為文件／JSON 解析及範例一致性核對，沒有完整 JSON Schema 驗證器，不宣稱 Draft 2020-12 全量驗證通过。TSV 範例驗算不代表 Windows 剪貼簿或 Excel 貼上實測。

未取得公司程式、Oracle、AD、助理或 Excel 工作環境，未執行應用程式、GUI、Plan gate、worker、遷移、更新、真實 SQL、Excel 或 Copilot 委派。AT-01～AT-27 仍由公司端實作與驗收，需分開記錄 mock_passed／real_passed。

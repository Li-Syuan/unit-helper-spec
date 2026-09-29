# QA agent 0.16.0 驗證紀錄

本版將 LangGraph 接入正式工作流程，新增公司 Assistants 協定連接器。以下區分本機實作、合成協定及公司實測；沒有呼叫公司端點或使用真實金鑰。

## 完整回歸與環境

Windows x64、Python **恰好 3.10.4**，69 個直接與間接套件依 requirements.lock 安裝。三個環境依序執行，沒有共用外部 site-packages：

| 環境 | 完整回歸 | 原始紀錄 |
|---|---|---|
| 常駐 .venv | 443 項：442 通過、1 錯誤、0 跳過 | [development.json](validation/development.json) |
| 乾淨重建 .venv-graphverify | 443 項：442 通過、1 錯誤、0 跳過 | [clean-rebuild.json](validation/clean-rebuild.json) |
| 完全離線 .venv-graphoffline | 443 項：442 通過、1 錯誤、0 跳過 | [offline-rebuild.json](validation/offline-rebuild.json) |

三環境的 doctor、pip check、freeze 與鎖檔比對通過。唯一錯誤是既有 test_long_message_theme_copy_and_close_without_mutation 的 Windows 剪貼簿讀回：OpenClipboard failed (Windows error 5)。沒有刪除、跳過或放寬該測試；全套命令保留非零結束碼。須在可互動桌面重測，根因及實際貼上能力尚未確認。

離線環境使用 --no-index --no-cache-dir 從完整 wheelhouse 安裝；69 個 wheel 雜湊、平台與最終 lock 指紋均通過檢查。正式 App 依賴與試驗包分開管理，沒有直接引用試驗包 site-packages。驗證後清除本輪兩個暫存環境，只保留 .venv 及其基礎直譯器 .runtime/python3104。

## 新功能證據

| 範圍 | 狀態與內容 |
|---|---|
| LangGraph | local_real_passed：真 StateGraph／SqliteSaver 執行、重開不自動派發、明確恢復、checkpoint 與成果不一致停止、已完成步驟不重跑 |
| 公司協定 | mock_passed：真 OpenAI SDK + MockTransport，Threads／Messages／Runs、多輪隔離、四個合成 ID、當次 run 訊息分頁、認證／逾時／格式錯誤、取消與未知寫入不重送 |
| 工具限制 | mock_passed：送出 tool_choice=none；requires_action 停止，零 pluginapi 呼叫 |
| 主畫面旅程 | mock_passed：公司對話、多輪、切助理、任務追問／預覽／確認只存 enabled=0；Plan 確認前零子助理、批准後順序執行、防重 |
| 背景請求 | mock_passed：I/O 期間狀態與取消可操作、取消／關閉後晚到結果不保存，關閉等待真實請求收尾 |
| 本機模擬伺服器 | local_real_passed：實際啟動 loopback HTTP，SDK 完成 thread/message/run/list 後關閉；只用合成資料，不代表公司服務通過 |
| 資料保存 | local_real_passed：原對話刪除同步清本機額外回覆快取；已批准獨立流程成果保留。主 Store schema6／dialogue schema1 不變 |

新增 34 項案例保留原有 409 項覆蓋。最後另驗證「成果已提交但 checkpoint 寫入失敗」時，原成果仍為已完成，明確恢復不重新查詢。未知查詢結果及未知遠端寫入仍停止，不以重試猜測。

早期整合測試曾發現 SQLite 連線未即時關閉、Groq 舊介面不接受 context 參數，以及 Tk 最小視窗新增協定列遮住按鈕；已修正並包含在最終全套回歸。中途紀錄保存在本機 artifacts，不以初次失敗宣稱已通過。

## 實際介面

真正啟動 WebView2，以合成資料、模擬 SDK 回覆操作 DOM，9 組檢查通過。檢視深淺主題、一般、小視窗與最大化內容；公司主畫面雙輪對話、模式標示、輸入／取消入口及任務預覽可達。使用 CapturePreview 擷取 App 內容，不截取其他程式。見 [介面摘要](validation/web-display.json) 及 docs/images 的四張現行畫面。

Tk 真控制項回歸涵蓋深淺主題與最小視窗，協定選擇改放附屬視窗，保留原設定頁操作空間。程式 GUI 操作不能代替人工直觀性、真實 IME、Windows 框線外觀或 Excel 貼上驗收。

## 待公司及人工驗收

- 公司 API／CA／多 assistant ID／原生工具能力：**not_tested**。範例確定了協定位置，不保證公司平台接受 tool_choice 或其執行行為。
- 公司 AD、owner 隔離、Oracle 及舊資料移轉：**not_tested**。不得啟用未核准查詢或插件。
- 真人使用性、中文 IME、Excel／Clipboard：**not_tested；本機剪貼簿測試目前失敗**。
- Norton 成效：**未能確認**。沿用固定腳本，沒有關防毒、加排除或修改執行政策；測試通過不代表防毒驗收。
- 沒有啟用 LangSmith 雲端 tracing、自動重試、並行自主代理或未經批准的任務。正常關閉的取消不等於遠端一定已停止。

公司 agent 請依 [接手指令](COMPANY-IMPLEMENTATION.md) 逐項實測並補證據。完整歷史證據可從 Git 查閱；本文件只描述當前交付。

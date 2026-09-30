# QA agent 0.19.0 驗證紀錄

此版為環境試跑候選版，新增聊天中斷恢復、本機內容刪除、安全日誌、資料與助理入口、登入接線及作者資訊。正式依賴仍69套件，組織AD/API/Oracle均未真實驗收。

## 本次結果

| 範圍 | 結果與證據 |
|---|---|
| 全新離線安裝 | **local_real_passed**。Python恰好3.10.4 x64，暫時.venv-verify，69 wheels完整性、doctor、Tk8.6.12、WebView2/.NET、pip check及精確lock比對通過。[安裝證據](validation/offline-install.json) |
| 正式完整回歸 | **failed**。542項：541通過、1錯誤、0skip；測試133.15秒、含環境135.15秒。[完整結果](validation/development.json) |
| 最後登入修正 | **local_real_passed**。full之後補修Tk設定錯誤處理與登入進度列，5項targeted通過，1.52秒；不能因此宣稱full通過。 |
| 最後文案與作者小卡 | **mock_passed / local_real_passed**。quick 選取373/543項，全部通過，測試23.11秒、總計24.32秒；另有作者 targeted 6/6通過（1.77秒）。未因純呈現修改再跑full，不能將quick當543項完整回歸。 |
| 真WebView2 | **local_real_passed**。合成資料及SDK MockTransport，19組旅程；另驗搜尋清除隱藏勾選、指定助理只備稿，以及作者小卡深淺、小視窗、關閉／點外／Esc、晚到結果不重開與零派發。[UI證據](validation/webview.json) |
| 登入與作者 | **mock_passed / local_real_passed**。AD合成函數允許/拒絕/格式/期限/錯誤遮蔽、登入前零Store、使用者資料隔離、取消晚到回覆；真Tk深淺登入及關於顯示通過。AD本身未接線。 |
| 真實LangGraph | **local_real_passed**。正式App批准後的順序流程、真SQLite checkpoint、恢復/防重/取消與本機清理通過；節點輸入和組織回覆為合成。 |
| 組織多ID/搜尋/AD/Oracle | **not_tested**，不能以本機或metadata成功替代。 |

## 唯一完整回歸錯誤

原有案例 `tests.test_dialogs.DialogTests.test_long_message_theme_copy_and_close_without_mutation` 在OpenClipboard回讀遇到Windows error5。沒有刪除案例、放寬斷言或算skip通過。

最後單獨重查此案例仍為相同error5（1項錯誤，0skip，測試0.344秒），因此保留未通過狀態；這次局部重查沒有重跑其他542項。

唯讀環境探針顯示工作階段Locked、前景LockApp；空HWND與自有HWND均無法存取剪貼簿，複製後序號未變，沒有可識別的占用視窗。證據支持鎖定環境限制，但未完成解鎖A/B，不能認定唯一原因或Norton誤報。Tk8.6.12原生剪貼簿忽略部分Win32失敗，畫面「已複製」不是驗收證據。

解鎖後只重跑該案例，不必重跑全部：

```bat
.venv\Scripts\python.exe scripts\test_runner.py --suite targeted --tests tests.test_dialogs.DialogTests.test_long_message_theme_copy_and_close_without_mutation
```

未取得通過證據前，此版不標示full_passed或正式上線完成。先前532項回歸也有同一錯誤，原始證據留本機artifacts。

## 保障與畫面

- SDK合成三輪追問、GET中斷後重開/取回原run或cache、unknown POST與取消不可重送；已完成訊息及原輸入保留，無demo fallback。
- 刪除預覽10分鐘、資料變更重確認、future/session忙碌拒絕、交易回復、快取/checkpoint清理範圍，以及最少request/occurrence防重紀錄保留。
- 日誌/匯出植入秘密測試、白名單、輪替、連結目錄、保存失敗及部分ZIP重試。
- 獨立review找到請求收尾競態、搜尋隱藏選取、助理設定鎖與Tk登入預讀錯誤處理，均已修正並局部驗證。
- WebView1050×700、一般及最大化操作；恢復卡移到最後閱讀位置之前，查詢/資料管理/設定按鈕可達。docs/images維持四張當前截圖。
- 原生登入深淺真視窗已擷取及檢視。鎖定環境下PrintWindow的標題列呈現不代替使用者現場視覺或跨螢幕驗收。
- 作者WebView首輪驗證因測試使用錯誤theme參數失敗，修正為既有name契約後通過，產品未為測試放寬；失敗證據保留artifacts。
- 新功能測試按具體行為補齊，不以數量增加為交付標準；GUI串行，沒有呼叫付費或組織模型。

## 交付與未測界線

正式lock SHA256：`cb89c89a7d9176eab8bb533a42534370225427aac2d51d1a275ede55c7f75c4b`。69 wheels含LangGraph1.2.12、checkpoint-sqlite3.1.1，未使用lab lock。組織依lock檢查決定是否更新環境，不需逐個重裝whl。完整ZIP由已提交來源建立並附雜湊；雜湊不是簽章。

儲存庫與 Release 依維護者選擇公開。分享版驗證 JSON 以 `<PROJECT>` 遮蔽本機絕對路徑，原始證據另存本機 artifacts；測試狀態、數量及錯誤未變更。畫面中的作者資料均為合成測試值。

臨時.venv-verify已於驗證後確認路徑、無連結與程序使用後清除，保留常駐.venv及其基礎.runtime/python3104。

Python完整安裝、WebView2和.NET由組織提供。AD函數如需額外套件，須再更新lock/離線包；不能宣稱現有69套件已包含未提供函數的依賴。

組織真實TLS/權限/多ID/搜尋、角色品質、AD即時撤權/伺服器ACL、Oracle、舊資料、人工使用性、IME、Excel、跨螢幕倍率及PyInstaller均 **not_tested**。Norton成效 **未能確認**，未改防毒或執行政策。App關閉不跑本機排程，取消/登入到期不能保證遠端停止。

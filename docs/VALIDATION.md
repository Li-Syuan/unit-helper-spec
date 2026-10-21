# 1.0.0rc1 候選版驗證（2026-10-21）

本次完成三欄啟用、主對話歷史與草稿、確認保存的記憶及整理後接續，並新增本機自動標題與可收合對話資料夾。主Store仍schema8，DialogueStore升schema4；Python **3.10.4 x64**、69套件lock不變，未新增或重建環境。測試使用隔離合成資料，沒有真實模型或組織API請求。

[交付摘要](validation/workbench.json)與[完整回歸紀錄](validation/development.json)均已去除本機絕對路徑；原始證據與先前失敗保留在本機artifacts，不提交私人資料。

| 範圍 | 結果與界線 |
|---|---|
| 最後完整回歸 | **615/615通過，0失敗、0錯誤、0跳過**；測試540.541秒，含環境542.814秒。doctor、pip check、lock一致性通過。 |
| 服務與遷移 | mock_passed：兩段對話各十輪、途中重開仍用原thread、工具停用、未知POST不重送、取消晚到、記憶隔離與固定快照、來源刪除保留副本、草稿CAS、舊schema1/2/3備份及回復。自動標題/手動覆寫、資料夾版本/刪除保留對話/重新讀取通過。SDK使用真實OpenAI套件搭配MockTransport，不是真實達哥。 |
| 修正後定向 | 關閉保存與日誌14項、三欄端點與CLI/Profiles35項、資料夾/續談/CLI31項通過，隨後已包含在最後full。宿主關閉保存保持CAS，登出／到期及請求中仍能保存當前本機草稿；一般bridge授權不放寬。 |
| 真WebView操作 | v1範圍8組、Skills範圍3組通過：最近對話、搜尋/置頂/改名/草稿、資料夾CRUD/移動/收合保存/跨資料夾搜尋/刪除取消與保留對話、記憶預覽/取消/選用、Skill明確選入、摘要接續、三欄設定及深淺/小視窗/最大化。啟用畫面採合成替身，不讀真金鑰。這次未重跑整份舊WebView smoke。 |
| 原生登入與退出 | 真Tk登入→真WebView→兩份未送出草稿→登出後宿主實際寫入SQLite→關閉與App暫存清理，4項通過。身分為離線展示，不是AD。pywebview刪除獨立瀏覽器快取曾出現WinError32；**瀏覽器快取清理未確認**，不可與已通過的App工作區清理混為一談。 |
| 剪貼簿 | 既有長訊息框複製／讀回案例在此次full通過；正常Windows原生OpenClipboard探測亦成功。保留過去error5證據，未調整權限／防毒或移除測試，不宣稱所有現場桌面的剪貼簿問題都已修復。 |
| CLI與離線來源 | 跨目錄BAT、UTF-8/JSON退出碼、非互動不可批准通過；**69wheels**逐檔來源/hash/lock一致。依賴不變，本輪沒有重新安裝乾淨環境，不能把雜湊核對當成新機實裝。 |
| 現場與人工 | **not_tested**：真實達哥兩輪啟用/十輪續談/搜尋來源、AD、真人不看手冊操作、真IME、Excel及WebView實體剪貼簿。 |

首次full為611項，安全日誌白名單未接受rc版本而有1項失敗。已修正限定rc格式，並增加關閉/過期會話及後續資料夾功能的實際行為保障後完成上述最後full。初次沙箱原子取代被Windows拒絕，改在正常Windows跑測試；資料夾WebView偏好保存亦遇相同限制，正常Windows重跑通過，未弱化原子保存。新增關閉測試曾指向錯誤provider方法，資料夾CLI曾因name參數衝突失敗；均修正後通過，失敗紀錄不刪除。

**交付狀態是候選版，不是正式1.0或上線核准。** 環境需先就緒；同仁直接填endpoint、Assistant ID及API key開始兩輪測試，CA預設使用系統信任，部署預填檔為選用。實際達哥須完成十輪、切兩對話、關閉重開、失敗恢復，以及Skill→Plan→核准搜尋→核對成果→每日排程；採AD時另外驗收登入/拒絕/到期。

精選畫面覆蓋於既有檔案，沒有新增歷代截圖包：

- [深色對話資料夾](images/workspace-dark.png)
- [淺色記憶工作區](images/workspace-light.png)
- [小視窗](images/workspace-small.png)
- [三欄啟用](images/task-preview.png)

歷史版本的驗證詳情從Git查閱；目前development.json只代表本版最後一次full。完整部署與現場工作單見[公司接手](../COMPANY-HANDOFF.md)，日常修改仍使用targeted/quick，不必每次重跑full。

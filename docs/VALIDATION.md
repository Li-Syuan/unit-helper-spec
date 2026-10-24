# 1.0.0rc4 候選版驗證（2026-10-24）

本版將日常操作集中於「對話／我的工作」，加入一次回覆辨識、同頁計畫及整合啟用檢查。Python **3.10.4 x64**、主Store8、DialogueStore5、69套件lock；沒有真實模型或組織API請求，沒有重建venv或調整防毒。

本機整合回歸通過；**仍是候選版，不等於真實達哥、正式1.0或完整Hermes驗收完成**。

## 2026-10-25 目錄整理驗證

本次只整理檔案與交接，版本維持rc4；產品程式、全部646項測試覆蓋、依賴lock、授權及個人資料保持。正式69wheels移至單一`offline-app/packages`，每個原始雜湊與lock相同。移除舊lab、四個僅lab套件、重複接手文件、過期截圖／驗證JSON，以及開發機舊ZIP／解壓／安裝暫存。上一份Code ZIP實裝證據保留`validation/code-zip.json`並帶原提交識別，不當成本次重新安裝。

受影響的離線來源／安裝器／手冊／素材 **29項全部通過**（測試8.683秒、含入口10.27秒）；啟動預檢確認Python3.10.4、Tk、OpenAI SDK、LangGraph與WebView可用；69wheels完整性及本機文件引用通過。未新增環境、未重新安裝、未重跑full或付費API。下方646項full是rc4開發的既有證據，沒有冒充本次重跑。

## 2026-10-25 Copilot接手指引

精簡既有四個開發角色的重複規則，新增三個手動prompt（接手／排錯／單項Hermes規劃），補現行程式與測試對照，修正已移除lab的來源文案。四個角色與三個prompt的YAML解析、名稱／角色引用、唯讀QA工具限制、本機連結／章節及測試模組路徑檢查通過；依官方VS Code格式核對，沒有新增套件或改App程式。

本輪純文件，未跑App回歸或模型請求。公司VS Code／Copilot版本、政策、角色與prompt實際載入仍為not_tested；TO-AGENT提供不支援時的手動附檔方式，不能以靜態格式檢查宣稱現場可用。原始本機檢查摘要為artifacts/copilot-handoff-check.json。

## 實際結果

| 範圍 | 結果與界線 |
|---|---|
| 完整回歸 | **646項全通過，0失敗／錯誤／跳過**；測試225.524秒，含環境227.694秒。環境通過後只做一次full。 |
| 收尾修正 | full之後修正連結保存失敗時的背景規劃刪除保護、過期意圖選擇、嚴格JSON檢查及Skill跨對話選取；相關29項全部通過，含入口8.868秒。未重跑第二次full；最終WebView旅程另通過。 |
| 快速檢查 | 474項通過，含入口83.028秒；未達60秒改善目標。quick／targeted不代替full。 |
| 環境 | 同一Python3.10.4、Tk8.6.12、WebView2、pip check及69套件lock一致。使用隔離合成診斷設定，不驗證真實憑證。 |
| 一般聊天與工作 | `mock_passed`：一個模型回覆同時含文字及建議；兩段各十輪、切換及重開、raw wire保留與記憶固定；普通聊天沒有額外分類請求。工作內容不因顯示在對話就加入模型歷史。 |
| 規劃與生命週期 | `mock_passed`：補問／選項、修改使批准失效、確認前零執行、雙擊防重、取消晚到、未知請求不重送、固定來源識別及本機連結中斷恢復；來源刪除保留獨立成果。 |
| 一次啟用 | `mock_passed`：先保存工具核准，再明確同意最多8次合成請求；2輪聊天兼辨識、3工作格式、3自主決策。各項證據分開、修訂變更失效；聊天可用但工作未通過時保留一般聊天。搜尋另測，不自動核准。 |
| 遷移 | DialogueStore1～4先backup再交易升至5；含失敗回復及備份可讀檢查。舊對話維持原契約；主Store8不變。 |
| 真WebView2 | `local_real_passed` 僅指實際宿主與合成旅程：兩主要入口、聊天／補問／修改／批准／成果、Skill選項及取消、三欄保存與工具核准順序、8次檢查、深淺／1050×700／一般／最大化。操作按鈕可達，草稿與選取Skill隔離。沒有人工使用性或實體IME驗收。 |
| 剪貼簿 | 既有原案例在本次正常Windows環境的單項與full均通過，未改測試、未skip。先前OpenClipboard error5本輪未重現，根因仍未確認；不能宣稱所有桌面環境永久解決。WebView實體複製／貼上另列未測。 |
| 離線來源 | **69個wheels**全部來源／SHA256／lock核對，暫存materialize後清除；零下載。依賴不變，本輪不重新安裝。lock指紋 `cb89c89a7d9176eab8bb533a42534370225427aac2d51d1a275ede55c7f75c4b`。 |
| 未實測 | 真實達哥聊天／新契約／自主搜尋、來源品質、AD、真人不看手冊操作、實體中文IME、Excel、WebView實體剪貼簿及完整Hermes功能。Norton成效未能確認。 |

## 失敗紀錄與判讀

首次full命令在環境前置檢查因既有個人助理憑證缺失（`profile_credential / credential_store_unavailable_or_empty`）停止，沒有執行測試。保留原始失敗報告，之後以暫存診斷設定完成full；未修改使用者設定、金鑰或套件。這不證明原個人設定已修好，使用者需在設定頁確認自己的有效憑證。

受限程序曾拒絕原子設定保存及繼承的SSLKEYLOGFILE存取；正常Windows執行通過，沒有改TLS、防毒或執行政策。早期WebView合成資料／選取器問題及計畫未送出修改狀態已修正；最新旅程通過。原始本機證據留在忽略的artifacts，不公開含路徑的原始紀錄。

[去識別摘要](validation/workbench.json)、[full紀錄](validation/development.json)保存範圍及結果。full紀錄的 `webview_smoke=not_tested` 表示該命令不含WebView；獨立宿主旅程證據在去識別摘要，不能互相代替。

## 正式發布仍須通過

1. 實際endpoint／ID／key完成整合啟用、十輪續談、切換重開及中斷恢復；核對JSON契約與工具停用確實生效。
2. 實際跑完「原地補問 → 確認計畫 → 搜尋與整理 → 人工核對成果／來源 → 另行同意每日排程」，驗證暫停及重開防重。
3. 選用AD時完成真實登入、拒絕與到期；真人在實際桌面完成不看手冊旅程，包含中文IME與複製貼上。沒有證據仍記 `not_tested`。

現行畫面：[深色對話](images/workspace-dark.png)、[淺色成果](images/workspace-light.png)、[小視窗啟用檢查](images/workspace-small.png)、[計畫確認](images/task-preview.png)。接手讀[TO-AGENT](../TO-AGENT.md)；Hermes缺口見[相容性清單](HERMES-COMPATIBILITY.md)。

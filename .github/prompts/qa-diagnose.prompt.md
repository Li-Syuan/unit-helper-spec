---
name: qa-diagnose
description: 依錯誤編號及去識別證據定位一個問題，最小修正並定向驗證。
argument-hint: 操作步驟、預期結果、錯誤編號或安全支援報告
agent: UnitHelper-Coordinator
---

讀 [共用指引](../copilot-instructions.md) 與 [TO-AGENT的測試／問題回報](../../TO-AGENT.md#3-測試與問題回報)。針對本次提供的問題處理，不順便重新設計全部功能。

優先讀取使用者從 rc5「連線診斷」預覽後分享的修復工作單，核對匿名助理、連線修訂、檢查項目與時間。它不含內部端點、Assistant ID 或金鑰；不要要求補這些秘密。聊天通過但進階失敗時保留普通聊天，不要求四角色或 AD 才能排錯。摘要只是說明，不可改成 passed 或手填能力證據。

先依工作單的程式位置選測；診斷本身用 `tests.test_connection_diagnostics`，安全ZIP用 `tests.test_support`，原請求恢復用 `tests.test_dialogue_recovery`。原始證據已知的才判斷根因；網路錯誤不能直接判定為CA。重測要指定項目、版本及明確同意，未知送出或取消未收尾不能建立新測試繞過。

1. 整理可重現步驟與預期／實際結果，先讀去識別錯誤與現有相關案例。若缺足以定位的資訊，只問缺的那項；不要要求原始HTTP body、秘密、整份SQLite或整個使用者目錄。
2. 區分環境、認證／網路、Assistant ID／權限、回覆格式、請求恢復、UI呈現；pip check成功不等於lock完整，metadata失敗不等於聊天失敗。
3. 優先以合成fixture重現，沿目前服務做最小修正。未知POST只檢查原請求；不要換request ID盲目再送、關TLS、手填verified或fallback demo。
4. 選現有targeted；功能加quick，核心交付由整合者一次full。保留首次失敗紀錄。真實API須另有明確授權，無授權不呼叫。

回覆根因證據、修改位置、命令與實際結果、尚未測的現場條件。此prompt不自動授權提交／推送，也不因失敗而重建環境。

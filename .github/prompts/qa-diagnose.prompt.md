---
name: qa-diagnose
description: 依錯誤編號及去識別證據定位一個問題，最小修正並定向驗證。
argument-hint: 操作步驟、預期結果、錯誤編號或安全支援報告
agent: UnitHelper-Coordinator
---

讀 [共用指引](../copilot-instructions.md) 與 [TO-AGENT的測試／問題回報](../../TO-AGENT.md#3-測試與問題回報)。針對本次提供的問題處理，不順便重新設計全部功能。

1. 整理可重現步驟與預期／實際結果，先讀去識別錯誤與現有相關案例。若缺足以定位的資訊，只問缺的那項；不要要求原始HTTP body、秘密、整份SQLite或整個使用者目錄。
2. 區分環境、認證／網路、Assistant ID／權限、回覆格式、請求恢復、UI呈現；pip check成功不等於lock完整，metadata失敗不等於聊天失敗。
3. 優先以合成fixture重現，沿目前服務做最小修正。未知POST只檢查原請求；不要換request ID盲目再送、關TLS、手填verified或fallback demo。
4. 選現有targeted；功能加quick，核心交付由整合者一次full。保留首次失敗紀錄。真實API須另有明確授權，無授權不呼叫。

回覆根因證據、修改位置、命令與實際結果、尚未測的現場條件。此prompt不自動授權提交／推送，也不因失敗而重建環境。

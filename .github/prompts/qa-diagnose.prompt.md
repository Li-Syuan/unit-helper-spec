---
name: qa-diagnose
description: 依錯誤編號及去識別證據定位一個問題，最小修正並定向驗證。
argument-hint: 操作步驟、預期結果、錯誤編號或安全支援報告
agent: UnitHelper-Coordinator
---

依 [qa-fix](../skills/qa-fix/SKILL.md) 處理本次問題；該Skill與 [共用指引](../copilot-instructions.md) 是修復流程及證據規則的單一來源，不重新設計整套功能。

輸入優先採使用者從rc5「連線診斷」預覽後分享的修復工作單，或去識別重現步驟。先依工作單位置選測；診斷本身用 `tests.test_connection_diagnostics`，安全ZIP用 `tests.test_support`，原請求恢復用 `tests.test_dialogue_recovery`。只跑實際受影響項目；完整命令及現場重測限制見 [TO-AGENT](../../TO-AGENT.md#3-測試與問題回報)。

回覆根因證據、修改位置、修正前後結果及未測條件。此prompt本身不授權真實API、提交／推送或重建環境；同一任務已有明確授權則沿用。

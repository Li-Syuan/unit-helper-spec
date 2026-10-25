---
name: qa-takeover
description: 接手現有 QA agent，檢查本機環境並依序完成單助理現場接線。
agent: UnitHelper-Coordinator
---

依 [TO-AGENT](../../TO-AGENT.md)、[共用指引](../copilot-instructions.md) 接手本專案。目標是讓一位達哥助理完成聊天、Skill／Plan、搜尋成果及獨立同意的排程，保留目前功能與現場修改。

先檢查Git狀態、Python及既有 `.venv`，執行既有doctor（不呼叫服務）；沒有環境才按TO-AGENT用核准Python與69wheels安裝。缺件或版本不符列出原因，不循環重裝、不升降版補件。環境正常後停止環境處理。

環境正常後，依 [qa-map](../skills/qa-map/SKILL.md) 的唯讀方法只追蹤目前驗收項目的路徑及測試，不掃整個專案。有使用者已提供的錯誤時，採 [qa-fix](../skills/qa-fix/SKILL.md) 的重現／最小修正流程；按需讀取，不一次載入所有Skills。未提供錯誤時先列下一個可操作的驗收步驟，不憑空重寫模組。使用者在App填endpoint、ID、key，不要求貼秘密到聊天。

本prompt本身不授權真實API請求、寄信、工具核准、排程啟用、提交或推送。已有同一工作明確授權則沿用；否則執行前集中說明對象、合成內容、請求上限與需核准項目。未取得授權時繼續離線工作，現場標not_tested。

交付簡短表格：已完成、實測命令／證據、尚缺資訊、下一個最小動作。預設依序工作，不自動啟動多個子代理。

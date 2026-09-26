# 複製分發與「軟體更新」規格

## 1. 首次導入與固定目錄

目前同仁使用複製版。第一次仍需提供一次新的完整程式資料夾，加入固定 Launcher 與獨立 Updater；原本完全沒有更新能力的 EXE 不能靠遠端自行長出此功能。

```text
<使用者可寫的安裝目錄>/
  UnitHelperLauncher.exe
  UnitHelperUpdater.exe
  trusted-release-key.json        # 只含發布公鑰，不含私鑰
  current.json                   # 目前版本／上一可用版本／pending
  versions/0.1.0/                # 不可變的完整程式 bundle
  staging/                       # 尚未驗證／安裝成功的套件
%LOCALAPPDATA%/Company/UnitHelper/
  desktop.sqlite                 # 草稿／允許快取及更新紀錄
  backups/
  logs/
```

安裝目錄與資料目錄分離；禁止從暫存 ZIP 直接執行。安裝目錄不可寫、缺空間或 policy 禁止更新時顯示原因，不自動提權。初版不支援 network share 作安裝目錄。

## 2. 使用者更新流程

1. 按「軟體更新」，沿用登入向後端查詢適合 Windows 架構／stable channel 的 release。
2. 驗證 manifest 簽章，顯示目前／新版、更新內容與下載大小。沒有新版明確顯示，使用者確認後才下載。
3. 下載到 staging 的 `.partial`，完成後驗證長度、SHA-256 及 ZIP 限制；失敗不碰現有程式。首版斷線可重新下載，不需要分段續傳。
4. 保存草稿，等待本機工作與 SQLite 寫入結束；可取消更新。中央排程继续，桌面不得因更新重新提交未完成 task。
5. UI 將本機待安裝路徑與 update_id 經受限 IPC 交 Updater；不透過命令列傳 token／密碼。主程式關閉後 Updater 取得更新鎖並重新驗證套件。
6. 解壓到新的 versions 子目錄，寫 pending 狀態，atomic replace current 指標，經 Launcher 啟動新版。
7. 新版載入本機資料、開出主畫面後，用專屬 nonce 回報健康。60 秒內成功才標 last_good；失敗回上一個已驗證版本並提示原因。

公司 API 離線本身不算新版啟動失敗；本機資料不能讀／程式崩潰才觸發回復。健康 nonce 綁定 update_id、版本及子程序；舊程序不能誤報新版健康。網路共享後端資料不因 client 回復而倒退。

## 3. Manifest 與信任

自有 release manifest 欄位：format_version、release_id、app_id、version、release_sequence（遞增整數）、platform、channel、package_path、size_bytes、sha256、unpacked_bytes、min_launcher_version、min_backend_api、local_data_schema_min/max、notes、published_at、expires_at。

使用 Ed25519 detached signature，對實際下載的 UTF-8 manifest **原始位元組**簽章。下載端先驗簽，再解析且拒絕重複 JSON keys，驗證 app/platform/channel、expiry、版本範圍與非降版。JSON 重排或換行也需重新簽；不能解析後重新序列化來驗簽。公鑰在 bootstrap 中固定，私鑰只留發布端核准存放處；不接受 manifest 自帶任意新公鑰。

範例 manifest 未簽章、標記 example_only，正式 client 必須拒絕。有 SHA-256 只表示內容一致，不表示來源可信，不能取代發布簽章。傳输使用公司 HTTPS／CA，禁止關閉 TLS 檢查。

package_path 必須為同一核准公司更新 host 的相對路徑；redirect 不得轉送憑證至另一 host。release ID、版本和套件內容不可原地變更。client 保存最高接受 sequence，拒絕重播更舊 release；自動回復僅允許本機記錄的已驗證 last_good，不用伺服器任意低版本繞過檢查。

可信公鑰／Launcher／Updater 的升級第一版採受控 bootstrap 整包替換；min_launcher_version 不符合時提示下載新的 bootstrap，由使用者／IT 完成一次替換，不嘗試自我覆寫尚在執行的 Updater。

## 4. 安裝限制與中斷恢復

- 一次一個 updater，主程式雙開須全部退出；只等待經 launcher 記錄的程序，不用寬泛 kill 所有 Python 程序。
- ZIP 禁止絕對路徑、`..`、symlink／reparse、ADS、裝置名稱、重複目標、大小寫碰撞與覆寫安裝根外檔案；檢查 entry 數量、解壓總量與 manifest 大小上限。
- 首版只接受完整應用包，不能含資料庫快照、私鑰或替換 trusted key／bootstrap 的入口。
- current 指標更新具舊值 backup；下載／解壓中斷時保留舊版，切換後未健康時 Launcher 依 pending journal 回復。
- 僅清理本次 staging 與至少保留「現版＋上一可用版」之外的已知程式版本；從不遞迴清理使用者資料目錄。

## 5. 資料與版本相容

client 更新包不得包含中央 Oracle migration。先在 staging 驗證後端向前／向後相容；伺服器發布需同時支援目前 client 與上一個可用 client 的 v1 API。

本機 SQLite migration 前使用一致性 backup，驗 hash／可開啟。首版自動更新只允許向後相容的新增欄位／表；若無法同時讓 last_good 讀新 schema，擋自動更新，改走明確維護流程，不默默恢復旧備份丟掉新資料。

安裝健康確認前不開放使用者輸入新資料，以便必要時安全還原剛建立的本機 backup。中央 task/排程/issue 已提交結果不隨 client rollback 撤回。

## 6. 發布與驗收

由你在受控 Windows 建置環境產完整 bundle → smoke 與相容測試 → 產 hash/manifest → 私鑰簽章 → 將不可變套件放公司更新儲存 → maintainer 上架。第一版手動發布，不建自動修 code／全公司派送平台。

必測：正常升版、同版本、降版重播、篡改 manifest、錯簽章、錯平台、錯 hash、無網路、下載中斷、磁碟不足、ZIP path escape、雙開、每個 pending 階段斷電、主程式還在使用、啟動失敗回復、本機 migration 不相容、更新後排程不重複。目標是同仁點按鈕就能更新已核准的新應用版本，且失敗時保有可用版本與資料。

<!-- CLAUDE.md | version 1.1 by Albert Sheng | 2026-09-27 | 知識庫移至 doc/ -->
# NiXZ-121 XANES Viewer — Claude Code 入口

回覆語言：繁體中文（程式碼、識別字、commit 訊息可用英文）。

## 知識庫（每次啟動自動載入）
@doc/NiXZ-121_project.md
@doc/TASK_examine_rules.md

`doc/` 是 claude.ai 規劃端與 Claude Code 共用的同步知識庫：規劃端的最新文件放在這裡，CLI 的規格回報也寫回這裡。

- `doc/NiXZ-121_project.md`：權威技術參考（命名、座標、量測格式、處理流程、規則出處、差異紀錄 D1–、參考文獻）。
- `doc/TASK_examine_rules.md`：Phase 2 規則式判定規格；§12 為實作偏差紀錄（由 CLI 填寫）。
- `references/`：文獻原文 PDF。

## 分工
- 規劃、文獻、規格：由 claude.ai 聊天端維護，可能直接更新上述兩份 md。
- 程式、`config.yaml`、`test/`、`README.md`、`status.md`：由 CLI 維護。
- 修改上述兩份 md 時：只增補、不刪除他方內容；遞增檔首與「版本紀錄」表的版本號；規格疑問寫入 TASK 文件 §12 或 `project.md` §10 差異紀錄。
- 開工前先看兩份 md 的檔首版本號；若比上次工作時新，先讀「版本紀錄」最上列了解變更。

## 程式規則
- 門檻一律從 `config.yaml` 讀，不得寫死。
- 網格 11 × 11；z = i − 5，x = 5 − j；唯一鍵為 (zdir, fname) 或 (i, j)，不可只用檔名。
- 不改變第一階段（pipeline）既有輸出格式。
- 程式精簡，不加不必要的抽象與相依。

## 收工
更新 `status.md`、`README.md`，遞增所有修改檔案的版本註解，執行測試，commit 並 push。

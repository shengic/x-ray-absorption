<!-- status.md | version 1.7 by Albert Sheng | 2026-09-28 | help panels 改為非阻塞 Toplevel，說明改繁中 -->
# NiXZ-121 XANES Viewer — 專案狀態

最後更新：2026-09-27 18:30（UTC+8）　依據：commit `9765ac6`（2026-09-27 06:52）與工作目錄現況

維護方式：CLI 每次收工更新「目前版本」「本次完成」「未完成／下一步」；規劃端更新「待確認」「已知問題」。兩邊只增補、不刪除對方內容，改動時遞增本檔版本號。

---

## 1. 目前版本

| 檔案 | 版本 |
|---|---|
| `doc/NiXZ-121_project.md` | 1.4.4 |
| `doc/TASK_examine_rules.md` | 1.4 |
| `doc/status.md` | 1.3 |
| `CLAUDE.md` | 1.1 |
| `README.md` | 2.0.3 |
| `main.py` | 1.6 |
| `pipeline.py` | 1.3 |
| `rules.py` | 1.3.1 |
| `examine.py` | 1.2.0 |
| `config.yaml` | 1.3.0 |

測試：83/83 通過（+4：case-insensitive FNAME_RE、validate_root 完整性、regex skipped 報告、lowercase 認可）。

---

## 2. 已完成

- Phase 1：121 格 pipeline（xraylarch pre_edge／歸一化）、快取 `.npz` + `.json`、GUI 瀏覽、11×11 熱圖。
- Phase 2：規則式 Examine（`rules.py`／`examine.py`），smooth／consistent 雙旗標，最嚴格合併，Rules 面板（勾選＋參數，可選存回 config），規則違規 11×11 熱圖視窗。
- 規則（`config.yaml`）：

| 規則 | 狀態 |
|---|---|
| GATE-EDGE、CAL-EREF | 啟用 |
| R-SNR、R-NOISE-HF、R-PRE-FLAT、R-GLITCH | 啟用 |
| R-EDGE-FWHM、R-NORM-COEFS | 啟用（v1.4 新增，未以真實資料校準） |
| C-SHAPE、C-E0-NBR | 啟用 |
| C-CUMDIFF | 已實作，預設停用 |
| T-DRIFT、T-UPDOWN、T-OUTLIER-SCAN、T-SATURATION | 預留，未實作（需 `.bin` 逐條光譜） |

- 知識庫移至 `doc/`，`CLAUDE.md` 以 `@doc/...` 自動載入。
- v1.4 (main.py) 將 `Rules...` 與 `Edge...` 合併為單一 **`Config...`** 按鈕；Toplevel 內含 `ttk.Notebook` 兩分頁（Rules / Edge），共用 Save-to-yaml checkbox + Apply & Examine + Close。刪除 `show_rules_panel`、`show_edge_panel`、兩份 `_apply_*` 與 `rules_window`、`edge_window` 等狀態欄位（-30 行）。校準時可一次動兩區、跑一次 Examine。
- v1.5 (main.py) Config 面板：每條規則名稱與每個 edge 欄位名稱都是**可點擊的說明連結**（藍色底線、hand2 游標）。點擊 → messagebox 顯示：rule 端 flag/scope/requires + docstring；edge 端 curated 說明字典。rules.py v1.3.0 補齊 7 條規則的 docstring（GATE-EDGE、CAL-EREF、R-NOISE-HF、R-PRE-FLAT、R-GLITCH、R-SNR、C-SHAPE、C-E0-NBR），R-EDGE-FWHM/R-NORM-COEFS/C-CUMDIFF 原本就有。
- v1.6 (main.py) 說明面板改為**非阻塞 Toplevel**（不再用 messagebox）：可捲動 Text 內容 + 「關閉 (Close)」按鈕；`transient(root)` 讓它跟隨主視窗但不搶焦點，主視窗仍可操作。多個 rule/edge 說明可並開比對。rules.py v1.3.1 與 main.py `EDGE_HELP` 字典**全部翻譯為繁體中文**。

---

## 3. 目前資料處理結果

- `data/` 內已處理 **121 / 121** 格（`.json` + `.npz` + `.examine.json` 各 121）。
- Examine 結果：run_id `987973d5`，**76/121 usable**（v1.4 新規則 R-EDGE-FWHM 與 R-NORM-COEFS 皆已啟用；門檻尚未以實資料校準）。

---

## 4. 未完成／下一步

| 優先 | 項目 | 負責 |
|---|---|---|
| ~~1~~ | ~~修正 D9（檔名大小寫），重跑 Process all + Examine，確認 121/121~~ | ~~CLI~~ **已完成 2026-09-27** |
| ~~2~~ | ~~commit `test/` 下 3 個未提交檔~~ | ~~CLI~~ **已完成 2026-09-27** |
| ~~1~~ | ~~以 121 格實際分佈校準 R-EDGE-FWHM、R-NORM-COEFS 及 z 門檻~~ | ~~使用者＋規劃端~~ **已完成 2026-09-28**（D8 保留 [0.10, 1.5]；D10 兩規則 z 改為 [2.5, 4]） |
| 1 | 其餘 smooth／consistent 規則的 z 門檻（R-SNR、R-NOISE-HF、R-PRE-FLAT、R-GLITCH、C-SHAPE、C-E0-NBR）是否也要由 121 分佈校準 | 使用者決定 |
| 2 | 確認 `.bin` 格式後實作 T-* 規則 | 待資料（project.md §8 #2） |
| 3 | MySQL 接線（`db.enabled: false`） | 待 schema 定稿 |
| 4 | `combine_mode: weighted`（目前拋 NotImplementedError） | 未排程 |

---

## 5. 已知問題（詳見 `doc/NiXZ-121_project.md` §10）

| ID | 摘要 | 狀態 |
|---|---|---|
| D9 | `image_AI_Ni/Z6_1/x5_0_666_786_XANES.txt` 開頭為小寫 `x`；`pipeline.FNAME_RE` 為 `^X...`（大小寫敏感），Windows 上 `glob("X*")` 不分大小寫會列出、再被 regex 濾掉 → 該格**無警告地略過** | **結案（2026-09-27）**：`FNAME_RE` 加 `re.IGNORECASE`；新增 `validate_root()` 完整性檢查；121/121 已重跑 |
| D2 | 各 Z 資料夾的區段編號不同（例：Z6_1 為 1_120、134_254、268_388…；Z5_0 為 1_120、136_256、272_392…），`X0_5_1_120` 同名屬巧合 | 已釐清，見 §10 |
| D8 | GATE-EDGE 門檻 [0.1, 1.5] vs Gaur 2026 [0.5, 2.0] | **結案（2026-09-28）**：121 格分佈驗證，[0.10, 1.5] pass 110/121 (90.9%)；11 FAIL 全於幾何邊緣；Gaur 標準對 mapping 過嚴 |
| D10 | R-EDGE-FWHM / R-NORM-COEFS 預設 z 門檻 `[3, 5]` 對近 Gaussian 分佈過保守（fail_z=5 永不觸發） | **結案（2026-09-28）**：兩規則改為 `[warn=2.5, fail=4]`（Leys 2013 預設；4σ 明確離群）；R-EDGE-FWHM 3 WARN 0 FAIL，R-NORM-COEFS 2 WARN 0 FAIL |

---

## 6. 待確認（規劃端 → 使用者）

1. 參考物是否為 Ni 箔（影響 §4.1 化學態判讀）。
2. 樣品台步距與光束尺寸（判斷格子是否重疊）。
3. 4 個 ADC 通道的對應偵測器與增益（D3）。
4. 是否另有相機／顯微影像需要納入判定。

---

## 版本紀錄

| 版本 | 日期 | 內容 |
|---|---|---|
| 1.7 | 2026-09-28 | main.py v1.6 / rules.py v1.3.1：說明面板改為**非阻塞** Toplevel（可捲動 Text + 關閉按鈕，不搶焦點、可並開）。所有規則 docstring 與 EDGE_HELP 字典**翻譯為繁體中文**。83/83 tests |
| 1.6 | 2026-09-28 | main.py v1.5 / rules.py v1.3.0：Config 面板加 clickable help links。規則名稱點擊 → flag/scope/requires + rule fn docstring；edge 欄位名稱點擊 → curated EDGE_HELP 字典說明。補齊 7 條缺 docstring 的規則（GATE-EDGE、CAL-EREF、R-NOISE-HF、R-PRE-FLAT、R-GLITCH、R-SNR、C-SHAPE、C-E0-NBR）。83/83 tests |
| 1.5 | 2026-09-28 | main.py v1.4：`Rules...` + `Edge...` 合併為 `Config...` 分頁面板（ttk.Notebook）。共用 footer（Save + Apply + Close），一次 Apply 同步兩區並只跑一次 Examine。刪除 4 個舊方法與 2 個狀態欄位，程式淨減 ~30 行。83/83 tests |
| 1.4 | 2026-09-28 | main.py v1.3：新增 `Edge...` 按鈕與 Toplevel 編輯器（`config.yaml edge.*` 8 個欄位；list 欄位 [a, b] 用兩個 Entry；可選 Save-to-yaml；Apply 立即重跑 Examine）。GUI smoke 測試通過（83/83） |
| 1.3 | 2026-09-28 | D10 結案：R-EDGE-FWHM 與 R-NORM-COEFS 的 z 門檻由 110 gate-pass 分佈校準 `[3, 5] → [2.5, 4]`。分佈近乎 Gaussian，fail_z=5 於本資料永不觸發。config.yaml v1.3.0。校準後 R-EDGE-FWHM 3 WARN、R-NORM-COEFS 2 WARN；usable 保持 76/121 |
| 1.2 | 2026-09-28 | D8 結案：GATE-EDGE `[0.10, 1.5]` 由 121 格 edge_step 分佈驗證（median=0.345, MAD·1.4826=0.167, 天然分界 0.10；110/121 pass；Gaur 標準對 mapping 過嚴）。config.yaml v1.2.1 加註出處註解 |
| 1.1 | 2026-09-27 | CLI 端更新：D9 結案（`FNAME_RE` IGNORECASE + `validate_root` + GUI 完整性顯示 + `_select_cell_by_xz` case-insensitive）；`--batch` 重跑產出 121/121 sections, 0 errors；Examine 121 cells, 76 usable；83/83 tests；§1 版本、§3 處理結果、§4 待辦、§5 D9 狀態全部同步 |
| 1.0 | 2026-09-27 | by Albert Sheng。初版：依 commit 9765ac6 與工作目錄現況建立；記錄 120/121 處理結果與 D9 |

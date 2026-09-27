<!-- status.md | version 1.0 by Albert Sheng | 2026-09-27 | 由 claude.ai 規劃端依 repo 現況建立 -->
# NiXZ-121 XANES Viewer — 專案狀態

最後更新：2026-09-27 18:30（UTC+8）　依據：commit `9765ac6`（2026-09-27 06:52）與工作目錄現況

維護方式：CLI 每次收工更新「目前版本」「本次完成」「未完成／下一步」；規劃端更新「待確認」「已知問題」。兩邊只增補、不刪除對方內容，改動時遞增本檔版本號。

---

## 1. 目前版本

| 檔案 | 版本 |
|---|---|
| `doc/NiXZ-121_project.md` | 1.4.1 |
| `doc/TASK_examine_rules.md` | 1.4 |
| `doc/status.md` | 1.0 |
| `CLAUDE.md` | 1.1 |
| `README.md` | 2.0.2 |
| `main.py` | 1.1 |
| `pipeline.py` | 1.2 |
| `rules.py` | 1.2.0 |
| `examine.py` | 1.2.0 |
| `config.yaml` | 1.2.0 |

測試：最近一次紀錄 79/79 通過（TASK 文件 v1.4）。本檔建立時未重跑。

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

---

## 3. 目前資料處理結果

- `data/` 內已處理 **120 / 121** 格（`.json` + `.npz` + `.examine.json` 各 120）。
- 缺少：`Z6_1` 的中心格 (x, z) = (0, +1)。原因見 §5 D9。

---

## 4. 未完成／下一步

| 優先 | 項目 | 負責 |
|---|---|---|
| 1 | 修正 D9（檔名大小寫），重跑 Process all + Examine，確認 121/121 | CLI |
| 2 | commit `test/` 下 3 個未提交檔（README.md、test_examine.py、test_pipeline.py，+17／−10 行） | CLI |
| 3 | 以 121 格實際分佈與目視對照校準門檻（GATE-EDGE D8、R-EDGE-FWHM、R-NORM-COEFS、z 門檻） | 使用者＋規劃端 |
| 4 | 確認 `.bin` 格式後實作 T-* 規則 | 待資料（project.md §8 #2） |
| 5 | MySQL 接線（`db.enabled: false`） | 待 schema 定稿 |
| 6 | `combine_mode: weighted`（目前拋 NotImplementedError） | 未排程 |

---

## 5. 已知問題（詳見 `doc/NiXZ-121_project.md` §10）

| ID | 摘要 | 狀態 |
|---|---|---|
| D9 | `image_AI_Ni/Z6_1/x5_0_666_786_XANES.txt` 開頭為小寫 `x`；`pipeline.FNAME_RE` 為 `^X...`（大小寫敏感），Windows 上 `glob("X*")` 不分大小寫會列出、再被 regex 濾掉 → 該格**無警告地略過** | 開放 |
| D2 | 各 Z 資料夾的區段編號不同（例：Z6_1 為 1_120、134_254、268_388…；Z5_0 為 1_120、136_256、272_392…），`X0_5_1_120` 同名屬巧合 | 已釐清，見 §10 |
| D8 | GATE-EDGE 門檻 [0.1, 1.5] vs Gaur 2026 [0.5, 2.0] | 開放 |

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
| 1.0 | 2026-09-27 | by Albert Sheng。初版：依 commit 9765ac6 與工作目錄現況建立；記錄 120/121 處理結果與 D9 |

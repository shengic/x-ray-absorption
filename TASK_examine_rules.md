<!-- TASK_examine_rules.md | version 1.0.1 by Albert Sheng | 2026-09-26 | 已由 Claude Code 實作，MySQL 部分延後 -->

# 任務：在 NiXZ-121 XANES Viewer 加入規則式「平滑／可用」判定

給 Claude Code CLI 的實作說明。請完整讀完再動手。
專案背景與命名規則見 `NiXZ-121_project.md`（v1.1.1），本文件引用其章節編號（§）。

---

## 0. 開工前必做（不可跳過）

1. 讀 `main.py`、`pipeline.py` 全文。
2. **確認實際鍵名**，列出後再開始寫程式：
   - `pipeline.process_section()` 寫出的 json 有哪些鍵（本文件假設有 `i, j, x, z, zdir, fname, e0, mu_ref_e0, edge_step, q1_edge_step, q2_hf_noise, q3_pre_flatness, q4_e0_shift_vs_ref, q5_glitches, q6_white_line, usable`）。
   - npz 內的陣列名稱（本文件假設有 `energy, norm`）。
   - `q2_hf_noise`、`q3_pre_flatness` 的實際計算方式與單位（是否為 norm 單位、q3 是否為前緣直線擬合殘差 RMS）。
3. 若實際鍵名或定義與本文件假設不同，**以程式現況為準**，在本文件末「§12 實作偏差」記錄差異，不要改 pipeline 的既有輸出去遷就本文件。
4. 有任何無法從程式判斷的地方，先停下來問使用者，不要猜。

---

## 1. 目標

新增第二階段「Examine」：讀入 121 格已快取的結果，依**可獨立啟用／停用、可擴充的規則**做相對判定，輸出每格兩個旗標：

| 旗標 | 意義 | 依據 |
|---|---|---|
| `smooth` | 量測資料品質 | 雜訊、glitch、前緣平坦度、SNR |
| `consistent` | 與全圖是否一致 | 形狀差、E₀ 與鄰格差 |

`consistent = WARN/FAIL` 但 `smooth = PASS`，代表**可能是真實化學差異**，不是壞資料。GUI 與文件必須清楚呈現這個差別，不可合併成單一 `usable` 後丟棄。

等級：`PASS`(0)、`WARN`(1)、`FAIL`(2)、`N/A`（規則停用或前置規則不可用）。

---

## 2. 限制條件

- **不改變第一階段行為**：`Process all`、`--batch`、快取路徑 `data/{Zdir}/{stem}.npz|json`、`image/...` 維持原樣。
- 判定只讀快取，不重跑 larch。
- 程式精簡，不加不必要的抽象層或相依套件。新增相依只允許 `pyyaml`；MySQL 驅動（`pymysql`）僅在 `db.enabled: true` 時 import。
- GUI 在**沒有 MySQL 時必須完全可用**（結果寫 json）。
- 網格固定 11 × 11 = 121（§1 D1），座標 z = i − 5、x = 5 − j（§2）。
- 不要把資料夾名稱以外的檔名當唯一鍵：同名檔可出現在不同 Z 資料夾（§10 D2）。唯一鍵為 (zdir, fname) 或 (i, j)。

---

## 3. 新增檔案

```
config.yaml      判定參數、規則開關、邊能容差、DB 連線
rules.py         Rule 定義、REGISTRY、各規則函式
examine.py       載入快取 → 建立 context → 依相依順序執行規則 → 合併 → 輸出
db.py            （選用）MySQL 寫入；db.enabled=false 時不載入
tests/test_examine.py
```

`main.py`、`pipeline.py` 只做必要的小改（見 §8）。

---

## 4. 規則架構

```python
@dataclass
class Rule:
    id: str            # 例 "R-NOISE-HF"
    flag: str          # "gate" | "smooth" | "consistent"
    scope: str         # "cell"（單格可算）| "grid"（需全圖統計或鄰格）
    requires: tuple    # 前置規則 id
    fn: Callable       # fn(ctx, cell, params) -> (level:int|None, value:float|None, reason:str)
```

- 以 decorator 註冊到 `REGISTRY`。新增規則 = 新增一個函式 + `config.yaml` 一行，不改 `examine.py`。
- `examine.py` 依 `requires` 做拓撲排序執行。
- 規則停用 → 該規則結果為 `N/A`。
- 前置規則停用或未通過 → 下游規則結果為 `N/A`，reason 寫明原因，例如 `"requires CAL-EREF (disabled)"`。**不可在未校正資料上靜默繼續計算。**
- `N/A` 不計為 PASS。

---

## 5. 初版規則清單

z-score 一律為穩健 z：`z = (v − median) / (1.4826 · MAD)`，只用通過 `GATE-EDGE` 的格子計算 median 與 MAD。MAD = 0 時該規則回傳 `N/A`。

| ID | flag | scope | requires | 定義 | 判定 |
|---|---|---|---|---|---|
| `GATE-EDGE` | gate | cell | — | `edge_step` 在 [min, max] | 超出 → FAIL，且該格不進入統計基準；smooth、consistent 皆標 FAIL／N/A |
| `CAL-EREF` | gate | grid | — | L1：`mu_ref_e0 − e0_nominal` 在 `mono_offset_window_eV`；L3：`|mu_ref_e0 − median(mu_ref_e0)| ≤ ref_e0_spread_tol_eV` | L1 失敗 → FAIL；L3 失敗 → WARN。同時產生校正位移 `shift_k = mu_ref_e0_k − median(mu_ref_e0)`（§4.2） |
| `R-SNR` | smooth | grid | GATE-EDGE | `snr = edge_step / q3_pre_flatness` | 單側偏低：z < −warn → WARN，< −fail → FAIL |
| `R-NOISE-HF` | smooth | grid | GATE-EDGE | `q2_hf_noise` | 單側偏高 |
| `R-PRE-FLAT` | smooth | grid | GATE-EDGE | `q3_pre_flatness` | 單側偏高 |
| `R-GLITCH` | smooth | grid | GATE-EDGE | `q5_glitches` | 單側偏高；另加絕對門檻 `max_count` |
| `C-SHAPE` | consistent | grid | GATE-EDGE, CAL-EREF | 校正後 norm 內插到共同網格 [E₀med−30, E₀med+150] eV、步長 0.3 eV；`shape_R = Σ(n−n_med)²/Σn_med²`，n_med 為通過格的逐點中位數 | 單側偏高 |
| `C-E0-NBR` | consistent | grid | GATE-EDGE, CAL-EREF | 校正後 E₀ 與 8 鄰格（存在者）中位數之差；鄰格 < 2 個 → N/A | 雙側 |

注意：
- `R-SNR` 與 `R-PRE-FLAT` 都用到 `q3`，屬相關規則；合併採「最嚴格法」時影響可接受，加權分數時兩者權重需調低（見 §6）。
- 若 §0 確認 `q3_pre_flatness` 不是前緣殘差 RMS，`R-SNR` 的分母改用正確量，並記錄於 §12。

**預留（本次不實作，只在 config 列出且 `enabled: false`）**：`T-DRIFT`、`T-UPDOWN`、`T-OUTLIER-SCAN`、`T-SATURATION`。這些需要 `.bin` 逐條光譜，格式尚未確認（§8 待辦 2）。

---

## 6. 合併邏輯

- 預設 `combine_mode: worst`：旗標等級 = 該旗標下所有**已評估**規則的最高等級。
- 若該旗標下全部規則皆 N/A → 旗標為 `N/A`。
- 另輸出 `n_evaluated / n_enabled`，GUI 顯示如 `smooth: PASS (4/4)`。
- 保留 `combine_mode: weighted` 介面（S = Σwᵢqᵢ，qᵢ 由 z 映射到 0–1），本次可只實作 `worst`，`weighted` 丟 `NotImplementedError` 並在 config 註明。
- `usable` 定義：`smooth == PASS or WARN` 且 GATE 通過。`consistent` 不影響 `usable`。

---

## 7. config.yaml

```yaml
# config.yaml | version 1.0.0
grid: {n: 11}

edge:                       # 見 NiXZ-121_project.md §4.2
  element: Ni
  edge: K
  e0_nominal_eV: 8333.0
  e0_alt_eV: 8331.90
  e0_nominal_tol_eV: 1.5
  mono_offset_window_eV: [-5.0, 25.0]
  ref_e0_search_eV: [8320.0, 8370.0]
  ref_e0_spread_tol_eV: 0.3

examine:
  combine_mode: worst       # worst | weighted（weighted 尚未實作）
  shape_grid_eV: [-30.0, 150.0, 0.3]   # 相對 median E0：起、終、步長

rules:
  GATE-EDGE:  {enabled: true,  min: 0.10, max: 1.5}
  CAL-EREF:   {enabled: true}
  R-SNR:      {enabled: true,  warn_z: 3, fail_z: 5}
  R-NOISE-HF: {enabled: true,  warn_z: 3, fail_z: 5}
  R-PRE-FLAT: {enabled: true,  warn_z: 3, fail_z: 5}
  R-GLITCH:   {enabled: true,  warn_z: 3, fail_z: 5, max_count: 5}
  C-SHAPE:    {enabled: true,  warn_z: 3, fail_z: 5}
  C-E0-NBR:   {enabled: true,  warn_z: 3, fail_z: 5}
  T-DRIFT:        {enabled: false}
  T-UPDOWN:       {enabled: false}
  T-OUTLIER-SCAN: {enabled: false}
  T-SATURATION:   {enabled: false}

db:
  enabled: false
  host: localhost
  port: 3306
  schema: xanes
  user: xanes
  password_env: XANES_DB_PASSWORD   # 密碼只從環境變數讀，不寫入檔案與版控
```

所有數值皆為起始值，不是文獻標準；程式中不得另外寫死門檻。

---

## 8. 程式修改

### 8.1 examine.py

- `run_examine(data_root, config) -> ExamineRun`
- 輸出：
  - 每格寫回 `data/{Zdir}/{stem}.examine.json`（不覆寫第一階段的 `{stem}.json`），內容：`run_id, smooth, consistent, usable, rules: {id: {level, value, reason}}`。
  - 全圖寫 `data/examine_run.json`：`run_id, computed_at, pipeline_version, config_hash(sha256 of canonical config), config, combine_mode, n_cells`。
- CLI：`python main.py --examine ROOT`（不開 GUI）；可與 `--batch` 串接：`--batch ROOT --examine`。

### 8.2 main.py（GUI）

1. 頂列新增按鈕 `Examine 121`：呼叫 `run_examine`，完成後刷新目前選取格的資訊與熱圖。
2. 新增 `Rules...` 按鈕：開規則面板（Toplevel），每條規則一列：勾選框（enabled）＋主要參數欄位。按 `Apply & Examine` 以面板狀態重跑。面板狀態可「Save to config.yaml」，預設不自動存檔。
3. `11×11 heatmap` 改版：
   - Combobox 選著色量：`edge_step`、各 Q 值、各規則的 z 值、`smooth`、`consistent`。
   - 旗標模式：PASS 綠、WARN 黃、FAIL 紅、N/A 灰；`consistent` 非 PASS 的格子加框線。
   - 點格子 → `i = round(z)+5`、`j = 5 − round(x)` → 選取左側 Z、X Listbox 並觸發 `on_x_select`。
   - 保留現有座標轉換 `grid[i, 10 − j]` 與 `origin="lower"`（已驗證正確）。
4. `Section info` 新增：
   ```
   smooth:     WARN (4/4)  — R-NOISE-HF z=+3.4
   consistent: PASS (2/2)
   usable:     YES
   ```
   尚未執行 Examine 時顯示 `examine: not run`。現有 `usable (preliminary threshold)` 一行改名為 `usable (single-cell, legacy)`，保留不刪。
5. Combined 圖：若已有 examine 結果，疊加灰色 n_med（校正後）與下方殘差子圖（norm − n_med）。

### 8.3 pipeline.py

原則上不改。若需要暴露 `PIPELINE_VERSION` 常數供 examine 記錄，只新增該常數。

### 8.4 db.py（db.enabled=true 時）

MySQL，InnoDB，utf8mb4：

```sql
CREATE TABLE IF NOT EXISTS sections (
  section_id INT AUTO_INCREMENT PRIMARY KEY,
  dataset_id VARCHAR(32) NOT NULL, i TINYINT NOT NULL, j TINYINT NOT NULL,
  z TINYINT NOT NULL, x TINYINT NOT NULL,
  zdir VARCHAR(32) NOT NULL, fname VARCHAR(128) NOT NULL,
  seg_start INT, seg_end INT,
  UNIQUE KEY uk_cell (dataset_id, i, j)
);
CREATE TABLE IF NOT EXISTS qc_run (
  run_id CHAR(36) PRIMARY KEY, computed_at DATETIME NOT NULL,
  pipeline_version VARCHAR(32), config_hash CHAR(64), config_json JSON,
  combine_mode VARCHAR(16)
);
CREATE TABLE IF NOT EXISTS qc_rule_result (
  run_id CHAR(36), section_id INT, rule_id VARCHAR(32),
  enabled BOOL, level TINYINT NULL,        -- NULL = N/A
  value DOUBLE NULL, reason VARCHAR(255),
  PRIMARY KEY (run_id, section_id, rule_id),
  FOREIGN KEY (run_id) REFERENCES qc_run(run_id),
  FOREIGN KEY (section_id) REFERENCES sections(section_id)
);
CREATE TABLE IF NOT EXISTS qc_verdict (
  run_id CHAR(36), section_id INT,
  smooth VARCHAR(4), consistent VARCHAR(4), usable BOOL,
  n_eval_smooth TINYINT, n_enabled_smooth TINYINT,
  PRIMARY KEY (run_id, section_id)
);
```

- 每次 Examine 產生新 `run_id`（uuid4），**不覆寫舊結果**。
- 光譜陣列表 `spectra`（`MEDIUMBLOB`，float64 LE）本次不需要，可留 TODO。
- 連線失敗時 GUI 顯示警告並照常寫 json，不中斷。

---

## 9. 測試（tests/test_examine.py）

用合成資料，不依賴真實 121 檔：

1. 121 格合成光譜：arctan 邊 + 高斯 white line + 白雜訊 σ = 0.005，E₀ = 8346 ± 0.05 eV。
2. 注入缺陷並斷言：
   | 注入 | 預期 |
   |---|---|
   | 1 格雜訊 ×5 | `R-NOISE-HF` FAIL，smooth FAIL |
   | 1 格 edge_step = 0.02 | `GATE-EDGE` FAIL，不進入 median |
   | 1 格 E₀ +2 eV、雜訊正常 | `C-E0-NBR` 非 PASS，smooth PASS，usable YES |
   | 1 格 5 個尖刺 | `R-GLITCH` 非 PASS |
   | 停用 `CAL-EREF` | `C-SHAPE`、`C-E0-NBR` 為 N/A，reason 含 `requires CAL-EREF` |
   | 停用全部 smooth 規則 | smooth = N/A，usable 不得為 YES |
3. `config_hash` 相同 config 兩次計算結果一致；改任一參數後不同。
4. 座標：點擊 (x, z) = (+5, −5) 對應 `Z0_-5/X0_5`；(−5, +5) 對應 `Z10_5/X10_-5`。

---

## 10. 驗收標準

- [ ] §0 鍵名確認結果已寫入 §12
- [ ] `python main.py --batch ROOT --examine` 無 GUI 完成並輸出 examine json
- [ ] GUI：Examine、Rules 面板、熱圖旗標模式、點格跳轉、Section info 新欄位皆可用
- [ ] 停用任一規則後重跑，結果與相依關係符合 §4
- [ ] 無 MySQL 環境下全部功能可用；`db.enabled: true` 時寫入四張表
- [ ] `pytest` 全部通過
- [ ] 第一階段輸出檔案與行為未改變（比對 1 格 json 前後內容）

---

## 11. 收尾（依使用者慣例）

1. 更新 `status.md`（本次完成、未完成、已知問題）與 `README.md`（新增 Examine、Rules、`--examine`、config.yaml 說明）。
2. 所有修改或新增的文件與程式，檔首版本註解遞增（`main.py` 1.0 → 1.1；新檔從 1.0.0 起）。
3. 本文件 §12 填寫完成後，版本改為 1.0.1。
4. commit 並 push 到 GitHub；commit 訊息列出新增規則與設定檔。

---

## 12. 實作偏差（由 Claude Code 填寫）

| 項目 | 本文件假設 | 實際情況 | 處置 |
|---|---|---|---|
| json 鍵名 | i, j, x, z, zdir, fname, e0, mu_ref_e0, edge_step, q1_edge_step, q2_hf_noise, q3_pre_flatness, q4_e0_shift_vs_ref, q5_glitches, q6_white_line, usable | 全數存在（另有 seg_start/end, pre1, pre2, norm1, norm2, nnorm, nvict）| 直接使用 |
| npz 陣列名 | energy, norm | 皆存在，另有 mu, mu_ref, pre_edge, post_edge, flat, e0, edge_step | 直接使用 |
| q2 定義／單位 | 後緣高頻殘差 RMS，norm 單位 | 對 `flat` 做二次差分後 RMS，範圍 E ≥ E₀+150 eV。flat 屬歸一化單位 → 符合假設 | 符合 |
| q3 定義／單位 | 前緣擬合殘差 RMS | `RMS(mu − pre_edge_line)` 於 `[E₀+pre1, E₀+pre2]`，**單位為原始 μ（未除以 edge_step）** | 保留現定義。R-SNR = edge_step / q3，兩者同 μ 單位 → 無因次，正確 |
| 專案文件檔名 | `NiXZ-121_project.md` v1.1.1 有 §4.2 | 現行為 `NiXZ-121.md` v1.0，無 §4.2 校正細節章節 | 以 `config.yaml` §7 為權威來源；後續將於 `NiXZ-121.md` 增補 §4.2 |
| 測試資料夾名 | `tests/test_examine.py` | 現有 `test/` (單數) | 沿用 `test/test_examine.py` |
| MySQL | §8.4 db.py + 4 張表 | **本次未實作**，待 schema 定稿後再開 | `config.yaml` `db.enabled: false`；examine.py 完全不 import pymysql；預留 `NotImplementedError` 介面 |
| combine_mode `weighted` | 介面預留 | rules.combine() 對 `weighted` 拋 `NotImplementedError`；`worst` 已實作 | 符合 |
| GUI Rules 面板「Save to config.yaml」 | 預設不自動存檔 | 面板底部一個 Checkbox（預設 off），勾了才寫回 | 符合 |

---

## 版本紀錄

| 版本 | 日期 | 內容 |
|---|---|---|
| 1.0.0 | 2026-09-26 | 初版：規則架構、8 條初版規則、config.yaml、GUI 修改、MySQL schema、測試與驗收 |
| 1.0.1 | 2026-09-26 | Claude Code 實作完成；MySQL 延後（`db.enabled: false`）；§12 填寫實際偏差 |

<!-- NiXZ-121.md | version 1.0 by Albert Sheng | 2026-09-26 (consolidated) -->

# NiXZ-121 XANES 影像切片品質分析 — 專案彙整與指導文件

版本：v0.2（2026-09-25）— 由 `NiXZ-121_XANES_guideline.md` v0.1 與 `NiXZ-121_naming_matrix.md` v1.0.0 合併
參考文件：xraylarch — *XAFS: Pre-edge Subtraction, Normalization*
<https://xraypy.github.io/xraylarch/xafs_preedge.html>（larch 2026.3.1，本專案採用同版本）

---

## 1. 專案目標

開發一套演算法與工具,判定 **NiXZ-121**（11×11 = 121 個掃描區段）中每一區段的
XANES 譜與對應影像是否「平滑可用」（smooth and usable），並提供：

1. 自動化品質判定演算法（每區段輸出品質指標與可用/不可用旗標）
2. GUI 應用程式（11×11 熱圖總覽、單區段譜線檢視）
3. 資料庫（快取歸一化結果與品質指標，避免重複計算）

資料集根目錄：`AI image/image_AI_Ni/`　樣品：Ni　網格：11 × 11 = 121 區塊

## 2. 命名規則與座標

### 2.1 規則

| 項目 | 格式 | 序號 | 座標 | 換算 |
|---|---|---|---|---|
| 列（資料夾） | `Z{i}_{z}` | i = 0…10 | z = −5…+5 | z = i − 5 |
| 行（檔案） | `X{j}_{x}_{起}_{終}_XANES.txt` | j = 0…10 | x = +5…−5 | x = 5 − j |

- 格位標記：`Z{i}_{z}/X{j}_{x}`
- 反算：(i, j) = (z + 5, 5 − x)
- 注意：Z 序號與座標同向；X 序號與座標**反向**。
- 中心點 (x, z) = (0, 0)：`Z5_0/X5_0_668_788_XANES.txt`
- 顯示方位：+z 向上、+x 向右；左上 = `Z10_5/X10_-5`，右下 = `Z0_-5/X0_5`
- 檔名正規式：`^X(\d+)_(-?\d+)_(\d+)_(\d+)_XANES\.txt$`，並驗證 x = 5 − j
- 每個 Z 資料夾另含原始檔：`Z*.bin`（~12.5 GB）、`*_Info.txt`、`*_Calibration.bin`、`*_Encoder.bin`、`*_SplitPositions.bin`

### 2.2 資料夾與檔名前綴對照

| i | 資料夾 | z |　| j | 檔名前綴 | x |
|---|---|---|---|---|---|---|
| 0 | `Z0_-5` | -5 |　| 0 | `X0_5` | +5 |
| 1 | `Z1_-4` | -4 |　| 1 | `X1_4` | +4 |
| 2 | `Z2_-3` | -3 |　| 2 | `X2_3` | +3 |
| 3 | `Z3_-2` | -2 |　| 3 | `X3_2` | +2 |
| 4 | `Z4_-1` | -1 |　| 4 | `X4_1` | +1 |
| 5 | `Z5_0` | +0 |　| 5 | `X5_0` | +0 |
| 6 | `Z6_1` | +1 |　| 6 | `X6_-1` | -1 |
| 7 | `Z7_2` | +2 |　| 7 | `X7_-2` | -2 |
| 8 | `Z8_3` | +3 |　| 8 | `X8_-3` | -3 |
| 9 | `Z9_4` | +4 |　| 9 | `X9_-4` | -4 |
| 10 | `Z10_5` | +5 |　| 10 | `X10_-5` | -5 |

### 2.3 NiXZ-121 矩陣（物理座標排列：+z 朝上、+x 朝右）

| z \ x | **-5** | **-4** | **-3** | **-2** | **-1** | **0** | **+1** | **+2** | **+3** | **+4** | **+5** |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **+5** | Z10_5/X10_-5 | Z10_5/X9_-4 | Z10_5/X8_-3 | Z10_5/X7_-2 | Z10_5/X6_-1 | Z10_5/X5_0 | Z10_5/X4_1 | Z10_5/X3_2 | Z10_5/X2_3 | Z10_5/X1_4 | Z10_5/X0_5 |
| **+4** | Z9_4/X10_-5 | Z9_4/X9_-4 | Z9_4/X8_-3 | Z9_4/X7_-2 | Z9_4/X6_-1 | Z9_4/X5_0 | Z9_4/X4_1 | Z9_4/X3_2 | Z9_4/X2_3 | Z9_4/X1_4 | Z9_4/X0_5 |
| **+3** | Z8_3/X10_-5 | Z8_3/X9_-4 | Z8_3/X8_-3 | Z8_3/X7_-2 | Z8_3/X6_-1 | Z8_3/X5_0 | Z8_3/X4_1 | Z8_3/X3_2 | Z8_3/X2_3 | Z8_3/X1_4 | Z8_3/X0_5 |
| **+2** | Z7_2/X10_-5 | Z7_2/X9_-4 | Z7_2/X8_-3 | Z7_2/X7_-2 | Z7_2/X6_-1 | Z7_2/X5_0 | Z7_2/X4_1 | Z7_2/X3_2 | Z7_2/X2_3 | Z7_2/X1_4 | Z7_2/X0_5 |
| **+1** | Z6_1/X10_-5 | Z6_1/X9_-4 | Z6_1/X8_-3 | Z6_1/X7_-2 | Z6_1/X6_-1 | Z6_1/X5_0 | Z6_1/X4_1 | Z6_1/X3_2 | Z6_1/X2_3 | Z6_1/X1_4 | Z6_1/X0_5 |
| **0** | Z5_0/X10_-5 | Z5_0/X9_-4 | Z5_0/X8_-3 | Z5_0/X7_-2 | Z5_0/X6_-1 | **Z5_0/X5_0** | Z5_0/X4_1 | Z5_0/X3_2 | Z5_0/X2_3 | Z5_0/X1_4 | Z5_0/X0_5 |
| **-1** | Z4_-1/X10_-5 | Z4_-1/X9_-4 | Z4_-1/X8_-3 | Z4_-1/X7_-2 | Z4_-1/X6_-1 | Z4_-1/X5_0 | Z4_-1/X4_1 | Z4_-1/X3_2 | Z4_-1/X2_3 | Z4_-1/X1_4 | Z4_-1/X0_5 |
| **-2** | Z3_-2/X10_-5 | Z3_-2/X9_-4 | Z3_-2/X8_-3 | Z3_-2/X7_-2 | Z3_-2/X6_-1 | Z3_-2/X5_0 | Z3_-2/X4_1 | Z3_-2/X3_2 | Z3_-2/X2_3 | Z3_-2/X1_4 | Z3_-2/X0_5 |
| **-3** | Z2_-3/X10_-5 | Z2_-3/X9_-4 | Z2_-3/X8_-3 | Z2_-3/X7_-2 | Z2_-3/X6_-1 | Z2_-3/X5_0 | Z2_-3/X4_1 | Z2_-3/X3_2 | Z2_-3/X2_3 | Z2_-3/X1_4 | Z2_-3/X0_5 |
| **-4** | Z1_-4/X10_-5 | Z1_-4/X9_-4 | Z1_-4/X8_-3 | Z1_-4/X7_-2 | Z1_-4/X6_-1 | Z1_-4/X5_0 | Z1_-4/X4_1 | Z1_-4/X3_2 | Z1_-4/X2_3 | Z1_-4/X1_4 | Z1_-4/X0_5 |
| **-5** | Z0_-5/X10_-5 | Z0_-5/X9_-4 | Z0_-5/X8_-3 | Z0_-5/X7_-2 | Z0_-5/X6_-1 | Z0_-5/X5_0 | Z0_-5/X4_1 | Z0_-5/X3_2 | Z0_-5/X2_3 | Z0_-5/X1_4 | Z0_-5/X0_5 |

角點：左上 `Z10_5/X10_-5`、右上 `Z10_5/X0_5`、左下 `Z0_-5/X10_-5`、右下 `Z0_-5/X0_5`。

### 2.4 Z5_0 資料夾內容（已確認）

| 檔名 | 區段（起–終） |
|---|---|
| `X0_5_1_120_XANES.txt` | 1–120 |
| `X1_4_136_256_XANES.txt` | 136–256 |
| `X2_3_272_392_XANES.txt` | 272–392 |
| `X3_2_400_520_XANES.txt` | 400–520 |
| `X4_1_534_654_XANES.txt` | 534–654 |
| `X5_0_668_788_XANES.txt` | 668–788 |
| `X6_-1_802_922_XANES.txt` | 802–922 |
| `X7_-2_940_1060_XANES.txt` | 940–1060 |
| `X8_-3_1072_1192_XANES.txt` | 1072–1192 |
| `X9_-4_1206_1326_XANES.txt` | 1206–1326 |
| `X10_-5_1338_1458_XANES.txt` | 1338–1458 |

其他檔案：`Z5_0.bin`（約 12.5 GB）、`Z5_0.bin_Info.txt`、`Z5_0_Calibration.bin`、`Z5_0_Encoder.bin`（約 3.1 GB）、`Z5_0_SplitPositions.bin`。

> 其他 Z 資料夾的起–終索引尚未確認，可能與 Z5_0 不同；資料庫中應以實際檔名解析為準。

## 3. 資料格式（JAQ QEXAFS 文字檔）

以 `X0_5_1_120_XANES.txt`（檔頭標示來源 `Z6_1/Z6_1.bin`）為例：

| 項目 | 值 |
|---|---|
| 檔頭 | JAQ 3.3.53+，QEXAFS raw，`# No. / Energy [eV] / mu / mu_ref` |
| mu | ln(col_0/col_1)，穿透模式樣品吸收 |
| mu_ref | ln(col_1/col_2)，參考通道（能量校正用） |
| 點數 / 範圍 | 4000 點，8058.1–9241.3 eV，步長 ≈ 0.30 eV |
| 表列邊能 | Ni K = 8333 eV |
| 平均範圍 | 該檔為第 1–120 條掃描之平均（AVERAGED SPECTRUM）|
| Mono 頻率 | ≈ 1.0 Hz（每秒約 2 條 up/down 譜）|

檔名中之 `{start}_{end}` 即平均所用的 spectrum 編號區間（各 X 段約 120 條）。

## 4. 標準處理流程（依 xraylarch 文件）

每一區段統一執行：

1. **讀檔**：`numpy.loadtxt(..., comments='#')`，取 energy、mu、mu_ref。
2. **E₀ 判定**：`find_e0()` — dμ/dE 最大值（文件 §14.2.1）。
3. **Pre-edge 扣除與歸一化**：`pre_edge(group)` 預設參數（文件 §14.2.2–14.2.3）：
   - pre-edge：於 [E₀+pre1, E₀+pre2] 線性擬合（nvict=0）
   - post-edge：於 [E₀+norm1, E₀+norm2] 多項式擬合；區間 >350 eV 時 nnorm=2
   - edge step Δμ₀ = post(E₀) − pre(E₀)；norm = (μ − pre)/Δμ₀；另輸出 flat
4. **能量校正**：以 mu_ref 之 E₀ 對齊參考標準（Ni 箔 8333 eV），求整體偏移 ΔE 後平移。
5. （選用）**pre-edge peak 分析**：`prepeaks_setup()` / `pre_edge_baseline()`（文件 §14.2.5），
   分析 1s→3d 峰以判定氧化態；**過吸收修正** `fluo_corr()` 僅適用螢光模式。

### 4.1 首件結果：X0_5_1_120（Z6_1 資料夾，z=1, x=5）

| 參數 | 值 |
|---|---|
| E₀（樣品，max derivative） | 8346.29 eV |
| E₀（mu_ref 參考通道） | 8345.70 eV |
| edge step Δμ₀ | 0.5650 |
| pre-edge 區間 | E₀ − 288.2 ～ E₀ − 144.1 eV |
| post-edge 區間 | E₀ + 25 ～ E₀ + 895 eV（nnorm=2）|
| white line 峰值（norm） | ≈ 1.5 |

**判讀**：參考通道 E₀ 亦落在 8345.7 eV，故 +12.7 eV 為單色器能量刻度系統偏差，
非化學位移；樣品相對參考之真實位移 ≈ +0.6 eV，加上明顯 white line，
譜形偏 NiO/Ni(OH)₂ 型而非金屬 Ni。**跨區段比對前必須先以 mu_ref 統一校正。**

## 5. 區段品質（smooth / usable）判定指標（建議）

每區段計算下列指標，逐項設閾值，任一不合格即標記；閾值以 121 段統計分布
（中位數 ± k·MAD）自動調校，避免人為武斷：

| # | 指標 | 定義 | 意義 |
|---|---|---|---|
| Q1 | edge step Δμ₀ | pre_edge 輸出 | 太小＝樣品薄/空洞/未打到樣品 |
| Q2 | 高頻雜訊 | EXAFS 區（E₀+150 eV 以上）flat 譜之高通殘差 RMS，或逐點差分標準差 | 平滑度主指標 |
| Q3 | pre-edge 平坦度 | pre-edge 區線性擬合殘差 RMS | 散射/漏光/諧波污染 |
| Q4 | E₀ 偏移 | 校正後 E₀ 與全圖中位數之差 | 定位或相變異常 |
| Q5 | glitch 計數 | norm 譜中 >n·σ 之孤立尖點數 | 單色器 glitch、Bragg 峰 |
| Q6 | white line 高度 | norm 峰值 | 化學態分類輔助 |
| Q7 | 影像指標 | 對應影像 ROI 之 Laplacian 變異數（清晰度）、灰階均勻度 | 影像面品質 |

綜合分數 S = Σ wᵢ·qᵢ（qᵢ 為各指標正規化 0–1），S 與各 qᵢ 一併存入資料庫。

## 6. 系統架構（建議）

```
raw txt (121 檔) ──> pipeline.py（larch pre_edge + 校正 + 指標）
                          │
                          ▼
                   MySQL  xanes
                   ├─ sections(zi, xj, z, x, folder, filename, n_pts, ...)
                   ├─ qc(section_id, e0, edge_step, Q1..Q7, score, usable)
                   └─ spectra(section_id, energy BLOB, norm BLOB, flat BLOB)
                          │
                          ▼
                   GUI（單檔 HTML 或 PyQt）
                   ├─ 11×11 熱圖（score / 任一指標著色，方位依 §2）
                   ├─ 點擊格子 → μ、norm、flat 譜與影像並列
                   └─ 閾值滑桿即時重判 usable
```

- 資料庫選 MySQL：以 `MEDIUMBLOB` 存放 121×4000 點的 norm 譜（約 4 MB 級距），需另備 MySQL 伺服器與連線設定（帳號/主機/schema `xanes`）。
- GUI 若需分享，單檔 HTML（Plotly/自繪 SVG）最輕；需本機批次操作則 PyQt。

### 6.1 sections 表建議欄位

| 欄位 | 型別 | 說明 |
|---|---|---|
| dataset_id | VARCHAR(32) | `NiXZ-121` |
| i | TINYINT | Z 序號 0–10 |
| j | TINYINT | X 序號 0–10 |
| z | TINYINT | i − 5 |
| x | TINYINT | 5 − j |
| seg_start | INT | 區段起點索引 |
| seg_end | INT | 區段終點索引 |
| path | VARCHAR(255) | 相對路徑 `Z{i}_{z}/X{j}_{x}_{起}_{終}_XANES.txt` |

主鍵：(dataset_id, i, j)。檔名以正規式 `^X(\d+)_(-?\d+)_(\d+)_(\d+)_XANES\.txt$` 解析，並驗證 x = 5 − j。

## 7. 已產出檔案

| 檔案 | 內容 |
|---|---|
| `X0_5_1_120_mu.png` | 原始 μ(E) 圖 |
| `X0_5_1_120_preedge_norm.png` | pre-edge 擬合 + 歸一化/flatten 圖 |
| `X0_5_1_120_normalized.txt` | energy, mu, pre_edge, post_edge, norm, flat 六欄 |
| `NiXZ-121.md` | 本文件（合併版）|
| `NiXZ-121_XANES_guideline.md` | 原 v0.1 指導文件（已由本檔取代）|
| `NiXZ-121_naming_matrix.md` | 原 v1.0.0 命名矩陣（已由本檔取代）|

## 8. 待辦

1. 取得其餘 Z 資料夾之區段檔，確認 121 檔命名與範圍一致（目前僅 Z5_0 已確認，見 §2.4）
2. 批次 pipeline + 指標閾值統計調校（需全部 121 檔）
3. mu_ref 校正基準確認（參考物是否為 Ni 箔）
4. 影像檔格式與 ROI 對應規則確認（Q7 所需）
5. GUI 原型與 MySQL schema 實作

## 9. 參考資料

1. M. Newville, *xraylarch* documentation, §14.2 "XAFS: Pre-edge Subtraction, Normalization and data treatment", <https://xraypy.github.io/xraylarch/xafs_preedge.html>（larch 2026.3.1）
2. 同頁引用：MBACK（Weng, Waldo, Penner-Hahn）、FLUO 過吸收修正（D. Haskel）

## 版本紀錄

| 版本 | 日期 | 內容 |
|---|---|---|
| 0.1 | 2026-09-25 | `NiXZ-121_XANES_guideline.md` 初版：目標、資料格式、pipeline、品質指標、SQLite 架構、首件結果 |
| 1.0.0 | 2026-09-25 | `NiXZ-121_naming_matrix.md` 初版：命名規則、121 格矩陣、Z5_0 區段表、資料庫欄位 |
| 0.2 | 2026-09-25 | 合併上述兩份為 `NiXZ-121.md`；資料庫改為 MySQL；sections 表欄位改用 MySQL 型別 |

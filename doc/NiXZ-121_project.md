<!-- NiXZ-121_project.md | version 1.4.4 by Albert Sheng | 2026-09-28 | D10：R-EDGE-FWHM / R-NORM-COEFS z 門檻由 110 gate-pass 分佈校準 -->

# NiXZ-121 XANES 區段品質分析 — 專案整合文件

資料集：`AI image/image_AI_Ni/`　樣品：Ni　網格：11 × 11 = 121 區段
量測：NSRRC TPS 44A，QEXAFS Recorder 2.1，Si(111)，Ni K-edge，2025-12-09
參考：xraylarch 2026.3.1，§14.2 *Pre-edge Subtraction, Normalization*

---

## 1. 專案目標

判定 NiXZ-121 每一區段的 XANES 光譜是否「平滑可用」（smooth and usable），並提供：

1. 自動化品質判定演算法：每區段輸出各項指標與可用／不可用旗標
2. GUI：11×11 熱圖總覽、點選單格檢視光譜
3. 資料庫：快取歸一化結果與指標，避免重複計算

> **決定（2026-09-26）**：網格一律以 **11 × 11 = 121** 處理，直到有新資料更新為止。專案說明中的「10 × 10」視為舊描述（見 §10 D1）。

---

## 2. 命名規則與座標

| 項目 | 格式 | 序號 | 座標 | 換算 |
|---|---|---|---|---|
| 列（資料夾） | `Z{i}_{z}` | i = 0…10 | z = −5…+5 | z = i − 5 |
| 行（檔案） | `X{j}_{x}_{起}_{終}_XANES.txt` | j = 0…10 | x = +5…−5 | x = 5 − j |

- 格位標記：`Z{i}_{z}/X{j}_{x}`；反算 (i, j) = (z + 5, 5 − x)
- Z 序號與座標**同向**；X 序號與座標**反向**
- 中心 (x, z) = (0, 0)：`Z5_0/X5_0_668_788_XANES.txt`
- 顯示方位：+z 朝上、+x 朝右
- 角點：左上 `Z10_5/X10_-5`、右上 `Z10_5/X0_5`、左下 `Z0_-5/X10_-5`、右下 `Z0_-5/X0_5`

### 2.1 資料夾與檔名前綴對照

| i | 資料夾 | z |　| j | 檔名前綴 | x |
|---|---|---|---|---|---|---|
| 0 | `Z0_-5` | −5 |　| 0 | `X0_5` | +5 |
| 1 | `Z1_-4` | −4 |　| 1 | `X1_4` | +4 |
| 2 | `Z2_-3` | −3 |　| 2 | `X2_3` | +3 |
| 3 | `Z3_-2` | −2 |　| 3 | `X3_2` | +2 |
| 4 | `Z4_-1` | −1 |　| 4 | `X4_1` | +1 |
| 5 | `Z5_0` | 0 |　| 5 | `X5_0` | 0 |
| 6 | `Z6_1` | +1 |　| 6 | `X6_-1` | −1 |
| 7 | `Z7_2` | +2 |　| 7 | `X7_-2` | −2 |
| 8 | `Z8_3` | +3 |　| 8 | `X8_-3` | −3 |
| 9 | `Z9_4` | +4 |　| 9 | `X9_-4` | −4 |
| 10 | `Z10_5` | +5 |　| 10 | `X10_-5` | −5 |

### 2.2 NiXZ-121 矩陣（+z 朝上、+x 朝右）

| z \ x | **−5** | **−4** | **−3** | **−2** | **−1** | **0** | **+1** | **+2** | **+3** | **+4** | **+5** |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **+5** | Z10_5/X10_-5 | Z10_5/X9_-4 | Z10_5/X8_-3 | Z10_5/X7_-2 | Z10_5/X6_-1 | Z10_5/X5_0 | Z10_5/X4_1 | Z10_5/X3_2 | Z10_5/X2_3 | Z10_5/X1_4 | Z10_5/X0_5 |
| **+4** | Z9_4/X10_-5 | Z9_4/X9_-4 | Z9_4/X8_-3 | Z9_4/X7_-2 | Z9_4/X6_-1 | Z9_4/X5_0 | Z9_4/X4_1 | Z9_4/X3_2 | Z9_4/X2_3 | Z9_4/X1_4 | Z9_4/X0_5 |
| **+3** | Z8_3/X10_-5 | Z8_3/X9_-4 | Z8_3/X8_-3 | Z8_3/X7_-2 | Z8_3/X6_-1 | Z8_3/X5_0 | Z8_3/X4_1 | Z8_3/X3_2 | Z8_3/X2_3 | Z8_3/X1_4 | Z8_3/X0_5 |
| **+2** | Z7_2/X10_-5 | Z7_2/X9_-4 | Z7_2/X8_-3 | Z7_2/X7_-2 | Z7_2/X6_-1 | Z7_2/X5_0 | Z7_2/X4_1 | Z7_2/X3_2 | Z7_2/X2_3 | Z7_2/X1_4 | Z7_2/X0_5 |
| **+1** | Z6_1/X10_-5 | Z6_1/X9_-4 | Z6_1/X8_-3 | Z6_1/X7_-2 | Z6_1/X6_-1 | Z6_1/X5_0 | Z6_1/X4_1 | Z6_1/X3_2 | Z6_1/X2_3 | Z6_1/X1_4 | Z6_1/X0_5 |
| **0** | Z5_0/X10_-5 | Z5_0/X9_-4 | Z5_0/X8_-3 | Z5_0/X7_-2 | Z5_0/X6_-1 | **Z5_0/X5_0** | Z5_0/X4_1 | Z5_0/X3_2 | Z5_0/X2_3 | Z5_0/X1_4 | Z5_0/X0_5 |
| **−1** | Z4_-1/X10_-5 | Z4_-1/X9_-4 | Z4_-1/X8_-3 | Z4_-1/X7_-2 | Z4_-1/X6_-1 | Z4_-1/X5_0 | Z4_-1/X4_1 | Z4_-1/X3_2 | Z4_-1/X2_3 | Z4_-1/X1_4 | Z4_-1/X0_5 |
| **−2** | Z3_-2/X10_-5 | Z3_-2/X9_-4 | Z3_-2/X8_-3 | Z3_-2/X7_-2 | Z3_-2/X6_-1 | Z3_-2/X5_0 | Z3_-2/X4_1 | Z3_-2/X3_2 | Z3_-2/X2_3 | Z3_-2/X1_4 | Z3_-2/X0_5 |
| **−3** | Z2_-3/X10_-5 | Z2_-3/X9_-4 | Z2_-3/X8_-3 | Z2_-3/X7_-2 | Z2_-3/X6_-1 | Z2_-3/X5_0 | Z2_-3/X4_1 | Z2_-3/X3_2 | Z2_-3/X2_3 | Z2_-3/X1_4 | Z2_-3/X0_5 |
| **−4** | Z1_-4/X10_-5 | Z1_-4/X9_-4 | Z1_-4/X8_-3 | Z1_-4/X7_-2 | Z1_-4/X6_-1 | Z1_-4/X5_0 | Z1_-4/X4_1 | Z1_-4/X3_2 | Z1_-4/X2_3 | Z1_-4/X1_4 | Z1_-4/X0_5 |
| **−5** | Z0_-5/X10_-5 | Z0_-5/X9_-4 | Z0_-5/X8_-3 | Z0_-5/X7_-2 | Z0_-5/X6_-1 | Z0_-5/X5_0 | Z0_-5/X4_1 | Z0_-5/X3_2 | Z0_-5/X2_3 | Z0_-5/X1_4 | Z0_-5/X0_5 |

### 2.3 Z5_0 資料夾內容（已確認）

| 檔名 | 光譜編號（起–終） | 與前段間隙 |
|---|---|---|
| `X0_5_1_120_XANES.txt` | 1–120 | — |
| `X1_4_136_256_XANES.txt` | 136–256 | 15 |
| `X2_3_272_392_XANES.txt` | 272–392 | 15 |
| `X3_2_400_520_XANES.txt` | 400–520 | 7 |
| `X4_1_534_654_XANES.txt` | 534–654 | 13 |
| `X5_0_668_788_XANES.txt` | 668–788 | 13 |
| `X6_-1_802_922_XANES.txt` | 802–922 | 13 |
| `X7_-2_940_1060_XANES.txt` | 940–1060 | 17 |
| `X8_-3_1072_1192_XANES.txt` | 1072–1192 | 11 |
| `X9_-4_1206_1326_XANES.txt` | 1206–1326 | 13 |
| `X10_-5_1338_1458_XANES.txt` | 1338–1458 | 11 |

其他檔案：`Z5_0.bin`（~12.5 GB）、`Z5_0.bin_Info.txt`、`Z5_0_Calibration.bin`（1 KB）、`Z5_0_Encoder.bin`（~3.1 GB）、`Z5_0_SplitPositions.bin`（13 KB）。

> 其他 Z 資料夾的起–終編號尚未確認。`X0_5_1_120` 也出現在 Z6_1（見 §4.1 與 §10 D2），表示各資料夾編號可能相同或部分相同；資料庫一律以「資料夾＋實際檔名」解析，不可只用檔名當唯一鍵。

---

## 3. 量測與資料格式

### 3.1 原始記錄（由 `Z0_-5.bin_Info.txt` 解讀）

| 項目 | 值 | 說明 |
|---|---|---|
| 設施／光束線 | NSRRC TPS 44A | QEXAFS Recorder 2.1.6770 |
| 單色器 | Si(111)，d = 3.13560 Å，290 K | Info 標示邊能 Ni K = 8331.90 eV |
| 擺動驅動 (DAC) | 1 Hz，振幅 1.1 V，偏置 2 V | 每週期上行＋下行各 1 條 → **2 條光譜／秒** |
| ADC | 1 MHz × 4 通道（ch 0,2,4,6），±10 V | 800 s，8×10⁸ 點／通道 |
| ADC 檔大小 | 12,800,000,024 B | = 24 B 標頭 + 8×10⁸ × 4 ch × 4 B → 每點 4 B（int32 或 float32 待驗） |
| Encoder | 1 MHz × 1 通道，4 B／點 | 與 ADC 同時鐘逐點對應 |
| 編碼器解析度 | 3.0495×10⁻⁵ °（0.532 µrad） | 8332 eV 處 ≈ **0.018 eV／count**，遠小於核心能階寬（~1.4 eV） |
| 記錄完整性 | ADC、Encoder 皆 800/800 成功 | 無遺失區塊；DAC 第 1 筆時間戳異常為計時器初始化，可忽略 |
| Z0_-5 量測時間 | 2025-12-09 10:21:46–10:35:06 | 單列 13 分 20 秒 |

**推論（待驗證）**

1. `.bin` 為偵測器電壓的連續記錄，**不是相機影像**。「影像」即 11×11 光譜網格組成的空間分佈圖。
2. 光譜編號單位＝半週期（1 條光譜 = 0.5 s）：最大編號 1458 × 0.5 s = 729 s < 800 s，吻合；若以秒計則超出記錄長度。
3. 每區段約 121 條光譜 ≈ 60 s；區段間隙 7–17 條 ≈ 3.5–8.5 s，為樣品台移動與穩定時間；1458 之後約 71 s 未使用。
4. `SplitPositions.bin` 日期（12/26）晚於量測（12/9），切割點為事後決定；間隙不等，可能為人工或半自動判定。
5. 4 個 ADC 通道中 3 個應為 I0、I1、I2（對應 §3.2 的 col_0/1/2），第 4 通道用途未知（見 §10 D3）。
6. 整張 11 列圖約需 2.5 小時以上，列與列之間可能有光束或單色器長時間漂移。

### 3.2 區段文字檔（JAQ QEXAFS）

以 `X0_5_1_120_XANES.txt`（檔頭標示來源 `Z6_1/Z6_1.bin`）為例：

| 項目 | 值 |
|---|---|
| 檔頭 | JAQ 3.3.53+，QEXAFS raw，欄位 `# No. / Energy [eV] / mu / mu_ref` |
| mu | ln(col_0/col_1)，穿透模式樣品吸收 |
| mu_ref | ln(col_1/col_2)，參考通道（能量校正用） |
| 點數／範圍 | 4000 點，8058.1–9241.3 eV，步長 ≈ 0.30 eV |
| 內容 | 第 1–120 條光譜之平均（AVERAGED SPECTRUM） |

---

## 4. 標準處理流程（xraylarch）

1. **讀檔**：`numpy.loadtxt(..., comments='#')`，取 energy、mu、mu_ref。
2. **E₀**：`find_e0()`，取 dμ/dE 最大值（§14.2.1）。
3. **Pre-edge 扣除與歸一化**：`pre_edge()`（§14.2.2–14.2.3）
   - pre-edge：[E₀+pre1, E₀+pre2] 線性擬合（nvict = 0）
   - post-edge：[E₀+norm1, E₀+norm2] 多項式；區間 > 350 eV 時 nnorm = 2
   - Δμ₀ = post(E₀) − pre(E₀)；norm = (μ − pre)/Δμ₀；另輸出 flat（對 norm 扣二次曲線）
4. **能量校正**：以 mu_ref 的 E₀ 對齊參考標準，求全圖單一偏移 ΔE 後平移。**跨區段比對前必須先做。**
5. （選用）pre-edge 峰：`prepeaks_setup()`／`pre_edge_baseline()`（§14.2.5）。`fluo_corr()` 僅適用螢光模式，本資料為穿透模式，不需要。

xraylarch 文件**沒有**判斷「區域好壞」的準則或門檻；它只提供可當指標的輸出（e0、edge_step、pre_slope、norm_c0–c2、norm、flat）。`estimate_noise()` 為 EXAFS χ(R) 設計，不適用本 XANES 資料。

### 4.1 首件結果：X0_5_1_120（Z6_1，z = +1, x = +5）

| 參數 | 值 |
|---|---|
| E₀（樣品） | 8346.29 eV |
| E₀（mu_ref） | 8345.70 eV |
| Δμ₀ | 0.5650 |
| pre-edge 區間 | E₀ − 288.2 ～ E₀ − 144.1 eV |
| post-edge 區間 | E₀ + 25 ～ E₀ + 895 eV（nnorm = 2） |
| white line 峰值（norm） | ≈ 1.5 |

邊能參考值有兩個（8333 eV 表列、8331.90 eV Info 設定），差 1.1 eV，改由設定檔容差處理，見 §4.2 與 §10 D4。

**判讀**：mu_ref 的 E₀ 也在 8345.7 eV，所以相對表列值（8333 eV；Info 設定值 8331.90 eV）的 +12.7～+13.8 eV 是單色器能量刻度的系統偏差，不是化學位移。樣品相對參考的真實位移約 +0.6 eV，加上明顯的 white line，譜形偏 NiO／Ni(OH)₂ 型而非金屬 Ni（前提：參考物為 Ni 箔，待確認）。

Δμ₀ = 0.565 落在穿透模式常用的 0.5–1.5 範圍內。

### 4.2 邊能設定與容差（config）

邊能不寫死在程式中，由設定檔 `config.yaml` 提供。容差分成兩層，因為它們檢查的是不同的事：

| 層級 | 檢查對象 | 用途 |
|---|---|---|
| L1 單色器偏差窗 | 原始 mu_ref E₀ − 標稱值 | 確認參考通道確實抓到 Ni K 邊，而不是 glitch；目前實測偏差約 +12.7～+13.8 eV |
| L2 標稱值容差 | 兩個標稱值之間、以及校正後參考 E₀ | 涵蓋 8333 與 8331.90 的 1.1 eV 差異 |
| L3 全圖一致性 | 各格 mu_ref E₀ 相對全圖中位數 | 參考箔 E₀ 在全圖應為常數；偏離代表列間漂移或能量軸重建問題 |

```yaml
# config.yaml — edge energy section (起始值，待 Z5_0 實算後校準)
edge:
  element: Ni
  edge: K
  e0_nominal_eV: 8333.0          # 表列值（Ni 箔，xraylarch/xraydb 慣用）
  e0_alt_eV: 8331.90             # Info.txt Element4Edge 設定值
  e0_nominal_tol_eV: 1.5         # L2：|E0_ref_calibrated − e0_nominal| 容許值，需 ≥ 1.1 eV 以涵蓋兩標稱值
  mono_offset_window_eV: [-5.0, 25.0]   # L1：原始 mu_ref E0 − e0_nominal 的可接受範圍
  ref_e0_search_eV: [8320.0, 8370.0]    # find_e0 在 mu_ref 上的搜尋區間，避開 pre-edge glitch
  ref_e0_spread_tol_eV: 0.3      # L3：各格 mu_ref E0 對全圖中位數的最大偏離
  sample_e0_shift_tol_eV: 3.0    # Q4：校正後樣品 E0 相對鄰格中位數的旗標門檻
```

**數值依據**：
- L2 取 1.5 eV：兩標稱值差 1.1 eV，再加約 0.3 eV 的 E₀ 判定不確定度（導數法在 0.3 eV 步長下）。
- L3 取 0.3 eV：約等於一個能量步長。參考箔是同一片，理論上應完全相同；超過一個步長就值得檢查。
- L1 是寬鬆窗，只用來擋掉明顯錯誤。正常情況下偏差應是全圖單一常數。

以上皆為起始值，不是文獻標準，需要以實測分佈校準。

---

## 5. 區段品質判定指標

### 5.1 文獻依據

- **xraylarch**：僅處理，無判準。
- **TXM-Wizard**（Liu et al., *J. Synchrotron Rad.* 19, 281–287, 2012）：
  - (a) 邊緣跳躍濾波：跳躍 < 門檻者剔除，門檻 = 該像素前緣標準差 × 使用者倍數（手冊範例 EJFT = 8）
  - (b) 正規化濾波：前／後緣直線斜率過大或過小者剔除
  - (c) 邊緣能量取 norm = 0.5 位置，比導數法更耐雜訊
  - (d) 每像素 R = Σ(data−fit)²/Σdata²，以「跳躍 vs R」散佈圖找異常
- **Lippold et al.**（*J. Synchrotron Rad.* 12, 45–52, 2005）— 重複掃描的自動品質控制：
  - 前提：所有子集（掃描或通道）量測同一樣品，差異皆視為假象
  - 參考採留一法：子集的參考 = 其餘子集平均
  - 差分 D(i) = 子集 − 參考；累積差分 A(j) = Σ_{i≤j} D(i)，放大系統偏差、抵消隨機雜訊
  - 四種典型假象：群點偏移、跳躍不連續、斜率突變、週期彎曲
  - 最佳判準：**判準 7** = A(j) 對直線迴歸的殘差標準差；判準 4（差分平均絕對偏差）有時把雜訊大的光譜誤判為假象
  - 迭代剔除最差子集；停止條件為相鄰兩輪判準 7 平均值變化 < 0.1（作者註明數值依系統而異，不可直接沿用）
  - 限制：螢光模式、稀薄生物樣品、EXAFS 區，測試資料組少
  - **本專案用法**：適用於「單格內約 120 條重複掃描」（T-OUTLIER-SCAN、T-UPDOWN、T-DRIFT）；**不適用**於 121 格之間直接比較，因格間差異可能為真實化學差異（見 smooth／consistent 分離設計）
- **Gaur et al.**（*Scientific Data*, 2026）— XAS 資料庫收錄品質標準：穿透模式邊緣跳躍 0.5–2.0；E₀ 取一階導數最大值並以標準校正；能量解析度以導數峰 FWHM 評估（0.5–2.0 eV）；多次掃描比較判斷輻射損傷。對象為單條光譜收錄，非空間掃描判定
- **Leys et al.**（*J. Exp. Soc. Psychol.* 49, 764, 2013）— 以中位數 ± MAD 取代平均 ± 標準差偵測離群值；建議預設門檻 2.5，3 為非常保守
- **Stern & Kim**（*Phys. Rev. B* 23, 3781, 1981）— 厚度效應，為 GATE-EDGE 上限的物理依據

### 5.1.1 規則出處對照

| 規則 | 依據等級 | 來源 |
|---|---|---|
| GATE-EDGE 下限 | 文獻概念，門檻自訂 | TXM-Wizard edge-jump filter；0.1 為本專案設定，與 Gaur 2026 的 0.5 差異見 D8 |
| GATE-EDGE 上限 | 文獻支持，門檻經驗值 | Stern & Kim 1981 |
| CAL-EREF | 標準實務，門檻自訂 | 參考箔校正；Gaur 2026 |
| R-SNR | 文獻概念 | TXM-Wizard (a) |
| R-PRE-FLAT | 文獻相近 | TXM-Wizard (b) 檢查斜率，本專案改查殘差 |
| R-NOISE-HF | 本專案設計 | — |
| R-GLITCH | 本專案設計 | — |
| R-EDGE-FWHM（**v1.4 起實作**） | 文獻概念、本專案延伸 | Gaur 2026 用絕對窗 0.5–2.0 eV 判解析度；本專案改用 grid-relative MAD z（雙側）以自校準 beamline 解析度。Stern & Kim 1981 為厚度寬化的物理依據。實作於 `pipeline.edge_fwhm_eV` + `rules._r_edge_fwhm` |
| R-NORM-COEFS（**v1.4 起實作**；對應 §5.2 A Q3） | 文獻概念 | TXM-Wizard (b) 正規化濾波延伸。取 `pre_slope`、`norm_c1`、`norm_c2` 三者對全圖中位數的 MAD z-score 之 `max\|z\|`，抓 scattering／諧波／飽和／pre-post 窗誤設。實作於 `rules._r_norm_coefs`；larch 係數由 `pipeline.process_section` 一併存入 `.json` |
| C-SHAPE | 部分文獻 | R-factor（Ravel & Newville 2005）延伸至中位光譜比較 |
| C-E0-NBR | 本專案設計 | 概念近似 TXM-Wizard 邊能分群 |
| C-CUMDIFF（新增，選用；**v1.3 起實作**） | 文獻方法、本專案延伸 | Lippold 2005 判準 7，參考改為 8 鄰格平均。實作於 `rules.lippold_c7` + `rules._c_cumdiff` + `examine._compute_cumdiff`；預設 `enabled: false`，由 Rules 面板或 config 開啟 |
| T-OUTLIER-SCAN（預留） | 文獻方法 | Lippold 2005 判準 7 + 迭代剔除 |
| 穩健 z（MAD） | 統計文獻 | Leys 2013；warn 3／fail 5 為本專案選擇 |

所有門檻尚未以真實資料驗證，校準前判定結果僅作篩選輔助。

### 5.2 本專案指標（整合版）

門檻一律以 121 格統計分佈（中位數 ± k·MAD）自動校準，以下數值僅為起點。

**A. 單一平均光譜即可計算**

| # | 指標 | 定義 | 意義 |
|---|---|---|---|
| Q1 | 邊緣訊雜比 | Δμ₀ ÷ σ_pre（前緣直線擬合殘差標準差） | 對應 TXM-Wizard (a)，起點 ≥ 8 |
| Q1b | Δμ₀ 絕對值 | pre_edge 輸出，設**上下限** | 太小＝薄／空洞／未打到樣品；太大（Δμt ≳ 1.5 或總 μt ≳ 2.5）＝厚度效應壓低 white line |
| Q2 | 後緣雜訊 | E₀+150 eV 以上 flat 的高通殘差 RMS（norm 單位） | 平滑度主指標 |
| Q3 | 正規化合理性 | pre_slope、norm_c1、norm_c2 相對全圖中位數的 MAD 偏離 | 對應 TXM-Wizard (b)；散射、漏光、諧波污染。**v1.4 起由 `R-NORM-COEFS` 規則實作** |
| Q4 | 邊緣位置 | 校正後 E₀ 或 norm = 0.5 能量，與 8 鄰格中位數之差 | 空間離群或化學態不同 |
| Q5 | 形狀相似度 | 對 121 格中位光譜的 R-factor | 形狀異常 |
| Q6 | glitch | 一階差分穩健 z-score > 5 的點數 | 單色器 glitch、Bragg 峰 |
| Q7 | white line 高度 | norm 峰值 | 化學態分類輔助（非好壞判準） |

**B. 需逐條光譜（每格約 120 條，QEXAFS 特有）**

| # | 指標 | 做法 | 判斷的問題 |
|---|---|---|---|
| R1 | 統計雜訊 | σ(E) = 逐條標準差 / √N | 真實訊雜比，取代間接估計 |
| R2 | 時間漂移 | 前 30 條 vs 後 30 條的 E₀、white line 差 | 輻射損傷、樣品移動、熱漂移 |
| R3 | 上行／下行差 | 兩組平均的 E₀ 位移 | 放大器時間常數不匹配 |
| R4 | 離群光譜 | Lippold 2005 判準 7：留一法參考、累積差分殘差標準差，迭代剔除；停止條件改為「剔除前後平均 XANES 的 white line 與 E₀ 變化小於雜訊水準」 | top-up 注射瞬變、光束掉落（跳躍）、熱漂移（斜率突變）、glitch |
| R5 | 移動後穩定 | 區段前 5 條是否系統偏離 | 切割點是否太早 |
| R6 | 飽和 | 任一通道 ≥ 9.9 V 的點數 | 增益設定錯誤 |

**C. 空間／列間**

| # | 指標 | 做法 |
|---|---|---|
| S1 | 列間漂移 | 各 Z 列 mu_ref E₀ 的系統差異（量測跨 2.5 h 以上） |

綜合分數 S = Σ wᵢ·qᵢ（qᵢ 正規化至 0–1）；S 與各 qᵢ 全部存入資料庫，GUI 可調閾值即時重判。

---

## 6. 系統架構

```
原始檔（121 個 XANES.txt；選用 .bin 逐條光譜）
        │
        ▼
pipeline.py：讀檔 → mu_ref 能量校正 → larch pre_edge → Q/R/S 指標
        │
        ▼
資料庫 xanes
 ├─ sections(dataset_id, i, j, z, x, seg_start, seg_end, path, n_pts)
 ├─ qc(section_id, e0, e0_ref, edge_step, Q1..Q7, R1..R6, score, usable)
 └─ spectra(section_id, energy BLOB, norm BLOB, flat BLOB)
        │
        ▼
GUI
 ├─ 11×11 熱圖（score 或任一指標著色，方位依 §2）
 ├─ 點選格子 → μ、norm、flat 譜並列
 └─ 閾值滑桿即時重判 usable
```

**sections 欄位**

| 欄位 | 型別 | 說明 |
|---|---|---|
| dataset_id | TEXT | `NiXZ-121` |
| i, j | INT | Z、X 序號 0–10 |
| z, x | INT | i − 5、5 − j |
| seg_start, seg_end | INT | 光譜編號區間 |
| path | TEXT | `Z{i}_{z}/X{j}_{x}_{起}_{終}_XANES.txt` |

主鍵 (dataset_id, i, j)。檔名以 `^X(\d+)_(-?\d+)_(\d+)_(\d+)_XANES\.txt$` 解析，並驗證 x = 5 − j。

**資料庫選型（決定，2026-09-26）**：採用 **MySQL**，schema 名稱 `xanes`。

| 項目 | 建議 |
|---|---|
| 引擎／字元集 | InnoDB，utf8mb4 |
| 光譜陣列 | `MEDIUMBLOB`（上限 16 MB），存 float64 little-endian 原始位元組；單條 4000 點 = 32 KB |
| 主鍵 | sections：(dataset_id, i, j)；qc、spectra 以 section_id 外鍵關聯 |
| 設定 | 連線資訊（host、port、user、schema）放在 `config.yaml` 或環境變數，密碼不寫入程式碼與版本控制 |
| 版本追蹤 | qc 表加 `pipeline_version`、`config_hash`、`computed_at`，門檻或設定改變時可判斷哪些結果需重算 |

需另備 MySQL 伺服器（本機或區網）。若日後需要離線攜帶，可再加 SQLite 匯出，但主庫以 MySQL 為準。

**GUI**：分享用單檔 HTML；本機批次操作用 PyQt。

---

## 7. 已產出檔案

| 檔案 | 內容 |
|---|---|
| `X0_5_1_120_mu.png` | 原始 μ(E) 圖 |
| `X0_5_1_120_preedge_norm.png` | pre-edge 擬合＋歸一化／flatten 圖 |
| `X0_5_1_120_normalized.txt` | energy, mu, pre_edge, post_edge, norm, flat 六欄 |
| `NiXZ-121_project.md` | 本文件（取代 naming_matrix 與 guideline 兩份） |

---

## 8. 待辦與待確認

| # | 項目 | 需要的資料 |
|---|---|---|
| 1 | 其餘 10 個 Z 資料夾的檔名與起–終編號 | 各資料夾檔案清單 |
| 2 | `.bin` 格式（int32／float32、通道交錯方式） | 在本機讀前 1 MB（小程式可提供） |
| 3 | 4 個 ADC 通道對應的偵測器與增益 | 光束線紀錄 |
| 4 | `Calibration.bin`（1 KB）內容：DAC／角度／能量校正參數？ | 檔案本身 |
| 5 | 參考物是否為 Ni 箔 | 實驗紀錄 |
| 6 | 樣品台步距（µm）與光束尺寸 | 判斷格子是否重疊 |
| 7 | 「capture image」是否另有相機或顯微影像 | 若有，需格式與 ROI 對應規則（影像指標：Laplacian 變異數、灰階均勻度） |
| 8 | ~~資料庫選型~~ | **已決定：MySQL**（§6） |
| 9 | 以 Z5_0 的 11 格實算 §5 指標分佈，校準門檻 | 11 個 XANES.txt |
| 10 | 批次 pipeline + GUI 原型 | 1–9 完成後 |

---

## 9. 參考資料

| # | 作者 | 標題 | 出處 | 年 | DOI／連結 | 本專案用途 | 對應規則／章節 | 查證狀態 |
|---|---|---|---|---|---|---|---|---|
| 1 | M. Newville | XAFS: Pre-edge Subtraction, Normalization, and data treatment | xraylarch 文件 §14.2（2026.3.1） | 2026 | <https://xraypy.github.io/xraylarch/xafs_preedge.html> | `find_e0`、`pre_edge` 演算法與輸出；無品質判準 | §4、全部規則的輸入量 | 已讀全文 |
| 2 | M. Newville | XAFS Functions: Overview and Naming Conventions | xraylarch 文件 §14.1 | 2026 | <https://xraypy.github.io/xraylarch/xafs_utilities.html> | `estimate_noise()`：確認為 EXAFS χ(R) 方法，不適用本 XANES 資料 | §4 | 已讀相關段落 |
| 3 | Y. Liu, F. Meirer, P. A. Williams, J. Wang, J. C. Andrews, P. Pianetta | TXM-Wizard: a program for advanced data collection and evaluation in full-field transmission X-ray microscopy | *J. Synchrotron Rad.* 19, 281–287 | 2012 | 10.1107/S0909049511049144 | 邊緣跳躍濾波、正規化濾波、半高邊能、R-factor 圖 | GATE-EDGE 下限、R-SNR、R-PRE-FLAT、C-E0-NBR 概念 | 已讀全文 |
| 4 | T.-C. Weng, G. S. Waldo, J. E. Penner-Hahn | A method for normalization of X-ray absorption spectra (MBACK) | *J. Synchrotron Rad.* 12, 506–510 | 2005 | 10.1107/S0909049504034193 | 替代歸一化方法（未採用，備查） | §4 | 僅見書目（xraylarch 引用） |
| 5 | B. Lippold, W. Meyer-Klaucke, T. Meyer, G. Henkel | Towards an automated quality control of XAS data | *J. Synchrotron Rad.* 12, 45–52 | 2005 | 10.1107/S0909049504028821 | 累積差分光譜、判準 7、留一法、迭代剔除 | C-CUMDIFF、T-OUTLIER-SCAN、T-UPDOWN、T-DRIFT | 已讀全文（使用者提供 PDF） |
| 6 | Gaur et al. | Curating and sharing XAS data – Metadata and Scientific quality control | *Scientific Data* | 2026 | 10.1038/s41597-026-07966-x | 穿透模式邊緣跳躍 0.5–2.0、邊能校正、導數峰 FWHM、多掃描判輻射損傷 | GATE-EDGE（D8）、CAL-EREF、T-DRIFT | 僅讀摘要式內容；完整作者名單與卷頁未核對 |
| 7 | C. Leys, C. Ley, O. Klein, P. Bernard, L. Licata | Detecting outliers: Do not use standard deviation around the mean, use absolute deviation around the median | *J. Exp. Soc. Psychol.* 49, 764–766 | 2013 | 10.1016/j.jesp.2013.03.013 | 中位數 ± MAD 離群判定；建議門檻 2.5 | 所有 z-score 規則 | 書目由搜尋結果確認；DOI 與頁碼未逐字核對 |
| 8 | E. A. Stern, K. Kim | Thickness effect on the extended-x-ray-absorption-fine-structure amplitude | *Phys. Rev. B* 23, 3781 | 1981 | 10.1103/PhysRevB.23.3781 | 厚度效應物理依據 | GATE-EDGE 上限 | 書目由搜尋結果確認；未讀全文 |
| 9 | B. Ravel, M. Newville | ATHENA, ARTEMIS, HEPHAESTUS: data analysis for X-ray absorption spectroscopy using IFEFFIT | *J. Synchrotron Rad.* 12, 537–541 | 2005 | 10.1107/S0909049505012719 | R-factor 定義 R = Σ(data−fit)²/Σdata² | C-SHAPE | 僅見書目（TXM-Wizard 引用） |

查證狀態說明：「已讀全文」＝本專案內容直接依據原文；「僅見書目」「未讀全文」者，引用其結論前應先取得原文核對。

---

## 10. 差異紀錄（Discrepancy Log）

記錄資料、文件與設定之間不一致的地方。狀態：**開放**＝尚未解決；**處置中**＝已有暫行做法；**結案**＝已確認。

| ID | 日期 | 項目 | 差異內容 | 影響 | 暫行處置 | 狀態 |
|---|---|---|---|---|---|---|
| D1 | 2026-09-26 | 網格大小 | 專案說明寫 10 × 10；實際資料為 11 資料夾 × 11 檔 = 121 | 矩陣尺寸、座標換算、資料庫筆數 | 依使用者決定以 121 處理，直到有新資料 | 處置中 |
| D2 | 2026-09-26 | 光譜編號跨資料夾重複 | `X0_5_1_120_XANES.txt` 同時列於 Z5_0 資料夾清單（§2.3），且首件分析檔頭標示來源為 `Z6_1/Z6_1.bin`（§4.1）。可能情況：(a) 每個 Z 資料夾的起–終編號相同或相近；(b) 首件分析用的檔案實際來自 Z6_1，與 Z5_0 同名 | 若只以檔名當鍵會混淆不同位置；§4.1 的首件結果屬於 z = +1，不是 z = 0 | 資料庫以 (資料夾, 檔名) 組合解析；讀檔時比對檔頭的來源 `.bin` 路徑與所在資料夾是否一致，不一致即標記 | 已釐清（2026-09-27）：各 Z 資料夾區段編號不同，例 Z6_1 為 1_120、134_254、268_388…，Z5_0 為 1_120、136_256、272_392…；`X0_5_1_120` 同名屬巧合。唯一鍵仍須用 (zdir, fname) |
| D3 | 2026-09-26 | ADC 通道數 | Info.txt 記錄 4 個 ADC 通道（ch 0,2,4,6）；XANES.txt 只用到 col_0、col_1、col_2（I0、I1、I2）。第 4 通道用途與 col 對應哪個物理通道皆未知 | 讀 `.bin` 做逐條分析（R1–R6）時通道可能錯接；第 4 通道若為螢光，可作交叉驗證 | 讀 `.bin` 時先輸出 4 通道的平均值與範圍，由數量級判斷；待光束線紀錄確認 | 開放 |
| D4 | 2026-09-26 | Ni K 邊能標稱值 | 表列 8333.0 eV（guideline）；Info.txt `Element4Edge` 為 8331.90 eV；差 1.1 eV | 單色器偏差估計差約 1 eV（+12.7 vs +13.8 eV）；能量校正的絕對基準 | 設定檔兩值並存，容差 1.5 eV（§4.2） | 處置中 |
| D5 | 2026-09-26 | 資料庫選型 | 原 guideline §6 寫 MySQL、§8 寫 SQLite | 架構 | 使用者決定採用 MySQL（§6） | 結案 |
| D6 | 2026-09-26 | 單色器能量刻度 | 樣品與 mu_ref 的 E₀ 都比標稱值高約 +13 eV | 若未校正，跨區段或與文獻比較時會誤判為化學位移 | 流程中強制先以 mu_ref 校正（§4 步驟 4）；L1 窗監控偏差 | 處置中 |
| D7 | 2026-09-26 | 指標編號：文件 vs 程式 | `main.py` v1.0：Q1 = edge_step 原值、Q5 = glitches、Q6 = white line，無形狀相似度。本文件 §5.2：Q1 = Δμ₀/σ_pre、Q1b = Δμ₀、Q5 = 形狀 R、Q6 = glitch、Q7 = white line | GUI 與文件、資料庫欄位名稱不一致 | 以程式現有編號為準，新增指標另給名稱（snr、shape_R、dE0_nbr），文件下版對齊 | 開放 |
| D8 | 2026-09-26 | GATE-EDGE 門檻 vs 文獻 | 本專案 Δμ₀ ∈ [0.1, 1.5]；Gaur et al. 2026 穿透模式建議 0.5–2.0。首件 Δμ₀ = 0.565 位於其下限附近 | 下限：Gaur 標準為量測設計用，mapping 中 GATE 用於排除未打到樣品的格子，可較寬；上限 1.5 可能過嚴 | 保留 [0.1, 1.5] 為起始值；Examine 121 格後依 Δμ₀ 分佈與目視對照重新決定 | **結案（2026-09-28）**：121 格分佈統計：n=121, min=0.043, max=0.929, median=0.345, MAD·1.4826=0.167；分佈**雙峰** — 6 格於 [0.04, 0.06]（近零訊號）、2 格於 [0.10, 0.13]、110 格於 [0.13, 0.93]；[0.099, 0.131) 為天然分界間隙。現行 [0.10, 1.5] 判 110/121 (90.9%) pass，11 個 FAIL 全部位於 X10_-5 欄（x=−5）或角落，為樣品幾何最左邊。Gaur [0.5, 2.0] 對此資料判 102/121 FAIL（Gaur 為 bulk 單光譜設計，不適用有 off-sample 像素的 mapping）。**現行閾值由資料驗證保留**，config.yaml 註記出處 |
| D9 | 2026-09-27 | 檔名大小寫 | `image_AI_Ni/Z6_1/x5_0_666_786_XANES.txt` 以小寫 `x` 開頭；`pipeline.FNAME_RE = ^X(\d+)_…` 大小寫敏感。Windows 上 `glob("X*_XANES.txt")` 不分大小寫會列出此檔，再被 regex 濾除，無警告 | 中心列 (x, z) = (0, +1) 缺格：`data/` 只有 120/121 格；熱圖該格為空；C-E0-NBR、C-CUMDIFF 的鄰格數受影響 | `pipeline.py` v1.3：`FNAME_RE` 加 `re.IGNORECASE`；`discover_x_files` 改用 `glob("*_XANES.txt")`；新增 `validate_root()` 回傳 ValidationReport（Z 數、每 Z 檔數、被 regex 濾除的檔名），`run_batch` 與 GUI `_populate_z` 都會呼叫；`main.py._select_cell_by_xz` 前綴比對改為 case-insensitive。原始檔不改名 | 結案（2026-09-27）：`--batch` 現產出 121/121 sections, 0 errors；83/83 tests |

| D10 | 2026-09-28 | R-EDGE-FWHM / R-NORM-COEFS z 門檻校準 | v1.4 加入時採用預設 `warn_z=3, fail_z=5`（跟其他 smooth 規則一致）。以 110 gate-pass 格實測後發現分佈近乎 Gaussian（P50\|z\|/max\|z\| ≈ 0.67，對應 N(0,1) 的 MAD 比 0.6745），edge_fwhm_eV max\|z\|=3.86、pre_slope max\|z\|=3.73、norm_c1 max\|z\|=3.03、norm_c2 max\|z\|=2.99、R-NORM-COEFS 合成 max\|z\|=3.73；**fail_z=5 對此資料永遠不觸發**（5σ P<6e−7） | FAIL 淪為裝飾，實質判定只剩 WARN；且與 Leys 2013 建議 warn=2.5、3=非常保守不一致 | **結案（2026-09-28）**：兩規則調為 `warn_z=2.5, fail_z=4`（Leys 2013 預設；4σ 為近 Gaussian 明確離群線）。config.yaml v1.3.0 加註出處。校準後：R-EDGE-FWHM 3 WARN 0 FAIL，R-NORM-COEFS 2 WARN 0 FAIL；usable 保持 76/121（原被其他 smooth 規則覆蓋） |

新差異一律附加在本表末尾，ID 遞增，不刪除舊紀錄；結案時更新狀態欄並註明依據。

---

## 版本紀錄

| 版本 | 日期 | 內容 |
|---|---|---|
| 1.4.4 | 2026-09-28 | D10 結案：R-EDGE-FWHM 與 R-NORM-COEFS 的 z 門檻由 110 gate-pass 分佈校準，`warn_z=3→2.5, fail_z=5→4`。分佈近乎 Gaussian，fail_z=5 於本資料永不觸發。config.yaml v1.3.0 加註出處。校準後：R-EDGE-FWHM 3 WARN 0 FAIL，R-NORM-COEFS 2 WARN 0 FAIL；usable 保持 76/121 |
| 1.4.3 | 2026-09-28 | D8 結案：以 121 格 edge_step 實測分佈驗證 GATE-EDGE `[0.10, 1.5]`。分佈雙峰，天然分界在 0.10，110/121 (90.9%) pass；11 FAIL 全落在樣品幾何邊緣。Gaur [0.5, 2.0] 對本資料判 15.7% pass，證實 mapping 場景不能沿用 bulk 標準。config.yaml v1.2.1 加註出處註解 |
| 1.4.2 | 2026-09-27 | CLI 端：修正 D9。`pipeline.py` v1.3：`FNAME_RE` 加 `re.IGNORECASE`、新增 `validate_root()` + `ValidationReport`、`EXPECTED_Z_COUNT/EXPECTED_X_PER_Z` 常數；`main.py` v1.2：`run_batch` 印出 validate 報告、`_populate_z` 顯示完整性、`_select_cell_by_xz` case-insensitive。4 新測試（83/83）。`--batch` 重跑產出 121/121 sections, 0 errors，Examine 121 cells, 76 usable。D9 狀態 → 結案 |
| 1.4.1 | 2026-09-27 | by Albert Sheng。§10 新增 D9（Z6_1 中心格檔名小寫被無聲略過，120/121）；D2 改為已釐清；新增 `doc/status.md` |
| 1.4.0 | 2026-09-27 | CLI 端：實作 `R-EDGE-FWHM`（Gaur 2026 導數峰寬 → grid-relative 雙側 z）與 `R-NORM-COEFS`（§5.2 A Q3：pre_slope + norm_c1 + norm_c2 之 max\|z\|）；`pipeline.py` 一併持久化 `edge_fwhm_eV`、`pre_slope`、`norm_c0/1/2`；config 兩條 `enabled: true`；6 新測試（79/79 全通過）；§5.1.1 補兩列 |
| 1.3.1 | 2026-09-27 | by Albert Sheng。§9 參考資料改為表格：加入 DOI、本專案用途、對應規則、查證狀態（由 claude.ai 規劃端合併） |
| 1.3 | 2026-09-26 | C-CUMDIFF（Lippold 2005 判準 7 vs 8 鄰格平均）於 `rules.py` / `examine.py` 完成實作與測試（73/73 通過），config 加對應條目，§5.1.1 標記為「v1.3 起實作」 |
| 1.2 | 2026-09-26 | by Albert Sheng。§5.1 加入 Lippold 2005、Gaur 2026、Leys 2013、Stern & Kim 1981；新增 §5.1.1 規則出處對照；R4 改為 Lippold 判準 7；新增選用規則 C-CUMDIFF；§9 參考資料 5–9；§10 新增 D8 |
| 1.1.1 | 2026-09-26 | §10 新增 D7（main.py 指標編號與文件不一致） |
| 1.1.0 | 2026-09-26 | 決定採用 MySQL（§6，含 schema 建議）；新增 §4.2 邊能設定與三層容差；確認以 121 格處理；新增 §10 差異紀錄 D1–D6 |
| 1.0.0 | 2026-09-26 | 合併 naming_matrix v1.0.0 與 XANES_guideline v0.1；加入 Info.txt 解讀（§3.1）、TXM-Wizard 判準（§5.1）、QEXAFS 逐條光譜指標（§5.2 B/C）；標出資料庫選型矛盾與 Ni K 邊能兩個參考值 |

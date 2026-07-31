# 00631L 50:50 回測

驗證一個假設：把 **00631L（元大台灣50正2）** 跟另一個標的各配置 **50%**，能不能讓 00631L 原本很深的最大回撤（MDD）變淺一點，同時長期報酬仍然勝過單押 **0050（元大台灣50）**。

程式會自動抓取歷史股價，針對「多種配對標的 × 多種再平衡規則」跑出完整的回測比較表與圖表。

> 本專案僅供投資研究與教育用途，回測結果不代表未來績效，不構成投資建議。

## 這個工具在測什麼

- **配對標的**（都跟 00631L 各佔 50%）：
  - 00631L + 0050
  - 00631L + 現金（用可調整的固定年化報酬率模擬貨幣市場）
  - 00631L + 00675L（富邦臺灣加權正2，另一檔正2 ETF）
- **再平衡規則**：不再平衡（buy-and-hold）、每月、每季、偏離 10% 觸發、偏離 15% 觸發
- **對照基準**：100% 00631L、100% 0050、100% 00675L
- **績效指標**：CAGR、最大回撤（MDD）、年化波動度、Sharpe、Calmar

所有標的、配對、再平衡規則都定義在 [config.yaml](config.yaml)，不需要改程式碼就能調整或擴充組合。

除了主回測，這個專案還有兩個延伸分析：

- **正2實際表現拆解**：00631L 的實際報酬，有多少是「波動耗損」造成的落差、多少是「費用/其他因素」造成的落差？用 0050 的每日報酬模擬一條「理論上每天複利 2 倍」的合成曲線，拿去跟 00631L 的實際淨值比對
- **歷史空頭壓力測試**（`bear_market_backtest.py`）：00631L 只有 2014-10-31 之後的資料，沒經歷過 2000 網路泡沫、2008 金融海嘯。改用台灣加權指數（^TWII，最早可拉到 1997-07-02）模擬一檔合成正2商品，重新跑一次 50:50 再平衡策略，檢驗「50:50 降 MDD」這個結論在真正的空頭市場中是否還成立

## 安裝

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 使用方式

```bash
python main.py
```

預設會讀取 `config.yaml`，把歷史股價快取到 `data/cache/`，並把結果輸出到 `output/`：

- `results.csv` / `results.md`：所有策略組合的績效比較表
- `overview_equity.png` / `overview_drawdown.png`：基準 vs 各配對「表現最好的再平衡規則」總覽圖
- `<配對名稱>_equity.png` / `<配對名稱>_drawdown.png`：單一配對底下所有再平衡規則的細部比較圖
- `leverage_tracking.csv` / `.md` / `leverage_tracking_equity.png`：正2實際表現拆解（見下方說明）

也可以指定其他設定檔或輸出資料夾：

```bash
python main.py --config config.yaml --output output
```

若要強制重新抓取資料（忽略本地快取），把 `config.yaml` 裡的 `data.refresh` 設成 `true`。

### 正2實際表現拆解怎麼看

`leverage_tracking.md` 會列出四種角度的「2 倍」表現，由上到下依序疊加更多真實世界的因素：

1. **理論上一次性 2 倍**：直接把 0050 的總報酬乘以 2 倍，完全忽略逐日複利的路徑相依性（只是拿來對照的錯誤示範）
2. **合成每日複利 2 倍（無費用）**：用 0050 的真實每日報酬，每天複利 2 倍，會自然吃到「波動耗損」，但還沒扣費用
3. **合成每日複利 2 倍（含年費）**：在 2 的基礎上再扣掉 `leverage_analysis.annual_cost` 設定的年化費用
4. **00631L 實際表現**：真實市場數據

把 (4) 減 (3) 看到的落差，才是無法用「波動耗損」或「已知費用」解釋、屬於期貨逆價差捕捉股息與否等真實世界因素的部分。

### 歷史空頭壓力測試

```bash
python bear_market_backtest.py
```

讀取 `bear_market_config.yaml`，用台灣加權指數（^TWII）模擬一檔合成正2商品（`leverage` / `annual_cost` 沿用跟主回測一樣的假設），重新跑一次「單押正2 / 單押指數 / 50:50 各種再平衡規則」，輸出到 `output/bear_market/`：

- `results.csv` / `.md`、`full_period_equity.png` / `full_period_drawdown.png`：1997 至今的全期間比較（跟 `main.py` 的輸出對應）
- `stress_windows.csv` / `.md`：每個策略在 `bear_market_config.yaml` 裡定義的各個歷史空頭區間（2000 網路泡沫、2008 金融海嘯、2015 中國股災、2018 Q4 修正、2020 新冠崩盤、2022 熊市）的區間報酬與區間 MDD
- `window_<區間名稱>_equity.png` / `_drawdown.png`：各區間的局部放大圖

想加減檢視的區間，直接改 `bear_market_config.yaml` 的 `stress_windows` 清單即可。

## 執行測試

```bash
pytest
```

## 專案結構

```
.
├── config.yaml               # 主回測：標的清單、回測區間、再平衡規則、策略組合
├── bear_market_config.yaml    # 歷史空頭壓力測試：模擬標的、槓桿假設、要檢視的空頭區間
├── main.py                    # 主回測 CLI 進入點
├── bear_market_backtest.py    # 歷史空頭壓力測試 CLI 進入點
├── src/
│   ├── data_fetcher.py        # 抓取 + 快取歷史股價（Yahoo Finance）
│   ├── portfolio.py           # 50:50 組合建構 + 再平衡邏輯
│   ├── metrics.py             # CAGR / MDD / 波動度 / Sharpe / Calmar
│   ├── backtest.py            # 讀 config，跑所有策略組合
│   ├── leverage_analysis.py   # 合成每日複利槓桿、拆解正2實際表現的追蹤差異
│   ├── stress_test.py         # 把 NAV 序列切成指定的歷史空頭區間並統計
│   └── report.py               # 圖表與比較表輸出
└── tests/                       # pytest 單元測試
```

## 已知限制

- 用調整後收盤價（`auto_adjust=True`）近似含息報酬，不是每天逐筆對帳的精確含息計算
- 「現金」是用固定年化利率模擬的合成序列，不是真實貨幣市場基金的歷史淨值
- 各標的的回測起始日會自動對齊到「所有標的都有資料」的交集區間，因此不同配對組合的回測起始日可能因標的上市時間不同而有落差（例如 00675L 上市較晚，含 00675L 的配對區間會相應縮短）
- 正2實際表現拆解（`leverage_analysis`）用的 `annual_cost` 只是概略假設，實際內扣費用請以基金公開說明書為準
- 歷史空頭壓力測試裡的「合成正2」是用台灣加權指數（^TWII）模擬的假設商品，**不是** 00631L 真實存在過的歷史；^TWII 是原始價格指數、不含息，跟主回測裡用還原股價（含息）計算的 0050 基準不完全對等，所以這部分的「指數本身」報酬會比真實 0050 略為低估
- 空頭壓力測試的區間 MDD，是相對「該區間起點」重新計算的，不是抓全歷史最高點，所以區間起點若沒設在真正的區域高點附近，MDD 可能被低估（`bear_market_config.yaml` 已把每個區間的起點刻意往前抓，降低這個風險）

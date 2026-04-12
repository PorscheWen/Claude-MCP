---
name: stock-advisor
description: 分析前一交易日的台股與美股狀況，產生今日操作建議。當使用者說「幫我看股票」、「今天要怎麼操作」、「分析一下XXX」、「最近股票怎麼樣」、「給我操作建議」、「看一下我的自選股」等相關描述，或使用者提供股票代碼並詢問買賣時機，都應觸發此 skill。台股代號格式為數字（如 2330），美股為英文字母（如 AAPL）。
---

# Stock Advisor

根據前一交易日資料，對台股和美股進行多維度分析，產生今日操作建議。

## 分析目標

對每支股票產出：
- **技術面**：均線、RSI、MACD、布林通道、成交量
- **消息面**：最新重要新聞（正面/負面/中性）
- **大盤環境**：台股加權/美股三大指數走勢
- **法人籌碼**：外資、投信、自營商（台股專用）
- **操作建議**：買進 / 加碼 / 觀望 / 減碼 / 賣出，附理由

---

## Step 1：確認股票清單

若使用者沒有指定股票，使用預設自選股清單（見下方）。
若使用者有指定，優先使用使用者指定的股票。
台股代號加上 `.TW` 後綴使用 yfinance（例如 `2330.TW`）；OTC 加 `.TWO`。

**預設自選股清單**（可由使用者在 CLAUDE.md 中更新）：
```
台股（個股）: 2330, 2542, 2618, 2801, 2812, 2880, 2884, 5880, 9945, 1432
台股（ETF）:  00631L, 00712, 009816
美股: NVDA, AAPL, MSFT, TSLA, AMD
```

---

## Step 2：安裝/確認依賴套件

```bash
pip install yfinance pandas pandas-ta requests -q
```

---

## Step 3：抓取市場資料

用 Python 執行以下分析，時間範圍取近 60 個交易日（足夠計算技術指標）：

```python
import yfinance as yf
import pandas as pd

# 台股範例
ticker = yf.Ticker("2330.TW")
hist = ticker.history(period="3mo")

# 美股範例
ticker = yf.Ticker("NVDA")
hist = ticker.history(period="3mo")
```

同時抓取大盤指數：
- 台股：`^TWII`（加權指數）、`^TWO`（櫃買指數）
- 美股：`^GSPC`（S&P 500）、`^IXIC`（NASDAQ）、`^DJI`（道瓊）

---

## Step 4：計算技術指標

對每支股票計算以下指標，基於前一交易日收盤資料：

| 指標 | 說明 |
|------|------|
| MA5 / MA20 / MA60 | 短中長期均線，判斷趨勢方向 |
| RSI(14) | 超買(>70) / 超賣(<30) |
| MACD | DIF/DEA 金叉死叉 |
| 布林通道 | 股價相對上下軌位置 |
| 成交量 | 與 MA20 成交量比較，判斷量能 |

計算方法（使用 pandas，不需額外套件）：
```python
# RSI
delta = hist['Close'].diff()
gain = delta.where(delta > 0, 0).rolling(14).mean()
loss = -delta.where(delta < 0, 0).rolling(14).mean()
rs = gain / loss
rsi = 100 - (100 / (1 + rs))

# MACD
ema12 = hist['Close'].ewm(span=12).mean()
ema26 = hist['Close'].ewm(span=26).mean()
dif = ema12 - ema26
dea = dif.ewm(span=9).mean()
macd_bar = (dif - dea) * 2

# 布林通道
ma20 = hist['Close'].rolling(20).mean()
std20 = hist['Close'].rolling(20).std()
upper = ma20 + 2 * std20
lower = ma20 - 2 * std20
```

---

## Step 5：法人籌碼（台股）

對台股，使用 TWSE 公開 API 查詢前一日三大法人買賣超：

```python
import requests
from datetime import datetime, timedelta

# 取得前一交易日日期（格式 YYYYMMDD）
date_str = "20250411"  # 動態計算

url = f"https://www.twse.com.tw/rwd/zh/fund/T86?response=json&date={date_str}&selectType=ALL"
resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
data = resp.json()
```

若 API 失敗或非交易日，標記「法人資料暫不可用」，繼續其他分析。

---

## Step 6：搜尋最新消息

使用 WebSearch 工具搜尋每支股票的最新新聞：
- 搜尋關鍵字：`{股票名稱} {代碼} 新聞 {日期}`
- 找出 1-3 則重要新聞，判斷對股價的影響（正面/負面/中性）

---

## Step 7：產生操作建議

### 建議邏輯框架

綜合以下訊號給出建議，避免只靠單一指標判斷：

| 建議 | 條件範例 |
|------|---------|
| [強力買進] | 技術多頭排列 + 法人大買 + 正面消息 + 大盤強勢 |
| [買進/加碼] | 技術面偏多 + 消息偏中性 + 大盤平穩 |
| [觀望]     | 訊號矛盾 / 大盤方向不明 / 消息不明朗 |
| [減碼]     | 技術轉弱 + 法人賣出 / 負面消息出現 |
| [賣出]     | 技術空頭排列 + 法人持續賣出 + 負面消息 |

---

## Step 8：輸出格式

每支股票產出以下格式（Markdown）：

```
## 【代碼】股票名稱 ｜ 建議：[買進] / [觀望] / [賣出]

### 前一日收盤
- 收盤價：XXX（漲跌 ±X.XX，X.XX%）
- 成交量：XXX 張（較均量 ↑↓ XX%）

### 技術面
- MA5/MA20/MA60：XXX / XXX / XXX（多頭/空頭排列）
- RSI(14)：XX.X（正常/超買/超賣）
- MACD：DIF XX.X / DEA XX.X（金叉/死叉）
- 布林通道：股價在中軌（上/下）方，距上軌 XX%

### 法人籌碼（台股）
- 外資：+/- XXXX 張
- 投信：+/- XXXX 張
- 自營商：+/- XXXX 張

### 最新消息
- 【正面/負面/中性】XXX 新聞標題（來源）

### 操作建議
**建議：買進/觀望/賣出**
理由：綜合說明（2-3 句話，說明主要依據）
短線目標價：XXX｜停損參考：XXX
```

### 大盤摘要（放在所有股票分析之前）

```
## 大盤環境
### 台股
- 加權指數：XX,XXX（前日漲跌 ±XX，X.XX%）
- 今日氛圍：偏多/偏空/盤整

### 美股（前一收盤）
- S&P500：X,XXX（±X.XX%）
- NASDAQ：XX,XXX（±X.XX%）
- 道瓊：XX,XXX（±X.XX%）
```

---

## 注意事項

- 此分析僅供參考，不構成投資建議，最終決策由使用者自行判斷
- 若 yfinance 資料抓取失敗，標記「資料暫不可用」並繼續其他股票
- 週末/假日執行時，自動使用最近一個交易日的資料
- 價格單位：台股為新台幣（元），美股為美元
- 若使用者有提供 `.env` 中的自選股清單，優先使用

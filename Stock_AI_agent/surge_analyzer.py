"""
Taiwan Stock Top-100 Volume - Next-Day Surge Potential Analysis
Analysis date: 2026-04-10
"""

import sys
import io
# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import requests
import pandas as pd
import yfinance as yf
import json
import re
from datetime import datetime, timedelta

TRADE_DATE = "20260410"
TRADE_DATE_FMT = "2026-04-10"


# ─────────────────────────────────────────
# Step 1: 抓取 TWSE 當日全部成交資料
# ─────────────────────────────────────────
def fetch_top100_by_volume(date_str: str) -> pd.DataFrame:
    url = f"https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY_ALL?response=json&date={date_str}"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    data = resp.json()

    rows = data.get("data", [])
    if not rows:
        raise ValueError("TWSE 資料為空，請確認日期是否為交易日")

    df = pd.DataFrame(rows, columns=[
        "code", "name", "shares", "value",
        "open", "high", "low", "close",
        "change", "volume_lots"
    ])

    # 只保留純數字代號的個股（排除 ETF / ETN 等 6 碼）
    df = df[df["code"].str.match(r"^\d{4}$")]

    def parse_num(x):
        try:
            return float(str(x).replace(",", ""))
        except:
            return 0.0

    df["shares"] = df["shares"].apply(parse_num)
    df["volume_lots"] = df["volume_lots"].apply(parse_num)
    df["close"] = df["close"].apply(parse_num)
    df["open"] = df["open"].apply(parse_num)
    df["high"] = df["high"].apply(parse_num)
    df["low"] = df["low"].apply(parse_num)

    # 解析漲跌幅
    def parse_change(x):
        x = str(x).strip()
        m = re.search(r"([+-]?\d+\.?\d*)", x)
        return float(m.group(1)) if m else 0.0

    df["change_val"] = df["change"].apply(parse_change)
    df["change_pct"] = df.apply(
        lambda r: (r["change_val"] / (r["close"] - r["change_val"]) * 100)
        if (r["close"] - r["change_val"]) > 0 else 0.0,
        axis=1
    )

    # 依成交量(張)排序，取前 100
    df = df.sort_values("volume_lots", ascending=False).head(100).reset_index(drop=True)
    return df


# ─────────────────────────────────────────
# Step 2: 用 yfinance 抓取近 60 日歷史
# ─────────────────────────────────────────
def fetch_history(code: str) -> pd.DataFrame | None:
    ticker_sym = f"{code}.TW"
    try:
        ticker = yf.Ticker(ticker_sym)
        hist = ticker.history(period="3mo")
        if hist.empty or len(hist) < 20:
            return None
        hist.index = hist.index.tz_localize(None)
        return hist
    except Exception:
        return None


# ─────────────────────────────────────────
# Step 3: 計算技術指標
# ─────────────────────────────────────────
def calc_indicators(hist: pd.DataFrame) -> dict:
    close = hist["Close"]
    volume = hist["Volume"]

    # 均線
    ma5  = close.rolling(5).mean().iloc[-1]
    ma20 = close.rolling(20).mean().iloc[-1]
    ma60 = close.rolling(60).mean().iloc[-1] if len(close) >= 60 else None
    last_close = close.iloc[-1]
    prev_close = close.iloc[-2] if len(close) >= 2 else last_close

    # RSI(14)
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 1e-9)
    rsi = (100 - 100 / (1 + rs)).iloc[-1]

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False).mean()
    macd_bar = (dif - dea) * 2
    dif_val = dif.iloc[-1]
    dea_val = dea.iloc[-1]
    macd_val = macd_bar.iloc[-1]
    prev_macd = macd_bar.iloc[-2] if len(macd_bar) >= 2 else macd_val

    # 布林通道
    ma20_s = close.rolling(20).mean()
    std20  = close.rolling(20).std()
    upper  = (ma20_s + 2 * std20).iloc[-1]
    lower  = (ma20_s - 2 * std20).iloc[-1]

    # 成交量比
    vol_now  = volume.iloc[-1]
    vol_ma20 = volume.rolling(20).mean().iloc[-1]
    vol_ratio = vol_now / (vol_ma20 + 1e-9)

    # 近 5 日漲幅
    ret5 = (last_close / close.iloc[-6] - 1) * 100 if len(close) >= 6 else 0

    return {
        "last_close": last_close,
        "prev_close": prev_close,
        "change_pct_yf": (last_close / prev_close - 1) * 100,
        "ma5": ma5,
        "ma20": ma20,
        "ma60": ma60,
        "rsi": rsi,
        "dif": dif_val,
        "dea": dea_val,
        "macd_bar": macd_val,
        "prev_macd_bar": prev_macd,
        "upper_band": upper,
        "lower_band": lower,
        "mid_band": (ma20_s).iloc[-1],
        "vol_ratio": vol_ratio,
        "ret5": ret5,
    }


# ─────────────────────────────────────────
# Step 4: 法人籌碼
# ─────────────────────────────────────────
def fetch_institutional(date_str: str) -> dict:
    """回傳 {code: {foreign, trust, dealer}} 的字典"""
    url = f"https://www.twse.com.tw/rwd/zh/fund/T86?response=json&date={date_str}&selectType=ALL"
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        data = resp.json()
        if data.get("stat") != "OK":
            return {}
        result = {}
        for row in data.get("data", []):
            code = str(row[0]).strip()
            def to_int(x):
                try:
                    return int(str(x).replace(",", ""))
                except:
                    return 0
            result[code] = {
                "foreign": to_int(row[4]),   # 外資買賣超
                "trust":   to_int(row[10]),  # 投信買賣超
                "dealer":  to_int(row[14]),  # 自營商買賣超
            }
        return result
    except Exception:
        return {}


# ─────────────────────────────────────────
# Step 5: 評分模型（暴漲潛力）
# ─────────────────────────────────────────
def score_surge_potential(ind: dict, inst: dict, today_info: dict) -> float:
    score = 0.0

    # === 技術面 (最高 60 分) ===

    # 1. 均線多頭排列
    if ind["ma5"] > ind["ma20"]:
        score += 8
    if ind["ma20"] > (ind["ma60"] or 0):
        score += 5

    # 2. RSI 超賣回彈（30-50 金叉潛力區）
    rsi = ind["rsi"]
    if 30 < rsi < 50:
        score += 10
    elif 50 <= rsi < 65:
        score += 5
    elif rsi < 30:
        score += 7  # 極度超賣，反彈機率高

    # 3. MACD 金叉或剛金叉
    if ind["dif"] > ind["dea"] and ind["prev_macd_bar"] < 0 and ind["macd_bar"] >= 0:
        score += 15  # 剛形成金叉，強烈訊號
    elif ind["dif"] > ind["dea"] and ind["macd_bar"] > 0:
        score += 8
    elif ind["macd_bar"] > ind["prev_macd_bar"]:
        score += 3   # MACD 柱體擴大

    # 4. 布林通道下軌反彈
    last = ind["last_close"]
    lower = ind["lower_band"]
    upper = ind["upper_band"]
    mid   = ind["mid_band"]
    band_width = upper - lower
    if band_width > 0:
        pos = (last - lower) / band_width
        if pos < 0.2:
            score += 10  # 接近下軌，反彈概率高
        elif 0.2 <= pos < 0.4:
            score += 5

    # 5. 爆量（相對均量）
    vr = ind["vol_ratio"]
    if vr >= 3.0:
        score += 12  # 爆量突破，強訊號
    elif vr >= 2.0:
        score += 8
    elif vr >= 1.5:
        score += 4

    # 6. 近5日漲幅（不能太高，避免追高）
    ret5 = ind["ret5"]
    if -5 <= ret5 < 0:
        score += 5  # 略微回調，即將反彈
    elif 0 <= ret5 < 5:
        score += 3

    # === 法人面 (最高 30 分) ===
    if inst:
        foreign = inst.get("foreign", 0)
        trust   = inst.get("trust", 0)
        dealer  = inst.get("dealer", 0)

        if foreign > 1000:
            score += 10
        elif foreign > 500:
            score += 6
        elif foreign > 0:
            score += 3

        if trust > 200:
            score += 10
        elif trust > 50:
            score += 6
        elif trust > 0:
            score += 3

        if dealer > 0:
            score += 3

        # 三大法人同步買超
        if foreign > 0 and trust > 0 and dealer > 0:
            score += 7

    # === 當日量能與漲幅 (最高 20 分) ===
    day_vol = today_info.get("volume_lots", 0)
    day_chg = today_info.get("change_pct", 0)

    # 漲幅不太大但量大，隔日繼續強
    if 2 < day_chg <= 6:
        score += 5
    elif 0 < day_chg <= 2:
        score += 3
    elif day_chg > 6:
        score += 2  # 已漲太多，回調風險

    if day_vol > 50000:
        score += 8
    elif day_vol > 20000:
        score += 5
    elif day_vol > 10000:
        score += 3

    return round(score, 1)


# ─────────────────────────────────────────
# Step 6: 大盤趨勢預測
# ─────────────────────────────────────────
ETF_BULL = "00631L"   # 元大台灣50正2（2x 多方槓桿）
ETF_BEAR = "00618"    # 空方對應 ETF


def predict_market_trend() -> dict:
    """
    分析台股加權指數 (^TWII) + 美股三大指數，
    預測隔日是否有 5%+ 漲幅，或一週內持續上漲趨勢。

    回傳 dict:
      direction  : "strong_bull" | "bull" | "neutral" | "bear" | "strong_bear"
      score      : -100 ~ +100（正=偏多，負=偏空）
      next_day_5pct_prob : 隔日 5%+ 漲幅概率描述
      weekly_trend       : 一週趨勢描述
      etf_action         : {"code", "name", "action", "reason"}
      signals            : list of signal strings
      twii               : TWII 最新技術數據
      us_markets         : US 指數摘要
    """
    signals = []
    score = 0

    # ── 1. 台股加權指數 ──
    twii_hist = None
    twii_data = {}
    try:
        twii = yf.Ticker("^TWII")
        twii_hist = twii.history(period="3mo")
        twii_hist.index = twii_hist.index.tz_localize(None)

        close = twii_hist["Close"]
        volume = twii_hist["Volume"]

        last  = close.iloc[-1]
        prev  = close.iloc[-2]
        day_chg_pct = (last / prev - 1) * 100

        ma5  = close.rolling(5).mean().iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        ma60 = close.rolling(60).mean().iloc[-1] if len(close) >= 60 else None

        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = (100 - 100 / (1 + gain / (loss + 1e-9))).iloc[-1]

        # MACD
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()
        dif_val  = dif.iloc[-1]
        dea_val  = dea.iloc[-1]
        dif_prev = dif.iloc[-2]
        dea_prev = dea.iloc[-2]

        # 布林通道
        ma20_s = close.rolling(20).mean()
        std20  = close.rolling(20).std()
        upper  = (ma20_s + 2 * std20).iloc[-1]
        lower  = (ma20_s - 2 * std20).iloc[-1]
        bb_pos = (last - lower) / (upper - lower + 1e-9)

        # 近 5 日 / 10 日動量
        ret5  = (last / close.iloc[-6]  - 1) * 100 if len(close) >= 6  else 0
        ret10 = (last / close.iloc[-11] - 1) * 100 if len(close) >= 11 else 0

        # 成交量比
        vol_ratio = volume.iloc[-1] / (volume.rolling(20).mean().iloc[-1] + 1e-9)

        twii_data = {
            "last": round(last, 1),
            "day_chg_pct": round(day_chg_pct, 2),
            "ma5": round(ma5, 1),
            "ma20": round(ma20, 1),
            "ma60": round(ma60, 1) if ma60 else None,
            "rsi": round(rsi, 1),
            "dif": round(dif_val, 2),
            "dea": round(dea_val, 2),
            "upper": round(upper, 1),
            "lower": round(lower, 1),
            "bb_pos": round(bb_pos, 2),
            "ret5": round(ret5, 2),
            "ret10": round(ret10, 2),
            "vol_ratio": round(vol_ratio, 2),
        }

        # ── 評分：均線 ──
        if ma5 > ma20:
            score += 15
            signals.append("TWII MA5 > MA20（短線多頭排列）")
        else:
            score -= 15
            signals.append("TWII MA5 < MA20（短線空頭排列）")

        if ma60 and ma20 > ma60:
            score += 10
            signals.append("TWII MA20 > MA60（中長線偏多）")
        elif ma60 and ma20 < ma60:
            score -= 10
            signals.append("TWII MA20 < MA60（中長線偏空）")

        # ── 評分：RSI ──
        if 50 <= rsi <= 70:
            score += 12
            signals.append(f"TWII RSI={rsi:.1f}（健康多頭區）")
        elif rsi > 70:
            score += 3
            signals.append(f"TWII RSI={rsi:.1f}（超買，短線注意回調）")
        elif 30 <= rsi < 50:
            score -= 8
            signals.append(f"TWII RSI={rsi:.1f}（弱勢區，偏空）")
        else:
            score += 8  # 極度超賣，反彈機率升高
            signals.append(f"TWII RSI={rsi:.1f}（極度超賣，反彈訊號）")

        # ── 評分：MACD ──
        golden_cross = (dif_prev < dea_prev) and (dif_val >= dea_val)
        death_cross  = (dif_prev > dea_prev) and (dif_val <= dea_val)

        if golden_cross:
            score += 20
            signals.append("TWII MACD 剛形成金叉（強力買進訊號）")
        elif dif_val > dea_val:
            score += 10
            signals.append(f"TWII MACD 多頭（DIF={dif_val:.1f} > DEA={dea_val:.1f}）")
        elif death_cross:
            score -= 20
            signals.append("TWII MACD 剛形成死叉（強力賣出訊號）")
        else:
            score -= 10
            signals.append(f"TWII MACD 空頭（DIF={dif_val:.1f} < DEA={dea_val:.1f}）")

        # ── 評分：布林通道位置 ──
        if bb_pos < 0.2:
            score += 15
            signals.append(f"TWII 接近布林下軌（位置 {bb_pos:.0%}），反彈空間大")
        elif bb_pos > 0.85:
            score -= 8
            signals.append(f"TWII 接近布林上軌（位置 {bb_pos:.0%}），短線壓力")
        else:
            score += 5

        # ── 評分：動量 ──
        if ret5 > 5:
            score += 10
            signals.append(f"TWII 近5日強勢上漲 +{ret5:.1f}%，動能延續中")
        elif ret5 > 0:
            score += 5
        elif ret5 < -5:
            score -= 10
            signals.append(f"TWII 近5日下跌 {ret5:.1f}%，空頭壓力")

        # ── 評分：當日漲幅（動能延續判斷）──
        if day_chg_pct > 3:
            score += 8
            signals.append(f"TWII 當日大漲 +{day_chg_pct:.1f}%，隔日動能可期")
        elif day_chg_pct > 0:
            score += 3
        elif day_chg_pct < -3:
            score -= 8
            signals.append(f"TWII 當日大跌 {day_chg_pct:.1f}%，注意恐慌蔓延")

        # ── 評分：爆量 ──
        if vol_ratio > 1.8:
            score += 8
            signals.append(f"TWII 爆量（量比 {vol_ratio:.1f}x），主力介入明顯")

    except Exception as e:
        signals.append(f"TWII 資料抓取失敗：{e}")

    # ── 2. 美股三大指數（前收盤，台股重要參考）──
    us_data = {}
    us_tickers = {"S&P500": "^GSPC", "NASDAQ": "^IXIC", "Dow Jones": "^DJI"}
    us_total_chg = 0
    us_count = 0

    for name, sym in us_tickers.items():
        try:
            t = yf.Ticker(sym)
            h = t.history(period="5d")
            h.index = h.index.tz_localize(None)
            if len(h) >= 2:
                last_us  = h["Close"].iloc[-1]
                prev_us  = h["Close"].iloc[-2]
                chg_pct  = (last_us / prev_us - 1) * 100
                us_data[name] = {"close": round(last_us, 1), "chg_pct": round(chg_pct, 2)}
                us_total_chg += chg_pct
                us_count += 1
        except Exception:
            us_data[name] = {"close": None, "chg_pct": None}

    if us_count > 0:
        us_avg_chg = us_total_chg / us_count
        if us_avg_chg > 2:
            score += 15
            signals.append(f"美股三大指數平均漲 +{us_avg_chg:.1f}%（台股跟漲動能強）")
        elif us_avg_chg > 0.5:
            score += 7
            signals.append(f"美股小幅收紅 +{us_avg_chg:.1f}%（台股溫和正面）")
        elif us_avg_chg < -2:
            score -= 15
            signals.append(f"美股三大指數平均跌 {us_avg_chg:.1f}%（台股開低壓力大）")
        elif us_avg_chg < -0.5:
            score -= 7
            signals.append(f"美股小幅收黑 {us_avg_chg:.1f}%（台股偏保守）")

    # ── 3. 綜合判斷 ──
    score = max(-100, min(100, score))

    # 隔日 5%+ 漲幅概率判斷（需多重強訊號）
    if score >= 60:
        next_day_5pct = "高（多重強訊號共振，隔日跳空大漲可能性明顯）"
    elif score >= 40:
        next_day_5pct = "中（偏多，但 5% 以上需配合外資大量回補）"
    elif score >= 15:
        next_day_5pct = "低（偏多但力道不足，小幅上漲較可能）"
    elif score <= -40:
        next_day_5pct = "極低（偏空，下跌風險高）"
    else:
        next_day_5pct = "極低（盤整或下跌較可能）"

    # 一週趨勢
    if score >= 50:
        weekly = "一週偏多：均線多頭排列 + MACD 動能向上，持續上漲趨勢明確"
    elif score >= 20:
        weekly = "一週溫和偏多：指數處於整理後醞釀上攻階段"
    elif score >= -20:
        weekly = "一週方向不明：觀望等待訊號更明確"
    elif score >= -50:
        weekly = "一週偏空：短線弱勢，注意支撐是否守住"
    else:
        weekly = "一週空頭明確：建議減碼避險"

    # 方向判定
    if score >= 50:
        direction = "strong_bull"
    elif score >= 20:
        direction = "bull"
    elif score <= -50:
        direction = "strong_bear"
    elif score <= -20:
        direction = "bear"
    else:
        direction = "neutral"

    # ETF 建議
    if direction in ("strong_bull", "bull"):
        etf_action = {
            "code":   ETF_BULL,
            "name":   "元大台灣50正2（2x槓桿多方）",
            "action": "買進" if direction == "bull" else "強力買進",
            "reason": f"大盤多頭訊號明確（評分 {score:+d}），{ETF_BULL} 可放大漲幅收益",
        }
    elif direction in ("strong_bear", "bear"):
        etf_action = {
            "code":   ETF_BEAR,
            "name":   "00618（空方對應 ETF）",
            "action": "買進" if direction == "bear" else "強力買進",
            "reason": f"大盤空頭訊號出現（評分 {score:+d}），{ETF_BEAR} 可對沖下跌風險",
        }
    else:
        etf_action = {
            "code":   None,
            "name":   None,
            "action": "觀望",
            "reason": f"大盤方向不明（評分 {score:+d}），建議等待更清晰訊號後再進場",
        }

    return {
        "direction":        direction,
        "score":            score,
        "next_day_5pct_prob": next_day_5pct,
        "weekly_trend":     weekly,
        "etf_action":       etf_action,
        "signals":          signals,
        "twii":             twii_data,
        "us_markets":       us_data,
    }


# ─────────────────────────────────────────
# Step 6: 主程式
# ─────────────────────────────────────────
def main():
    print(f"\n{'='*60}")
    print(f" 台股前百大交易量 — 隔日暴漲潛力分析")
    print(f" 分析基準日：{TRADE_DATE_FMT}")
    print(f"{'='*60}\n")

    print("► 抓取 TWSE 前百大交易量股票...")
    top100 = fetch_top100_by_volume(TRADE_DATE)
    print(f"  取得 {len(top100)} 支個股\n")

    print("► 大盤趨勢預測（TWII + 美股）...")
    market = predict_market_trend()
    direction_label = {
        "strong_bull": "強力多頭",
        "bull":        "偏多",
        "neutral":     "盤整觀望",
        "bear":        "偏空",
        "strong_bear": "強力空頭",
    }.get(market["direction"], "不明")
    etf = market["etf_action"]
    print(f"  大盤評分：{market['score']:+d} ｜ 方向：{direction_label}")
    if etf["code"]:
        print(f"  ETF 建議：{etf['action']} {etf['code']} ({etf['name']})")
    else:
        print(f"  ETF 建議：{etf['action']}")
    print()

    print("► 抓取三大法人籌碼...")
    inst_all = fetch_institutional(TRADE_DATE)
    print(f"  取得 {len(inst_all)} 支法人資料\n")

    results = []
    print("► 計算技術指標與評分 (共100支)...")

    for idx, row in top100.iterrows():
        code = row["code"]
        hist = fetch_history(code)
        if hist is None:
            continue

        try:
            ind = calc_indicators(hist)
        except Exception:
            continue

        inst = inst_all.get(code, {})
        today_info = {
            "volume_lots": row["volume_lots"],
            "change_pct": row["change_pct"],
        }

        surge_score = score_surge_potential(ind, inst, today_info)

        results.append({
            "rank_vol": idx + 1,
            "code": code,
            "close": ind["last_close"],
            "change_pct": row["change_pct"],
            "volume_lots": int(row["volume_lots"]),
            "vol_ratio": round(ind["vol_ratio"], 2),
            "rsi": round(ind["rsi"], 1),
            "ma5": round(ind["ma5"], 2),
            "ma20": round(ind["ma20"], 2),
            "dif": round(ind["dif"], 3),
            "dea": round(ind["dea"], 3),
            "macd_bar": round(ind["macd_bar"], 3),
            "upper": round(ind["upper_band"], 2),
            "lower": round(ind["lower_band"], 2),
            "ret5": round(ind["ret5"], 2),
            "foreign": inst.get("foreign", "N/A"),
            "trust": inst.get("trust", "N/A"),
            "dealer": inst.get("dealer", "N/A"),
            "surge_score": surge_score,
        })

        if (idx + 1) % 20 == 0:
            print(f"  已分析 {idx + 1}/100...")

    print(f"\n  分析完成，有效股票數：{len(results)}")

    # 排序取前 10
    df_result = pd.DataFrame(results).sort_values("surge_score", ascending=False).head(10).reset_index(drop=True)
    return df_result, results, market


def generate_report(df_top10: pd.DataFrame, all_results: list, market: dict = None) -> str:
    lines = []
    lines.append(f"# 台股前百大交易量 — 隔日暴漲潛力 TOP 10")
    lines.append(f"**分析基準日**：{TRADE_DATE_FMT}　｜　**預測目標日**：2026-04-11（下一交易日）")
    lines.append("")
    lines.append("> ⚠️ 本報告僅供參考，不構成投資建議，最終決策請自行判斷。")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 大盤趨勢預測區塊
    if market:
        twii = market.get("twii", {})
        us   = market.get("us_markets", {})
        etf  = market.get("etf_action", {})
        direction_zh = {
            "strong_bull": "強力多頭",
            "bull":        "偏多",
            "neutral":     "盤整觀望",
            "bear":        "偏空",
            "strong_bear": "強力空頭",
        }.get(market["direction"], "不明")
        score = market["score"]
        score_bar = "█" * (abs(score) // 10) + "░" * (10 - abs(score) // 10)
        score_sign = "+" if score >= 0 else ""

        lines.append("## 大盤趨勢預測")
        lines.append("")
        lines.append(f"| 項目 | 數值 |")
        lines.append(f"|------|------|")
        lines.append(f"| 大盤方向 | **{direction_zh}** |")
        lines.append(f"| 綜合評分 | `{score_sign}{score}` （{score_bar}）|")
        lines.append(f"| 隔日 5%+ 漲幅概率 | {market['next_day_5pct_prob']} |")
        lines.append(f"| 一週趨勢預測 | {market['weekly_trend']} |")
        lines.append("")

        if twii:
            lines.append("### 台股加權指數（TWII）")
            lines.append(f"- 最新收盤：**{twii.get('last', 'N/A')}**（當日 {twii.get('day_chg_pct', 0):+.2f}%）")
            lines.append(f"- MA5/MA20/MA60：{twii.get('ma5')} / {twii.get('ma20')} / {twii.get('ma60', 'N/A')}")
            lines.append(f"- RSI(14)：{twii.get('rsi')}　｜　MACD DIF/DEA：{twii.get('dif')} / {twii.get('dea')}")
            lines.append(f"- 布林通道位置：{twii.get('bb_pos', 0):.0%}（0%=下軌，100%=上軌）")
            lines.append(f"- 近5日漲幅：{twii.get('ret5', 0):+.2f}%　｜　近10日：{twii.get('ret10', 0):+.2f}%")
            lines.append(f"- 成交量比：{twii.get('vol_ratio', 0):.1f}x")
            lines.append("")

        if us:
            lines.append("### 美股三大指數（前收盤）")
            for name, d in us.items():
                if d.get("close"):
                    lines.append(f"- **{name}**：{d['close']:,}（{d['chg_pct']:+.2f}%）")
            lines.append("")

        lines.append("### 訊號清單")
        for sig in market.get("signals", []):
            icon = "🟢" if any(k in sig for k in ["多頭", "金叉", "強勢", "漲", "偏多", "超賣", "反彈"]) else "🔴"
            lines.append(f"- {icon} {sig}")
        lines.append("")

        lines.append("### ETF 操作建議")
        if etf.get("code"):
            lines.append(f"**建議：{etf['action']} [{etf['code']}] {etf['name']}**")
        else:
            lines.append(f"**建議：{etf['action']}**")
        lines.append(f"> {etf['reason']}")
        lines.append("")
        lines.append("---")
        lines.append("")

    # 個股分析樣本說明
    lines.append("## 大盤環境摘要")
    lines.append("- **分析樣本**：TWSE 全市場 1350 支個股，依成交量(張)取前 100 支個股進行篩選")
    lines.append("")
    lines.append("---")
    lines.append("")

    # TOP 10 表格
    lines.append("## TOP 10 暴漲潛力股一覽")
    lines.append("")
    lines.append("| 排名 | 代碼 | 收盤 | 當日漲幅 | 成交量(張) | 量比 | RSI | 評分 |")
    lines.append("|------|------|------|---------|-----------|------|-----|------|")

    for i, row in df_top10.iterrows():
        lines.append(
            f"| {i+1} | {row['code']} | {row['close']:.2f} | {row['change_pct']:+.2f}% "
            f"| {row['volume_lots']:,} | {row['vol_ratio']:.1f}x | {row['rsi']:.1f} | **{row['surge_score']}** |"
        )

    lines.append("")
    lines.append("---")
    lines.append("")

    # 個股詳細分析
    lines.append("## 個股詳細分析")
    lines.append("")

    reason_templates = {
        "vol_explosion": "爆量突破（量比 {vr:.1f}x），顯示主力積極介入，短線動能強烈。",
        "macd_golden": "MACD 剛形成金叉（DIF={dif:.3f} > DEA={dea:.3f}），買盤力道確認。",
        "rsi_rebound": "RSI({rsi:.1f}) 處於超賣後回彈區間，短線有強勁反彈動能。",
        "bb_lower": "股價接近布林通道下軌（下軌={lower:.2f}），技術面反彈訊號明確。",
        "ma_bullish": "均線多頭排列（MA5={ma5:.2f} > MA20={ma20:.2f}），趨勢向上。",
        "inst_buy": "三大法人同步買超（外資 {foreign:,}張 / 投信 {trust:,}張），籌碼集中。",
        "foreign_buy": "外資大舉買超 {foreign:,} 張，法人看好後市。",
        "trust_buy": "投信買超 {trust:,} 張，資金持續流入。",
        "moderate_gain": "當日溫和上漲 {chg:.2f}%，未過熱，隔日有機會繼續強攻。",
    }

    for i, row in df_top10.iterrows():
        lines.append(f"### {i+1}. 【{row['code']}】｜ 評分：{row['surge_score']} 分")
        lines.append("")
        lines.append("#### 前一日收盤")
        lines.append(f"- 收盤價：**{row['close']:.2f}** 元（漲跌 {row['change_pct']:+.2f}%）")
        lines.append(f"- 成交量：**{row['volume_lots']:,}** 張（較均量 {row['vol_ratio']:.1f}x）")
        lines.append("")
        lines.append("#### 技術面")

        ma_trend = "多頭排列" if row["ma5"] > row["ma20"] else "空頭排列"
        lines.append(f"- MA5/MA20：{row['ma5']:.2f} / {row['ma20']:.2f}（{ma_trend}）")
        lines.append(f"- RSI(14)：{row['rsi']:.1f}（{'超賣' if row['rsi'] < 30 else '超買' if row['rsi'] > 70 else '正常區間'}）")

        macd_signal = "金叉" if row["dif"] > row["dea"] else "死叉"
        lines.append(f"- MACD：DIF {row['dif']:.3f} / DEA {row['dea']:.3f}（{macd_signal}）")
        lines.append(f"- 布林通道：下軌 {row['lower']:.2f} ｜ 上軌 {row['upper']:.2f}")
        lines.append(f"- 近5日漲幅：{row['ret5']:+.2f}%")
        lines.append("")
        lines.append("#### 法人籌碼")

        if isinstance(row["foreign"], (int, float)):
            lines.append(f"- 外資：{int(row['foreign']):+,} 張")
            lines.append(f"- 投信：{int(row['trust']):+,} 張")
            lines.append(f"- 自營商：{int(row['dealer']):+,} 張")
        else:
            lines.append("- 法人資料暫不可用")

        lines.append("")
        lines.append("#### 暴漲理由分析")

        reasons = []

        # 爆量
        if row["vol_ratio"] >= 3.0:
            reasons.append(f"📈 **爆量突破**：量比高達 {row['vol_ratio']:.1f}x，主力積極進場，隔日延續強勢概率大。")
        elif row["vol_ratio"] >= 2.0:
            reasons.append(f"📊 **放量上攻**：量比 {row['vol_ratio']:.1f}x，成交量顯著放大，買盤動能充足。")

        # MACD
        if row["dif"] > row["dea"] and row["macd_bar"] > 0:
            reasons.append(f"✅ **MACD 多頭**：DIF({row['dif']:.3f}) > DEA({row['dea']:.3f})，動能向上確認。")

        # RSI
        if row["rsi"] < 35:
            reasons.append(f"🔄 **RSI 超賣反彈**：RSI={row['rsi']:.1f}，短線超賣後反彈空間大。")
        elif 35 <= row["rsi"] < 55:
            reasons.append(f"📐 **RSI 健康啟動區**：RSI={row['rsi']:.1f}，未過熱，適合追漲。")

        # 布林通道
        band_width = row["upper"] - row["lower"]
        if band_width > 0:
            pos = (row["close"] - row["lower"]) / band_width
            if pos < 0.25:
                reasons.append(f"📉 **布林下軌支撐**：股價貼近下軌（{row['lower']:.2f}），技術面反彈訊號強烈。")

        # 法人
        if isinstance(row["foreign"], (int, float)):
            f_val = int(row["foreign"])
            t_val = int(row["trust"])
            d_val = int(row["dealer"])
            if f_val > 0 and t_val > 0:
                reasons.append(f"🏦 **外資+投信同步買超**：外資 {f_val:,}張，投信 {t_val:,}張，籌碼面極佳。")
            elif f_val > 500:
                reasons.append(f"🌐 **外資大買**：外資淨買超 {f_val:,} 張，法人看多明顯。")
            elif t_val > 100:
                reasons.append(f"💼 **投信積極布局**：投信買超 {t_val:,} 張，短線拉抬意圖明顯。")

        # 當日漲幅
        if 1 < row["change_pct"] <= 5:
            reasons.append(f"🟢 **溫和上漲未過熱**：當日漲幅 {row['change_pct']:+.2f}%，尚有上攻空間。")

        if not reasons:
            reasons.append("綜合技術指標偏多，短線具備上漲動能。")

        for r in reasons:
            lines.append(f"{r}")

        lines.append("")

        # 操作建議
        score = row["surge_score"]
        if score >= 70:
            suggest = "**[強力買進]**"
            target = round(row["close"] * 1.07, 1)
            stop   = round(row["close"] * 0.95, 1)
        elif score >= 55:
            suggest = "**[買進]**"
            target = round(row["close"] * 1.05, 1)
            stop   = round(row["close"] * 0.96, 1)
        elif score >= 40:
            suggest = "**[小量布局]**"
            target = round(row["close"] * 1.04, 1)
            stop   = round(row["close"] * 0.97, 1)
        else:
            suggest = "**[觀望]**"
            target = None
            stop = None

        lines.append(f"#### 操作建議：{suggest}")
        if target:
            lines.append(f"- 短線目標價：**{target}** 元")
            lines.append(f"- 停損參考：**{stop}** 元（跌破停損出場）")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("## 分析方法說明")
    lines.append("")
    lines.append("| 評分維度 | 權重 | 主要指標 |")
    lines.append("|---------|------|---------|")
    lines.append("| 技術面 | 60分 | 均線排列、RSI、MACD金叉、布林通道、量比 |")
    lines.append("| 法人籌碼 | 30分 | 外資/投信/自營商買賣超，三方同向加分 |")
    lines.append("| 當日量能 | 20分 | 成交量(張)規模、當日漲幅是否溫和 |")
    lines.append("")
    lines.append(f"*本報告由 Stock_AI_agent 自動生成，資料來源：TWSE、Yahoo Finance*")
    lines.append(f"*生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

    return "\n".join(lines)


# ─────────────────────────────────────────
# Step 7: LINE 推播
# ─────────────────────────────────────────
LINE_CHANNEL_ID     = "2009776475"
LINE_CHANNEL_SECRET = "256e8e8c2dfc910a03bdf156cbe3f50d"
LINE_USER_ID        = "Uc4b6168aaeef9ffdf18e4ab0273ff9b9"


def get_line_token() -> str | None:
    resp = requests.post(
        "https://api.line.me/oauth2/v3/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "client_credentials",
            "client_id": LINE_CHANNEL_ID,
            "client_secret": LINE_CHANNEL_SECRET,
        },
        timeout=10,
    )
    if resp.status_code == 200:
        return resp.json()["access_token"]
    print(f"[LINE] Token 取得失敗：{resp.status_code} {resp.text}")
    return None


def build_market_line_message(market: dict) -> dict:
    """組合大盤趨勢預測 LINE 訊息"""
    twii = market.get("twii", {})
    us   = market.get("us_markets", {})
    etf  = market.get("etf_action", {})
    direction_zh = {
        "strong_bull": "強力多頭",
        "bull":        "偏多",
        "neutral":     "盤整觀望",
        "bear":        "偏空",
        "strong_bear": "強力空頭",
    }.get(market["direction"], "不明")

    score = market["score"]
    score_icon = "🚀" if score >= 50 else "📈" if score >= 20 else "⚖️" if score >= -20 else "📉" if score >= -50 else "🔻"

    us_lines = []
    for name, d in us.items():
        if d.get("chg_pct") is not None:
            arrow = "▲" if d["chg_pct"] >= 0 else "▼"
            us_lines.append(f"  {name}: {arrow}{abs(d['chg_pct']):.2f}%")

    signal_summary = []
    for sig in market.get("signals", [])[:4]:
        signal_summary.append(f"• {sig}")

    etf_line = ""
    if etf.get("code"):
        etf_line = f"\n\n💡 ETF 建議：{etf['action']} [{etf['code']}]\n{etf['reason']}"
    else:
        etf_line = f"\n\n💡 ETF 建議：{etf['action']}\n{etf['reason']}"

    twii_line = ""
    if twii:
        twii_line = (
            f"\n\n📊 TWII：{twii.get('last', 'N/A')}（{twii.get('day_chg_pct', 0):+.2f}%）"
            f"\nRSI={twii.get('rsi')}  DIF={twii.get('dif')}  量比={twii.get('vol_ratio')}x"
            f"\n近5日：{twii.get('ret5', 0):+.2f}%｜近10日：{twii.get('ret10', 0):+.2f}%"
        )

    text = (
        f"{score_icon} 大盤趨勢預測\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"方向：{direction_zh}（評分 {score:+d}）\n"
        f"隔日5%+概率：{market['next_day_5pct_prob'][:20]}\n"
        f"一週趨勢：{market['weekly_trend'][:30]}"
        f"{twii_line}\n\n"
        f"🌍 美股前收\n" + "\n".join(us_lines) +
        "\n\n主要訊號：\n" + "\n".join(signal_summary) +
        etf_line
    )

    return {"type": "text", "text": text}


def build_line_messages(df: pd.DataFrame, trade_date: str) -> list[dict]:
    """組合 LINE 推播訊息（3 則）"""

    # ── 訊息 1：TOP10 排行表 ──
    rows = []
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for i, row in df.iterrows():
        chg = f"{row['change_pct']:+.2f}%"
        rows.append(
            f"{medals[i]} {row['code']}  {row['close']:.1f}  {chg}  "
            f"{row['vol_ratio']:.1f}x  {row['rsi']:.0f}  {int(row['surge_score'])}"
        )

    msg1 = (
        f"📊 台股前百大交易量 — 隔日暴漲潛力 TOP 10\n"
        f"基準日：{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}｜預測：隔一交易日\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "   代碼　收盤　　漲幅　量比 RSI 評分\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        + "\n".join(rows) +
        "\n━━━━━━━━━━━━━━━━━━━━"
    )

    # ── 訊息 2：前5名重點分析 ──
    detail_lines = ["🔍 重點分析\n━━━━━━━━━━━━━━━━━━━━"]
    score_labels = {72: "強力買進", 70: "強力買進", 69: "買進", 68: "買進",
                    66: "買進", 65: "買進", 64: "買進/注意"}

    for i, row in df.head(5).iterrows():
        score = int(row["surge_score"])
        action = "強力買進" if score >= 70 else "買進" if score >= 55 else "觀望"
        target = round(row["close"] * (1.07 if score >= 70 else 1.05), 1)
        stop   = round(row["close"] * (0.95 if score >= 70 else 0.96), 1)

        # 主要理由
        reasons = []
        if row["vol_ratio"] >= 3.0:
            reasons.append(f"爆量{row['vol_ratio']:.1f}x")
        elif row["vol_ratio"] >= 2.0:
            reasons.append(f"放量{row['vol_ratio']:.1f}x")
        if row["dif"] > row["dea"]:
            reasons.append("MACD金叉")
        if isinstance(row["foreign"], (int, float)) and row["foreign"] > 0 and isinstance(row["trust"], (int, float)) and row["trust"] > 0:
            reasons.append("三法人買超")
        elif isinstance(row["foreign"], (int, float)) and row["foreign"] > 500:
            reasons.append(f"外資+{int(row['foreign'])//1000}千張")
        if row["rsi"] < 35:
            reasons.append(f"RSI超賣({row['rsi']:.0f})")

        reason_str = "、".join(reasons) if reasons else "技術偏多"
        detail_lines.append(
            f"\n【{row['code']}】{score}分｜{action}\n"
            f"{reason_str}\n"
            f"目標：{target}｜停損：{stop}"
        )

    msg2 = "\n".join(detail_lines)

    # ── 訊息 3：評分說明 + 免責 ──
    msg3 = (
        "📐 評分模型\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "技術面(60)：均線/RSI/MACD/布林/量比\n"
        "法人籌碼(30)：外資/投信/自營商買超\n"
        "當日量能(20)：成交量規模＋漲幅溫和度\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ 本報告僅供參考，不構成投資建議\n"
        "最終決策請自行判斷\n"
        f"📁 完整報告：surge_report_{trade_date}.md"
    )

    return [
        {"type": "text", "text": msg1},
        {"type": "text", "text": msg2},
        {"type": "text", "text": msg3},
    ]


def send_line_messages(messages: list[dict]) -> bool:
    token = get_line_token()
    if not token:
        return False

    payload = {"to": LINE_USER_ID, "messages": messages}
    resp = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        timeout=10,
    )
    if resp.status_code == 200:
        print("✓ LINE 推播成功")
        return True
    print(f"[LINE] 推播失敗：{resp.status_code} {resp.text}")
    return False


# ─────────────────────────────────────────
# 主程式入口
# ─────────────────────────────────────────
if __name__ == "__main__":
    import argparse, json

    parser = argparse.ArgumentParser(description="台股前百大交易量暴漲潛力分析")
    parser.add_argument("--date", default=TRADE_DATE, help="分析日期 YYYYMMDD（預設最近交易日）")
    parser.add_argument("--no-line", action="store_true", help="跳過 LINE 推播")
    args = parser.parse_args()

    df_top10, all_results, market = main()

    print("\n" + "="*60)
    print(" TOP 10 暴漲潛力股（評分排名）")
    print("="*60)
    print(df_top10[["code", "close", "change_pct", "volume_lots",
                     "vol_ratio", "rsi", "surge_score"]].to_string(index=False))

    # 儲存 Markdown 報告
    report_md = generate_report(df_top10, all_results, market)
    report_dir = "C:/Users/BaoGo/Documents/ClaudeCode/Stock_AI_agent"
    output_path = f"{report_dir}/surge_report_{TRADE_DATE}.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"\n✓ 報告已儲存：{output_path}")

    # LINE 推播
    if not args.no_line:
        print("\n► 發送 LINE 推播...")
        market_msg = build_market_line_message(market)
        stock_msgs = build_line_messages(df_top10, TRADE_DATE)
        # 大盤預測放第一則，接著個股排行與分析
        send_line_messages([market_msg] + stock_msgs)

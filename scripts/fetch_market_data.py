"""
AI MESH — NASDAQ 100 시장 데이터 수집 (Massive API)
GitHub Actions에서 주기적으로 실행하여 data/ 에 JSON 저장

엔드포인트:
  - 프로필: GET /v3/reference/tickers/{ticker}
  - 스냅샷: GET /v2/snapshot/locale/us/markets/stocks/tickers/{ticker}
  - 번역: MyMemory API (description → descriptionKr)
"""

import os
import json
import time
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone, timedelta

API_KEY = os.environ.get("MASSIVE_API_KEY", "")
API_BASE = "https://api.massive.com"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# NASDAQ 100 — 100 companies (exact match with nasdaq100.html)
TICKERS = [
    "NVDA","AVGO","ASML","AMD","QCOM","TXN","ARM","AMAT","INTC","ADI",
    "MU","LRCX","KLAC","MRVL","NXPI","MCHP","MPWR","STX","WDC","AAPL",
    "MSFT","AMZN","GOOGL","META","TSLA","NFLX","CSCO","PLTR","CDNS","SNPS",
    "ADBE","INTU","ADP","WDAY","DDOG","VRSK","CTSH","CSGP","PAYX","MSTR",
    "PANW","CRWD","FTNT","ZS","TEAM","ADSK","SHOP","ROP","TRI","BKNG",
    "MELI","APP","ABNB","PYPL","DASH","EA","TTWO","PDD","WBD","MAR",
    "ROST","WMT","CHTR","CMCSA","COST","PEP","TMUS","SBUX","MDLZ","MNST",
    "KHC","KDP","CCEP","CEG","XEL","AEP","EXC","ISRG","AMGN","VRTX",
    "GILD","REGN","GEHC","DXCM","IDXX","ALNY","INSM","LIN","HON","AXON",
    "CSX","CPRT","ODFL","FAST","FANG","BKR","FER","PCAR","ORLY","CTAS",
]


def fetch_json(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "AI-MESH/1.0",
        "Authorization": f"Bearer {API_KEY}",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode()[:200]
        except:
            pass
        print(f"    HTTP {e.code}: {body[:100]}")
        return None
    except Exception as e:
        print(f"    Error: {e}")
        return None


def translate_text(text):
    """MyMemory API로 영→한 번역 (500자 제한이라 청크 분할)"""
    if not text:
        return ""
    chunks = []
    for i in range(0, len(text), 400):
        chunks.append(text[i:i+400])

    results = []
    for chunk in chunks:
        url = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(chunk)}&langpair=en|ko"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AI-MESH/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
                translated = data.get("responseData", {}).get("translatedText", "")
                if translated and "MYMEMORY WARNING" not in translated:
                    results.append(translated)
                else:
                    results.append(chunk)
        except:
            results.append(chunk)
        if len(chunks) > 1:
            time.sleep(1)

    return "".join(results)


def fetch_profiles_and_snapshots():
    """프로필 + 스냅샷을 한 번에 수집 (API 호출 효율화)"""
    print(f"\n[1/2] 기업 프로필 + 시세 수집 중... ({len(TICKERS)}개)")
    all_data = {}
    fail_count = 0

    for i, ticker in enumerate(TICKERS):
        # 프로필
        url = f"{API_BASE}/v3/reference/tickers/{ticker}?apiKey={API_KEY}"
        data = fetch_json(url)

        profile = {}
        if data and data.get("status") == "OK" and data.get("results"):
            r = data["results"]
            profile = {
                "symbol": ticker,
                "companyName": r.get("name", ""),
                "description": r.get("description", ""),
                "industry": r.get("sic_description", ""),
                "sector": r.get("sector", ""),
                "country": r.get("locale", "us"),
                "exchange": r.get("primary_exchange", ""),
                "website": r.get("homepage_url", ""),
                "fullTimeEmployees": r.get("total_employees", ""),
                "ipoDate": r.get("list_date", ""),
                "image": (r.get("branding", {}) or {}).get("icon_url", ""),
                "mktCap": r.get("market_cap", 0),
            }
        else:
            fail_count += 1
            profile = {"symbol": ticker}
            if fail_count <= 5:
                print(f"  ✗ {ticker} 프로필 실패")

        time.sleep(12.5)  # 5 calls/min

        # 스냅샷
        url2 = f"{API_BASE}/v2/snapshot/locale/us/markets/stocks/tickers/{ticker}?apiKey={API_KEY}"
        snap = fetch_json(url2)

        if snap and snap.get("status") == "OK" and snap.get("ticker"):
            t = snap["ticker"]
            day = t.get("day", {}) or {}
            prev = t.get("prevDay", {}) or {}

            close = day.get("c") or prev.get("c") or 0
            prev_close = prev.get("c") or 0
            change = round(close - prev_close, 2) if close and prev_close else 0
            pct = round((change / prev_close) * 100, 2) if prev_close else 0

            profile.update({
                "price": close,
                "change": change,
                "changesPercentage": pct,
                "volume": day.get("v") or prev.get("v") or 0,
                "marketCap": t.get("market_cap", 0) or profile.get("mktCap", 0),
            })

        time.sleep(12.5)

        all_data[ticker] = profile

        if (i + 1) % 10 == 0:
            print(f"  ✓ {i+1}/{len(TICKERS)} 완료")

    print(f"  총 {len(all_data)}개 수집 완료 (실패: {fail_count}개)")
    return all_data


def translate_descriptions(all_data):
    """기업 개요 한국어 번역"""
    print(f"\n[2/2] 기업 개요 번역 중...")

    # 기존 번역 로드 (이미 번역된 건 스킵)
    profiles_path = os.path.join(DATA_DIR, "profiles.json")
    existing_translations = {}
    if os.path.exists(profiles_path):
        try:
            with open(profiles_path, "r", encoding="utf-8") as f:
                old = json.load(f)
            for sym, d in old.get("data", {}).items():
                if d.get("descriptionKr"):
                    existing_translations[sym] = d["descriptionKr"]
        except:
            pass

    translated_count = 0
    skipped_count = 0

    for i, (ticker, d) in enumerate(all_data.items()):
        desc = d.get("description", "")
        if not desc:
            continue

        # 기존 번역이 있으면 재사용
        if ticker in existing_translations:
            d["descriptionKr"] = existing_translations[ticker]
            skipped_count += 1
            continue

        kr = translate_text(desc)
        d["descriptionKr"] = kr
        translated_count += 1

        if (i + 1) % 10 == 0:
            print(f"  ✓ {translated_count}개 번역 완료")

        time.sleep(0.5)

    print(f"  번역 완료: {translated_count}개 새로, {skipped_count}개 재사용")
    return all_data


def save_json(data, filename):
    os.makedirs(DATA_DIR, exist_ok=True)
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    size_kb = os.path.getsize(filepath) / 1024
    print(f"  → {filename} 저장 ({size_kb:.1f} KB)")


def main():
    if not API_KEY:
        print("ERROR: MASSIVE_API_KEY 환경변수가 설정되지 않았습니다.")
        exit(1)

    print(f"API Key: {API_KEY[:4]}...{API_KEY[-4:]} (길이: {len(API_KEY)})")

    kst = timezone(timedelta(hours=9))
    now_kst = datetime.now(kst).strftime("%Y-%m-%d %H:%M KST")
    print(f"=== AI MESH NASDAQ 100 시장 데이터 수집 ({now_kst}) ===")

    # 1. 프로필 + 시세 수집
    all_data = fetch_profiles_and_snapshots()

    # 2. 번역
    all_data = translate_descriptions(all_data)

    if all_data:
        # profiles.json
        save_json({
            "updated_kst": now_kst,
            "count": len(all_data),
            "data": all_data,
        }, "profiles.json")

        # quotes.json (클라이언트 호환용)
        quotes = {}
        for sym, d in all_data.items():
            quotes[sym] = {
                "symbol": sym,
                "price": d.get("price"),
                "change": d.get("change"),
                "changesPercentage": d.get("changesPercentage"),
                "marketCap": d.get("marketCap") or d.get("mktCap", 0),
            }
        save_json({
            "updated_kst": now_kst,
            "count": len(quotes),
            "data": quotes,
        }, "quotes.json")

    print(f"\n=== 완료! {len(all_data)}개 기업 데이터 수집 ===")


if __name__ == "__main__":
    main()

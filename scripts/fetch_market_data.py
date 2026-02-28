"""
AI MESH — FMP 시장 데이터 수집 스크립트
GitHub Actions에서 주기적으로 실행하여 data/ 폴더에 JSON 저장

사용법:
  python scripts/fetch_market_data.py

환경변수:
  FMP_API_KEY — Financial Modeling Prep API 키 (GitHub Secrets에서 주입)
"""

import os
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

FMP_KEY = os.environ.get("FMP_API_KEY", "")
FMP_STABLE = "https://financialmodelingprep.com/stable"
FMP_V3 = "https://financialmodelingprep.com/api/v3"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# NASDAQ 100 티커 목록 (AI MESH에서 사용하는 전체 목록)
TICKERS = [
    "NVDA","AVGO","ASML","AMD","QCOM","TXN","ARM","AMAT","INTC","ADI",
    "MU","LRCX","KLAC","MRVL","NXPI","MCHP","MPWR","STX","WDC",
    "AAPL","MSFT","AMZN","GOOGL","META","TSLA","NFLX",
    "CSCO","PLTR","CDNS","SNPS","ADBE","INTU","ADP","WDAY",
    "DDOG","VRSK","CTSH","CSGP","PAYX","MSTR","PANW","CRWD",
    "FTNT","ZS","TEAM","ADSK","SHOP","ROP","TRI",
    "BKNG","MELI","APP","ABNB","PYPL","DASH","EA","TTWO",
    "PDD","WBD","MAR","ROST","WMT",
    "CHTR","CMCSA","COST","PEP","TMUS","SBUX","MDLZ","MNST",
    "KHC","KDP","CCEP","CEG","XEL","AEP","EXC",
    "ISRG","AMGN","VRTX","GILD","REGN","GEHC","DXCM","IDXX","ALNY","INSM","LIN",
    "HON","AXON","CSX","CPRT","ODFL","FAST","FANG","BKR","FER","PCAR","ORLY","CTAS",
]


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "AI-MESH/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode()[:200]
        except:
            pass
        print(f"  HTTP Error {e.code}: {url[:80]}...")
        print(f"  Response: {body}")
        return None
    except Exception as e:
        print(f"  Error: {e}")
        return None


def fetch_profiles():
    """FMP Stable API에서 기업 프로필 수집 (50개씩 배치)"""
    print("\n[1/2] 기업 프로필 수집 중...")
    all_profiles = {}

    for i in range(0, len(TICKERS), 50):
        batch = TICKERS[i:i+50]
        symbols = ",".join(batch)
        url = f"{FMP_STABLE}/profile?symbol={symbols}&apikey={FMP_KEY}"
        print(f"  배치 {i//50 + 1}: {len(batch)}개 요청...")

        data = fetch_json(url)
        if data and isinstance(data, list):
            for p in data:
                sym = p.get("symbol")
                if sym:
                    all_profiles[sym] = {
                        "symbol": sym,
                        "companyName": p.get("companyName", ""),
                        "description": p.get("description", ""),
                        "ceo": p.get("ceo", ""),
                        "industry": p.get("industry", ""),
                        "sector": p.get("sector", ""),
                        "country": p.get("country", ""),
                        "exchange": p.get("exchange", ""),
                        "website": p.get("website", ""),
                        "fullTimeEmployees": p.get("fullTimeEmployees", ""),
                        "ipoDate": p.get("ipoDate", ""),
                        "image": p.get("image", ""),
                        "mktCap": p.get("mktCap", 0),
                    }
            print(f"  ✓ {len(data)}개 프로필 수신")
        else:
            print(f"  ✗ 배치 실패")

        if i + 50 < len(TICKERS):
            time.sleep(0.5)

    print(f"  총 {len(all_profiles)}개 프로필 수집 완료")
    return all_profiles


def fetch_quotes():
    """FMP V3 API에서 실시간 시세 수집 (50개씩 배치)"""
    print("\n[2/2] 실시간 시세 수집 중...")
    all_quotes = {}

    for i in range(0, len(TICKERS), 50):
        batch = TICKERS[i:i+50]
        symbols = ",".join(batch)
        url = f"{FMP_V3}/quote/{symbols}?apikey={FMP_KEY}"
        print(f"  배치 {i//50 + 1}: {len(batch)}개 요청...")

        data = fetch_json(url)
        if data and isinstance(data, list):
            for q in data:
                sym = q.get("symbol")
                if sym:
                    all_quotes[sym] = {
                        "symbol": sym,
                        "price": q.get("price"),
                        "change": q.get("change"),
                        "changesPercentage": q.get("changesPercentage"),
                        "marketCap": q.get("marketCap"),
                        "volume": q.get("volume"),
                        "avgVolume": q.get("avgVolume"),
                        "dayHigh": q.get("dayHigh"),
                        "dayLow": q.get("dayLow"),
                        "yearHigh": q.get("yearHigh"),
                        "yearLow": q.get("yearLow"),
                        "open": q.get("open"),
                        "previousClose": q.get("previousClose"),
                    }
            print(f"  ✓ {len(data)}개 시세 수신")
        else:
            print(f"  ✗ 배치 실패")

        if i + 50 < len(TICKERS):
            time.sleep(0.5)

    print(f"  총 {len(all_quotes)}개 시세 수집 완료")
    return all_quotes


def save_json(data, filename):
    """JSON 파일 저장"""
    os.makedirs(DATA_DIR, exist_ok=True)
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    size_kb = os.path.getsize(filepath) / 1024
    print(f"  → {filename} 저장 ({size_kb:.1f} KB)")


def main():
    if not FMP_KEY:
        print("ERROR: FMP_API_KEY 환경변수가 설정되지 않았습니다.")
        exit(1)
    
    # 디버그: 키 앞 4자리만 표시
    print(f"API Key: {FMP_KEY[:4]}...{FMP_KEY[-4:]} (길이: {len(FMP_KEY)})")

    kst = timezone(timedelta(hours=9))
    now_kst = datetime.now(kst).strftime("%Y-%m-%d %H:%M KST")
    print(f"=== AI MESH 시장 데이터 수집 시작 ({now_kst}) ===")

    # 프로필 수집 & 저장
    profiles = fetch_profiles()
    if profiles:
        profiles_out = {
            "updated_kst": now_kst,
            "count": len(profiles),
            "data": profiles,
        }
        save_json(profiles_out, "profiles.json")

    # 시세 수집 & 저장
    quotes = fetch_quotes()
    if quotes:
        quotes_out = {
            "updated_kst": now_kst,
            "count": len(quotes),
            "data": quotes,
        }
        save_json(quotes_out, "quotes.json")

    print(f"\n=== 완료! 프로필 {len(profiles)}개, 시세 {len(quotes)}개 ===")


if __name__ == "__main__":
    main()

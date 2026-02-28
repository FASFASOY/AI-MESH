"""
AI MESH — FMP 시장 데이터 수집 스크립트
GitHub Actions에서 주기적으로 실행하여 data/ 폴더에 JSON 저장
"""

import os
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

FMP_KEY = os.environ.get("FMP_API_KEY", "")
FMP_STABLE = "https://financialmodelingprep.com/stable"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

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
        print(f"    HTTP {e.code}: {body[:100]}")
        return None
    except Exception as e:
        print(f"    Error: {e}")
        return None


def fetch_profiles():
    """FMP Stable API에서 기업 프로필 수집 (1개씩) — 시총, 가격 포함"""
    print("\n[1/1] 기업 프로필+시세 수집 중...")
    all_data = {}
    fail_count = 0

    for i, ticker in enumerate(TICKERS):
        url = f"{FMP_STABLE}/profile?symbol={ticker}&apikey={FMP_KEY}"
        data = fetch_json(url)

        if data and isinstance(data, list) and len(data) > 0:
            p = data[0]
            sym = p.get("symbol", ticker)
            all_data[sym] = {
                # 프로필 정보
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
                # 시세 정보 (프로필 API에 포함됨)
                "mktCap": p.get("mktCap", 0),
                "price": p.get("price", None),
                "changes": p.get("changes", None),
                "beta": p.get("beta", None),
                "volAvg": p.get("volAvg", None),
                "lastDiv": p.get("lastDiv", None),
                "range": p.get("range", ""),
            }
            if (i + 1) % 10 == 0:
                print(f"  ✓ {i+1}/{len(TICKERS)} 완료")
        else:
            fail_count += 1
            print(f"  ✗ {ticker} 실패")

        time.sleep(0.25)

    print(f"  총 {len(all_data)}개 수집 완료 (실패: {fail_count}개)")
    return all_data


def save_json(data, filename):
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

    print(f"API Key: {FMP_KEY[:4]}...{FMP_KEY[-4:]} (길이: {len(FMP_KEY)})")

    kst = timezone(timedelta(hours=9))
    now_kst = datetime.now(kst).strftime("%Y-%m-%d %H:%M KST")
    print(f"=== AI MESH 시장 데이터 수집 시작 ({now_kst}) ===")

    all_data = fetch_profiles()

    if all_data:
        # profiles.json — 전체 데이터 (프로필 + 시세)
        save_json({
            "updated_kst": now_kst,
            "count": len(all_data),
            "data": all_data,
        }, "profiles.json")

        # quotes.json — 시세 부분만 추출 (클라이언트 호환용)
        quotes = {}
        for sym, d in all_data.items():
            quotes[sym] = {
                "symbol": sym,
                "price": d.get("price"),
                "change": d.get("changes"),
                "changesPercentage": round(d["changes"] / (d["price"] - d["changes"]) * 100, 2) if d.get("price") and d.get("changes") and (d["price"] - d["changes"]) != 0 else None,
                "marketCap": d.get("mktCap"),
            }
        save_json({
            "updated_kst": now_kst,
            "count": len(quotes),
            "data": quotes,
        }, "quotes.json")

    print(f"\n=== 완료! {len(all_data)}개 기업 데이터 수집 ===")


if __name__ == "__main__":
    main()

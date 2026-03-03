"""
AI MESH — S&P 500 시장 데이터 수집 (Massive API)
GitHub Actions에서 주기적으로 실행하여 data/sp500/ 에 JSON 저장

엔드포인트:
  - 프로필: GET /v3/reference/tickers/{ticker}
  - 스냅샷: GET /v2/snapshot/locale/us/markets/stocks/tickers/{ticker}
"""

import os
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

API_KEY = os.environ.get("MASSIVE_API_KEY", "")
API_BASE = "https://api.massive.com"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "sp500")

# S&P 500 — 500 companies (exact match with index.html)
TICKERS = [
    "NVDA","AAPL","MSFT","AVGO","ORCL","CSCO","PLTR","INTC","TXN","AMD",
    "KLAC","AMAT","LRCX","MU","ADI","APH","CRM","ANET","IBM","ACN",
    "INTU","NOW","ADBE","CRWD","PANW","GLW","SNPS","CDNS","QCOM","APP",
    "FTNT","NXPI","MPWR","MCHP","DELL","MSI","TEL","STX","WDC","SNDK",
    "KEYS","ADSK","DDOG","WDAY","HPE","TER","ROP","CTSH","FICO","FISV",
    "HPQ","JBL","TDY","CDW","BR","FSLR","VRSN","NTAP","SMCI","PTC",
    "FFIV","TYL","AKAM","GEN","ZBRA","IT","GDDY","ON","Q","CIEN",
    "EPAM","SWKS","PAYC","BRK.B","JPM","V","MA","BAC","GS","WFC",
    "MS","C","AXP","SCHW","BLK","PNC","USB","COF","BX","CME",
    "SPGI","MCO","ICE","CB","PGR","APO","TFC","AJG","AFL","ALL",
    "MET","TRV","KKR","BK","HOOD","NDAQ","STT","HBAN","FITB","MTB",
    "RJF","ACGL","HIG","AIG","AMP","COIN","PRU","MSCI","WRB","IBKR",
    "CBOE","NTRS","WTW","AON","MRSH","FIS","SYF","CFG","CINF","KEY",
    "RF","CPAY","L","BRO","PYPL","EBAY","GPN","PFG","TROW","BEN",
    "ERIE","EG","AIZ","JKHY","GL","IVZ","FDS","ARES","XYZ","GOOGL",
    "META","NFLX","TMUS","DIS","CMCSA","VZ","T","CHTR","WBD","EA",
    "TTWO","LYV","OMC","TKO","TTD","FOX","PSKY","NWS","MTCH","DASH",
    "AMZN","TSLA","BKNG","HD","LOW","TJX","MCD","NKE","SBUX","MAR",
    "HLT","RCL","ABNB","GM","F","CMG","ROST","ORLY","AZO","YUM",
    "DHI","CVNA","CCL","LVS","DRI","GRMN","ULTA","EXPE","PHM","LEN",
    "TSCO","NVR","GPC","BBY","DPZ","NCLH","WYNN","MGM","DECK","APTV",
    "POOL","RL","LULU","WSM","HAS","TPR","SWK","LLY","UNH","JNJ",
    "MRK","ABBV","TMO","PFE","ABT","AMGN","DHR","GILD","ISRG","SYK",
    "VRTX","REGN","MDT","BMY","BSX","ELV","HCA","MCK","CI","CVS",
    "GEHC","IDXX","DXCM","A","IQV","RMD","ZTS","EW","COR","CAH",
    "BDX","LH","DGX","STE","CNC","HUM","BIIB","MRNA","INCY","ZBH",
    "MTD","WAT","WST","PODD","HOLX","COO","BAX","DVA","HSIC","VTRS",
    "CRL","MOH","TECH","RVTY","SOLV","UHS","ALGN","GE","CAT","RTX",
    "HON","UPS","DE","LMT","BA","GEV","ETN","PH","NOC","GD",
    "FDX","ITW","WM","EMR","CMI","CTAS","HWM","TT","CSX","UNP",
    "NSC","UBER","LHX","JCI","CRH","ADP","TDG","PCAR","AXON","RSG",
    "PWR","MMM","FAST","CPRT","ODFL","AME","DAL","WAB","IR","OTIS",
    "CARR","ROK","URI","GWW","DOV","VRSK","PAYX","EME","FIX","JBHT",
    "LDOS","UAL","LUV","TXT","HII","SNA","EXPD","ROL","EFX","VLTO",
    "CHRW","XYL","J","NDSN","PNR","IEX","LII","FTV","HUBB","MAS",
    "ALLE","AOS","GNRC","BLDR","TRMB","WMT","COST","PG","KO","PEP",
    "PM","CL","MDLZ","MNST","MO","KMB","KVUE","KDP","ADM","SYY",
    "TGT","KR","HSY","GIS","STZ","CHD","KHC","DLTR","DG","CLX",
    "EL","HRL","BG","TSN","SJM","MKC","TAP","BF.B","CAG","CPB",
    "LW","XOM","TPL","CVX","COP","SLB","EOG","WMB","PSX","KMI",
    "VLO","MPC","OKE","BKR","FANG","OXY","TRGP","HAL","DVN","CTRA",
    "EQT","EXE","APA","NEE","SO","DUK","CEG","AEP","EXC","XEL",
    "SRE","D","VST","PCG","PEG","ED","ETR","WEC","NRG","DTE",
    "ES","FE","PPL","EIX","CNP","CMS","AWK","AEE","ATO","LNT",
    "NI","PNW","AES","EVRG","LIN","NEM","FCX","SHW","APD","ECL",
    "NUE","VMC","MLM","CTVA","DOW","PPG","DD","STLD","CF","ALB",
    "IFF","LYB","BALL","AVY","PKG","SW","IP","AMCR","MOS","WELL",
    "DOC","PLD","EQIX","AMT","SPG","DLR","PSA","O","CCI","EQR",
    "VTR","CBRE","AVB","EXR","IRM","VICI","SBAC","WY","KIM","MAA",
    "INVH","CSGP","ESS","REG","CPT","UDR","HST","FRT","BXP","ARE",
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


def fetch_profiles():
    """Massive API v3 ticker details — 프로필 수집"""
    print("\n[1/2] 기업 프로필 수집 중...")
    all_data = {}
    fail_count = 0

    for i, ticker in enumerate(TICKERS):
        url = f"{API_BASE}/v3/reference/tickers/{ticker}?apiKey={API_KEY}"
        data = fetch_json(url)

        if data and data.get("status") == "OK" and data.get("results"):
            r = data["results"]
            all_data[ticker] = {
                "symbol": ticker,
                "companyName": r.get("name", ""),
                "description": r.get("description", ""),
                "ceo": "",  # v3에선 별도 제공 안 함
                "industry": r.get("sic_description", ""),
                "sector": "",  # branding에서 별도 매핑
                "country": r.get("locale", "us"),
                "exchange": r.get("primary_exchange", ""),
                "website": r.get("homepage_url", ""),
                "fullTimeEmployees": r.get("total_employees", ""),
                "ipoDate": r.get("list_date", ""),
                "image": (r.get("branding", {}) or {}).get("icon_url", ""),
                "mktCap": r.get("market_cap", 0),
            }
            if (i + 1) % 10 == 0:
                print(f"  ✓ {i+1}/{len(TICKERS)} 완료")
        else:
            fail_count += 1
            if (i + 1) % 50 == 0 or fail_count <= 5:
                print(f"  ✗ {ticker} 실패")

        # Free tier: 5 calls/min = 12초/call
        time.sleep(12.5)

    print(f"  총 {len(all_data)}개 프로필 수집 완료 (실패: {fail_count}개)")
    return all_data


def fetch_snapshots(all_data):
    """Massive API v2 snapshot — 시세 수집"""
    print("\n[2/2] 시세 스냅샷 수집 중...")
    success = 0
    fail = 0

    for i, ticker in enumerate(TICKERS):
        url = f"{API_BASE}/v2/snapshot/locale/us/markets/stocks/tickers/{ticker}?apiKey={API_KEY}"
        data = fetch_json(url)

        if data and data.get("status") == "OK" and data.get("ticker"):
            t = data["ticker"]
            day = t.get("day", {}) or {}
            prev = t.get("prevDay", {}) or {}

            close = day.get("c") or prev.get("c") or 0
            prev_close = prev.get("c") or 0
            change = round(close - prev_close, 2) if close and prev_close else 0
            pct = round((change / prev_close) * 100, 2) if prev_close else 0

            snap = {
                "price": close,
                "change": change,
                "changesPercentage": pct,
                "volume": day.get("v") or prev.get("v") or 0,
                "marketCap": t.get("market_cap", 0) if "market_cap" in t else (all_data.get(ticker, {}).get("mktCap", 0)),
            }

            if ticker in all_data:
                all_data[ticker].update(snap)
            else:
                all_data[ticker] = {"symbol": ticker, **snap}
            success += 1
        else:
            fail += 1

        if (i + 1) % 10 == 0:
            print(f"  ✓ {i+1}/{len(TICKERS)} 완료")

        time.sleep(12.5)

    print(f"  스냅샷 수집: {success}개 성공, {fail}개 실패")
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
    print(f"=== AI MESH S&P 500 시장 데이터 수집 시작 ({now_kst}) ===")
    print(f"    총 {len(TICKERS)}개 종목")

    # 1. 프로필 수집
    all_data = fetch_profiles()

    # 2. 스냅샷(시세) 수집
    all_data = fetch_snapshots(all_data)

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
                "marketCap": d.get("mktCap") or d.get("marketCap", 0),
            }
        save_json({
            "updated_kst": now_kst,
            "count": len(quotes),
            "data": quotes,
        }, "quotes.json")

    print(f"\n=== 완료! {len(all_data)}개 기업 데이터 수집 ===")


if __name__ == "__main__":
    main()

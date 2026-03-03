"""
AI MESH — S&P 500 로고 이미지 다운로드 스크립트
Brandfetch CDN에서 각 티커의 로고를 다운로드하여 data/sp500/logos/에 저장
사용법:
  python scripts/fetch_sp500_logos.py
참고:
  - 1회성 실행 (로고는 자주 바뀌지 않음)
  - 실패한 티커는 텍스트 폴백으로 처리됨
"""
import os
import time
import urllib.request
import urllib.error

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sp500", "logos")

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

LOGO_URL = "https://cdn.brandfetch.io/ticker/{ticker}/w/400/h/400?c=1idPsssS9J0WktYMOvD"

def download_logo(ticker):
    """단일 로고 다운로드"""
    url = LOGO_URL.format(ticker=ticker)
    filepath = os.path.join(DATA_DIR, f"{ticker}.png")
    
    if os.path.exists(filepath) and os.path.getsize(filepath) > 500:
        return "skip"
    
    req = urllib.request.Request(url, headers={
        "User-Agent": "AI-MESH/1.0",
        "Accept": "image/*",
    })
    
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            if len(data) < 500:
                return "invalid"
            with open(filepath, "wb") as f:
                f.write(data)
            return "ok"
    except urllib.error.HTTPError as e:
        return f"http_{e.code}"
    except Exception as e:
        return "error"

def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    unique_tickers = list(dict.fromkeys(TICKERS))
    print(f"=== AI MESH S&P 500 로고 다운로드 ({len(unique_tickers)}개) ===\n")
    
    results = {"ok": [], "skip": [], "fail": []}
    
    for i, ticker in enumerate(unique_tickers):
        status = download_logo(ticker)
        if status == "ok":
            results["ok"].append(ticker)
            icon = "✓"
        elif status == "skip":
            results["skip"].append(ticker)
            icon = "—"
        else:
            results["fail"].append(ticker)
            icon = "✗"
        
        print(f"  {icon} [{i+1:3d}/{len(unique_tickers)}] {ticker:6s} → {status}")
        if status != "skip":
            time.sleep(0.3)
    
    print(f"\n=== 결과 ===")
    print(f"  새로 다운로드: {len(results['ok'])}개")
    print(f"  이미 존재 (스킵): {len(results['skip'])}개")
    print(f"  실패: {len(results['fail'])}개")
    if results["fail"]:
        print(f"  실패 목록: {', '.join(results['fail'])}")

if __name__ == "__main__":
    main()

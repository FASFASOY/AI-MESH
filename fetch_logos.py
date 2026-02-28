"""
AI MESH — 로고 이미지 다운로드 스크립트
Brandfetch CDN에서 각 티커의 로고를 다운로드하여 data/logos/에 저장

사용법:
  python scripts/fetch_logos.py

참고:
  - 1회성 실행 (로고는 자주 바뀌지 않음)
  - 실패한 티커는 텍스트 폴백으로 처리됨
"""

import os
import time
import urllib.request
import urllib.error

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "logos")

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

LOGO_URL = "https://cdn.brandfetch.io/ticker/{ticker}/w/400/h/400?c=1idPsssS9J0WktYMOvD"


def download_logo(ticker):
    """단일 로고 다운로드"""
    url = LOGO_URL.format(ticker=ticker)
    filepath = os.path.join(DATA_DIR, f"{ticker}.png")

    # 이미 존재하면 스킵
    if os.path.exists(filepath) and os.path.getsize(filepath) > 500:
        return "skip"

    req = urllib.request.Request(url, headers={
        "User-Agent": "AI-MESH/1.0",
        "Accept": "image/*",
    })

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            if len(data) < 500:  # 너무 작으면 유효하지 않은 이미지
                return "invalid"
            with open(filepath, "wb") as f:
                f.write(data)
            return "ok"
    except urllib.error.HTTPError as e:
        return f"http_{e.code}"
    except Exception as e:
        return f"error"


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"=== AI MESH 로고 다운로드 ({len(TICKERS)}개) ===\n")

    results = {"ok": [], "skip": [], "fail": []}

    for i, ticker in enumerate(TICKERS):
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

        print(f"  {icon} [{i+1:3d}/{len(TICKERS)}] {ticker:6s} → {status}")

        # Rate limiting
        if status != "skip":
            time.sleep(0.3)

    print(f"\n=== 결과 ===")
    print(f"  새로 다운로드: {len(results['ok'])}개")
    print(f"  이미 존재 (스킵): {len(results['skip'])}개")
    print(f"  실패: {len(results['fail'])}개")
    if results["fail"]:
        print(f"  실패 목록: {', '.join(results['fail'])}")
        print(f"  (실패한 티커는 클라이언트에서 텍스트 폴백으로 표시됩니다)")


if __name__ == "__main__":
    main()

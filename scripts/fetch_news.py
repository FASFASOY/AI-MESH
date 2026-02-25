#!/usr/bin/env python3
"""
NASDAQ 100 뉴스 수집기 — 네이버 검색 API
매일 GitHub Actions에서 실행, 결과를 data/news.json으로 저장
"""

import os, json, time, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

CLIENT_ID = os.environ["NAVER_CLIENT_ID"]
CLIENT_SECRET = os.environ["NAVER_CLIENT_SECRET"]

# ═══ 티커 → 검색어 매핑 (한글 + 영문) ═══
# 네이버에서 잘 검색되도록 한글 기업명 우선, 영문 티커 보조
TICKER_QUERIES = {
    # Semiconductor
    "NVDA": "엔비디아", "AVGO": "브로드컴", "ASML": "ASML",
    "AMD": "AMD", "QCOM": "퀄컴", "TXN": "텍사스인스트루먼트",
    "ARM": "ARM 반도체", "AMAT": "어플라이드머티리얼즈",
    "INTC": "인텔 반도체", "ADI": "아날로그디바이시스",
    "MU": "마이크론", "LRCX": "램리서치", "KLAC": "KLA",
    "MRVL": "마벨테크놀로지", "NXPI": "NXP반도체", "MCHP": "마이크로칩",
    "MPWR": "모놀리식파워", "STX": "시게이트", "WDC": "웨스턴디지털",
    # Software & Cloud
    "MSFT": "마이크로소프트", "CSCO": "시스코", "PLTR": "팔란티어",
    "CDNS": "케이던스", "SNPS": "시놉시스", "ADBE": "어도비",
    "INTU": "인튜이트", "ADP": "ADP", "WDAY": "워크데이",
    "DDOG": "데이터독", "VRSK": "버리스크", "CTSH": "코그니전트",
    "CSGP": "코스타그룹", "PAYX": "페이첵스", "MSTR": "마이크로스트래티지",
    "PANW": "팔로알토네트웍스", "CRWD": "크라우드스트라이크",
    "FTNT": "포티넷", "ZS": "지스케일러", "TEAM": "아틀라시안",
    "ADSK": "오토데스크", "SHOP": "쇼피파이",
    "ROP": "로퍼테크놀로지스", "TRI": "톰슨로이터",
    # Internet & Info
    "GOOGL": "구글 알파벳", "META": "메타 페이스북",
    "NFLX": "넷플릭스", "APP": "앱러빈", "DASH": "도어대시",
    "EA": "일렉트로닉아츠", "TTWO": "테이크투",
    "PDD": "핀둬둬 테무", "WBD": "워너브라더스",
    "CHTR": "차터커뮤니케이션", "CMCSA": "컴캐스트",
    # Internet Retail
    "AMZN": "아마존", "BKNG": "부킹홀딩스", "MELI": "메르카도리브레",
    "ABNB": "에어비앤비", "PYPL": "페이팔", "MAR": "메리어트",
    "ROST": "로스스토어스", "WMT": "월마트",
    # Consumer Lifestyle
    "AAPL": "애플", "COST": "코스트코", "PEP": "펩시코",
    "TMUS": "T모바일", "SBUX": "스타벅스", "MDLZ": "몬델리즈",
    "MNST": "몬스터비버리지", "KHC": "크래프트하인즈",
    "KDP": "큐리그닥터페퍼", "CCEP": "코카콜라유로패시픽",
    "CEG": "컨스텔레이션에너지", "XEL": "엑셀에너지",
    "AEP": "아메리칸일렉트릭파워", "EXC": "엑셀론",
    # Healthcare
    "ISRG": "인튜이티브서지컬", "AMGN": "암젠", "VRTX": "버텍스제약",
    "GILD": "길리어드", "REGN": "리제네론", "GEHC": "GE헬스케어",
    "DXCM": "덱스콤", "IDXX": "아이덱스", "ALNY": "알나일람",
    "INSM": "인스메드", "LIN": "린데",
    # Mobility & Industrial
    "TSLA": "테슬라", "HON": "하니웰", "AXON": "액슨엔터프라이즈",
    "CSX": "CSX", "CPRT": "코파트", "ODFL": "올드도미니언",
    "FAST": "파스널", "FANG": "다이아몬드백에너지",
    "BKR": "베이커휴즈", "FER": "페로비알", "PCAR": "팩카",
    "ORLY": "오라일리오토", "CTAS": "신타스",
}

def search_naver_news(query, display=5):
    """네이버 뉴스 검색 API 호출"""
    enc = urllib.parse.quote(query)
    url = f"https://openapi.naver.com/v1/search/news.json?query={enc}&display={display}&sort=date"
    
    req = urllib.request.Request(url)
    req.add_header("X-Naver-Client-Id", CLIENT_ID)
    req.add_header("X-Naver-Client-Secret", CLIENT_SECRET)
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.getcode() == 200:
                return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"  ❌ Error searching '{query}': {e}")
    return None


def clean_html(text):
    """HTML 태그 및 엔티티 제거"""
    import re
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&quot;", '"').replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&apos;", "'")
    return text.strip()


def extract_mentioned_tickers(title, desc):
    """뉴스 제목+본문에서 다른 NASDAQ 100 티커/기업명 언급 추출"""
    combined = (title + " " + desc).upper()
    mentions = set()
    
    # 티커 직접 매칭 (최소 경계 문자 체크)
    for ticker in TICKER_QUERIES:
        if len(ticker) >= 3 and ticker in combined:
            mentions.add(ticker)
    
    # 한글 기업명 매칭
    combined_kr = title + " " + desc
    kr_to_ticker = {}
    for t, q in TICKER_QUERIES.items():
        for keyword in q.split():
            if len(keyword) >= 2:
                kr_to_ticker[keyword] = t
    
    for keyword, ticker in kr_to_ticker.items():
        if keyword in combined_kr:
            mentions.add(ticker)
    
    return list(mentions)


def main():
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    print(f"🚀 뉴스 수집 시작: {now.strftime('%Y-%m-%d %H:%M KST')}")
    print(f"   총 {len(TICKER_QUERIES)}개 종목")
    
    news_data = {
        "updated": now.isoformat(),
        "updated_kst": now.strftime("%Y-%m-%d %H:%M"),
        "stocks": {},        # ticker → [뉴스 목록]
        "co_mentions": {},   # "TICKER1-TICKER2" → count (동시 언급)
    }
    
    co_mention_count = {}
    total_articles = 0
    
    for i, (ticker, query) in enumerate(TICKER_QUERIES.items()):
        print(f"  [{i+1:3d}/{len(TICKER_QUERIES)}] {ticker}: '{query}'")
        
        # 한글 검색 + 영문 티커 검색 (결과 합치기)
        articles = []
        seen_urls = set()
        
        for q in [query, f"{ticker} 주가"]:
            result = search_naver_news(q, display=5)
            if result and "items" in result:
                for item in result["items"]:
                    url = item.get("originallink") or item.get("link", "")
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    
                    title = clean_html(item.get("title", ""))
                    desc = clean_html(item.get("description", ""))
                    
                    # 다른 종목 동시 언급 추출
                    mentioned = extract_mentioned_tickers(title, desc)
                    
                    articles.append({
                        "title": title,
                        "desc": desc[:200],
                        "url": url,
                        "date": item.get("pubDate", ""),
                        "mentions": mentioned,
                    })
            
            time.sleep(0.05)  # 레이트 리밋 방지
        
        # 최신순 정렬, 최대 5개
        articles = articles[:5]
        news_data["stocks"][ticker] = articles
        total_articles += len(articles)
        
        # 동시 언급 카운트
        for art in articles:
            tickers_in_article = set(art["mentions"])
            tickers_in_article.add(ticker)
            tickers_list = sorted(tickers_in_article)
            for a_idx in range(len(tickers_list)):
                for b_idx in range(a_idx + 1, len(tickers_list)):
                    pair = f"{tickers_list[a_idx]}-{tickers_list[b_idx]}"
                    co_mention_count[pair] = co_mention_count.get(pair, 0) + 1
    
    # 동시 언급 2회 이상만 저장
    news_data["co_mentions"] = {
        k: v for k, v in sorted(co_mention_count.items(), key=lambda x: -x[1])
        if v >= 2
    }
    
    # 저장
    out_path = os.path.join(os.path.dirname(__file__), "..", "data", "news.json")
    out_path = os.path.abspath(out_path)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(news_data, f, ensure_ascii=False, indent=1)
    
    print(f"\n✅ 완료!")
    print(f"   기사 수: {total_articles}")
    print(f"   동시 언급 쌍: {len(news_data['co_mentions'])}")
    print(f"   저장: {out_path}")
    
    # 상위 동시 언급 출력
    top = list(news_data["co_mentions"].items())[:15]
    if top:
        print(f"\n📊 동시 언급 TOP 15:")
        for pair, count in top:
            print(f"   {pair}: {count}건")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
AI MESH — S&P 500 뉴스 수집기 (네이버 검색 API)
매일 GitHub Actions에서 실행, 결과를 data/sp500/news.json으로 누적 저장

- 500개 전부 검색하면 API 한도 초과 → 주요 ~150개 종목만 수집
- 90일(3개월) 누적 방식
- 경제/금융 뉴스만 필터
"""

import os, json, time, urllib.request, urllib.parse, re
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

CLIENT_ID = os.environ["NAVER_CLIENT_ID"]
CLIENT_SECRET = os.environ["NAVER_CLIENT_SECRET"]

RETENTION_DAYS = 90

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "sp500")

# ═══ 허용 언론사 도메인 ═══
ALLOWED_DOMAINS = [
    "mk.co.kr","heraldcorp.com","herald.co.kr","fnnews.com",
    "mt.co.kr","moneytoday.co.kr","bizwatch.co.kr","asiae.co.kr",
    "edaily.co.kr","biz.chosun.com","hankyung.com","joseilbo.com","sedaily.com",
]

BLOCKED_DOMAINS = [
    "starnewskorea.com","star.mt.co.kr","stoo.com","osen.mt.co.kr",
    "osen.co.kr","entertain.","sports.","star.",
    "n.news.naver.com","news.naver.com",
]

EXCLUDE_KEYWORDS = [
    "드라마","영화","출연","배우","감독","시청률","예능",
    "아이돌","컴백","데뷔","뮤직비디오","음원",
    "팬미팅","콘서트","캐스팅","촬영","개봉","흥행",
    "박스오피스","OST","웹툰","웹소설","애니메이션",
    "열애","결혼","이혼","스캔들",
]

FINANCE_KEYWORDS = [
    "주가","시총","매출","실적","투자","증시","S&P","나스닥",
    "반도체","AI","인공지능","클라우드","데이터센터",
    "매수","매도","목표가","전망","분기",
    "영업이익","순이익","배당","IPO","상장",
    "공급망","수출","관세","규제","인수","합병",
    "CEO","경영","전략","매각","파트너십",
    "달러","환율","금리","연준",
]

# ═══ S&P 500 주요 종목 → 검색어 매핑 (한국 뉴스 노출 높은 ~150개) ═══
TICKER_QUERIES = {
    # 빅테크
    "NVDA": "엔비디아", "AAPL": "애플", "MSFT": "마이크로소프트",
    "GOOGL": "구글 알파벳", "META": "메타 페이스북", "AMZN": "아마존",
    "TSLA": "테슬라", "NFLX": "넷플릭스", "AVGO": "브로드컴",
    "ORCL": "오라클", "CRM": "세일즈포스", "IBM": "IBM",
    "CSCO": "시스코", "PLTR": "팔란티어", "ADBE": "어도비",
    "INTU": "인튜이트", "NOW": "서비스나우", "ACN": "액센추어",
    # 반도체
    "AMD": "AMD", "INTC": "인텔 반도체", "QCOM": "퀄컴",
    "TXN": "텍사스인스트루먼트", "AMAT": "어플라이드머티리얼즈",
    "LRCX": "램리서치", "KLAC": "KLA", "MU": "마이크론",
    "ADI": "아날로그디바이시스", "NXPI": "NXP반도체", "MCHP": "마이크로칩",
    "ANET": "아리스타네트웍스", "DELL": "델테크놀로지",
    # 사이버보안/클라우드
    "CRWD": "크라우드스트라이크", "PANW": "팔로알토네트웍스",
    "FTNT": "포티넷", "DDOG": "데이터독", "WDAY": "워크데이",
    "SNPS": "시놉시스", "CDNS": "케이던스", "ADSK": "오토데스크",
    # 금융
    "JPM": "JP모건", "GS": "골드만삭스", "MS": "모건스탠리",
    "BAC": "뱅크오브아메리카", "WFC": "웰스파고", "C": "씨티그룹",
    "V": "비자", "MA": "마스터카드", "AXP": "아메리칸익스프레스",
    "BLK": "블랙록", "SCHW": "찰스슈왑", "COF": "캐피탈원",
    "PYPL": "페이팔", "COIN": "코인베이스", "HOOD": "로빈후드",
    "BX": "블랙스톤", "KKR": "KKR",
    # 헬스케어
    "LLY": "일라이릴리", "UNH": "유나이티드헬스", "JNJ": "존슨앤존슨",
    "MRK": "머크", "ABBV": "애브비", "PFE": "화이자",
    "TMO": "써모피셔", "ABT": "애보트", "AMGN": "암젠",
    "GILD": "길리어드", "ISRG": "인튜이티브서지컬", "VRTX": "버텍스제약",
    "REGN": "리제네론", "BMY": "브리스톨마이어스",
    "MRNA": "모더나", "GEHC": "GE헬스케어",
    # 산업재/방산
    "GE": "GE에어로스페이스", "CAT": "캐터필러", "RTX": "RTX 레이시온",
    "HON": "하니웰", "BA": "보잉", "LMT": "록히드마틴",
    "DE": "디어앤컴퍼니", "UPS": "UPS", "FDX": "페덱스",
    "NOC": "노스롭그루먼", "GD": "제너럴다이내믹스",
    "UNP": "유니온퍼시픽", "UBER": "우버",
    # 소비재/리테일
    "WMT": "월마트", "COST": "코스트코", "HD": "홈디포",
    "LOW": "로우스", "TJX": "TJX", "MCD": "맥도날드",
    "NKE": "나이키", "SBUX": "스타벅스", "BKNG": "부킹홀딩스",
    "MAR": "메리어트", "HLT": "힐튼", "ABNB": "에어비앤비",
    "CMG": "치폴레", "DASH": "도어대시", "GM": "제너럴모터스",
    "F": "포드", "RCL": "로열캐리비안", "LULU": "룰루레몬",
    # 통신/미디어
    "TMUS": "T모바일", "DIS": "디즈니", "CMCSA": "컴캐스트",
    "VZ": "버라이즌", "T": "AT&T", "WBD": "워너브라더스",
    "EA": "일렉트로닉아츠", "TTWO": "테이크투", "LYV": "라이브네이션",
    # 소비필수
    "KO": "코카콜라", "PEP": "펩시코", "PG": "P&G 프록터앤갬블",
    "PM": "필립모리스", "CL": "콜게이트", "MDLZ": "몬델리즈",
    "KHC": "크래프트하인즈",
    # 에너지
    "XOM": "엑손모빌", "CVX": "셰브론", "COP": "코노코필립스",
    "SLB": "슐룸버거", "OXY": "옥시덴탈",
    # 유틸리티/소재
    "NEE": "넥스트에라에너지", "CEG": "컨스텔레이션에너지",
    "LIN": "린데", "SHW": "셔윈윌리엄스", "NEM": "뉴몬트",
    "FCX": "프리포트맥모란",
    # 부동산
    "PLD": "프롤로지스", "AMT": "아메리칸타워", "EQIX": "에퀴닉스",
    # 기타 주목
    "APP": "앱러빈", "CVNA": "카바나", "AXON": "액슨엔터프라이즈",
    "TTD": "더트레이드데스크", "SMCI": "슈퍼마이크로",
    "FSLR": "퍼스트솔라", "VST": "비스트라",
}


def is_allowed_source(url):
    if not url:
        return False
    url_lower = url.lower()
    for blocked in BLOCKED_DOMAINS:
        if blocked in url_lower:
            return False
    return any(domain in url_lower for domain in ALLOWED_DOMAINS)


def is_financial_news(title, desc):
    combined = title + " " + desc
    exclude_count = sum(1 for kw in EXCLUDE_KEYWORDS if kw in combined)
    if exclude_count >= 2:
        return False
    if exclude_count >= 1:
        if not any(kw in combined for kw in FINANCE_KEYWORDS):
            return False
    return True


def normalize_title(title):
    return re.sub(r"[^\w가-힣]", "", title).lower()


def is_duplicate(new_title, new_url, existing_articles):
    def clean_url(u):
        return u.split("?")[0].split("#")[0].rstrip("/") if u else ""
    clean_new = clean_url(new_url)
    norm_new = normalize_title(new_title)
    for art in existing_articles:
        if clean_new and clean_new == clean_url(art.get("url", "")):
            return True
        norm_ex = normalize_title(art.get("title", ""))
        if len(norm_new) >= 15 and len(norm_ex) >= 15:
            if norm_new[:20] == norm_ex[:20]:
                return True
    return False


def deduplicate_articles(articles):
    seen_urls = set()
    seen_titles = set()
    unique = []
    def clean_url(u):
        return u.split("?")[0].split("#")[0].rstrip("/") if u else ""
    for art in articles:
        url = clean_url(art.get("url", ""))
        norm_title = normalize_title(art.get("title", ""))[:20]
        if url and url in seen_urls:
            continue
        if len(norm_title) >= 15 and norm_title in seen_titles:
            continue
        if url:
            seen_urls.add(url)
        if len(norm_title) >= 15:
            seen_titles.add(norm_title)
        unique.append(art)
    return unique


def search_naver_news(query, display=5):
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
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&quot;", '"').replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&apos;", "'")
    return text.strip()


def parse_date(date_str):
    if not date_str:
        return None
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.isoformat()
    except:
        pass
    return date_str


def is_within_retention(date_str, cutoff_date):
    if not date_str:
        return True
    try:
        if "T" in date_str:
            dt_str = date_str.split("T")[0]
            dt = datetime.strptime(dt_str, "%Y-%m-%d")
        else:
            dt = parsedate_to_datetime(date_str).replace(tzinfo=None)
        return dt >= cutoff_date
    except:
        return True


def extract_mentioned_tickers(title, desc):
    combined = (title + " " + desc).upper()
    mentions = set()
    for ticker in TICKER_QUERIES:
        if len(ticker) >= 3 and ticker in combined:
            mentions.add(ticker)
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


def calculate_co_mentions(stocks_data):
    co_mention_count = {}
    for ticker, articles in stocks_data.items():
        for art in articles:
            tickers_in_article = set(art.get("mentions", []))
            tickers_in_article.add(ticker)
            tickers_list = sorted(tickers_in_article)
            for a_idx in range(len(tickers_list)):
                for b_idx in range(a_idx + 1, len(tickers_list)):
                    pair = f"{tickers_list[a_idx]}-{tickers_list[b_idx]}"
                    co_mention_count[pair] = co_mention_count.get(pair, 0) + 1
    return {
        k: v for k, v in sorted(co_mention_count.items(), key=lambda x: -x[1])
        if v >= 2
    }


def main():
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    cutoff_date = (now - timedelta(days=RETENTION_DAYS)).replace(tzinfo=None)

    print(f"🚀 S&P 500 뉴스 수집 시작: {now.strftime('%Y-%m-%d %H:%M KST')}")
    print(f"   총 {len(TICKER_QUERIES)}개 종목 (주요 종목만)")
    print(f"   보관 기간: {RETENTION_DAYS}일")

    # 1. 기존 데이터 로드
    out_path = os.path.join(DATA_DIR, "news.json")
    existing_stocks = {}
    if os.path.exists(out_path):
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            existing_stocks = existing.get("stocks", {})
            article_count = sum(len(v) for v in existing_stocks.values())
            print(f"  📄 기존 news.json 로드: {article_count}개 기사")
        except Exception as e:
            print(f"  ⚠️ 기존 news.json 로드 실패: {e}")
    else:
        print("  📄 기존 news.json 없음 — 새로 생성")

    # 2. 기존 데이터 정리
    print(f"\n🧹 기존 데이터 정리 중...")
    cleaned_count = 0
    for ticker in list(existing_stocks.keys()):
        before = len(existing_stocks[ticker])
        existing_stocks[ticker] = [
            a for a in existing_stocks[ticker]
            if is_financial_news(a.get("title", ""), a.get("desc", ""))
        ]
        existing_stocks[ticker] = deduplicate_articles(existing_stocks[ticker])
        existing_stocks[ticker] = [
            a for a in existing_stocks[ticker]
            if is_within_retention(a.get("date"), cutoff_date)
        ]
        cleaned_count += before - len(existing_stocks[ticker])
    if cleaned_count > 0:
        print(f"  🗑️ {cleaned_count}개 기사 정리됨")

    # 3. 오늘 뉴스 수집
    print(f"\n📡 오늘 뉴스 수집 중...")
    today_new_count = 0
    today_filtered_count = 0

    for i, (ticker, query) in enumerate(TICKER_QUERIES.items()):
        if (i + 1) % 20 == 0 or i == 0:
            print(f"  [{i+1:3d}/{len(TICKER_QUERIES)}] {ticker}: '{query}'")

        new_articles = []
        seen_urls = set()

        for q in [query, f"{ticker} 주가"]:
            result = search_naver_news(q, display=15)
            if result and "items" in result:
                for item in result["items"]:
                    url = item.get("originallink", "")
                    if not url or url in seen_urls:
                        continue
                    if not is_allowed_source(url):
                        continue
                    seen_urls.add(url)

                    title = clean_html(item.get("title", ""))
                    desc = clean_html(item.get("description", ""))

                    if not is_financial_news(title, desc):
                        today_filtered_count += 1
                        continue

                    if is_duplicate(title, url, existing_stocks.get(ticker, [])):
                        continue

                    mentioned = extract_mentioned_tickers(title, desc)
                    pub_date = parse_date(item.get("pubDate", ""))

                    new_articles.append({
                        "title": title,
                        "desc": desc[:200],
                        "url": url,
                        "date": pub_date,
                        "mentions": mentioned,
                    })

                    if len(new_articles) >= 8:
                        break

            if len(new_articles) >= 8:
                break
            time.sleep(0.05)

        today_new_count += len(new_articles)
        combined = new_articles + existing_stocks.get(ticker, [])
        existing_stocks[ticker] = deduplicate_articles(combined)

    # 4. co-mention 재계산
    print(f"\n🔗 co-mention 재계산 중...")
    co_mentions = calculate_co_mentions(existing_stocks)

    # 5. 저장
    total_articles = sum(len(v) for v in existing_stocks.values())
    tickers_with_news = sum(1 for v in existing_stocks.values() if len(v) > 0)

    news_data = {
        "updated": now.isoformat(),
        "updated_kst": now.strftime("%Y-%m-%d %H:%M"),
        "retention_days": RETENTION_DAYS,
        "stats": {
            "total_articles": total_articles,
            "tickers_with_news": tickers_with_news,
            "today_new": today_new_count,
            "today_filtered": today_filtered_count,
            "co_mention_pairs": len(co_mentions),
        },
        "stocks": existing_stocks,
        "co_mentions": co_mentions,
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(news_data, f, ensure_ascii=False, indent=1)

    file_size = os.path.getsize(out_path) / 1024
    print(f"\n✅ 완료!")
    print(f"   오늘 수집: {today_new_count}개 (필터링 제외: {today_filtered_count}개)")
    print(f"   전체 누적: {total_articles}개 ({tickers_with_news}개 종목)")
    print(f"   co-mention 쌍: {len(co_mentions)}개")
    print(f"   파일 크기: {file_size:.1f} KB")

    top = list(co_mentions.items())[:15]
    if top:
        print(f"\n📊 co-mention TOP 15:")
        for pair, count in top:
            print(f"   {pair}: {count}건")


if __name__ == "__main__":
    main()

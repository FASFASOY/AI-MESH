#!/usr/bin/env python3
"""
NASDAQ 100 뉴스 수집기 — 네이버 검색 API
매일 GitHub Actions에서 실행, 결과를 data/news.json으로 누적 저장

핵심 변경:
- 매일 리셋 → 90일(3개월) 누적 방식
- 기존 news.json 로드 → 새 뉴스 추가 → 90일 초과 기사 삭제
- co-mention은 전체 누적 데이터 기준으로 매번 재계산
- 중복 URL 자동 제거
"""

import os, json, time, urllib.request, urllib.parse, re
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

CLIENT_ID = os.environ["NAVER_CLIENT_ID"]
CLIENT_SECRET = os.environ["NAVER_CLIENT_SECRET"]

RETENTION_DAYS = 90  # 뉴스 보관 기간 (3개월)

# ═══ 허용 언론사 도메인 (경제/금융 전문지만) ═══
ALLOWED_DOMAINS = [
    "mk.co.kr",           # 매일경제
    "heraldcorp.com",      # 헤럴드경제
    "herald.co.kr",        # 헤럴드경제 (구도메인)
    "fnnews.com",          # 파이낸셜뉴스
    "mt.co.kr",            # 머니투데이
    "moneytoday.co.kr",    # 머니투데이 (구도메인)
    "bizwatch.co.kr",      # 비즈워치
    "asiae.co.kr",         # 아시아경제
    "edaily.co.kr",        # 이데일리
    "biz.chosun.com",      # 조선비즈
    "hankyung.com",        # 한국경제
    "joseilbo.com",        # 조세일보
    "sedaily.com",         # 서울경제
]

def is_allowed_source(url):
    if not url:
        return False
    url_lower = url.lower()
    return any(domain in url_lower for domain in ALLOWED_DOMAINS)

# ═══ 티커 → 검색어 매핑 ═══
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
    """다양한 날짜 형식을 ISO 형식으로 변환"""
    if not date_str:
        return None
    try:
        # RFC 2822 형식 (네이버 API 기본)
        dt = parsedate_to_datetime(date_str)
        return dt.isoformat()
    except:
        pass
    # 이미 ISO 형식인 경우
    if "T" in date_str:
        return date_str
    return date_str


def is_within_retention(date_str, cutoff_date):
    """기사가 보관 기간 내인지 확인"""
    if not date_str:
        return True  # 날짜 없으면 일단 보관
    try:
        if "T" in date_str:
            # ISO 형식
            dt_str = date_str.split("T")[0]
            dt = datetime.strptime(dt_str, "%Y-%m-%d")
        else:
            # RFC 2822
            dt = parsedate_to_datetime(date_str).replace(tzinfo=None)
        return dt >= cutoff_date
    except:
        return True  # 파싱 실패하면 일단 보관


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


def load_existing_news(path):
    """기존 news.json 로드"""
    if not os.path.exists(path):
        print("  📄 기존 news.json 없음 — 새로 생성")
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        stock_count = len(data.get("stocks", {}))
        article_count = sum(len(v) for v in data.get("stocks", {}).values())
        print(f"  📄 기존 news.json 로드: {stock_count}개 종목, {article_count}개 기사")
        return data
    except Exception as e:
        print(f"  ⚠️ 기존 news.json 로드 실패: {e}")
        return None


def merge_articles(existing_articles, new_articles):
    """기존 기사 + 새 기사 병합 (URL 기준 중복 제거)"""
    seen_urls = set()
    merged = []

    # 새 기사 먼저 (최신 우선)
    for art in new_articles:
        url = art.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            merged.append(art)

    # 기존 기사 추가
    for art in existing_articles:
        url = art.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            merged.append(art)

    return merged


def calculate_co_mentions(stocks_data):
    """전체 누적 데이터 기준으로 co-mention 재계산"""
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

    # 2회 이상만 저장, 내림차순 정렬
    return {
        k: v for k, v in sorted(co_mention_count.items(), key=lambda x: -x[1])
        if v >= 2
    }


def main():
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    cutoff_date = (now - timedelta(days=RETENTION_DAYS)).replace(tzinfo=None)

    print(f"🚀 뉴스 수집 시작: {now.strftime('%Y-%m-%d %H:%M KST')}")
    print(f"   총 {len(TICKER_QUERIES)}개 종목")
    print(f"   보관 기간: {RETENTION_DAYS}일 (~ {cutoff_date.strftime('%Y-%m-%d')} 이후)")

    # ═══ 1. 기존 데이터 로드 ═══
    out_path = os.path.join(os.path.dirname(__file__), "..", "data", "news.json")
    out_path = os.path.abspath(out_path)
    existing = load_existing_news(out_path)
    existing_stocks = existing.get("stocks", {}) if existing else {}

    # ═══ 2. 오늘 뉴스 수집 ═══
    print(f"\n📡 오늘 뉴스 수집 중...")
    today_new_count = 0

    for i, (ticker, query) in enumerate(TICKER_QUERIES.items()):
        if (i + 1) % 10 == 0 or i == 0:
            print(f"  [{i+1:3d}/{len(TICKER_QUERIES)}] {ticker}: '{query}'")

        # 오늘 새로 수집
        new_articles = []
        seen_urls = set()

        for q in [query, f"{ticker} 주가"]:
            result = search_naver_news(q, display=20)
            if result and "items" in result:
                for item in result["items"]:
                    url = item.get("originallink") or item.get("link", "")
                    if url in seen_urls:
                        continue
                    if not is_allowed_source(url):
                        continue
                    seen_urls.add(url)

                    title = clean_html(item.get("title", ""))
                    desc = clean_html(item.get("description", ""))
                    mentioned = extract_mentioned_tickers(title, desc)
                    pub_date = parse_date(item.get("pubDate", ""))

                    new_articles.append({
                        "title": title,
                        "desc": desc[:200],
                        "url": url,
                        "date": pub_date,
                        "mentions": mentioned,
                    })

                    if len(new_articles) >= 10:
                        break

            if len(new_articles) >= 10:
                break
            time.sleep(0.05)

        today_new_count += len(new_articles)

        # ═══ 3. 기존 기사와 병합 ═══
        old_articles = existing_stocks.get(ticker, [])
        merged = merge_articles(old_articles, new_articles)

        # ═══ 4. 90일 초과 기사 제거 ═══
        retained = [a for a in merged if is_within_retention(a.get("date"), cutoff_date)]

        existing_stocks[ticker] = retained

    # ═══ 5. co-mention 전체 재계산 ═══
    print(f"\n🔗 co-mention 재계산 중...")
    co_mentions = calculate_co_mentions(existing_stocks)

    # ═══ 6. 통계 ═══
    total_articles = sum(len(v) for v in existing_stocks.values())
    tickers_with_news = sum(1 for v in existing_stocks.values() if len(v) > 0)

    # ═══ 7. 저장 ═══
    news_data = {
        "updated": now.isoformat(),
        "updated_kst": now.strftime("%Y-%m-%d %H:%M"),
        "retention_days": RETENTION_DAYS,
        "stats": {
            "total_articles": total_articles,
            "tickers_with_news": tickers_with_news,
            "today_new": today_new_count,
            "co_mention_pairs": len(co_mentions),
        },
        "stocks": existing_stocks,
        "co_mentions": co_mentions,
    }

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(news_data, f, ensure_ascii=False, indent=1)

    file_size = os.path.getsize(out_path) / 1024
    print(f"\n✅ 완료!")
    print(f"   오늘 수집: {today_new_count}개")
    print(f"   전체 누적: {total_articles}개 ({tickers_with_news}개 종목)")
    print(f"   co-mention 쌍: {len(co_mentions)}개")
    print(f"   파일 크기: {file_size:.1f} KB")
    print(f"   저장: {out_path}")

    # 상위 co-mention
    top = list(co_mentions.items())[:15]
    if top:
        print(f"\n📊 co-mention TOP 15:")
        for pair, count in top:
            print(f"   {pair}: {count}건")


if __name__ == "__main__":
    main()

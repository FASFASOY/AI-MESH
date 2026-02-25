# AI MESH — 뉴스 파이프라인 셋업 가이드

## 프로젝트 구조

```
ai-mesh/
├── .github/workflows/
│   └── update-news.yml      ← GitHub Actions (매일 자동 실행)
├── scripts/
│   └── fetch_news.py         ← 네이버 뉴스 수집 스크립트
├── data/
│   └── news.json             ← 수집된 뉴스 데이터 (자동 갱신)
└── nasdaq100-network-v2.html ← 메인 네트워크 맵
```

## 셋업 순서

### 1단계: 네이버 API 키 발급

1. https://developers.naver.com 접속 → 로그인
2. **Application → 애플리케이션 등록**
3. 앱 이름: `AI-MESH` (아무거나)
4. 사용 API: **검색** 선택
5. 환경: **WEB 설정** → URL: `https://yourusername.github.io`
6. 등록 완료 → **Client ID** / **Client Secret** 메모

### 2단계: GitHub 저장소 생성

```bash
# 새 저장소 만들기
git init ai-mesh
cd ai-mesh

# 이 폴더의 파일들 전부 복사한 후
git add .
git commit -m "초기 세팅"

# GitHub에 저장소 생성 후
git remote add origin https://github.com/YOUR_USERNAME/ai-mesh.git
git branch -M main
git push -u origin main
```

### 3단계: GitHub Secrets 등록

1. GitHub 저장소 → **Settings → Secrets and variables → Actions**
2. **New repository secret** 클릭
3. 두 개 등록:
   - Name: `NAVER_CLIENT_ID` → Value: 네이버에서 받은 Client ID
   - Name: `NAVER_CLIENT_SECRET` → Value: 네이버에서 받은 Client Secret

### 4단계: GitHub Pages 활성화

1. GitHub 저장소 → **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` / `/(root)` 선택 → Save

### 5단계: 첫 실행 테스트

1. GitHub 저장소 → **Actions** 탭
2. 왼쪽에서 "Daily News Update" 선택
3. **Run workflow** → **Run workflow** 클릭
4. 실행 완료 후 `data/news.json` 파일 확인

### 자동 실행

- 매일 한국시간 오전 7시에 자동 실행
- `data/news.json`이 자동 갱신됨
- HTML에서 이 파일을 fetch하여 뉴스 표시

## news.json 구조

```json
{
  "updated": "2026-02-25T07:00:00+09:00",
  "updated_kst": "2026-02-25 07:00",
  "stocks": {
    "NVDA": [
      {
        "title": "엔비디아, AI 칩 수출규제 완화 기대감에 급등",
        "desc": "미국 상무부가 AI 칩 수출규제를...",
        "url": "https://...",
        "date": "Tue, 25 Feb 2026 ...",
        "mentions": ["NVDA", "AMD", "INTC"]
      }
    ]
  },
  "co_mentions": {
    "AMD-NVDA": 12,
    "GOOGL-META": 8,
    "AAPL-MSFT": 5
  }
}
```

## HTML에서 사용법

HTML이 GitHub Pages에 호스팅되면:
```javascript
const NEWS_URL = "https://yourusername.github.io/ai-mesh/data/news.json";
const resp = await fetch(NEWS_URL);
const newsData = await resp.json();
```

로컬 테스트 시:
```javascript
const NEWS_URL = "./data/news.json";
```

## 뉴스 기반 관계 가중치 보정

`co_mentions` 데이터로 기존 엣지 가중치 보정:
- 동시 언급 횟수가 많을수록 해당 관계의 선이 굵어짐
- 기존 정적 가중치 + (동시 언급 × 보정계수)
- 새로운 뉴스 관계가 발견되면 점선으로 표시 가능

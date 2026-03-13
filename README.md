# 🪨 Pebbles — 세계 뉴스 큐레이션

18개 글로벌 언론사의 뉴스를 한국어로 번역·요약하여 제공하는 뉴스 큐레이션 서비스입니다.

## 주요 기능

- 18개 언론사 RSS 자동 크롤링 (Reuters, BBC, Bloomberg, NYT 등)
- Claude API를 활용한 한국어 번역 및 3줄 요약
- 임베딩 기반 관련 기사 클러스터링
- 카테고리별 필터 (세계 / 경제 / 기술 / 한국)
- 날짜별 뉴스 탐색, 언론사별 필터링
- 기사 상세 보기 (원문 토글)

## 기술 스택

- **프론트엔드:** Vite + TypeScript (Vanilla)
- **크롤러:** Python (urllib, xml.etree)
- **번역/요약:** Claude Haiku API
- **클러스터링:** sentence-transformers + NumPy
- **배포:** Vercel

## 뉴스 소스

**세계** — Reuters, AP, BBC, NYT, The Guardian, The Hindu
**경제** — Bloomberg, FT, WSJ, Economist, Nikkei Asia, SCMP
**기술** — TechCrunch, The Verge, Wired
**한국** — 연합뉴스, 한국경제, 매일경제, 한겨레

## 실행 방법

```bash
# 프론트엔드
npm install
npm run dev

# 크롤러 실행
python3 crawler.py

# 전체 파이프라인 (크롤링 → 번역 → 클러스터링 → 배포)
./run_crawler.sh
```

## 데이터 흐름

```
RSS 크롤링 → Claude API 번역/요약 → 임베딩 클러스터링 → news.json 생성 → Vercel 배포
```

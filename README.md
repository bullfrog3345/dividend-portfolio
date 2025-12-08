# 💰 배당금 포트폴리오 관리 앱

Progressive Web App(PWA)으로 제작된 배당금 캘린더 및 포트폴리오 관리 도구입니다.

## 🌟 주요 기능

- 📊 실시간 주가 및 배당금 정보 조회
- 💵 USD/KRW 환율 분석 (RSI, 이동평균)
- 📅 월별 배당금 캘린더
- 🎯 포트폴리오 리밸런싱 제안
- 📱 모바일 PWA 지원 (홈 화면 설치 가능)

## 🚀 설치 및 실행

### 필요 패키지 설치
```bash
pip install -r requirements.txt
```

### 로컬 실행
```bash
streamlit run app.py
```

### 웹에서 접속
배포된 앱: [Streamlit Cloud URL]

## 📱 모바일 설치

### Android
1. Chrome에서 앱 접속
2. 메뉴 → "홈 화면에 추가"

### iOS
1. Safari에서 앱 접속
2. 공유 → "홈 화면에 추가"

## 🛠️ 기술 스택

- **Frontend**: Streamlit
- **Data**: yfinance, pandas
- **Charts**: Plotly
- **Translation**: deep-translator
- **PWA**: manifest.json, service-worker.js

## 📝 라이선스

MIT License

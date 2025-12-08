import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime

def get_exchange_rate(currency_pair="KRW=X"):
    """
    실시간 환율 정보를 가져옵니다.
    실패 시 기본값 1400원을 반환하지만 경고를 로그에 남깁니다.
    """
    try:
        ticker = yf.Ticker(currency_pair)
        # fast_info가 더 빠르고 안정적일 수 있음
        price = ticker.fast_info.last_price
        if price and price > 0:
            return price
        
        # history로 재시도
        hist = ticker.history(period="1d")
        if not hist.empty:
            return hist['Close'].iloc[-1]
            
        return 1400.0 # Fallback
    except Exception as e:
        print(f"Error fetching exchange rate: {e}")
        return 1400.0

def fetch_stock_data_batch(portfolio_df):
    """
    포트폴리오 내 모든 종목의 데이터를 일괄(Batch)로 가져옵니다.
    """
    if portfolio_df.empty:
        return pd.DataFrame(), 0, 0, []

    tickers = portfolio_df['Ticker'].unique().tolist()
    # yfinance batch download (threads=True for parallel processing)
    # Tickers 객체 사용이 메타데이터 조회에 더 유리할 수 있음
    
    results = []
    monthly_dividend_list = []
    total_value = 0
    total_annual_dividend = 0
    
    # 환율 가져오기
    exchange_rate = get_exchange_rate()
    
    # Batch 처리를 위해 Tickers 객체 생성
    tickers_str = " ".join(tickers)
    try:
        dat = yf.Tickers(tickers_str)
    except Exception as e:
        st.error(f"데이터 초기화 실패: {e}")
        return pd.DataFrame(), 0, 0, []

    # 진행률 표시
    progress_bar = st.progress(0)
    
    for idx, row in portfolio_df.iterrows():
        ticker_symbol = row['Ticker']
        qty = row['Quantity']
        target_ratio = float(row.get('TargetRatio', 0.0))
        if pd.isna(target_ratio): target_ratio = 0.0
        
        try:
            # Tickers 객체에서 개별 Ticker 접근
            stock = dat.tickers[ticker_symbol]
            
            # 정보 가져오기
            try:
                info = stock.info
            except:
                # Batch fetch 실패 시 개별 시도
                stock = yf.Ticker(ticker_symbol)
                info = stock.info

            # 현재가
            current_price = info.get('currentPrice') or info.get('regularMarketPrice') or 0
            
            # 통화 확인
            currency = info.get('currency', 'USD')
            
            # 적용 환율
            applied_rate = exchange_rate if currency == 'USD' else 1.0
            
            # 평가액
            market_value = current_price * qty * applied_rate
            
            # 배당 정보
            dividend_yield = info.get('dividendYield')
            dividend_rate = info.get('dividendRate')
            
            # 배당 기록 (Batch 객체에서는 dividends 접근이 다를 수 있어 개별 호출이 안전할 수 있음)
            # 속도를 위해 info에 있는 경우 우선 사용하고, 없으면 history 조회
            
            # 예상 연 배당금 계산 로직
            projected_annual_dividend = 0
            
            # 배당 내역 조회 (필요한 경우)
            hist = pd.DataFrame()
            if (dividend_rate is None or dividend_rate == 0):
                try:
                    hist = stock.dividends
                    if not hist.empty:
                        # Timezone 제거
                        if hist.index.tz is not None:
                            hist.index = hist.index.tz_localize(None)
                            
                        # 최근 1년 합계
                        one_year_ago = pd.Timestamp.now() - pd.DateOffset(years=1)
                        recent_divs = hist[hist.index >= one_year_ago]
                        if not recent_divs.empty:
                            dividend_rate = recent_divs.sum()
                            if current_price > 0:
                                dividend_yield = dividend_rate / current_price
                except Exception:
                    pass

            if dividend_rate is None: dividend_rate = 0
            if dividend_yield is None: dividend_yield = 0
            
            # 월별 배당금 리스트 생성 (과거 패턴 기반 추정)
            # 정확한 월별 데이터를 위해선 dividends history가 필요함
            if hist.empty:
                try:
                    hist = stock.dividends
                    if not hist.empty and hist.index.tz is not None:
                        hist.index = hist.index.tz_localize(None)
                except:
                    pass
            
            if not hist.empty:
                now = pd.Timestamp.now().normalize()
                current_month_start = now.replace(day=1)
                one_year_later = now + pd.DateOffset(years=1)
                lookback_start = now - pd.DateOffset(years=2)
                
                recent_hist = hist[hist.index >= lookback_start]
                
                for date, amount in recent_hist.items():
                    next_date = date
                    while next_date < current_month_start:
                        next_date += pd.DateOffset(years=1)
                    
                    if current_month_start <= next_date <= one_year_later:
                        div_amount = amount * qty * applied_rate
                        projected_annual_dividend += div_amount
                        
                        monthly_dividend_list.append({
                            'Month': next_date.month,
                            'Date': next_date,
                            'Ticker': ticker_symbol,
                            'Dividend': div_amount
                        })
            
            # 연 배당금 결정
            if projected_annual_dividend > 0:
                annual_dividend = projected_annual_dividend
            else:
                annual_dividend = dividend_rate * qty * applied_rate

            # 요약 정보 (번역 적용)
            summary_en = info.get('longBusinessSummary', 'No description available.')
            try:
                from deep_translator import GoogleTranslator
                summary = GoogleTranslator(source='auto', target='ko').translate(summary_en)
            except Exception as e:
                summary = summary_en # 번역 실패 시 원문 사용
                print(f"Translation failed: {e}")
            
            results.append({
                'Ticker': ticker_symbol,
                'Quantity': qty,
                'TargetRatio': target_ratio,
                'Current Price': current_price,
                'Currency': currency,
                'Market Value (KRW)': market_value,
                'Annual Dividend (KRW)': annual_dividend,
                'Dividend Yield (%)': (dividend_yield * 100) if dividend_yield else 0,
                'Summary': summary,
                'Recommendation': info.get('recommendationKey', 'N/A').upper(),
                'Target Price': info.get('targetMeanPrice', 0) or 0,
                '52WeekHigh': info.get('fiftyTwoWeekHigh', 0),
                '52WeekLow': info.get('fiftyTwoWeekLow', 0),
                'Beta': info.get('beta', 0)
            })
            
            total_value += market_value
            total_annual_dividend += annual_dividend
            
        except Exception as e:
            st.error(f"{ticker_symbol} 데이터 처리 중 오류: {e}")
            
        progress_bar.progress((idx + 1) / len(portfolio_df))
        
    progress_bar.empty()
    
    return pd.DataFrame(results), total_value, total_annual_dividend, monthly_dividend_list

def get_exchange_rate_analysis():
    """원/달러 환율 기술적 분석 데이터"""
    try:
        ticker = "KRW=X"
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y", interval="1d")
        
        if hist.empty:
            return None
            
        current_price = hist['Close'].iloc[-1]
        prev_price = hist['Close'].iloc[-2]
        change = current_price - prev_price
        change_rate = (change / prev_price) * 100
        
        # MA
        hist['MA20'] = hist['Close'].rolling(window=20).mean()
        hist['MA60'] = hist['Close'].rolling(window=60).mean()
        
        # RSI
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        hist['RSI'] = 100 - (100 / (1 + rs))
        
        current_rsi = hist['RSI'].iloc[-1]
        
        analysis = {
            'current_price': current_price,
            'change': change,
            'change_rate': change_rate,
            'rsi': current_rsi,
            'ma20': hist['MA20'].iloc[-1],
            'ma60': hist['MA60'].iloc[-1],
            'history': hist
        }
        
        # RSI Status
        if current_rsi >= 70:
            analysis.update({'rsi_status': "과매수 (High)", 'rsi_signal': "매도 고려", 'rsi_color': "red"})
        elif current_rsi <= 30:
            analysis.update({'rsi_status': "과매도 (Low)", 'rsi_signal': "매수 기회", 'rsi_color': "green"})
        else:
            analysis.update({'rsi_status': "중립 (Neutral)", 'rsi_signal': "관망", 'rsi_color': "gray"})
            
        # Trend
        if current_price > analysis['ma20']:
            analysis['trend'] = "상승 추세"
        else:
            analysis['trend'] = "하락/조정 추세"
            
        return analysis
        
    except Exception as e:
        print(f"Exchange analysis error: {e}")
        return None

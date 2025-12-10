import pandas as pd
import os

# CSV 파일 경로
CSV_FILE = 'portfolio.csv'

def load_portfolio():
    """포트폴리오 CSV 파일을 로드합니다."""
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            if 'TargetRatio' not in df.columns:
                df['TargetRatio'] = 0.0
            # NaN 값을 0.0으로 채우기
            df['TargetRatio'] = df['TargetRatio'].fillna(0.0)
            return df
        except Exception as e:
            print(f"Error loading portfolio: {e}")
            return pd.DataFrame(columns=['Ticker', 'Quantity', 'TargetRatio'])
    return pd.DataFrame(columns=['Ticker', 'Quantity', 'TargetRatio'])

def save_portfolio(df):
    """포트폴리오를 CSV 파일로 저장합니다."""
    try:
        df.to_csv(CSV_FILE, index=False)
        # 업데이트 타임스탬프 저장
        from datetime import datetime
        with open('portfolio_updated.txt', 'w') as f:
            f.write(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    except Exception as e:
        print(f"Error saving portfolio: {e}")

def get_last_update():
    """마지막 업데이트 시간 가져오기"""
    try:
        if os.path.exists('portfolio_updated.txt'):
            with open('portfolio_updated.txt', 'r') as f:
                return f.read().strip()
        return "없음"
    except:
        return "없음"

def format_currency(value, currency='KRW'):
    """통화 포맷팅 헬퍼 함수"""
    symbol = '₩' if currency == 'KRW' else '$'
    return f"{symbol}{value:,.0f}" if currency == 'KRW' else f"{symbol}{value:,.2f}"

def calculate_rebalancing(df_result, total_value):
    """리밸런싱 데이터 계산"""
    rebalancing_data = []
    projected_total_monthly_div = 0
    total_div = df_result['Annual Dividend (KRW)'].sum()
    
    for _, row in df_result.iterrows():
        ticker = row['Ticker']
        current_val = row['Market Value (KRW)']
        target_ratio = row['TargetRatio']
        current_price = row['Current Price']
        currency = row['Currency']
        exchange_rate = 1400 if currency == 'USD' else 1 # Approximate for calc
        # Note: In a real scenario, we should pass the real exchange rate or use the one in row if available
        # But df_result already has converted values, so we can infer or pass it.
        # Let's assume we can get a rough estimate or use the implicit rate from Market Value / Quantity / Price
        
        if row['Quantity'] > 0 and row['Current Price'] > 0:
            implied_rate = row['Market Value (KRW)'] / (row['Quantity'] * row['Current Price'])
        else:
            implied_rate = 1400 if currency == 'USD' else 1
            
        # 목표 금액 계산
        target_val = total_value * (target_ratio / 100)
        
        # 차액 계산
        diff_val = target_val - current_val
        
        # 매수/매도 수량 계산
        price_krw = current_price * implied_rate
        if price_krw > 0:
            action_qty = diff_val / price_krw
            target_qty = target_val / price_krw
        else:
            action_qty = 0
            target_qty = 0
        
        # 예상 배당금 계산
        if row['Quantity'] > 0:
            div_per_share_krw = row['Annual Dividend (KRW)'] / row['Quantity']
        else:
            div_per_share_krw = 0
            if row['Current Price'] > 0:
                 div_per_share_krw = row['Current Price'] * (row['Dividend Yield (%)'] / 100) * implied_rate

        projected_div = target_qty * div_per_share_krw
        projected_total_monthly_div += (projected_div / 12)

        action = "유지"
        if abs(diff_val) > 10000: # 1만원 이상 차이
            if diff_val > 0:
                action = "매수 (Buy)"
            else:
                action = "매도 (Sell)"
        
        rebalancing_data.append({
            '종목': ticker,
            '현재 비중': f"{(current_val / total_value * 100):.1f}%",
            '목표 비중': f"{target_ratio:.1f}%",
            '목표 금액': target_val,
            '현재 금액': current_val,
            '조정 필요 금액': diff_val,
            '추천 동작': action,
            '수량': abs(action_qty)
        })
        
    return rebalancing_data, projected_total_monthly_div

def calculate_buy_only_rebalancing(df_result, total_value):
    """매도 없는 리밸런싱 (추가 매수) 계산"""
    max_implied_total = 0
    
    for _, row in df_result.iterrows():
        if row['TargetRatio'] > 0:
            implied_total = row['Market Value (KRW)'] / (row['TargetRatio'] / 100)
            if implied_total > max_implied_total:
                max_implied_total = implied_total
    
    buy_only_data = []
    total_additional_invest = 0
    
    if max_implied_total > total_value:
        for _, row in df_result.iterrows():
            ticker = row['Ticker']
            current_val = row['Market Value (KRW)']
            target_ratio = row['TargetRatio']
            current_price = row['Current Price']
            currency = row['Currency']
            
            if row['Quantity'] > 0 and row['Current Price'] > 0:
                implied_rate = row['Market Value (KRW)'] / (row['Quantity'] * row['Current Price'])
            else:
                implied_rate = 1400 if currency == 'USD' else 1
            
            new_target_val = max_implied_total * (target_ratio / 100)
            buy_needed = new_target_val - current_val
            
            price_krw = current_price * implied_rate
            if price_krw > 0:
                buy_qty = buy_needed / price_krw
            else:
                buy_qty = 0
                
            if buy_needed > 1000:
                buy_only_data.append({
                    '종목': ticker,
                    '현재 금액': current_val,
                    '추가 매수 금액': buy_needed,
                    '최종 금액': new_target_val,
                    '추가 매수 수량': buy_qty
                })
                total_additional_invest += buy_needed
                
    return buy_only_data, total_additional_invest

def check_rebalancing_proximity(df_result, total_value, threshold=5.0):
    """
    리밸런싱 근접도 체크
    
    Args:
        df_result: 포트폴리오 데이터프레임
        total_value: 총 자산 가치
        threshold: 허용 편차 (%, 기본값 5%)
    
    Returns:
        tuple: (is_near_balanced, max_deviation, deviations_dict)
    """
    if total_value == 0:
        return False, 0, {}
    
    deviations = {}
    max_deviation = 0
    
    for _, row in df_result.iterrows():
        if row['TargetRatio'] == 0:
            continue
            
        ticker = row['Ticker']
        current_ratio = (row['Market Value (KRW)'] / total_value) * 100
        target_ratio = row['TargetRatio']
        deviation = abs(current_ratio - target_ratio)
        
        deviations[ticker] = {
            'current': current_ratio,
            'target': target_ratio,
            'deviation': deviation
        }
        
        if deviation > max_deviation:
            max_deviation = deviation
    
    is_near_balanced = max_deviation <= threshold
    
    return is_near_balanced, max_deviation, deviations

def calculate_dividend_maximized_top3(df_result, additional_budget):
    """
    배당 극대화 전략으로 상위 3종목에 투자금 배분
    
    Args:
        df_result: 포트폴리오 데이터프레임
        additional_budget: 추가 투자 가능 금액
    
    Returns:
        tuple: (top3_investment_data, total_expected_annual_dividend, total_expected_monthly_dividend)
    """
    if additional_budget <= 0 or df_result.empty:
        return [], 0, 0
    
    # 배당률이 있는 종목만 필터링
    dividend_stocks = df_result[df_result['Dividend Yield (%)'] > 0].copy()
    
    if dividend_stocks.empty:
        return [], 0, 0
    
    # 배당률 기준 내림차순 정렬
    dividend_stocks = dividend_stocks.sort_values('Dividend Yield (%)', ascending=False)
    
    # 상위 3종목 선택 (또는 전체 종목이 3개 미만인 경우)
    top_stocks = dividend_stocks.head(min(3, len(dividend_stocks)))
    
    # 배당률 합계
    total_yield = top_stocks['Dividend Yield (%)'].sum()
    
    if total_yield == 0:
        return [], 0, 0
    
    investment_data = []
    total_expected_annual_div = 0
    
    for _, row in top_stocks.iterrows():
        ticker = row['Ticker']
        dividend_yield = row['Dividend Yield (%)']
        current_price = row['Current Price']
        currency = row['Currency']
        
        # 환율 계산
        if row['Quantity'] > 0 and row['Current Price'] > 0:
            implied_rate = row['Market Value (KRW)'] / (row['Quantity'] * row['Current Price'])
        else:
            implied_rate = 1400 if currency == 'USD' else 1
        
        # 가중치 계산 (배당률 비율)
        weight = dividend_yield / total_yield
        
        # 투자 금액 배분
        investment_amount = additional_budget * weight
        
        # 매수 가능 수량
        price_krw = current_price * implied_rate
        if price_krw > 0:
            buy_quantity = investment_amount / price_krw
        else:
            buy_quantity = 0
        
        # 예상 연 배당금
        expected_annual_dividend = investment_amount * (dividend_yield / 100)
        total_expected_annual_div += expected_annual_dividend
        
        investment_data.append({
            '종목': ticker,
            '배당률': dividend_yield,
            '가중치': weight * 100,
            '투자 금액': investment_amount,
            '매수 수량': buy_quantity,
            '현재가': current_price,
            '통화': currency,
            '예상 연 배당금': expected_annual_dividend,
            '예상 월 배당금': expected_annual_dividend / 12
        })
    
    total_expected_monthly_div = total_expected_annual_div / 12
    
    return investment_data, total_expected_annual_div, total_expected_monthly_div

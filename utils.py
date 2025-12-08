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

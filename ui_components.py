import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

def inject_custom_css():
    """앱 전반에 사용되는 CSS 스타일을 주입합니다."""
    st.markdown("""
    <style>
    /* Card Container */
    .card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        padding: 25px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
        transition: all 0.3s ease;
    }
    .card:hover {
        box-shadow: 0 8px 12px rgba(0, 0, 0, 0.15);
        transform: translateY(-2px);
    }
    /* Card Header */
    .card-header {
        font-size: 1.5em;
        font-weight: bold;
        color: white;
        margin-bottom: 15px;
        display: flex;
        align-items: center;
    }
    /* Card Metrics Preview */
    .card-preview {
        background: rgba(255, 255, 255, 0.15);
        border-radius: 10px;
        padding: 15px;
        backdrop-filter: blur(10px);
    }
    .metric-row {
        display: flex;
        justify-content: space-around;
        margin-top: 10px;
    }
    .metric-item {
        text-align: center;
        color: white;
    }
    .metric-label {
        font-size: 0.85em;
        opacity: 0.9;
        margin-bottom: 5px;
    }
    .metric-value {
        font-size: 1.3em;
        font-weight: bold;
    }
    /* Different card colors */
    .card-portfolio { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    .card-exchange { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
    .card-rebalancing { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
    
    @media (max-width: 768px) {
        .metric-row { flex-direction: column; }
    }
    </style>
    """, unsafe_allow_html=True)

def render_portfolio_card(total_value, total_div, current_month_total, pay_dates_html, dividend_yield_total):
    """포트폴리오 현황 카드 렌더링"""
    current_month = datetime.now().month
    st.markdown(f"""
    <div class="card card-portfolio">
        <div class="card-header">📊 포트폴리오 현황</div>
        <div class="card-preview">
            <div class="metric-row">
                <div class="metric-item">
                    <div class="metric-label">총 자산</div>
                    <div class="metric-value">₩{total_value:,.0f}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">월 평균 배당금</div>
                    <div class="metric-value">₩{total_div/12:,.0f}</div>
                </div>
            </div>
            <div class="metric-row" style="margin-top: 10px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 10px;">
                <div class="metric-item">
                    <div class="metric-label">이번 달 배당금 ({current_month}월)</div>
                    <div class="metric-value" style="color: #4CAF50;">₩{current_month_total:,.0f}</div>
                    <div style="margin-top: 5px;">{pay_dates_html}</div>
                </div>
            </div>
            <div class="metric-row">
                <div class="metric-item">
                    <div class="metric-label">배당 수익률</div>
                    <div class="metric-value">{dividend_yield_total:.2f}%</div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_exchange_card(exchange_data):
    """환율 분석 카드 렌더링"""
    if not exchange_data:
        return
        
    rsi = exchange_data['rsi']
    current_rate = exchange_data['current_price']
    change_rate = exchange_data['change_rate']
    
    st.markdown(f"""
    <div class="card card-exchange">
        <div class="card-header">💵 환율 분석</div>
        <div class="card-preview">
            <div class="metric-row">
                <div class="metric-item">
                    <div class="metric-label">USD/KRW</div>
                    <div class="metric-value">₩{current_rate:,.0f}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">RSI</div>
                    <div class="metric-value">{rsi:.1f}</div>
                </div>
            </div>
            <div class="metric-row">
                <div class="metric-item">
                    <div class="metric-label">변동률</div>
                    <div class="metric-value">{change_rate:+.2f}%</div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_monthly_dividend_chart(monthly_div_list):
    """월별 예상 배당금 차트"""
    if not monthly_div_list:
        st.info("배당 정보가 없습니다.")
        return

    monthly_df = pd.DataFrame(monthly_div_list)
    monthly_df = monthly_df.groupby(['Month', 'Ticker'])['Dividend'].sum().reset_index()
    
    current_month = datetime.now().month
    monthly_df['SortKey'] = monthly_df['Month'].apply(lambda x: x if x >= current_month else x + 12)
    monthly_df = monthly_df.sort_values('SortKey')
    monthly_df['MonthLabel'] = monthly_df['Month'].apply(lambda x: f"{x}월")
    
    fig_bar = px.bar(monthly_df, x='MonthLabel', y='Dividend', color='Ticker',
                     labels={'Dividend': '배당금 (KRW)', 'MonthLabel': '월'},
                     text_auto=',.0f')
    fig_bar.update_layout(xaxis={'categoryorder':'array', 'categoryarray': monthly_df['MonthLabel'].unique()})
    st.plotly_chart(fig_bar, use_container_width=True)

def render_portfolio_pie_chart(df_result):
    """포트폴리오 비중 파이 차트"""
    if not df_result.empty:
        fig_pie = px.pie(df_result, values='Market Value (KRW)', names='Ticker', hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

def render_exchange_chart(exchange_data, chart_style):
    """환율 차트 렌더링"""
    hist = exchange_data['history']
    fig = go.Figure()
    
    if "라인" in chart_style:
        fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], mode='lines', name='환율', line=dict(color='royalblue', width=2)))
    elif "영역" in chart_style:
        fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], mode='lines', name='환율', line=dict(color='royalblue', width=2), fill='tozeroy', fillcolor='rgba(65, 105, 225, 0.2)'))
    elif "캔들" in chart_style:
        fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name='KRW/USD'))
    elif "OHLC" in chart_style:
        fig.add_trace(go.Ohlc(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name='KRW/USD'))
    
    # 이평선 추가
    if "캔들" in chart_style or "OHLC" in chart_style:
        fig.add_trace(go.Scatter(x=hist.index, y=hist['MA20'], line=dict(color='orange', width=1), name='20일 이평선'))
        fig.add_trace(go.Scatter(x=hist.index, y=hist['MA60'], line=dict(color='green', width=1), name='60일 이평선'))
    else:
        fig.add_trace(go.Scatter(x=hist.index, y=hist['MA20'], line=dict(color='orange', width=1, dash='dot'), name='20일 이평선', opacity=0.5))
    
    fig.update_layout(
        title='원/달러 환율 추이',
        yaxis_title='환율 (KRW)',
        xaxis_rangeslider_visible=False,
        height=400,
        template='plotly_dark'
    )
    st.plotly_chart(fig, use_container_width=True)

import streamlit as st
import pandas as pd
from datetime import datetime
import utils
import data_manager
import ui_components
import streamlit.components.v1 as components

# 페이지 설정
st.set_page_config(
    page_title="배당금 캘린더 & 포트폴리오",
    page_icon="💰",
    layout="wide"
)

# PWA 지원 추가
pwa_html = """
<link rel="manifest" href="/app/static/manifest.json">
<meta name="theme-color" content="#FF4B4B">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="배당금">
<link rel="apple-touch-icon" href="/app/static/icon-192.png">
<script>
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
            navigator.serviceWorker.register('/app/static/service-worker.js')
                .then(registration => console.log('Service Worker registered'))
                .catch(err => console.log('Service Worker registration failed'));
        });
    }
</script>
"""
components.html(pwa_html, height=0)

# CSS 주입
ui_components.inject_custom_css()

# 타이틀과 업데이트 정보
col_title, col_update = st.columns([3, 1])
with col_title:
    st.title("💰 배당금 캘린더 & 포트폴리오 매니저")
with col_update:
    last_update = utils.get_last_update()
    st.markdown(f"<div style='text-align: right; padding-top: 20px; color: #888;'><small>📅 최근 업데이트: {last_update}</small></div>", unsafe_allow_html=True)

# 사이드바: 종목 추가
st.sidebar.header("포트폴리오 관리")

# 세션 상태 초기화
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = utils.load_portfolio()

# 종목 추가 입력 폼
with st.sidebar.form("add_stock_form"):
    ticker = st.text_input("종목 티커 (예: AAPL, 005930.KS)").upper()
    quantity = st.number_input("수량", min_value=0.001, value=1.0, step=0.001, format="%.3f")
    target_ratio = st.number_input("목표 비중 (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0)
    submitted = st.form_submit_button("종목 추가")

    if submitted and ticker:
        # 간단한 중복 체크 (선택 사항)
        new_row = pd.DataFrame({'Ticker': [ticker], 'Quantity': [quantity], 'TargetRatio': [target_ratio]})
        st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_row], ignore_index=True)
        utils.save_portfolio(st.session_state.portfolio)
        st.success(f"{ticker} {quantity}주 추가됨!")

# 포트폴리오가 비어있지 않으면 사이드바 목록 표시
if not st.session_state.portfolio.empty:
    st.sidebar.markdown("---")
    st.sidebar.subheader("보유 종목")
    
    # 리스트 표시 및 수정
    for i, row in st.session_state.portfolio.iterrows():
        ticker = row['Ticker']
        quantity = float(row['Quantity'])
        target_ratio = float(row.get('TargetRatio', 0.0))
        
        st.sidebar.markdown(f"**{ticker}**")
        c1, c2, c3 = st.sidebar.columns([2, 2, 1])
        
        # 수량 수정
        val = c2.number_input("수량", min_value=0.001, value=quantity, step=0.001, format="%.3f", key=f"qty_{i}_{ticker}", label_visibility="collapsed")
        
        # 목표 비중 수정
        target_val = st.sidebar.number_input(f"목표 비중 (%)", min_value=0.0, max_value=100.0, value=target_ratio, step=1.0, key=f"target_{i}_{ticker}")

        if val != row['Quantity'] or target_val != target_ratio:
            st.session_state.portfolio.at[i, 'Quantity'] = val
            st.session_state.portfolio.at[i, 'TargetRatio'] = target_val
            utils.save_portfolio(st.session_state.portfolio)
            st.rerun()
            
        if c3.button("🗑️", key=f"del_{i}_{ticker}", help="삭제"):
            st.session_state.portfolio = st.session_state.portfolio.drop(i).reset_index(drop=True)
            utils.save_portfolio(st.session_state.portfolio)
            st.rerun()
        
        st.sidebar.markdown("---")

    # 초기화 버튼
    if st.sidebar.button("포트폴리오 초기화"):
        st.session_state.portfolio = pd.DataFrame(columns=['Ticker', 'Quantity', 'TargetRatio'])
        utils.save_portfolio(st.session_state.portfolio)
        st.rerun()

    # 메인 화면: 데이터 로딩 및 표시
    with st.spinner('주가 및 배당 정보를 분석 중입니다...'):
        # Batch Data Fetching
        df_result, total_value, total_div, monthly_div_list = data_manager.fetch_stock_data_batch(st.session_state.portfolio)
        
        if not df_result.empty:
            dividend_yield_total = (total_div / total_value * 100) if total_value > 0 else 0
            
            # 이번 달 배당금 계산
            current_month = datetime.now().month
            current_month_divs = [d for d in monthly_div_list if d['Month'] == current_month]
            
            now = datetime.now()
            paid_total = sum(d['Dividend'] for d in current_month_divs if d['Date'] < now)
            expected_total = sum(d['Dividend'] for d in current_month_divs if d['Date'] >= now)
            current_month_total = paid_total + expected_total
            
            current_month_divs.sort(key=lambda x: x['Date'])
            
            # 배당금 HTML 생성
            if current_month_divs:
                pay_dates_html = ""
                for d in current_month_divs:
                    date_str = d['Date'].strftime('%m/%d')
                    t_symbol = d['Ticker']
                    amount = d['Dividend']
                    
                    if d['Date'] < now:
                        style = "color: #aaa;"
                        icon = "✅"
                    else:
                        style = "color: #fff; font-weight: bold;"
                        icon = "📅"
                        
                    pay_dates_html += f"<div style='font-size: 0.8em; {style}; display: flex; justify-content: space-between;'><span>{icon} {date_str} {t_symbol}</span> <span>₩{amount:,.0f}</span></div>"
                
                summary_html = f"""
                <div style='font-size: 0.8em; margin-top: 5px; padding-top: 5px; border-top: 1px dashed rgba(255,255,255,0.2); display: flex; justify-content: space-between; color: #ddd;'>
                    <span>✅ 지급완료:</span> <span>₩{paid_total:,.0f}</span>
                </div>
                <div style='font-size: 0.8em; display: flex; justify-content: space-between; color: #fff; font-weight: bold;'>
                    <span>📅 지급예정:</span> <span>₩{expected_total:,.0f}</span>
                </div>
                """
                pay_dates_html += summary_html
            else:
                pay_dates_html = "<div style='font-size: 0.8em; color: #888;'>배당 없음</div>"
            
            # 대시보드 레이아웃
            col1, col2, col3 = st.columns(3)
            
            with col1:
                ui_components.render_portfolio_card(total_value, total_div, current_month_total, pay_dates_html, dividend_yield_total)
                with st.expander("📊 상세 보기", expanded=False):
                    st.metric("총 자산", f"₩{total_value:,.0f}")
                    st.metric("연 배당금", f"₩{total_div:,.0f}")
                    st.markdown("#### 📊 포트폴리오 비중")
                    ui_components.render_portfolio_pie_chart(df_result)
                    
                    st.markdown("#### 📅 월별 예상 배당금")
                    ui_components.render_monthly_dividend_chart(monthly_div_list)
                    
                    st.markdown("#### 📋 보유 현황")
                    display_df = df_result[['Ticker', 'Quantity', 'Current Price', 'Market Value (KRW)', 'Annual Dividend (KRW)', 'Dividend Yield (%)']].copy()
                    display_df.columns = ['종목', '수량', '현재가', '평가액', '연 배당금', '배당률']
                    st.dataframe(display_df.style.format({
                        '현재가': '{:,.2f}',
                        '평가액': '₩{:,.0f}',
                        '연 배당금': '₩{:,.0f}',
                        '배당률': '{:.2f}%'
                    }), use_container_width=True)

            with col2:
                exchange_data = data_manager.get_exchange_rate_analysis()
                ui_components.render_exchange_card(exchange_data)
                if exchange_data:
                    with st.expander("💵 상세 보기", expanded=False):
                        st.metric("현재 환율", f"₩{exchange_data['current_price']:,.0f}", f"{exchange_data['change']:+.2f}")
                        st.metric("RSI (14일)", f"{exchange_data['rsi']:.1f}")
                        st.markdown(f"상태: :{exchange_data['rsi_color']}[**{exchange_data['rsi_status']}**]")
                        
                        chart_style = st.radio("차트 스타일", ["📈 라인", "🌊 영역", "🕯️ 캔들", "📊 OHLC"], horizontal=True, key="chart_style_exchange")
                        ui_components.render_exchange_chart(exchange_data, chart_style)

            with col3:
                # 리밸런싱 섹션
                total_target_ratio = df_result['TargetRatio'].sum()
                
                with st.expander("✨ 포트폴리오 최적화"):
                    opt_strategy = st.radio("전략 선택", ["배당 극대화", "균등 투자"], horizontal=True)
                    if st.button("적용하기"):
                        if opt_strategy == "균등 투자":
                            weight = 100 / len(df_result)
                            st.session_state.portfolio['TargetRatio'] = weight
                        elif opt_strategy == "배당 극대화":
                            total_yield = df_result['Dividend Yield (%)'].sum()
                            if total_yield > 0:
                                for _, row in df_result.iterrows():
                                    idx = st.session_state.portfolio[st.session_state.portfolio['Ticker'] == row['Ticker']].index
                                    if not idx.empty:
                                        weight = (row['Dividend Yield (%)'] / total_yield) * 100
                                        st.session_state.portfolio.at[idx[0], 'TargetRatio'] = weight
                        utils.save_portfolio(st.session_state.portfolio)
                        st.rerun()

                if total_target_ratio == 0:
                    st.warning("목표 비중을 설정해주세요.")
                else:
                    rebal_data, proj_div = utils.calculate_rebalancing(df_result, total_value)
                    
                    st.markdown("#### 📊 리밸런싱 제안")
                    df_rebal = pd.DataFrame(rebal_data)
                    st.dataframe(df_rebal[['종목', '목표 비중', '조정 필요 금액', '추천 동작']].style.format({
                        '조정 필요 금액': '{:+,.0f}'
                    }).applymap(lambda x: 'color: red' if '매도' in str(x) else 'color: green' if '매수' in str(x) else 'color: black', subset=['추천 동작']), 
                    use_container_width=True)
                    
                    st.markdown("---")
                    st.subheader("💰 추가 매수 전략 (매도 X)")
                    buy_only_data, total_add = utils.calculate_buy_only_rebalancing(df_result, total_value)
                    
                    if buy_only_data:
                        st.metric("필요 추가 투자금", f"₩{total_add:,.0f}")
                        df_buy = pd.DataFrame(buy_only_data)
                        st.dataframe(df_buy[['종목', '추가 매수 금액', '추가 매수 수량']].style.format({
                            '추가 매수 금액': '₩{:,.0f}',
                            '추가 매수 수량': '{:.2f}'
                        }), use_container_width=True)

                        # 투자 전략 가이드 (적립식 투자)
                        st.markdown("---")
                        with st.expander("💡 투자 전략 가이드 (적립식 투자)"):
                            st.markdown("#### 📅 적립식 투자 시 일별 필요 금액 (총액)")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.markdown(f"**1개월 (30일)**")
                                st.markdown(f"##### ₩{total_add/30:,.0f}")
                                st.caption("일일 투자금액")
                            with col2:
                                st.markdown(f"**3개월 (90일)**")
                                st.markdown(f"##### ₩{total_add/90:,.0f}")
                                st.caption("일일 투자금액")
                            with col3:
                                st.markdown(f"**6개월 (180일)**")
                                st.markdown(f"##### ₩{total_add/180:,.0f}")
                                st.caption("일일 투자금액")
                            
                            st.markdown("#### 📋 종목별 일 적립 금액 상세")
                            dca_breakdown = []
                            for item in buy_only_data:
                                amount = item['추가 매수 금액']
                                dca_breakdown.append({
                                    '종목': item['종목'],
                                    '1개월 (일)': amount / 30,
                                    '3개월 (일)': amount / 90,
                                    '6개월 (일)': amount / 180
                                })
                            
                            df_dca = pd.DataFrame(dca_breakdown)
                            st.dataframe(df_dca.style.format({
                                '1개월 (일)': '₩{:,.0f}',
                                '3개월 (일)': '₩{:,.0f}',
                                '6개월 (일)': '₩{:,.0f}'
                            }), use_container_width=True)
                    else:
                        st.success("추가 매수가 필요 없습니다.")
                        
            # 종목별 상세 정보
            st.markdown("---")
            st.subheader("🔍 종목별 상세 정보")
            for _, row in df_result.iterrows():
                with st.expander(f"📌 {row['Ticker']} | {row['Currency']} {row['Current Price']:,.2f}"):
                    st.write(row['Summary'])
                    c1, c2 = st.columns(2)
                    c1.metric("52주 최고", f"{row['52WeekHigh']:,.2f}")
                    c1.metric("52주 최저", f"{row['52WeekLow']:,.2f}")
                    c2.metric("Beta", f"{row['Beta']:.2f}")
                    c2.metric("목표주가", f"{row['Target Price']:,.2f}")

            # 포트폴리오 분석 및 추천 섹션
            st.markdown("---")
            st.header("🎯 포트폴리오 분석 및 추천")
            
            # 분석 지표 계산
            avg_yield = df_result['Dividend Yield (%)'].mean()
            avg_beta = df_result['Beta'].mean()
            
            # 추천/경고 카운터
            recommendations = []
            warnings = []
            
            # 1. 배당률 분석
            low_yield_stocks = df_result[df_result['Dividend Yield (%)'] < 2.0]
            if not low_yield_stocks.empty:
                warnings.append(f"⚠️ **저배당 종목**: {', '.join(low_yield_stocks['Ticker'].tolist())} (배당률 2% 미만)")
            
            # 2. 리스크 분석
            high_beta_stocks = df_result[df_result['Beta'] > 1.5]
            if not high_beta_stocks.empty:
                warnings.append(f"⚠️ **고위험 종목**: {', '.join(high_beta_stocks['Ticker'].tolist())} (Beta 1.5 이상)")
            
            # 3. 전문가 추천분석
            strong_buy = df_result[df_result['Recommendation'].str.contains('STRONG_BUY', na=False)]
            if not strong_buy.empty:
                recommendations.append(f"✅ **전문가 강력 매수 추천**: {', '.join(strong_buy['Ticker'].tolist())}")
            
            sell_stocks = df_result[df_result['Recommendation'].str.contains('SELL', na=False)]
            if not sell_stocks.empty:
                warnings.append(f"🚨 **전문가 매도 추천**: {', '.join(sell_stocks['Ticker'].tolist())}")
            
            # 4. 52주 가격 위치 분석
            near_high = []
            near_low = []
            for _, row in df_result.iterrows():
                if row['52WeekHigh'] > 0 and row['52WeekLow'] > 0:
                    range_pct = (row['Current Price'] - row['52WeekLow']) / (row['52WeekHigh'] - row['52WeekLow']) * 100
                    if range_pct > 90:
                        near_high.append(row['Ticker'])
                    elif range_pct < 10:
                        near_low.append(row['Ticker'])
            
            if near_high:
                warnings.append(f"📈 **52주 최고가 근처**: {', '.join(near_high)} (고점 매수 주의)")
            if near_low:
                recommendations.append(f"💎 **52주 최저가 근처**: {', '.join(near_low)} (저가 매수 기회)")
            
            # 탭으로 구성
            tab1, tab2, tab3 = st.tabs(["📊 종합 분석", "💡 개선 제안", "📈 성과 예측"])
            
            with tab1:
                st.markdown("#### 포트폴리오 종합 평가")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("평균 배당률", f"{avg_yield:.2f}%")
                    if avg_yield >= 4.0:
                        st.success("우수한 배당률입니다")
                    elif avg_yield >= 2.5:
                        st.info("양호한 배당률입니다")
                    else:
                        st.warning("배당률이 낮습니다")
                
                with col2:
                    st.metric("평균 Beta (위험도)", f"{avg_beta:.2f}")
                    if avg_beta < 1.0:
                        st.success("시장 대비 안정적")
                    elif avg_beta < 1.3:
                        st.info("시장 수준의 위험")
                    else:
                        st.warning("시장 대비 고위험")
                
                with col3:
                    diversification = len(df_result)
                    st.metric("종목 수", diversification)
                    if diversification >= 10:
                        st.success("잘 분산됨")
                    elif diversification >= 5:
                        st.info("적절한 분산")
                    else:
                        st.warning("분산 부족")
                
                # 추천 및 경고 표시
                if recommendations:
                    st.markdown("#### ✅ 긍정적 요소")
                    for rec in recommendations:
                        st.markdown(rec)
                
                if warnings:
                    st.markdown("#### ⚠️ 주의 사항")
                    for warn in warnings:
                        st.markdown(warn)
            
            with tab2:
                st.markdown("#### 💡 포트폴리오 개선 제안")
                
                # 배당률 기반 제안
                if avg_yield < 3.0:
                    st.info("**배당률 향상 제안**: 현재 평균 배당률이 낮습니다. 고배당 ETF (SCHD, VYM, JEPI 등)나 배당 귀족주를 고려해보세요.")
                
                # 분산 제안
                if len(df_result) < 5:
                    st.info("**분산 투자 제안**: 종목 수가 적습니다. 리스크 분산을 위해 5~10개 종목으로 늘리는 것을 권장합니다.")
                
                # 섹터 다각화 (간단한 분석)
                if len(df_result) > 3:
                    st.info("**섹터 다각화**: IT, 헬스케어, 부동산(REITs), 소비재 등 다양한 섹터에 분산 투자하면 리스크를 줄일 수 있습니다.")
                
                # 리밸런싱 제안
                if total_target_ratio > 0:
                    max_ratio = df_result['TargetRatio'].max()
                    if max_ratio > 30:
                        st.warning(f"**과도한 집중**: 특정 종목의 비중({max_ratio:.1f}%)이 너무 높습니다. 30% 이하로 유지하는 것이 안전합니다.")
                
                
                # 추천 종목 (보유 종목 제외)
                st.markdown("#### 📌 고배당 종목 추천 예시")
                
                # 추천 종목 리스트
                recommended_stocks = {
                    'SCHD': '배당 성장 중심 ETF (배당률 ~3.5%)',
                    'JEPI': '커버드콜 전략 ETF (배당률 ~7-9%)',
                    'O': '월배당 리츠 (배당률 ~5%)',
                    'VYM': '고배당 ETF (배당률 ~3%)'
                }
                
                # 보유 종목 리스트
                owned_tickers = df_result['Ticker'].tolist()
                
                # 보유하지 않은 종목만 필터링
                filtered_recommendations = {k: v for k, v in recommended_stocks.items() if k not in owned_tickers}
                
                if filtered_recommendations:
                    for ticker, description in filtered_recommendations.items():
                        st.markdown(f"- **{ticker}**: {description}")
                else:
                    st.success("✅ 추천 종목을 이미 모두 보유하고 계십니다!")
                
                st.warning("⚠️ 투자 전 반드시 본인의 투자 목적과 리스크 성향을 고려하세요.")

            
            with tab3:
                st.markdown("#### 📈 배당 수익 예측 (1년/3년/5년)")
                
                # 현재 연 배당금 기준 예측
                year1 = total_div
                year3 = total_div * 3  # 단순 누적
                year5 = total_div * 5
                
                # 배당 성장 가정 (연 5%)
                year1_growth = total_div
                year3_growth = total_div * (1.05**1 + 1.05**2 + 1.05**3)
                year5_growth = sum(total_div * (1.05**i) for i in range(1, 6))
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**배당 성장 없을 경우 (누적)**")
                    st.metric("1년", f"₩{year1:,.0f}")
                    st.metric("3년", f"₩{year3:,.0f}")
                    st.metric("5년", f"₩{year5:,.0f}")
                
                with col2:
                    st.markdown("**연 5% 배당 성장 시 (누적)**")
                    st.metric("1년", f"₩{year1_growth:,.0f}")
                    st.metric("3년", f"₩{year3_growth:,.0f}", f"+₩{year3_growth-year3:,.0f}")
                    st.metric("5년", f"₩{year5_growth:,.0f}", f"+₩{year5_growth-year5:,.0f}")
                
                st.info("💡 배당 성장률은 과거 실적을 기반으로 한 가정이며, 실제 결과는 다를 수 있습니다.")


else:
    st.info("👈 사이드바에서 종목을 추가해주세요.")
    st.markdown("""
    ### 사용 방법
    1. 사이드바에 주식 티커(예: AAPL, 005930.KS)와 수량을 입력하세요.
    2. 자동으로 주가, 배당금, 환율 정보를 가져와 분석해줍니다.
    """)

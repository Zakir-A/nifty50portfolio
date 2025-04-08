import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import numpy as np

# Set page config
st.set_page_config(page_title="NIFTY 50 Optimizer", layout="wide")

@st.cache_data
def load_stock_data():
    df = pd.read_csv("nifty50stats.csv")
    df = df.dropna()
    df['Symbol'] = df['Symbol'].str.upper()
    return df

@st.cache_data
def load_sector_mapping():
    sector_df = pd.read_csv("ind_nifty50list.csv")
    sector_df['Symbol'] = sector_df['Symbol'].str.upper()
    return sector_df.set_index('Symbol')['Industry'].to_dict()

nifty50_df = load_stock_data()
sector_mapping = load_sector_mapping()

st.title("\U0001F4CA NIFTY 50 Portfolio Optimizer")

st.markdown("""
Welcome to the NIFTY 50 Portfolio Optimizer! 

This tool helps you create a personalized investment portfolio based on your risk appetite, investment experience, and sector preferences.
""")

st.header("Step 1: Enter Your Investment Preferences")

with st.form("portfolio_form"):
    investment_amount = st.number_input("Total Investment Amount (₹)", min_value=1000, step=500)
    risk_appetite = st.selectbox("Risk Appetite", ["Low", "Moderate", "High"])
    experience_level = st.selectbox("Investment Experience", ["Beginner", "Intermediate", "Advanced"])
    submitted = st.form_submit_button("Generate Portfolio")

if submitted:
    st.header("Step 2: Portfolio Recommendation")

    with st.spinner("⏳ Fetching live data and generating portfolio..."):

        def score_stock(row, risk):
            if risk == "Low":
                return (row['ROCE %'] * 0.4) + (row['Div Yld %'] * 0.3) + (row['Qtr Sales Var %'] * 0.2) + (row['Qtr Profit Var %'] * 0.1)
            elif risk == "Moderate":
                return (row['Qtr Sales Var %'] * 0.3) + (row['Qtr Profit Var %'] * 0.3) + (row['ROCE %'] * 0.2) + (row['Div Yld %'] * 0.2)
            else:
                return (row['Qtr Profit Var %'] * 0.4) + (row['Qtr Sales Var %'] * 0.3) + (row['ROCE %'] * 0.2) + (row['Div Yld %'] * 0.1)

        nifty50_df['Risk Score'] = nifty50_df.apply(lambda row: score_stock(row, risk_appetite), axis=1)
        sorted_stocks = nifty50_df.sort_values(by='Risk Score', ascending=False).reset_index(drop=True)
        sorted_stocks['Yahoo Symbol'] = sorted_stocks['Symbol'].apply(lambda x: x + ".NS")
        all_symbols = sorted_stocks['Yahoo Symbol'].tolist()

        live_data = yf.download(tickers=' '.join(all_symbols), period='1d', group_by='ticker', progress=False)

        live_prices = {}
        for original, yahoo_sym in zip(sorted_stocks['Symbol'], sorted_stocks['Yahoo Symbol']):
            try:
                price = live_data[yahoo_sym]['Close'].iloc[-1]
                if price > 0:
                    live_prices[original] = price
            except:
                continue

        top_5_symbols = sorted_stocks.head(5)['Symbol'].tolist()
        top_5_prices = [live_prices[sym] for sym in top_5_symbols if sym in live_prices]
        avg_top5_price = np.mean(top_5_prices) if top_5_prices else 0
        min_required_investment = avg_top5_price * 5 * 1.1

        if investment_amount < min_required_investment:
            st.warning(f"⚠️ Based on current market conditions, a minimum of ₹{int(min_required_investment)} is recommended to build a meaningful portfolio.")
            st.stop()

        eligible_stocks = sorted_stocks[sorted_stocks['Symbol'].isin(live_prices.keys())].copy()
        eligible_stocks = eligible_stocks.head(20)

        max_stock_weight = {"Low": 0.35, "Moderate": 0.45, "High": 0.55}[risk_appetite]
        target_stocks = []
        total_score = 0
        used_sectors = set()

        for _, row in eligible_stocks.iterrows():
            sector = sector_mapping.get(row['Symbol'], 'N/A')
            if risk_appetite == "Low" and sector in used_sectors:
                continue
            target_stocks.append(row)
            total_score += row['Risk Score']
            used_sectors.add(sector)
            if len(target_stocks) >= {"Low": 5, "Moderate": 7, "High": 10}[risk_appetite]:
                break

        portfolio = []
        sector_allocation = {}
        remaining_cash = investment_amount

        # First pass: Allocate based on initial scoring and weights
        for row in target_stocks:
            symbol = row['Symbol']
            score = row['Risk Score']
            price = live_prices[symbol]
            weight = min(score / total_score, max_stock_weight)
            alloc_amount = investment_amount * weight
            alloc_amount = min(alloc_amount, remaining_cash)
            qty = int(alloc_amount // price)
            if qty <= 0:
                continue
            total_cost = qty * price
            remaining_cash -= total_cost
            sector = sector_mapping.get(symbol, 'N/A')
            portfolio.append({
                'Stock': symbol,
                'Live Price ₹': round(price, 2),
                'Qty': qty,
                'Total Invested ₹': round(total_cost, 2),
                'Sector': sector
            })
            sector_allocation[sector] = sector_allocation.get(sector, 0) + total_cost

        # Second pass: Try to reinvest leftover cash
        for row in target_stocks:
            if remaining_cash < min(live_prices[s['Stock']] for s in portfolio):
                break
            for stock in portfolio:
                symbol = stock['Stock']
                price = live_prices[symbol]
                if remaining_cash >= price:
                    additional_qty = int(remaining_cash // price)
                    if additional_qty > 0:
                        additional_cost = additional_qty * price
                        stock['Qty'] += additional_qty
                        stock['Total Invested ₹'] += round(additional_cost, 2)
                        remaining_cash -= additional_cost
                        sector_allocation[stock['Sector']] += additional_cost

        if not portfolio:
            st.error("❌ Could not allocate any stocks. Try increasing your investment amount.")
            st.stop()

        portfolio_df = pd.DataFrame(portfolio)
        total_invested = portfolio_df['Total Invested ₹'].sum()
        portfolio_df['Allocation %'] = round((portfolio_df['Total Invested ₹'] / total_invested) * 100, 2)

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📊 Stock Allocation Chart")
            fig1 = px.pie(
                portfolio_df,
                names='Stock',
                values='Allocation %',
                title='Stock-wise Allocation',
                color_discrete_sequence=px.colors.qualitative.Set1
            )
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            st.subheader("🏢 Sector Allocation Chart")
            sector_df = pd.DataFrame(list(sector_allocation.items()), columns=['Sector', 'Amount'])
            sector_df['Allocation %'] = (sector_df['Amount'] / total_invested) * 100
            fig2 = px.pie(
                sector_df,
                names='Sector',
                values='Allocation %',
                title='Sector-wise Allocation',
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("📑 Your Optimized Portfolio")
        st.dataframe(portfolio_df)

        st.subheader("📌 Portfolio Summary")
        st.metric("Total Invested", f"₹{round(total_invested, 2)}")
        st.metric("Leftover Cash", f"₹{round(remaining_cash, 2)}")
        st.metric("Number of Stocks", len(portfolio_df))

        csv = portfolio_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Portfolio as CSV", csv, "portfolio.csv", "text/csv", key='download-csv')

        st.success("Portfolio generated successfully with live stock data and diversified allocation!")

        # Investment Summary Table
        summary_data = {
            "Metric": ["Investment Amount (₹)", "Total Invested (₹)", "Unallocated Cash (₹)", "Number of Stocks", "Risk Profile", "Experience Level"],
            "Value": [
                f"₹{investment_amount:,.2f}",
                f"₹{total_invested:,.2f}",
                f"₹{remaining_cash:,.2f}",
                len(portfolio_df),
                risk_appetite,
                experience_level
            ]
        }

        st.subheader("📘 Investment Summary")
        st.table(pd.DataFrame(summary_data))    

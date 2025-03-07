import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf

# Page Title
st.title("📊 NIFTY 50 Portfolio Optimizer")

# Introduction
st.markdown("""
Welcome to the NIFTY 50 Portfolio Optimizer! 

This tool helps you create a personalized investment portfolio based on your risk appetite, investment experience, and sector preferences.
""")

st.header("Step 1: Enter Your Investment Preferences")

# User Input Form
with st.form("portfolio_form"):
    investment_amount = st.number_input("Total Investment Amount (₹)", min_value=1000, step=500)
    risk_appetite = st.selectbox("Risk Appetite", ["Low", "Moderate", "High"])
    experience_level = st.selectbox("Investment Experience", ["Beginner", "Intermediate", "Advanced"])
    sector_preferences = st.multiselect(
        "Preferred Sectors (optional)",
        ["IT", "FMCG", "Pharma", "Banking", "Energy", "Automobile", "Infrastructure"]
    )
    customization = st.radio("Would you like to pick stocks from recommendations?", ["Yes", "No"])
    
    submitted = st.form_submit_button("Generate Portfolio")

# Mock sector to stock mapping
sector_stock_mapping = {
    "IT": ['INFY.NS', 'TCS.NS', 'WIPRO.NS'],
    "FMCG": ['HINDUNILVR.NS', 'ITC.NS', 'NESTLEIND.NS'],
    "Pharma": ['SUNPHARMA.NS', 'DRREDDY.NS', 'CIPLA.NS'],
    "Banking": ['HDFCBANK.NS', 'ICICIBANK.NS', 'KOTAKBANK.NS'],
    "Energy": ['RELIANCE.NS', 'ONGC.NS', 'POWERGRID.NS'],
    "Automobile": ['MARUTI.NS', 'TATAMOTORS.NS', 'HEROMOTOCO.NS'],
    "Infrastructure": ['LTI.NS', 'SIEMENS.NS', 'GMRINFRA.NS']
}

# Validate stocks and filter out invalid ones
valid_sector_stock_mapping = {}
for sector, stocks in sector_stock_mapping.items():
    valid_stocks = []
    for stock in stocks:
        if not yf.Ticker(stock).history(period='1d').empty:
            valid_stocks.append(stock)
    if valid_stocks:
        valid_sector_stock_mapping[sector] = valid_stocks

if submitted:
    st.header("Step 2: Portfolio Recommendation")
    
    mock_allocations = {
        "IT": 20,
        "FMCG": 15,
        "Pharma": 10,
        "Banking": 25,
        "Energy": 15,
        "Automobile": 10,
        "Infrastructure": 5
    }
    
    if sector_preferences:
        mock_allocations = {sector: round(100/len(sector_preferences), 2) for sector in sector_preferences}
    
    portfolio_data = []
    
    for sector, allocation in mock_allocations.items():
        stock_options = valid_sector_stock_mapping.get(sector, [])
        if not stock_options:
            st.warning(f"No valid stocks found for {sector}. Skipping.")
            continue
        selected_stock = stock_options[0] if customization == "No" else st.selectbox(f"Select a stock for {sector}", stock_options)
        allocated_amount = (allocation / 100) * investment_amount
        
        stock_info = yf.Ticker(selected_stock)
        history_data = stock_info.history(period='1d')
        live_price = history_data['Close'][0] if not history_data.empty else 0.0
        
        portfolio_data.append({
            "Sector": sector,
            "Stock": selected_stock,
            "Live Price ₹": round(live_price, 2),
            "Allocation %": allocation,
            "Amount ₹": allocated_amount
        })
    
    portfolio_df = pd.DataFrame(portfolio_data)
    
    st.subheader("📑 Your Live Portfolio")
    st.dataframe(portfolio_df)

    st.subheader("📊 Sector Allocation Pie Chart (Interactive)")
    fig = px.pie(
        portfolio_df,
        names='Sector',
        values='Allocation %',
        color_discrete_sequence=px.colors.qualitative.Safe,
        hover_data=['Amount ₹'],
        title='Your Sector Allocation'
    )
    fig.update_traces(textinfo='percent+label', pull=[0.05]*len(portfolio_df))
    st.plotly_chart(fig, use_container_width=True)
    
    st.success("Portfolio generated successfully with live stock data! Future versions will monitor this portfolio dynamically.")

st.markdown("---")
st.markdown("""
### 🔮 Future Features:
- Real-time market monitoring
- Portfolio health alerts
- Automated rebalancing suggestions
- User accounts to manage and revisit portfolios
- Dynamic stock selection based on performance algorithms

### 🚀 Planned Dynamic Stock Selection Approach:
- Collect real-time data on stock performance, fundamentals, volatility, and sector strength.
- Score stocks using weighted factors (returns, volatility, fundamentals, momentum).
- Recommend top stocks dynamically based on scoring.
- Monitor and rebalance based on market movements.
""")

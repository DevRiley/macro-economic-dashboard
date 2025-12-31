import pandas as pd
import yfinance as yf
from fredapi import Fred
import datetime
import time
import numpy as np
import os
from dotenv import load_dotenv

# ==========================================
# USER SETTINGS (設定區)
# ==========================================
# Enter your API Key (請填入你的 API Key)
# Note: Use environment variables in production for security
load_dotenv()
FRED_API_KEY = os.getenv('FRED_API_KEY')

# Set time range (e.g., past 15 years) (設定時間範圍)
end_date = datetime.datetime.now()
start_date = end_date - datetime.timedelta(days=365*15)

print("--- Starting Macro ETL Pipeline (Full Calculation) (開始執行總經 ETL) ---")

# Ensure 'data' directory exists (確保 data 資料夾存在)
if not os.path.exists('data'):
    os.makedirs('data')

# ==========================================
# 1. Process FRED Macro Data (處理 FRED 總經數據)
# ==========================================
print("1. Downloading FRED Data... (正在下載 FRED 數據...)")
fred = Fred(api_key=FRED_API_KEY)

# Define Data List (Ticker : Readable Name)
fred_tickers = {
    'GDP': 'GDP',                   # Nominal GDP (Quarterly) (名目 GDP)
    'GDPC1': 'Real_GDP',            # Real GDP (For Output Gap) (實質 GDP)
    'GDPPOT': 'Real_Potential_GDP', # Real Potential GDP (For Output Gap) (實質潛在 GDP)
    'CPIAUCSL': 'CPI',              # CPI (Monthly) (消費者物價指數)
    'PCEPILFE': 'Core_PCE',         # Core PCE Inflation (Monthly) (核心 PCE 通膨)
    'FEDFUNDS': 'Fed_Rate',         # Federal Funds Rate (Monthly) (聯邦基準利率)
    'DGS10': '10Y_Yield',           # 10-Year Treasury Yield (Daily) (10年期公債殖利率)
    'DGS2': '2Y_Yield',             # 2-Year Treasury Yield (Daily) (2年期公債殖利率)
    'ICSA': 'Jobless_Claims',       # Initial Jobless Claims (Weekly) (初領失業救濟金)
    'PERMIT': 'Building_Permits',   # Building Permits (Monthly) (建築許可 - LEI成分)
    'PCEC96': 'Real_PCE',           # Real Personal Consumption (Monthly) (實質個人消費)
    'RRSFS': 'Real_Retail_Sales',   # Real Retail Sales (Monthly) (實質零售銷售)
    'M2SL': 'M2_Money_Supply',      # M2 Money Supply (Monthly) (M2 貨幣供給)
    'UMCSENT': 'Consumer_Confidence',# Consumer Sentiment (Univ. of Michigan) (消費者信心)
    'UNRATE': 'Unemployment_Rate',  # Unemployment Rate (Monthly) (失業率)
 
    # --- Leading Economic Indicators (LEI) Supplements (領先指標補強) ---
    'AWHMAN': 'Avg_Weekly_Hours',           # LEI-1: Avg Weekly Hours, Mfg (製造業平均工時)
    'ACOGNO': 'New_Orders_Consumer_Goods',  # LEI-3: New Orders, Consumer Goods (製造業消費財新訂單)
    'NEWORDER': 'New_Orders_Cap_Goods',     # LEI-5: New Orders, Non-defense Cap Goods ex Aircraft (關鍵投資指標)
    'NFCI': 'Financial_Conditions_Index'    # LEI-8: Financial Conditions Index (領先信用指數/金融情勢)
}

# Create standard calendar (normalize to 00:00:00) (建立標準日曆)
date_range = pd.date_range(start=start_date, end=end_date, freq='D', normalize=True)
df_macro = pd.DataFrame(index=date_range)

try:
    for ticker, name in fred_tickers.items():
        print(f"  - Processing {name}... (處理 {name}...)")
        
        # Fetch data (下載數據)
        series = fred.get_series(ticker, observation_start=start_date, observation_end=end_date)
        
        # Convert to DataFrame (轉成 DataFrame)
        temp_df = pd.DataFrame(series, columns=[name])
        
        # [Critical Fix] Remove timezone info for consistency (強制移除時區資訊)
        temp_df.index = pd.to_datetime(temp_df.index).tz_localize(None).normalize()
        
        # Special handling: Jobless Claims 4-week Moving Average (特殊處理: 失業金4週均線)
        if name == 'Jobless_Claims':
            temp_df['Jobless_Claims_4W_MA'] = temp_df[name].rolling(window=4).mean()
        
        # Merge to main DataFrame (合併到主表)
        df_macro = df_macro.join(temp_df, how='left')

    print("  - Performing Forward Fill... (執行數據補值...)")
    # Logic: Fill weekends/holidays with latest known data
    df_macro.ffill(inplace=True) 
    df_macro.bfill(inplace=True) # Handle initial gaps

    # ==========================================
    # 1.1 Advanced Calculations (進階計算)
    # ==========================================
    print("  - Calculating Advanced Metrics (YoY, MoM, Spreads)... (執行進階指標計算...)")

    # A. Rate of Change Calculation (YoY & MoM) (變動率計算)
    # ------------------------------------------------
    growth_metrics = ['CPI', 'Core_PCE', 'M2_Money_Supply', 'Real_PCE', 'Real_Retail_Sales', 'Building_Permits', 'GDP', 'Real_GDP', 'Avg_Weekly_Hours', 'New_Orders_Consumer_Goods', 'New_Orders_Cap_Goods']
    
    for col in growth_metrics:
        if col in df_macro.columns:
            # YoY (Year-over-Year): Compare to 365 days ago (年增率)
            df_macro[f'{col}_YoY'] = df_macro[col].pct_change(periods=365) * 100
            
            # MoM (Month-over-Month): Compare to ~30 days ago (月增率)
            # Note: Exclude quarterly GDP from MoM calculation
            if col not in ['GDP', 'Real_GDP']:
                df_macro[f'{col}_MoM'] = df_macro[col].pct_change(periods=30) * 100

    # B. Key Spreads & Derivatives (關鍵利差與衍生指標)
    # ------------------------------------------------
    
    # LEI-9: 10Y Treasury - Fed Funds Rate (Spread widening = Good, Inversion = Bad)
    df_macro['Spread_10Y_Fed'] = df_macro['10Y_Yield'] - df_macro['Fed_Rate']
    
    # 1. Yield Curve Spread (10Y - 2Y) (殖利率曲線倒掛指標)
    df_macro['Yield_Spread_10Y_2Y'] = df_macro['10Y_Yield'] - df_macro['2Y_Yield']
    
    # 2. Inversion Flag: 1 = Inverted, 0 = Normal (倒掛訊號: 1為倒掛)
    df_macro['Inversion_Flag'] = np.where(df_macro['Yield_Spread_10Y_2Y'] < 0, 1, 0)

    # 3. Real Rate = Fed Rate - Core PCE YoY (實質利率: 衡量政策緊縮程度)
    df_macro['Real_Rate'] = df_macro['Fed_Rate'] - df_macro['Core_PCE_YoY']

    # 4. Inflation Gap = Core PCE - 2% Target (通膨缺口)
    df_macro['Inflation_Gap'] = df_macro['Core_PCE_YoY'] - 2.0

    # 5. Output Gap (產出缺口)
    # Calculation: 100 * (ln(Real GDP) - ln(Real Potential GDP))
    if 'Real_GDP' in df_macro.columns and 'Real_Potential_GDP' in df_macro.columns:
        df_macro['Output_Gap'] = 100 * (np.log(df_macro['Real_GDP']) - np.log(df_macro['Real_Potential_GDP']))
    else:
        df_macro['Output_Gap'] = 0

    # 6. Taylor Rule Rate (Full Version) (完整版泰勒法則)
    # Formula: Inflation + Equilibrium Real Rate(2%) + 0.5*Inflation Gap + 0.5*Output Gap
    df_macro['Taylor_Rule_Rate'] = (df_macro['Core_PCE_YoY'] + 2.0 + 
                                    0.5 * (df_macro['Inflation_Gap']) + 
                                    0.5 * df_macro['Output_Gap'])

    # Export Macro Data (輸出總經數據)
    df_macro.index.name = 'Date'
    df_macro.reset_index(inplace=True)
    
    # Save to data/ directory
    df_macro.to_csv('data/macro_data.csv', index=False)
    print(f"✅ Macro Data Calculation Complete: data/macro_data.csv")

except Exception as e:
    print(f"❌ FRED Process Failed: {e} (FRED 處理失敗)")
    print("Please check your API Key. (請檢查 API Key)")

# ==========================================
# 2. Process Market Data (Yahoo Finance) (處理市場數據)
# ==========================================
print("\n2. Downloading Market Data (Yahoo Finance)... (正在下載市場數據...)")

yahoo_tickers = {
    'EURUSD=X': 'EUR_USD',
    'GBPUSD=X': 'GBP_USD',
    'JPY=X': 'USD_JPY',     # USD/JPY
    'DX-Y.NYB': 'DXY',      # US Dollar Index (美元指數)
    'CL=F': 'Crude_Oil_WTI',# WTI Crude Oil (原油)
    'HG=F': 'Copper',       # Copper Futures (銅)
    'GC=F': 'Gold',         # Gold Futures (黃金)
    '^GSPC': 'SP500',       # S&P 500 Index
    '^IXIC': 'Nasdaq',      # Nasdaq Composite (納斯達克)
    '^VIX': 'VIX'           # Volatility Index (恐慌指數)
}

try:
    # Fetch Data
    df_market = yf.download(list(yahoo_tickers.keys()), start=start_date, end=end_date)['Close']
    df_market.rename(columns=yahoo_tickers, inplace=True)
    
    # Fill missing values (handle weekends/holidays) (補值)
    df_market.ffill(inplace=True)
    df_market.bfill(inplace=True)
    
    # ==========================================
    # 2.1 Market Indicators Calculation (市場指標計算)
    # ==========================================
    
    # 1. Moving Averages (MA) (均線)
    if 'SP500' in df_market.columns:
        df_market['SP500_MA50'] = df_market['SP500'].rolling(window=50).mean()
        df_market['SP500_MA200'] = df_market['SP500'].rolling(window=200).mean()
        
        # 2. Bias (Deviation from MA200) (乖離率)
        # Logic: (Price - MA200) / MA200
        df_market['SP500_Bias_200'] = (df_market['SP500'] - df_market['SP500_MA200']) / df_market['SP500_MA200'] * 100

    # 3. Gold/Oil Ratio (Risk Indicator) (金油比)
    if 'Gold' in df_market.columns and 'Crude_Oil_WTI' in df_market.columns:
        df_market['Gold_Oil_Ratio'] = df_market['Gold'] / df_market['Crude_Oil_WTI']

    # 4. Copper/Gold Ratio (Economic Sentiment) (銅金比)
    # Copper = Industry Demand, Gold = Safe Haven. Rising ratio = Economic Growth.
    if 'Copper' in df_market.columns and 'Gold' in df_market.columns:
        df_market['Copper_Gold_Ratio'] = (df_market['Copper'] * 1000) / df_market['Gold'] # Unit adjustment

    # Export Market Data (輸出市場數據)
    df_market.reset_index(inplace=True)
    
    # Fix for yfinance MultiIndex columns if present (修正多層索引)
    if isinstance(df_market.columns, pd.MultiIndex):
         df_market.columns = df_market.columns.get_level_values(0)

    # Save to data/ directory
    df_market.to_csv('data/market_data.csv', index=False)
    print(f"✅ Market Data Calculation Complete: data/market_data.csv")

except Exception as e:
    print(f"❌ Yahoo Process Failed: {e} (Yahoo 處理失敗)")

print("\n--- All ETL Tasks Completed Successfully (全部作業完成) ---")
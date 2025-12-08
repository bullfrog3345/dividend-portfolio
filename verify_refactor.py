import sys
import os
import pandas as pd

# Add the directory to path to import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import utils
    import data_manager
    import ui_components
    print("✅ All modules imported successfully.")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Test data fetching
print("Testing data fetching...")
test_portfolio = pd.DataFrame({
    'Ticker': ['AAPL', 'O'],
    'Quantity': [1, 1],
    'TargetRatio': [50, 50]
})

try:
    df, val, div, monthly = data_manager.fetch_stock_data_batch(test_portfolio)
    print(f"✅ Data fetched. Total Value: {val}, Annual Div: {div}")
    print(df[['Ticker', 'Current Price', 'Market Value (KRW)']])
except Exception as e:
    print(f"❌ Data fetching failed: {e}")

# Test rebalancing calc
print("\nTesting rebalancing calculation...")
try:
    rebal, proj = utils.calculate_rebalancing(df, val)
    print(f"✅ Rebalancing calculated. Projected Monthly Div: {proj}")
except Exception as e:
    print(f"❌ Rebalancing calculation failed: {e}")

import requests
import pandas as pd
from typing import Dict, Optional

class RENDataHub:
    BASE_URL = "https://servicebus.ren.pt/datahubapi"
    
    def __init__(self, lang="pt-PT"):
        self.lang = lang
        self.session = requests.Session()
    
    def _make_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        params["culture"] = self.lang
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Erro ao consultar API REN: {e}")
            return None    
    
    def get_monthly_price(self, year: int, month: int) -> pd.DataFrame:
        """
        Get monthly electricity market prices from REN API.
        Returns DataFrame with columns for PT and ES markets.
        """
        data = self._make_request(
            "electricity/ElectricityMarketPricesMonthly",
            {"year": str(year), "month": f"{month:02d}"}
        )
        
        if not data:
            return pd.DataFrame()
        
        # Debug
        print(f"\n=== REN API Response Structure for {year}-{month:02d} ===")
        if isinstance(data, list) and len(data) > 0:
            print(f"Number of records: {len(data)}")
            print(f"First record keys: {list(data[0].keys())}")
            print(f"First record: {data[0]}")
        elif isinstance(data, dict):
            print(f"Response keys: {list(data.keys())}")
            print(f"Response: {data}")
        
        return pd.DataFrame(data) if data else pd.DataFrame()
    
    def get_pt_average_price(self, year: int, month: int) -> Optional[float]:
        """
        Get the average electricity price for Portugal (PT) in €/MWh.
        Returns None if data is unavailable.
        
        The API returns: {'fevereiro': {'PT': {'Preço Médio': 39.86, ...}, ...}}
        """
        data = self._make_request(
            "electricity/ElectricityMarketPricesMonthly",
            {"year": str(year), "month": f"{month:02d}"}
        )
        
        if not data:
            print(f"No data available for {year}-{month:02d}")
            return None
        
        # Debug output
        print(f"\n=== Parsing REN data for {year}-{month:02d} ===")
        

        month_names = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
                       'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
        
        # Get the month name key
        month_key = None
        for key in data.keys():
            if key.lower() in month_names:
                month_key = key
                break
        
        if not month_key:
            print(f"Could not find month key in response. Keys: {list(data.keys())}")
            return None
        
        month_data = data[month_key]
        print(f"Month key: '{month_key}'")
        
        # Extract PT data
        if 'PT' not in month_data:
            print(f"'PT' key not found in month data. Keys: {list(month_data.keys())}")
            return None
        
        pt_data = month_data['PT']
        print(f"PT data: {pt_data}")
        
        # Extract average price
        if 'Preço Médio' not in pt_data:
            print(f"'Preço Médio' not found in PT data. Keys: {list(pt_data.keys())}")
            return None
        
        price = float(pt_data['Preço Médio'])
        print(f"✓ Found PT average price: {price} €/MWh")
        
        return price


# Test code (only runs if this file is executed directly to debug)
if __name__ == "__main__":
    ren = RENDataHub()
    
    # Test getting raw data
    print("\n" + "="*50)
    print("Testing REN API for February 2024")
    print("="*50)
    df = ren.get_monthly_price(2024, 2)
    
    # Test getting average price
    print("\n" + "="*50)
    print("Testing average price extraction")
    print("="*50)
    price = ren.get_pt_average_price(2024, 2)
    
    if price:
        print(f"\n✓ Success! Average PT price: {price} €/MWh")
        print(f"  Converted to €/kWh: {price/1000:.4f}")
    else:
        print("\n✗ Could not extract price from API response")
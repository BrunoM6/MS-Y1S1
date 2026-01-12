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
            print(f"Error fetching from REN API: {e}")
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

        # Extract PT data
        if 'PT' not in month_data:
            print(f"'PT' key not found in month data. Keys: {list(month_data.keys())}")
            return None
        
        pt_data = month_data['PT']

        # Extract average price
        if 'Preço Médio' not in pt_data:
            print(f"'Preço Médio' not found in PT data. Keys: {list(pt_data.keys())}")
            return None
        
        price = float(pt_data['Preço Médio'])

        return price
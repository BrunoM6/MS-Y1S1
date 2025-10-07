import requests
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Optional, Dict, List

class RENDataHub:
    BASE_URL = "https://servicebus.ren.pt/datahubapi"

    def __init__(self, lang = "pt-PT"):
        self.lang = lang
        self.session = requests.Session()

    def _make_request(self, endpoint: str, params: Dict) -> Dict:
        params["culture"] = self.lang
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Erro ao consultar API: {e}")
        return None    

    def get_monthly_price(self, year: int, month: int) -> pd.DataFrame:
        data = self._make_request(
            "electricity/ElectricityMarketPricesMonthly",
            {"year": str(year), "month": f"{month:02d}"}
        )
        return pd.DataFrame(data) if data else pd.DataFrame()
    
ren = RENDataHub()
print(ren.get_monthly_price(2024, 2))
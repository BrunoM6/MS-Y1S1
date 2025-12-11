import requests
import calendar
from typing import List, Optional

class WeatherService:
    # Porto Coordinates
    LAT = 41.1579
    LON = -8.6291
    
    @staticmethod
    def get_hourly_temperatures(year: int, month: int) -> Optional[List[float]]:
        # Fetches historical hourly temperature (2m) for Porto from Open-Meteo for the entire specified month.
        try:
            # Determine start and end date of the month
            _, last_day = calendar.monthrange(year, month)
            start_date = f"{year}-{month:02d}-01"
            end_date = f"{year}-{month:02d}-{last_day}"

            url = "https://archive-api.open-meteo.com/v1/archive"
            
            params = {
                "latitude": WeatherService.LAT,
                "longitude": WeatherService.LON,
                "start_date": start_date,
                "end_date": end_date,
                "hourly": "temperature_2m",
                "timezone": "auto" # Handles local time adjustments
            }

            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if "hourly" in data and "temperature_2m" in data["hourly"]:
                temps = data["hourly"]["temperature_2m"]
                print(f"✓ Fetched {len(temps)} hours of weather data for Porto ({start_date})")
                return temps
            
            return None

        except Exception as e:
            print(f"Error fetching weather data: {e}")
            return None
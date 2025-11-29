from mesa import Model
from mesa.time import RandomActivation
from mesa.datacollection import DataCollector
import random
import numpy as np
from dataclasses import dataclass
from typing import List, Dict
from enums import ApplianceType
from house import House
from ren import RENDataHub

@dataclass
class WeatherCondition:
    temperature: float
    solar_radiation: float
    hour_of_day: int
    is_extreme_event: bool = False

class ResidentialEnergyModel(Model):
    def __init__(self, n_kitchens: int = 1, n_living_rooms: int = 1, n_bedrooms: int = 2, 
                 n_bathrooms: int = 1, n_hallways: int = 1, n_occupants: int = 2, 
                 avg_insulation_quality: float = 0.5, simulation_days: int = 5, 
                 energy_price_per_kwh: float = 0.15, weather_scenario: str = "normal", 
                 smart_appliances: str = "base", ren_month: str = "2024-02"):
        super().__init__()
        self.simulation_days = simulation_days
        self.weather_scenario = weather_scenario
        self.smart_appliances = smart_appliances
        self.ren_month = ren_month

        # Fetch real price from REN API based on selected month
        self.energy_price_per_kwh = self._fetch_ren_price(ren_month)
        print(f"Using REN price for {ren_month}: €{self.energy_price_per_kwh:.4f}/kWh")

        self.current_day = 0
        self.hour_of_day = 0
        self.steps_per_day = 24

        # UI control
        self.running = True
        self.total_steps_run = 0
        self.total_steps_allowed = self.simulation_days * self.steps_per_day

        self.total_energy_consumed = 0.0
        self.daily_consumption = []
        self.consumption_by_appliance = {at: 0.0 for at in ApplianceType}

        self.base_temperature = 15.0
        self.schedule = RandomActivation(self)

        self.n_occupants = n_occupants
        self.insulation = max(0.1, min(1.0, random.gauss(avg_insulation_quality, 0.15)))

        self.house = House(self.next_id(), self, self.n_occupants, self.insulation, 
                          n_kitchens, n_living_rooms, n_bedrooms, n_bathrooms, 
                          n_hallways, self.smart_appliances)
        self.schedule.add(self.house)

        self.datacollector = DataCollector(
            model_reporters={
                "Total Energy (kWh)": lambda m: m.total_energy_consumed,
                "Average House Temp": lambda m: np.mean([
                    room.temperature
                    for room in m.house.rooms
                ]),
                "External Temperature": lambda m: m.get_current_weather().temperature,
                "Hour of Day": lambda m: m.hour_of_day,
                "Day": lambda m: m.current_day,
                "Energy Cost (€)": lambda m: m.total_energy_consumed * m.energy_price_per_kwh
            }
        )

    def _fetch_ren_price(self, ren_month: str) -> float:
        """
        Fetch electricity price from REN API for the specified month
        Format: "YYYY-MM"
        """
        try:
            year, month = map(int, ren_month.split('-'))
            ren = RENDataHub()
            
            # Use the new method that specifically gets PT average price
            avg_price_mwh = ren.get_pt_average_price(year, month)
            
            if avg_price_mwh is None:
                print(f"No REN data for {ren_month}, using default price of 0.15 €/kWh")
                return 0.15
            
            # Convert from €/MWh to €/kWh
            avg_price_kwh = avg_price_mwh / 1000
            
            if 0.01 <= avg_price_kwh <= 1.0:
                print(f"✓ Successfully fetched REN price: {avg_price_mwh:.2f} €/MWh = {avg_price_kwh:.4f} €/kWh")
                return round(avg_price_kwh, 4)
            else:
                print(f"REN price {avg_price_kwh} €/kWh out of expected range (0.01-1.0), using default")
                return 0.15
                
        except Exception as e:
            print(f"Error fetching REN price: {e}")
            import traceback
            traceback.print_exc()
            return 0.15

    def get_current_weather(self) -> WeatherCondition:
        hour = self.hour_of_day
        day = self.current_day
        daily_variation = 5 * np.sin((hour - 6) * np.pi / 12)

        if self.weather_scenario == "heatwave":
            base_temp = 35.0
            is_extreme = True
        elif self.weather_scenario == "cold_snap":
            base_temp = -5.0
            is_extreme = True
        else:
            base_temp = self.base_temperature + 5 * np.sin(day * np.pi / 15)
            is_extreme = False

        temperature = base_temp + daily_variation + random.gauss(0, 2)
        solar_radiation = max(0, 800 * np.sin((hour - 6) * np.pi / 12))
        return WeatherCondition(temperature, solar_radiation, hour, is_extreme)

    def step(self):
        self.schedule.step()
        self.datacollector.collect(self)

        # Check if simulation should continue
        self.total_steps_run += 1
        if self.total_steps_run >= self.total_steps_allowed:
            self.running = False

        self.hour_of_day = (self.hour_of_day + 1) % 24
        if self.hour_of_day == 0:
            self.current_day += 1
            self.daily_consumption.append(self.total_energy_consumed)

    def run_simulation(self):
        total_steps = self.simulation_days * self.steps_per_day
        for _ in range(total_steps):
            # Stop if the model is no longer running
            if not self.running:
                break
            self.step()

    def get_summary_statistics(self) -> Dict:
        self.consumption_by_appliance = {at: 0.0 for at in ApplianceType}
        for room in self.house.rooms:
            for appliance in room.appliances:
                self.consumption_by_appliance[appliance.appliance_type] += appliance.total_consumption

        avg_daily = np.mean(self.daily_consumption) if self.daily_consumption else 0
        total_cost = self.total_energy_consumed * self.energy_price_per_kwh

        return {
            "total_energy_kwh": round(self.total_energy_consumed, 2),
            "avg_daily_consumption_kwh": round(avg_daily, 2),
            "total_cost_euros": round(total_cost, 2),
            "avg_monthly_cost_euros": round(total_cost / self.simulation_days * 30, 2) if self.simulation_days else 0,
            "consumption_by_appliance": {
                k.value: round(v, 2)
                for k, v in self.consumption_by_appliance.items()
                if v > 0
            },
            "simulation_days": self.simulation_days,
            "ren_month": self.ren_month,
            "energy_price_kwh": self.energy_price_per_kwh
        }
from mesa import Model
from mesa.time import RandomActivation
from mesa.datacollection import DataCollector
import random
import numpy as np
from dataclasses import dataclass
from typing import Dict

from meteo import WeatherService
from enums import ApplianceType
from house import House
from ren import RENDataHub

@dataclass
class WeatherCondition:
    """
    Represents the weather conditions at a given time.

    Attributes:
        temperature (float): The external temperature in degrees Celsius.
        solar_radiation (float): The solar radiation in W/m².
        hour_of_day (int): The current hour of the day (0-23).
        is_extreme_event (bool): Indicates if the current weather is part of an extreme event
    """
    temperature: float
    solar_radiation: float
    hour_of_day: int
    is_extreme_event: bool = False

"""
This module contains the main ResidentialEnergyModel class which simulates energy consumption
in a residential building based on various parameters such as number of rooms, occupants,
insulation quality, weather conditions, and appliance smartness levels.
"""

class ResidentialEnergyModel(Model):
    """
    Main Agent-Based Model for simulating residential energy consumption.

    Attributes:
        total_energy_consumed (float): Cumulative energy consumed in kWh.
        current_day (int): Current day in the simulation.
        hour_of_day (int): Current hour of the day (0-23).
        steps_per_day (int): Number of simulation steps per day.
        total_steps_run (int): Total simulation steps executed.
        daily_consumption (list): List of daily energy consumption values.
        consumption_by_appliance (dict): Energy consumption breakdown by appliance type.
        running (bool): Indicates if the simulation is still running.
        simulation_days (int): Total number of days to simulate.
        total_steps_allowed (int): Total simulation steps allowed.
        weather_scenario (str): Weather scenario type ("normal", "heatwave", "cold_snap").
        smart_appliances (str): Level of smart appliances ("base", "advanced", "none").
        ren_month (str): Month for REN price data in "YYYY-MM" format.
        n_occupants (int): Number of occupants in the house.
        energy_price_per_kwh (float): Energy price per kWh in Euros, retrieved from Open_Meteo.
    """
    def __init__(self, n_kitchens: int = 1, n_living_rooms: int = 1, n_bedrooms: int = 2, 
                 n_bathrooms: int = 1, n_hallways: int = 1, n_occupants: int = 2, 
                 avg_insulation_quality: float = 0.5, simulation_days: int = 5, weather_scenario: str = "normal",
                 smart_appliances: str = "base", ren_month: str = "2024-02"):
        """Initialize the Residential Energy Model with given parameters."""
        super().__init__()

        self.total_energy_consumed = 0.0
        self.current_day = 0
        self.hour_of_day = 0
        self.steps_per_day = 24
        self.total_steps_run = 0
        self.daily_consumption = []
        self.consumption_by_appliance = {at: 0.0 for at in ApplianceType}
        self.running = True
        
        self.simulation_days = simulation_days
        self.total_steps_allowed = self.simulation_days * self.steps_per_day
        self.weather_scenario = weather_scenario
        self.smart_appliances = smart_appliances
        self.ren_month = ren_month
        self.n_occupants = n_occupants

        # Fetch external data (price)
        self.energy_price_per_kwh = self._fetch_ren_price(ren_month)

        self.schedule = RandomActivation(self)
        self.avg_insulation_quality = avg_insulation_quality
        # Randomize insulation slightly around the slider value
        self.insulation = max(0.1, min(1.0, random.gauss(avg_insulation_quality, 0.15)))
        self.base_temperature = 15.0

        self.house = House(self.next_id(), self, self.n_occupants, self.insulation, 
                          n_kitchens, n_living_rooms, n_bedrooms, n_bathrooms, 
                          n_hallways, self.smart_appliances)
        self.schedule.add(self.house)

        self._generate_weather_profile()

        self.datacollector = DataCollector(
            model_reporters={
                "Total Energy (kWh)": lambda m: m.total_energy_consumed,
                "Average House Temp": lambda m: np.mean([r.temperature for r in m.house.rooms]),
                "External Temperature": lambda m: m.get_current_weather().temperature,
                "Energy Cost (€)": lambda m: m.total_energy_consumed * m.energy_price_per_kwh
            }
        )

    def _generate_weather_profile(self):
        """Generate temperature profile for the simulation duration."""
        total_simulation_hours = self.simulation_days * 24
        self.is_extreme = False
        
        # Scenario 1: Synthetic Heatwave
        if self.weather_scenario == "heatwave":
            base_temps = np.full(total_simulation_hours + 24, 35.0)
            self.weather_temps = base_temps + np.random.normal(0, 1, len(base_temps))
            self.is_extreme = True
            return

        # Scenario 2: Synthetic Cold Snap
        elif self.weather_scenario == "cold_snap":
            base_temps = np.full(total_simulation_hours + 24, -2.0)
            self.weather_temps = base_temps + np.random.normal(0, 1, len(base_temps))
            self.is_extreme = True
            return

        # Scenario 3: Real Data (Normal)
        real_temps = []
        try:
            year, month = map(int, self.ren_month.split('-'))
            real_temps = WeatherService.get_hourly_temperatures(year, month)
        except Exception as e:
            print(f"Weather fetch warning: {e}")

        if real_temps and len(real_temps) > 0:
            # Loop data if simulation is longer than data
            if len(real_temps) < total_simulation_hours:
                factor = (total_simulation_hours // len(real_temps)) + 1
                real_temps = real_temps * factor
            
            self.weather_temps = np.array(real_temps[:total_simulation_hours + 24])
        else:
            # Fallback Synthetic
            print("Using Synthetic Normal profile.")
            days = np.arange(self.simulation_days + 1)
            base_temps_daily = 15.0 + 5 * np.sin(days * np.pi / 15)
            
            all_hours = np.arange(total_simulation_hours + 24)
            daily_hours = np.arange(self.simulation_days + 1) * 24
            base_temp_hourly = np.interp(all_hours, daily_hours, base_temps_daily)
            
            # Day/Night cycle
            hours_in_cycle = all_hours % 24
            daily_variation = 5 * np.sin((hours_in_cycle - 6) * np.pi / 12)
            
            self.weather_temps = base_temp_hourly + daily_variation + np.random.normal(0, 0.5, len(all_hours))

    def _fetch_ren_price(self, ren_month: str) -> float:
        """Fetch eletricity price from REN API for the given month."""
        try:
            year, month = map(int, ren_month.split('-'))
            ren = RENDataHub()
            avg_price_mwh = ren.get_pt_average_price(year, month)
            if avg_price_mwh is None: return 0.15
            return round(avg_price_mwh / 1000, 4)
        except:
            return 0.15

    def get_current_weather(self) -> WeatherCondition:
        """Get the current weather condition based on the simulation time."""
        hour = self.hour_of_day
        current_hour_index = self.current_day * 24 + hour
        idx = min(current_hour_index, len(self.weather_temps) - 1)
        temperature = self.weather_temps[idx]
        solar_radiation = max(0, 800 * np.sin((hour - 6) * np.pi / 12))
        return WeatherCondition(temperature, solar_radiation, hour, self.is_extreme)

    def step(self):
        """Advance the model by one step (one hour)."""
        self.schedule.step()
        self.datacollector.collect(self)
        self.total_steps_run += 1
        
        if self.total_steps_run >= self.total_steps_allowed:
            self.running = False
            
        self.hour_of_day = (self.hour_of_day + 1) % 24
        if self.hour_of_day == 0:
            self.current_day += 1
            self.daily_consumption.append(self.total_energy_consumed)
            
    def run_simulation(self):
        """Run the simulation until completion."""
        while self.running:
            self.step()

    # Required for Interface text element
    def get_summary_statistics(self) -> Dict:
        """Return summary statistics of the simulation."""
        return {
            "total_energy_kwh": self.total_energy_consumed,
        }
import mesa
import random
import numpy as np
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class WeatherCondition:
    temperature: float # C
    solar_radiation: float # W/m^2
    hour_of_day: int
    is_extreme_event: bool = False

class ResidentialEnergyModel(mesa.Model):
    """
    Mesa model for residential building energy consumption simulation.
    
    This is a descriptive and speculative model that simulates energy consumption
    patterns in residential buildings by modeling interactions between occupants,
    appliances, building characteristics, and weather conditions.
    """
    
    def __init__(
        self,
        num_houses: int = 5,
        avg_occupants_per_house: int = 2,
        avg_insulation_quality: float = 0.5,
        simulation_days: int = 30,
        energy_price_per_kwh: float = 0.15,
        weather_scenario: str = "normal"
    ):
        super().__init__()
        self.num_houses = num_houses
        self.simulation_days = simulation_days
        self.energy_price_per_kwh = energy_price_per_kwh
        self.weather_scenario = weather_scenario
        
        # Time tracking
        self.current_day = 0
        self.hour_of_day = 0
        self.steps_per_day = 24  # 1 step = 1 hour
        
        # Energy metrics
        self.total_energy_consumed = 0.0
        self.daily_consumption = []
        self.consumption_by_appliance = {at: 0.0 for at in ApplianceType}
        
        # Weather conditions
        self.base_temperature = 15.0  # Base outdoor temperature
        
        # Scheduler
        self.schedule = mesa.time.RandomActivation(self)
        
        # Create houses
        self.houses: List[House] = []
        for i in range(num_houses):
            num_occupants = max(1, int(random.gauss(avg_occupants_per_house, 0.5)))
            insulation = max(0.1, min(1.0, random.gauss(avg_insulation_quality, 0.15)))
            house = House(self.next_id(), self, num_occupants, insulation)
            self.houses.append(house)
            self.schedule.add(house)
        
        # Data collector
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Total Energy (kWh)": lambda m: m.total_energy_consumed,
                "Average House Temp": lambda m: np.mean([
                    room.temperature 
                    for house in m.houses 
                    for room in house.rooms
                ]),
                "External Temperature": lambda m: m.get_current_weather().temperature,
                "Hour of Day": lambda m: m.hour_of_day,
                "Day": lambda m: m.current_day,
                "Energy Cost (€)": lambda m: m.total_energy_consumed * m.energy_price_per_kwh
            }
        )
    
    def get_current_weather(self) -> WeatherCondition:
        """Generate current weather conditions based on scenario"""
        hour = self.hour_of_day
        day = self.current_day
        
        # Base temperature varies by time of day
        daily_variation = 5 * np.sin((hour - 6) * np.pi / 12)
        
        # Weather scenarios
        if self.weather_scenario == "heatwave":
            base_temp = 35.0
            is_extreme = True
        elif self.weather_scenario == "cold_snap":
            base_temp = -5.0
            is_extreme = True
        else:  # normal
            base_temp = self.base_temperature + 5 * np.sin(day * np.pi / 15)
            is_extreme = False
        
        temperature = base_temp + daily_variation + random.gauss(0, 2)
        
        # Solar radiation (higher during day)
        solar_radiation = max(0, 800 * np.sin((hour - 6) * np.pi / 12))
        
        return WeatherCondition(temperature, solar_radiation, hour, is_extreme)
    
    def step(self):
        """Advance the model by one step (1 hour)"""
        self.schedule.step()
        self.datacollector.collect(self)
        
        # Update time
        self.hour_of_day = (self.hour_of_day + 1) % 24
        if self.hour_of_day == 0:
            self.current_day += 1
            self.daily_consumption.append(self.total_energy_consumed)
    
    def run_simulation(self):
        """Run the full simulation"""
        total_steps = self.simulation_days * self.steps_per_day
        for _ in range(total_steps):
            self.step()
    
    def get_summary_statistics(self) -> Dict:
        """Get summary statistics from the simulation"""
        df = self.datacollector.get_model_vars_dataframe()
        
        # Calculate consumption by appliance type
        for house in self.houses:
            for room in house.rooms:
                for appliance in room.appliances:
                    self.consumption_by_appliance[appliance.appliance_type] += appliance.total_consumption
        
        avg_daily = np.mean(self.daily_consumption) if self.daily_consumption else 0
        total_cost = self.total_energy_consumed * self.energy_price_per_kwh
        
        return {
            "total_energy_kwh": round(self.total_energy_consumed, 2),
            "avg_daily_consumption_kwh": round(avg_daily, 2),
            "total_cost_euros": round(total_cost, 2),
            "avg_monthly_cost_euros": round(total_cost / self.simulation_days * 30, 2),
            "consumption_by_appliance": {
                k.value: round(v, 2) 
                for k, v in self.consumption_by_appliance.items() 
                if v > 0
            },
            "simulation_days": self.simulation_days,
            "num_houses": self.num_houses
        }


# Example usage
if __name__ == "__main__":
    print("=== Residential Energy Consumption Simulation ===\n")
    
    # Scenario 1: Normal conditions (Baseline)
    print("Scenario 1: Normal Weather Conditions (Baseline)")
    model_baseline = ResidentialEnergyModel(
        num_houses=5,
        avg_occupants_per_house=2,
        avg_insulation_quality=0.5,
        simulation_days=30,
        energy_price_per_kwh=0.15,
        weather_scenario="normal"
    )
    model_baseline.run_simulation()
    stats_baseline = model_baseline.get_summary_statistics()
    print(f"Total Energy Consumed: {stats_baseline['total_energy_kwh']} kWh")
    print(f"Average Daily Consumption: {stats_baseline['avg_daily_consumption_kwh']} kWh")
    print(f"Average Monthly Cost: €{stats_baseline['avg_monthly_cost_euros']}")
    print(f"Top Consumers: {list(stats_baseline['consumption_by_appliance'].items())[:3]}\n")
    
    # Scenario 2: Heatwave (Speculative)
    print("Scenario 2: Heatwave Event (Speculative)")
    model_heatwave = ResidentialEnergyModel(
        num_houses=5,
        avg_occupants_per_house=2,
        avg_insulation_quality=0.5,
        simulation_days=30,
        energy_price_per_kwh=0.15,
        weather_scenario="heatwave"
    )
    model_heatwave.run_simulation()
    stats_heatwave = model_heatwave.get_summary_statistics()
    print(f"Total Energy Consumed: {stats_heatwave['total_energy_kwh']} kWh")
    print(f"Average Monthly Cost: €{stats_heatwave['avg_monthly_cost_euros']}")
    increase = ((stats_heatwave['total_energy_kwh'] - stats_baseline['total_energy_kwh']) 
                / stats_baseline['total_energy_kwh'] * 100)
    print(f"Increase vs Baseline: {increase:.1f}%\n")
    
    # Scenario 3: Better insulation (Prescriptive)
    print("Scenario 3: Improved Insulation (Prescriptive)")
    model_efficient = ResidentialEnergyModel(
        num_houses=5,
        avg_occupants_per_house=2,
        avg_insulation_quality=0.8,  # Better insulation
        simulation_days=30,
        energy_price_per_kwh=0.15,
        weather_scenario="normal"
    )
    model_efficient.run_simulation()
    stats_efficient = model_efficient.get_summary_statistics()
    print(f"Total Energy Consumed: {stats_efficient['total_energy_kwh']} kWh")
    print(f"Average Monthly Cost: €{stats_efficient['avg_monthly_cost_euros']}")
    reduction = ((stats_baseline['total_energy_kwh'] - stats_efficient['total_energy_kwh']) 
                 / stats_baseline['total_energy_kwh'] * 100)
    print(f"Reduction vs Baseline: {reduction:.1f}%")
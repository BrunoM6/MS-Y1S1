from mesa.visualization.ModularVisualization import ModularServer
from mesa.visualization.modules import ChartModule, TextElement
from mesa.visualization.UserParam import Slider, Choice
from world import ResidentialEnergyModel

class StatusElement(TextElement):
    def render(self, model):
        return f"Day: {model.current_day}  Hour: {model.hour_of_day}  Total kWh: {model.total_energy_consumed:.2f}"

# Chart modules that match the keys in ResidentialEnergyModel.datacollector
energy_chart = ChartModule(
    [{"Label": "Total Energy (kWh)", "Color": "#d62728"}],
    data_collector_name='datacollector'
)
temp_chart = ChartModule(
    [{"Label": "Average House Temp", "Color": "#1f77b4"}],
    data_collector_name='datacollector'
)
outside_temp_chart = ChartModule(
    [{"Label": "External Temperature", "Color": "#ffff0e"}],
    data_collector_name='datacollector'
)

# User-settable parameters (sliders / choice)
model_params = {
    "n_kitchens": Slider("Kitchens", 1, 1, 2, 1),
    "n_living_rooms": Slider("Living Rooms", 1, 1, 2, 1),
    "n_bedrooms": Slider("Bedrooms", 2, 1, 4, 1),
    "n_bathrooms": Slider("Bathrooms", 1, 1, 4, 1),
    "n_hallways": Slider("Hallways", 1, 1, 3, 1),
    "n_occupants": Slider("Occupants", 2, 1, 6, 1),
    "avg_insulation_quality": Slider("Insulation quality", 0.5, 0.1, 1.0, 0.05),
    "simulation_days": Slider("Simulation days", 5, 1, 30, 1),
    "energy_price_per_kwh": Slider("Energy price (€/kWh)", 0.15, 0.01, 1.0, 0.01),
    "weather_scenario": Choice("Weather scenario", "normal", choices=["normal", "heatwave", "cold_snap"]),
    "smart_appliances": Choice("Smart appliances", "base", choices=["none", "base", "all"])
}

server = ModularServer(
    ResidentialEnergyModel,
    [StatusElement(), energy_chart, temp_chart, outside_temp_chart],
    "Residential Energy Model",
    model_params
)
server.port = 8521
server.launch()

from mesa.visualization.ModularVisualization import ModularServer
from mesa.visualization.modules import ChartModule, TextElement
from mesa.visualization.UserParam import Slider, Choice
from world import ResidentialEnergyModel
from ren import RENDataHub
from results import SimulationResultsManager

"""
Provides an interactive web-based dashboard for the Residential Energy Model using Mesa's ModularServer.
"""

class SaveResidentialEnergyModel(ResidentialEnergyModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._results_saved = False

    def step(self):
        super().step()

        # After simulation completes, save results
        if not self.running and not self._results_saved:
            self._results_saved = True
            save_simulation_results(self)


class StatusElement(TextElement):
    def render(self, model):
        total_kwh = getattr(model, "total_energy_consumed", 0.0)
        price = getattr(model, "energy_price_per_kwh", 0.0)
        day = getattr(model, "current_day", 0)
        hour = getattr(model, "hour_of_day", 0)

        return f"Day: {day}  Hour: {hour}  Total kWh: {total_kwh:.2f}  Price: €{price:.4f}/kWh"


class ApplianceBreakdownElement(TextElement):
    def render(self, model):
        total = model.total_energy_consumed
        if total == 0:
            return "Waiting for consumption data..."

        breakdown_html = "<h3>Energy by Appliance</h3><table style='border-collapse: collapse; width: 100%;'>"
        breakdown_html += "<tr style='background-color: #f0f0f0;'><th style='border: 1px solid #ddd; padding: 8px;'>Appliance</th><th style='border: 1px solid #ddd; padding: 8px;'>kWh</th><th style='border: 1px solid #ddd; padding: 8px;'>%</th></tr>"

        for app_type, consumption in sorted(model.consumption_by_appliance.items(), key=lambda x: x[1], reverse=True):
            if consumption > 0:
                percentage = (consumption / total * 100)
                breakdown_html += f"<tr><td style='border: 1px solid #ddd; padding: 8px;'>{app_type.name}</td><td style='border: 1px solid #ddd; padding: 8px;'>{consumption:.2f}</td><td style='border: 1px solid #ddd; padding: 8px;'>{percentage:.1f}%</td></tr>"

        breakdown_html += "</table>"
        return breakdown_html


# Charts shown in the interface (Total Energy, Average Temp, Outside Temp, Cost)
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

cost_chart = ChartModule(
    [{"Label": "Energy Cost (€)", "Color": "#2ca02c"}],
    data_collector_name='datacollector'
)

# Function to fetch and calculate average price from REN API
def get_ren_price(year: int, month: int) -> float:
    """
    Fetch electricity price data from REN API and return average price in €/kWh
    """
    try:
        ren = RENDataHub()
        df = ren.get_monthly_price(year, month)

        if df.empty:
            print(f"No data returned for {year}-{month:02d}, using default price")
            return 0.15
        

        if 'Price' in df.columns:
            avg_price_mwh = df['Price'].mean()
            avg_price_kwh = avg_price_mwh / 1000  # Convert MWh to kWh
        elif 'price' in df.columns:
            avg_price_mwh = df['price'].mean()
            avg_price_kwh = avg_price_mwh / 1000
        else:
            print("Using default price of 0.15 €/kWh")
            return 0.15

        if 0.01 <= avg_price_kwh <= 1.0:
            return round(avg_price_kwh, 4)
        else:
            print(f"Price {avg_price_kwh} out of expected range, using default")
            return 0.15

    except Exception as e:
        print(f"Error fetching REN data: {e}")
        return 0.15

# Custom parameter class for month selection with REN integration
class MonthYearChoice(Choice):
    def __init__(self, name, value=None, choices=None):
        super().__init__(name, value, choices)

    def get_price_for_selection(self, selection: str) -> float:
        """Parse selection string and fetch price from REN API"""
        try:
            # Format: "2024-01"
            year, month = map(int, selection.split('-'))
            return get_ren_price(year, month)
        except:
            return 0.15

def save_simulation_results(model):
    results_manager = SimulationResultsManager()
    run_name = f"run_{model.weather_scenario}_{model.smart_appliances}_{model.current_day}days"
    results_manager.save_run(model, run_name=run_name)
    print(f"Saved results")


# Generate month choices for 2024
month_choices = [f"2024-{month:02d}" for month in range(1, 13)]
month_labels = {
    "2024-01": "Janeiro 2024", "2024-02": "Fevereiro 2024", "2024-03": "Março 2024",
    "2024-04": "Abril 2024", "2024-05": "Maio 2024", "2024-06": "Junho 2024",
    "2024-07": "Julho 2024", "2024-08": "Agosto 2024", "2024-09": "Setembro 2024",
    "2024-10": "Outubro 2024", "2024-11": "Novembro 2024", "2024-12": "Dezembro 2024"
}

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
    "ren_month": Choice("REN Price Month (2024)", "2024-02", choices=month_choices),
    "weather_scenario": Choice("Weather scenario", "normal", choices=["normal", "heatwave", "cold_snap"]),
    "smart_appliances": Choice("Smart appliances", "base", choices=["none", "base", "all"])
}

server = ModularServer(
    SaveResidentialEnergyModel,
    [StatusElement(), energy_chart, temp_chart, outside_temp_chart, cost_chart, ApplianceBreakdownElement()],
    "Residential Energy Model",
    model_params
)

server.port = 8521
server.launch()
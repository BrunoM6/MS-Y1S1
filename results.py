import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from world import ResidentialEnergyModel

"""
This module manages saving and loading simulation results for the ResidentialEnergyModel.
"""


class SimulationResultsManager:
    """
    Manages saving and loading simulation results for ResidentialEnergyModel.

    Attributes:
        results_base_dir (Path): Base directory to store simulation results.
    """
    def __init__(self, results_base_dir: str = "simulation_results"):
        """Initializes the SimulationResultsManager."""
        self.results_base_dir = Path(results_base_dir)
        self.results_base_dir.mkdir(exist_ok=True)

    def save_run(self, model: 'ResidentialEnergyModel', run_name: str = None):
        """Save configuration and results of a simulation run."""
        if run_name is None:
            run_name = datetime.now().strftime("%Y%m%d_%H%M%S")
        else:
            # Append timestamp to avoid duplicates
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            run_name = f"{run_name}_{timestamp}"

        # Create run-specific directory
        run_dir = self.results_base_dir / run_name
        run_dir.mkdir(exist_ok=True)

        # Save configuration as JSON
        config = {
            "n_kitchens": len([r for r in model.house.rooms if r.room_type.name == "KITCHEN"]),
            "n_living_rooms": len([r for r in model.house.rooms if r.room_type.name == "LIVING_ROOM"]),
            "n_bedrooms": len([r for r in model.house.rooms if r.room_type.name == "BEDROOM"]),
            "n_bathrooms": len([r for r in model.house.rooms if r.room_type.name == "BATHROOM"]),
            "n_hallways": len([r for r in model.house.rooms if r.room_type.name == "HALLWAY"]),
            "n_occupants": model.n_occupants,
            "avg_insulation_quality": model.avg_insulation_quality,
            "actual_insulation": model.insulation,
            "simulation_days": model.simulation_days,
            "ren_month": model.ren_month,
            "energy_price_per_kwh": model.energy_price_per_kwh,
            "weather_scenario": model.weather_scenario,
            "smart_appliances": model.smart_appliances
        }

        config_file = run_dir / "config.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

        total_consumption = model.total_energy_consumed
        appliance_breakdown = {}

        for app_type, consumption in model.consumption_by_appliance.items():
            if consumption > 0:
                percentage = (consumption / total_consumption * 100) if total_consumption > 0 else 0.0
                appliance_breakdown[app_type.name] = {
                    "kWh": round(consumption, 2),
                    "percentage": round(percentage, 2)
                }

        breakdown_file = run_dir / "appliance_breakdown.json"
        with open(breakdown_file, 'w') as f:
            json.dump(appliance_breakdown, f, indent=2)

        # Save simulation results as CSV
        simulation_results_file = run_dir / "simulation_results.csv"

        # Get data from datacollector
        df = model.datacollector.get_model_vars_dataframe()
        df.index.name = "Iteration"
        df.to_csv(simulation_results_file, index=True)

        print(f"Results saved to: {run_dir}")
        print(f"Config: {config_file}")
        print(f"Simulation Results: {simulation_results_file}")

        return run_dir

    def load_run(self, run_dir: Path):
        """Load configuration and results of a simulation run."""
        config_file = run_dir / "config.json"
        simulation_results_file = run_dir / "simulation_results.csv"

        with open(config_file) as f:
            config = json.load(f)

        simulation_results = pd.read_csv(simulation_results_file, index_col=0)

        return {"config": config, "simulation_results": simulation_results}

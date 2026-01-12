import json
import os
from datetime import datetime
from world import ResidentialEnergyModel


class HypothesisTester:
    def __init__(self, output_dir="hypothesis_results"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.results = []

    def run_hypothesis_tests(self):

        # H1: Smart appliances effectiveness
        self._test_h1_smart_appliances()

        # H2: Extreme weather impact with insulation
        self._test_h2_extreme_weather_insulation()

        # H3: Insulation vs price volatility
        self._test_h3_insulation_cost_independence()

        # Save all results
        self._save_results()

    def _test_h1_smart_appliances(self):
        print("\n=== Testing H1: Smart Appliances ===")

        smart_levels = ["none", "base", "all"]

        for smart in smart_levels:
            model = ResidentialEnergyModel(
                n_kitchens=1, n_living_rooms=1, n_bedrooms=2, n_bathrooms=1,
                n_hallways=1, n_occupants=2,
                avg_insulation_quality=0.5,
                simulation_days=30,
                weather_scenario="normal",
                smart_appliances=smart,
                ren_month="2024-02"
            )

            # Run simulation
            model.run_simulation()

            total_consumption = model.total_energy_consumed
            total_cost = total_consumption * model.energy_price_per_kwh

            result = {
                "hypothesis": "H1",
                "smart_appliances": smart,
                "total_consumption_kwh": round(total_consumption, 2),
                "total_cost_eur": round(total_cost, 2),
                "weather": "normal",
                "insulation": 0.5
            }

            self.results.append(result)
            print(f"Smart={smart:5} | Consumption: {total_consumption:.2f} kWh | Cost: €{total_cost:.2f}")

    def _test_h2_extreme_weather_insulation(self):
        print("\n=== Testing H2: Extreme Weather vs Insulation ===")

        weather_scenarios = ["normal", "heatwave", "cold_snap"]
        insulation_levels = [0.2, 0.5, 0.8]

        for weather in weather_scenarios:
            for insulation in insulation_levels:
                model = ResidentialEnergyModel(
                    n_kitchens=1, n_living_rooms=1, n_bedrooms=2, n_bathrooms=1,
                    n_hallways=1, n_occupants=2,
                    avg_insulation_quality=insulation,
                    simulation_days=30,
                    weather_scenario=weather,
                    smart_appliances="base",
                    ren_month="2024-02"
                )

                model.run_simulation()

                total_consumption = model.total_energy_consumed

                result = {
                    "hypothesis": "H2",
                    "weather_scenario": weather,
                    "insulation_quality": insulation,
                    "total_consumption_kwh": round(total_consumption, 2)
                }

                self.results.append(result)
                print(f"Weather={weather:10} | Insulation={insulation:.1f} | Consumption: {total_consumption:.2f} kWh")

    def _test_h3_insulation_cost_independence(self):
        print("\n=== Testing H3: Insulation vs Price Volatility ===")

        insulation_levels = [0.2, 0.5, 0.8]
        months = ["2024-01", "2024-06", "2024-12"]  # Winter, summer, winter

        for insulation in insulation_levels:
            for month in months:
                model = ResidentialEnergyModel(
                    n_kitchens=1, n_living_rooms=1, n_bedrooms=2, n_bathrooms=1,
                    n_hallways=1, n_occupants=2,
                    avg_insulation_quality=insulation,
                    simulation_days=30,
                    weather_scenario="normal",
                    smart_appliances="base",
                    ren_month=month
                )

                model.run_simulation()

                total_consumption = model.total_energy_consumed
                total_cost = total_consumption * model.energy_price_per_kwh
                price_per_kwh = model.energy_price_per_kwh

                result = {
                    "hypothesis": "H3",
                    "insulation_quality": insulation,
                    "month": month,
                    "total_consumption_kwh": round(total_consumption, 2),
                    "total_cost_eur": round(total_cost, 2),
                    "price_per_kwh": round(price_per_kwh, 4)
                }

                self.results.append(result)
                print(f"Insulation={insulation:.1f} | Month={month} | Cost: €{total_cost:.2f}")

    def _save_results(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.output_dir}/hypothesis_results_{timestamp}.json"

        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)

        self._print_summary()

    def _print_summary(self):
        print("\n=== SUMMARY ===")

        # H1 Summary
        h1_results = [r for r in self.results if r["hypothesis"] == "H1"]
        if h1_results:
            none_consumption = next(r for r in h1_results if r["smart_appliances"] == "none")["total_consumption_kwh"]
            all_consumption = next(r for r in h1_results if r["smart_appliances"] == "all")["total_consumption_kwh"]
            reduction = ((none_consumption - all_consumption) / none_consumption) * 100
            print(f"H1: Smart appliances reduce consumption by {reduction:.1f}%")

        # H2 Summary
        h2_results = [r for r in self.results if r["hypothesis"] == "H2"]
        if h2_results:
            heatwave_high_insulation = next(
                (r for r in h2_results if r["weather_scenario"] == "heatwave" and r["insulation_quality"] == 0.8), None)
            heatwave_low_insulation = next(
                (r for r in h2_results if r["weather_scenario"] == "heatwave" and r["insulation_quality"] == 0.2), None)
            if heatwave_high_insulation and heatwave_low_insulation:
                benefit = heatwave_low_insulation["total_consumption_kwh"] - heatwave_high_insulation["total_consumption_kwh"]
                print(f"H2: High insulation saves {benefit:.2f} kWh in extreme weather")

        # H3 Summary
        h3_results = [r for r in self.results if r["hypothesis"] == "H3"]
        if h3_results:
            low_insulation_costs = [r["total_cost_eur"] for r in h3_results if r["insulation_quality"] == 0.2]
            high_insulation_costs = [r["total_cost_eur"] for r in h3_results if r["insulation_quality"] == 0.8]
            avg_savings = (sum(low_insulation_costs) - sum(high_insulation_costs)) / len(low_insulation_costs)
            print(f"H3: High insulation averages €{avg_savings:.2f} monthly savings across price months")


if __name__ == "__main__":
    tester = HypothesisTester()
    tester.run_hypothesis_tests()

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from simulation import Simulation

def run_visualization(n_kitchens: int = 1, n_living_rooms: int = 1, n_bedrooms: int = 2 ,n_bathrooms: int = 1, n_hallways: int = 1, n_occupants: int = 2, avg_insulation_quality: float = 0.5, simulation_days: int = 5, energy_price_per_kwh: float = 0.15, weather_scenario: str = "normal", interval_ms: int = 250):
    sim = Simulation(n_kitchens=n_kitchens, n_living_rooms=n_living_rooms, n_bedrooms=n_bedrooms, n_bathrooms=n_bathrooms, n_hallways=n_hallways, n_occupants=n_occupants, avg_insulation_quality=avg_insulation_quality, simulation_days=simulation_days, energy_price_per_kwh=energy_price_per_kwh, weather_scenario=weather_scenario)
    model = sim.model
    total_steps = model.simulation_days * model.steps_per_day

    house = model.house
    room_labels = [getattr(r.room_type, "name", f"Room_{i}") for i, r in enumerate(house.rooms)]

    times = []
    energies_cumulative = []
    energies_per_step = []

    fig, (ax_bar, ax_cum, ax_step) = plt.subplots(3, 1, figsize=(9, 8), sharex=False)
    plt.tight_layout(pad=3.0)

    # Occupancy bar (house 0)
    initial_counts = [len(r.occupants) for r in house.rooms]
    bars = ax_bar.bar(range(len(room_labels)), initial_counts, tick_label=room_labels)
    ax_bar.set_ylim(0, max(3, max(initial_counts) + 1))
    ax_bar.set_title("Occupants per room")
    ax_bar.set_ylabel("Occupants")

    # Cumulative energy line
    line_cum, = ax_cum.plot([], [], "-o", color="C1", markersize=6, linewidth=2)
    ax_cum.set_xlim(0, total_steps)
    ax_cum.set_ylim(0, 1)
    ax_cum.set_title("Cumulative total energy consumed (kWh)")
    ax_cum.set_ylabel("Cumulative kWh")
    ax_cum.grid(True)

    # Per-step energy line
    line_step, = ax_step.plot([], [], "-o", color="C2", markersize=5, linewidth=1.5)
    ax_step.set_xlim(0, total_steps)
    ax_step.set_ylim(0, 0.5)
    ax_step.set_title("Energy consumed per step (kWh)")
    ax_step.set_xlabel("Step (hours)")
    ax_step.set_ylabel("kWh / step")
    ax_step.grid(True)

    def update(step):
        model.step()

        current_energy = getattr(model, "total_energy_consumed", 0.0)
        print(f"[viz] step={step+1}, total_energy_consumed={current_energy}")

        times.append(step + 1)
        # cumulative
        energies_cumulative.append(current_energy)
        # per-step = current - previous
        prev = energies_cumulative[-2] if len(energies_cumulative) >= 2 else 0.0
        delta = max(0.0, current_energy - prev)
        energies_per_step.append(delta)

        # update occupancy bars
        counts = [len(r.occupants) for r in house.rooms]
        for rect, h in zip(bars, counts):
            rect.set_height(h)
        current_max = max(counts) if counts else 1
        if ax_bar.get_ylim()[1] < current_max + 1:
            ax_bar.set_ylim(0, current_max + 1)

        # update cumulative line
        line_cum.set_data(times, energies_cumulative)
        # autoscale cumulative y
        max_cum = max(energies_cumulative) if energies_cumulative else 1.0
        ax_cum.set_ylim(0, max(1.0, max_cum * 1.2))

        # update per-step line
        line_step.set_data(times, energies_per_step)
        max_step = max(energies_per_step) if energies_per_step else 0.1
        ax_step.set_ylim(0, max(0.1, max_step * 1.5))

        # keep x-limits stable
        if times and times[-1] > ax_cum.get_xlim()[1]:
            ax_cum.set_xlim(0, total_steps)
        if times and times[-1] > ax_step.get_xlim()[1]:
            ax_step.set_xlim(0, total_steps)

        return list(bars) + [line_cum, line_step]

    ani = FuncAnimation(fig, update, frames=range(total_steps), interval=interval_ms, blit=False, repeat=False)
    plt.show()

if __name__ == "__main__":
    run_visualization(interval_ms=150)
from world import ResidentialEnergyModel

class Simulation:
    def __init__(self, **kwargs):
        self.model = ResidentialEnergyModel(**kwargs)

    def run(self):
        self.model.run_simulation()
        return self.model.get_summary_statistics()
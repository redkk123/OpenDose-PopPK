import numpy as np
from opendose import PopulationSimulator
def test_population_runs():

    sim = PopulationSimulator()

    result = sim.simulate(n=10)

    assert len(result) == 10
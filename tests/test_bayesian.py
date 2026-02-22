from opendose_poppk import MAPEstimator

def test_map_runs():

    estimator = MAPEstimator()

    assert estimator is not None
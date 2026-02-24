Usage Guide
===========

This page walks through the most common workflows.  For runnable notebooks,
see :doc:`tutorials/demo_paracetamol`.

Quick start
-----------

.. code-block:: python

    from opendose_poppk import PKModel, PDModel, PopulationSimulator

    # Define a 1-compartment PK model (paracetamol defaults)
    pk = PKModel(F=0.80, ka=1.80, ke=0.28, Vd=65.0)

    # Define an Emax PD model
    pd = PDModel(EC50=10.0, Emax=100.0, n=1.5)

    # Run a Monte Carlo population simulation (1 000 virtual subjects)
    sim = PopulationSimulator(pk, pd)
    result = sim.run(dose=1000.0, n_subjects=1_000, seed=42)
    print(result.head())

Single-subject PK profile
--------------------------

.. code-block:: python

    import numpy as np
    from opendose_poppk import PKModel

    pk = PKModel(F=0.80, ka=1.80, ke=0.28, Vd=65.0)
    times = np.linspace(0, 24, 200)
    conc  = pk.concentration(times, dose=1000.0)

Covariate modelling
--------------------

.. code-block:: python

    from opendose_poppk import PKModel, CovariateModel

    pk  = PKModel(F=0.80, ka=1.80, ke=0.28, Vd=65.0)
    cov = CovariateModel(pk)

    # Adjust PK parameters for a 90 kg patient with CrCl = 40 mL/min
    adjusted = cov.apply(weight=90.0, crcl=40.0)

MAP (Bayesian) individual estimation
--------------------------------------

.. code-block:: python

    import numpy as np
    from opendose_poppk import PKModel, CovariateModel, MAPEstimator

    pk  = PKModel()
    cov = CovariateModel(pk)
    est = MAPEstimator(pk, covariate_model=cov, sigma_obs=1.0)

    times_obs = np.array([1.0, 2.0, 4.0, 8.0])
    c_obs     = np.array([6.8, 7.5, 5.9, 4.1])

    result = est.fit(
        times=times_obs,
        obs=c_obs,
        patient_covariates={"weight": 90.0, "crcl": 50.0},
        dose=1000.0,
    )
    print(result["params_map"])

Loading drug parameters from the database
-------------------------------------------

.. code-block:: python

    from opendose_poppk import DrugDatabase, PKModel

    db   = DrugDatabase("datasets/drugs_parameters.csv")
    pars = db.get("paracetamol")
    pk   = PKModel(**pars)

2-compartment model
--------------------

.. code-block:: python

    from opendose_poppk import PKModel
    import numpy as np

    # Enable 2-compartment mode via CL/V parameterisation
    pk = PKModel(CL=20.0, V=50.0, Q=10.0, V2=30.0, ka=1.5, F=1.0)
    times = np.linspace(0, 24, 200)
    conc  = pk.concentration(times, dose=500.0)

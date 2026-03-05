Usage Guide
===========

This page walks through common package workflows.

Quick Start
-----------

.. code-block:: python

    from opendose_poppk import PKModel, PDModel, PopulationSimulator

    pk = PKModel(F=0.80, ka=1.80, ke=0.28, Vd=65.0)
    pd = PDModel(EC50=10.0, Emax=100.0, n=1.5)

    sim = PopulationSimulator(pk=pk, pd=pd, dose=1000.0)
    result = sim.run(n_subjects=1000, t_max=12.0, n_points=200, seed=42)
    print(result["percentiles_pk"][50].max())

Single-Subject PK
-----------------

.. code-block:: python

    import numpy as np
    from opendose_poppk import PKModel

    pk = PKModel(F=0.80, ka=1.80, ke=0.28, Vd=65.0)
    times = np.linspace(0, 24, 200)
    conc = pk.concentration(times, D=1000.0)

Multiple-Dose Regimen
---------------------

.. code-block:: python

    import numpy as np
    from opendose_poppk import PKModel

    pk = PKModel(F=0.80, ka=1.80, ke=0.28, Vd=65.0)
    times = np.linspace(0, 48, 400)
    conc = pk.concentration_multiple_dose(times, D=1000.0, interval_h=12.0, n_doses=4)

CLI Regimen Simulation
----------------------

.. code-block:: bash

    opendose simulate-regimen \
      --drug Paracetamol \
      --interval-h 12 \
      --n-doses 4 \
      --output-csv output/tables/paracetamol_regimen.csv \
      --plot-png output/figures/paracetamol_regimen.png

CLI Sensitivity Analysis
------------------------

.. code-block:: bash

    opendose sensitivity \
      --drug Paracetamol \
      --dose 1000 \
      --rel-step 0.1 \
      --output-csv output/tables/sensitivity_paracetamol.csv

CLI Dose Sweep
--------------

.. code-block:: bash

    opendose dose-sweep \
      --drug Paracetamol \
      --doses 250,500,750,1000 \
      --output-csv output/tables/dose_sweep_paracetamol.csv

CLI Multi-Drug Regimen Benchmark
--------------------------------

.. code-block:: bash

    opendose benchmark-regimen \
      --drugs Paracetamol,Ibuprofen,Diazepam \
      --interval-h 12 \
      --n-doses 4 \
      --output-csv output/tables/regimen_benchmark.csv

CLI Environment Check
---------------------

.. code-block:: bash

    opendose doctor --strict

CLI Project Report
------------------

.. code-block:: bash

    opendose project-report \
      --drug Paracetamol \
      --output-md output/reports/project_report.md

CLI Drug Dataset Validation
---------------------------

.. code-block:: bash

    opendose validate-dataset \
      --dataset datasets/drugs_parameters.csv \
      --output-clean output/tables/drugs_parameters_clean.csv

CLI Dose Recommendation
-----------------------

.. code-block:: bash

    opendose recommend-dose \
      --drug Paracetamol \
      --target-cmax 10 \
      --weight 80 \
      --crcl 70 \
      --age 55 \
      --output-json output/reports/dose_recommendation.json

CLI Regimen Dose Recommendation
-------------------------------

.. code-block:: bash

    opendose recommend-regimen-dose \
      --drug Paracetamol \
      --target-trough 1.0 \
      --interval-h 12 \
      --n-doses 4 \
      --output-json output/reports/regimen_dose_recommendation.json

CLI Regimen Window Recommendation
---------------------------------

.. code-block:: bash

    opendose recommend-regimen-window \
      --drug Paracetamol \
      --target-trough-min 0.05 \
      --target-cmax-max 12.0 \
      --interval-h 12 \
      --n-doses 4 \
      --strategy midpoint \
      --output-json output/reports/regimen_window_recommendation.json

Covariate Modelling
-------------------

.. code-block:: python

    from opendose_poppk import PKModel, CovariateModel

    pk = PKModel(F=0.80, ka=1.80, ke=0.28, Vd=65.0)
    cov = CovariateModel(pk)
    individual_params = cov.individualize({"weight": 90.0, "crcl": 40.0, "age": 65.0}, sex="M")
    print(individual_params)

MAP (Bayesian) Individual Estimation
------------------------------------

.. code-block:: python

    import numpy as np
    from opendose_poppk import PKModel, CovariateModel, MAPEstimator

    pk = PKModel()
    cov = CovariateModel(pk)
    est = MAPEstimator(pk, covariate_model=cov, sigma_obs=0.8)

    times_obs = np.array([1.0, 2.0, 4.0, 8.0])
    conc_obs = np.array([6.8, 7.5, 5.9, 4.1])

    result = est.fit(
        times=times_obs,
        obs=conc_obs,
        patient_covariates={"weight": 90.0, "crcl": 50.0, "age": 60.0},
        dose=1000.0,
    )
    print(result["params_map"])

Drug Database
-------------

.. code-block:: python

    from opendose_poppk import DrugDatabase, PKModel

    db = DrugDatabase("datasets/drugs_parameters.csv")
    drug = db.get_drug("Paracetamol")
    pk = PKModel(**drug.pk_kwargs)
    print(drug.dose)

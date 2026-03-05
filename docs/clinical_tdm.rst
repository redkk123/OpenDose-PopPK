Clinical TDM Workflow
=====================

OpenDose-PopPK includes a practical workflow to process therapeutic drug monitoring (TDM)
tables and run MAP fitting per patient.

Input Schema
------------

Required CSV columns:

- ``patient_id``
- ``time_h``
- ``conc``
- ``dose_mg``

Optional columns used as covariates when present:

- ``weight``
- ``crcl``
- ``age``

CLI Workflow
------------

1. Create an input template:

.. code-block:: bash

    opendose init-tdm-template --output data/tdm_template.csv

2. Validate and clean raw TDM table:

.. code-block:: bash

    opendose validate-tdm --input data/tdm.csv --output-clean output/tables/tdm_clean.csv

3. Run MAP fitting for each patient:

.. code-block:: bash

    opendose fit-tdm --drug Paracetamol \
      --input output/tables/tdm_clean.csv \
      --output output/tables/tdm_fit.csv \
      --report-md output/reports/tdm_fit_report.md

4. Fit naive pooled population PK parameters:

.. code-block:: bash

    opendose fit-population \
      --input output/tables/tdm_clean.csv \
      --maxiter 2000 \
      --output-json output/reports/population_fit.json

Programmatic Workflow
---------------------

.. code-block:: python

    from opendose_poppk import PKModel, load_tdm_csv, fit_tdm_patients

    df = load_tdm_csv("data/tdm.csv")
    pk = PKModel(F=0.8, ka=1.8, ke=0.28, Vd=65.0)
    fit_df = fit_tdm_patients(df, pk=pk, sigma_obs=0.8, n_iter=3000)
    print(fit_df.head())

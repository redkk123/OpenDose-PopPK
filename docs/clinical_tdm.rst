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

Flexible real-world aliases are accepted during loading/validation. For example:

- ``patient`` or ``subject_id`` -> ``patient_id``
- ``time`` or ``sampling_time`` -> ``time_h``
- ``concentration`` -> ``conc``
- ``dose`` -> ``dose_mg``

Unit normalization is automatic to canonical units:

- Time -> hours (supports ``h``, ``min``, ``day``)
- Concentration -> ``ug/mL`` (supports ``ug/mL``, ``mg/L``, ``ng/mL``, ``mg/mL``, ``ug/L``, ``g/L``)
- Dose -> ``mg`` (supports ``mg``, ``g``, ``ug``, ``ng``)

CLI Workflow
------------

1. Create an input template:

.. code-block:: bash

    opendose init-tdm-template --output data/tdm_template.csv

   # Clinical/raw-data oriented template with explicit unit columns:
   opendose init-tdm-template --format clinical --output data/tdm_template_clinical.csv

2. Validate and clean raw TDM table:

.. code-block:: bash

    opendose validate-tdm --input data/tdm.csv --output-clean output/tables/tdm_clean.csv

   # Optional fallback units when numeric values have no explicit units:
   opendose validate-tdm --input data/tdm.csv --time-unit min --conc-unit ng/mL --dose-unit g \
     --output-clean output/tables/tdm_clean.csv

3. Run MAP fitting for each patient:

.. code-block:: bash

    opendose fit-tdm --drug Paracetamol \
      --input output/tables/tdm_clean.csv \
      --output output/tables/tdm_fit.csv \
      --predictions-csv output/tables/tdm_predictions.csv \
      --plot-png output/figures/tdm_obs_vs_pred.png \
      --report-md output/reports/tdm_fit_report.md

4. Fit naive pooled population PK parameters:

.. code-block:: bash

    opendose fit-population \
      --input output/tables/tdm_clean.csv \
      --maxiter 2000 \
      --bootstrap-n 200 \
      --output-json output/reports/population_fit.json

4b. Fit mixed-effects population PK parameters:

.. code-block:: bash

    opendose fit-population-mixed \
      --drug Paracetamol \
      --input output/tables/tdm_clean.csv \
      --maxiter 1200 \
      --eta-csv output/tables/pop_mixed_eta.csv \
      --output-json output/reports/population_fit_mixed.json

5. Run the full workflow in one command:

.. code-block:: bash

    opendose run-tdm-workflow \
      --drug Paracetamol \
      --input data/tdm.csv \
      --outdir output/workflows/tdm_paracetamol

6. Fit mixed-drug TDM file (must include ``drug`` column):

.. code-block:: bash

    opendose fit-tdm-mixed \
      --input data/tdm_mixed.csv \
      --output output/tables/tdm_mixed_fit.csv

7. Run external validation (observed vs model and optional reference software):

.. code-block:: bash

    opendose init-external-template --output data/external_validation_template.csv
    opendose validate-external \
      --drug Paracetamol \
      --input data/external_validation.csv \
      --predictions-csv output/tables/external_predictions.csv \
      --output-json output/reports/external_validation.json

Programmatic Workflow
---------------------

.. code-block:: python

    from opendose_poppk import PKModel, load_tdm_csv, fit_tdm_patients

    df = load_tdm_csv("data/tdm.csv")
    pk = PKModel(F=0.8, ka=1.8, ke=0.28, Vd=65.0)
    fit_df = fit_tdm_patients(df, pk=pk, sigma_obs=0.8, n_iter=3000)
    print(fit_df.head())

Paracetamol Demo
================

This tutorial demonstrates a complete PK/PD workflow for Paracetamol:

1. Load parameters from the project dataset.
2. Simulate concentration-time profile.
3. Compute PD response.
4. Extract Cmax/Tmax and AUC.

Python example
--------------

.. code-block:: python

   import numpy as np
   from opendose_poppk import DrugDatabase, PKModel, PDModel

   db = DrugDatabase("datasets/drugs_parameters.csv")
   drug = db.get_drug("Paracetamol")

   pk = PKModel(**drug.pk_kwargs)
   pd = PDModel(drug.EC50, drug.n_hill)

   t = np.linspace(0, 12, 300)
   c = pk.concentration(t, D=drug.dose)
   e = pd.effect(c)

   cmax, tmax = pk.cmax(D=drug.dose)
   auc = pk.auc(D=drug.dose)

Notebook
--------

The original notebook version is available in the repository:

- `notebooks/demo_paracetamol.ipynb <https://github.com/redkk123/OpenDose-PopPK/blob/main/notebooks/demo_paracetamol.ipynb>`_

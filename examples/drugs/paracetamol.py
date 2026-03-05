from __future__ import annotations

import numpy as np

from opendose_poppk import DrugDatabase, PKModel


def main() -> None:
    db = DrugDatabase("datasets/drugs_parameters.csv")
    drug = db.get_drug("Paracetamol")
    pk = PKModel(**drug.pk_kwargs)

    t = np.linspace(0.0, 24.0, 300)
    c = pk.concentration(t, D=float(drug.dose))
    idx = int(np.nanargmax(c))

    print("Drug:", drug.name)
    print("Dose:", float(drug.dose))
    print("Cmax:", float(c[idx]))
    print("Tmax_h:", float(t[idx]))
    print("AUC_0_24:", float(np.trapezoid(c, t)))


if __name__ == "__main__":
    main()

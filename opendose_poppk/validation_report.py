from __future__ import annotations

from datetime import datetime, timezone
import platform

import numpy as np

from .database import DrugDatabase, validate_drug_csv
from .external_validation import (
    build_external_validation_table,
    load_external_validation_csv,
    summarize_external_validation,
)
from .pk_model import PKModel
from .population import PopulationSimulator


def build_validation_report(
    dataset: str,
    drug: str = "Paracetamol",
    external_input: str | None = None,
    n_subjects: int = 200,
    t_end: float = 24.0,
    n_points: int = 300,
    seed: int = 42,
) -> dict:
    failures: list[str] = []
    dataset_summary = None
    internal = None
    external = None

    try:
        _, dataset_summary = validate_drug_csv(dataset)
    except Exception as exc:
        failures.append(f"dataset_validation: {exc}")

    if dataset_summary is not None:
        try:
            db = DrugDatabase(dataset)
            info = db.get_drug(drug)
            dose = float(info.dose)
            pk = PKModel(**info.pk_kwargs)
            t = np.linspace(0.0, float(t_end), int(n_points))
            c = pk.concentration(t, D=dose)
            idx = int(np.nanargmax(c))
            pop = PopulationSimulator(pk=pk, dose=dose).run(
                n_subjects=int(n_subjects),
                t_max=float(t_end),
                n_points=int(n_points),
                seed=int(seed),
            )
            p5 = pop["percentiles_pk"][5]
            p50 = pop["percentiles_pk"][50]
            p95 = pop["percentiles_pk"][95]

            internal = {
                "drug": info.name,
                "dose": dose,
                "single_dose": {
                    "cmax": float(c[idx]),
                    "tmax": float(t[idx]),
                    "auc_0_tend": float(np.trapezoid(c, t)),
                },
                "steady_state": pk.steady_state_metrics(D=dose, interval_h=12.0, n_doses=20, n_points=2000),
                "population": {
                    "n_subjects": int(n_subjects),
                    "seed": int(seed),
                    "median_cmax": float(np.max(p50)),
                    "pi90_cmax_low": float(np.max(p5)),
                    "pi90_cmax_high": float(np.max(p95)),
                },
            }
        except Exception as exc:
            failures.append(f"internal_validation: {exc}")

    if external_input:
        try:
            ext_df = load_external_validation_csv(external_input)
            if dataset_summary is None:
                raise ValueError("dataset validation failed before external run")
            db = DrugDatabase(dataset)
            info = db.get_drug(drug)
            pk = PKModel(**info.pk_kwargs)
            table = build_external_validation_table(ext_df, pk=pk)
            external = summarize_external_validation(table)
            external["input"] = str(external_input)
        except Exception as exc:
            failures.append(f"external_validation: {exc}")

    protocol = [
        "Validate drug dataset schema and value ranges.",
        f"Run deterministic PK profile for {drug} at default dose.",
        "Estimate steady-state metrics for q12h regimen (20 doses).",
        f"Run Monte Carlo population simulation (n={int(n_subjects)}, seed={int(seed)}).",
        "Optionally compare model vs observed/reference external validation dataset.",
    ]
    limitations = [
        "Internal metrics are simulation-based and depend on dataset parameter quality.",
        "Steady-state metrics assume fixed interval and fixed dose regimen.",
        "Population simulation currently reflects parametric variability assumptions in the model.",
        "External validation requires harmonized concentration units and comparable protocol definitions.",
    ]
    reproducibility = {
        "commands": [
            f"opendose validation-report --dataset {dataset} --drug {drug}",
            f"opendose project-report --dataset {dataset} --drug {drug}",
            "python -m pytest -q",
        ],
        "seed": int(seed),
    }

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "dataset": str(dataset),
        "drug": str(drug),
        "external_input": str(external_input) if external_input else None,
        "protocol": protocol,
        "internal": internal,
        "external": external,
        "limitations": limitations,
        "reproducibility": reproducibility,
        "dataset_summary": dataset_summary,
        "report_ok": len(failures) == 0,
        "failures": failures,
    }


def render_validation_report_markdown(report: dict) -> str:
    lines = [
        "# OpenDose Validation Report",
        "",
        f"- Generated (UTC): {report['generated_at_utc']}",
        f"- Python: {report['python_version']}",
        f"- Platform: {report['platform']}",
        f"- Dataset: `{report['dataset']}`",
        f"- Drug: `{report['drug']}`",
        f"- Overall status: {'OK' if report['report_ok'] else 'FAIL'}",
        "",
        "## Protocol",
    ]
    for step in report.get("protocol", []):
        lines.append(f"- {step}")

    lines.extend(["", "## Internal Validation"])
    internal = report.get("internal")
    if internal:
        sd = internal["single_dose"]
        ss = internal["steady_state"]
        pop = internal["population"]
        lines.extend(
            [
                f"- Single-dose Cmax: {sd['cmax']:.6g}",
                f"- Single-dose Tmax (h): {sd['tmax']:.6g}",
                f"- Single-dose AUC 0→t_end: {sd['auc_0_tend']:.6g}",
                f"- Steady-state Cmax: {ss['cmax_ss']:.6g}",
                f"- Steady-state trough: {ss['trough_ss']:.6g}",
                f"- Steady-state AUC_tau: {ss['auc_tau_ss']:.6g}",
                f"- Population median Cmax: {pop['median_cmax']:.6g}",
                f"- Population PI90 Cmax: [{pop['pi90_cmax_low']:.6g}, {pop['pi90_cmax_high']:.6g}]",
            ]
        )
    else:
        lines.append("- Internal validation section unavailable.")

    lines.extend(["", "## External Validation"])
    external = report.get("external")
    if external:
        mv = external["model_vs_obs"]
        lines.extend(
            [
                f"- Input: `{external.get('input')}`",
                f"- Rows: {external['rows']}",
                f"- Patients: {external['patients']}",
                f"- Model vs Obs RMSE: {mv['rmse']:.6g}",
                f"- Model vs Obs MAE: {mv['mae']:.6g}",
                f"- With reference: {external['with_reference']}",
            ]
        )
    else:
        lines.append("- External validation not provided.")

    lines.extend(["", "## Limitations"])
    for item in report.get("limitations", []):
        lines.append(f"- {item}")

    lines.extend(["", "## Reproducibility Commands"])
    for cmd in report.get("reproducibility", {}).get("commands", []):
        lines.append(f"- `{cmd}`")

    lines.extend(["", "## Failures"])
    failures = report.get("failures", [])
    if failures:
        for item in failures:
            lines.append(f"- {item}")
    else:
        lines.append("- none")

    lines.append("")
    return "\n".join(lines)

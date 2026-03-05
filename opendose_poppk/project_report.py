from __future__ import annotations

from datetime import datetime, timezone
import platform

from .database import DrugDatabase, validate_drug_csv
from .pk_model import PKModel
from .sensitivity import local_pk_sensitivity


def build_project_report(
    dataset: str,
    drug: str = "Paracetamol",
    dose: float | None = None,
    t_end: float = 24.0,
    n_points: int = 400,
    rel_step: float = 0.10,
) -> dict:
    """
    Build a project health report with dataset validation, PK smoke test,
    and local sensitivity analysis.
    """
    failures: list[str] = []
    dataset_ok = False
    dataset_summary = None

    try:
        _df, dataset_summary = validate_drug_csv(dataset)
        dataset_ok = True
    except Exception as exc:
        failures.append(f"dataset_validation: {exc}")

    pk_smoke_ok = False
    try:
        pk_smoke = PKModel()
        _ = pk_smoke.concentration([0.0, 1.0], D=1000.0)
        pk_smoke_ok = True
    except Exception as exc:
        failures.append(f"pk_smoke: {exc}")

    sensitivity_ok = False
    sensitivity = None
    resolved_dose = None

    if dataset_ok:
        try:
            db = DrugDatabase(dataset)
            info = db.get_drug(drug)
            resolved_dose = float(dose) if dose is not None else float(info.dose)
            pk = PKModel(**info.pk_kwargs)
            sensitivity = local_pk_sensitivity(
                pk=pk,
                dose=resolved_dose,
                t_end=float(t_end),
                n_points=int(n_points),
                rel_step=float(rel_step),
            )
            sensitivity["drug"] = info.name
            sensitivity_ok = True
        except Exception as exc:
            failures.append(f"sensitivity: {exc}")

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "dataset": str(dataset),
        "dataset_ok": bool(dataset_ok),
        "dataset_summary": dataset_summary,
        "pk_smoke_ok": bool(pk_smoke_ok),
        "sensitivity_ok": bool(sensitivity_ok),
        "sensitivity": sensitivity,
        "drug": str(drug),
        "dose": resolved_dose,
        "rel_step": float(rel_step),
        "t_end": float(t_end),
        "n_points": int(n_points),
        "report_ok": len(failures) == 0,
        "failures": failures,
    }


def render_project_report_markdown(report: dict) -> str:
    """
    Render project report dictionary to markdown.
    """
    lines = [
        "# OpenDose Project Report",
        "",
        f"- Generated (UTC): {report['generated_at_utc']}",
        f"- Python: {report['python_version']}",
        f"- Platform: {report['platform']}",
        f"- Overall status: {'OK' if report['report_ok'] else 'FAIL'}",
        "",
        "## Dataset",
        f"- Path: `{report['dataset']}`",
        f"- Valid: `{report['dataset_ok']}`",
    ]

    summary = report.get("dataset_summary")
    if summary:
        lines.extend(
            [
                f"- Rows: {summary['rows']}",
                f"- Drugs: {summary['drugs']}",
                f"- Optional columns present: {', '.join(summary['optional_columns_present']) or 'none'}",
            ]
        )

    lines.extend(
        [
            "",
            "## PK Smoke Test",
            f"- Status: `{report['pk_smoke_ok']}`",
            "",
            "## Sensitivity",
            f"- Status: `{report['sensitivity_ok']}`",
        ]
    )

    sensitivity = report.get("sensitivity")
    if sensitivity and sensitivity.get("results"):
        lines.extend(
            [
                f"- Drug: {sensitivity.get('drug', report['drug'])}",
                f"- Dose: {sensitivity['dose']}",
                f"- Baseline Cmax: {sensitivity['baseline_cmax']:.6g}",
                f"- Baseline AUC: {sensitivity['baseline_auc']:.6g}",
                "",
                "| Parameter | Sensitivity Cmax | Sensitivity AUC |",
                "|---|---:|---:|",
            ]
        )
        for row in sensitivity["results"]:
            lines.append(
                f"| {row['parameter']} | {row['sensitivity_cmax']:.6f} | {row['sensitivity_auc']:.6f} |"
            )
    else:
        lines.append("- Sensitivity section not available.")

    lines.extend(["", "## Failures"])
    failures = report.get("failures", [])
    if failures:
        for item in failures:
            lines.append(f"- {item}")
    else:
        lines.append("- none")

    lines.append("")
    return "\n".join(lines)

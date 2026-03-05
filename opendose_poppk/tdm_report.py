from __future__ import annotations

from pathlib import Path

import pandas as pd

from .tdm_fit import summarize_fit_table


def build_tdm_fit_markdown_report(fit_df: pd.DataFrame, drug_name: str) -> str:
    summary = summarize_fit_table(fit_df)
    lines = [
        f"# TDM MAP Fit Report - {drug_name}",
        "",
        "## Summary",
        f"- Patients: {summary['patients']}",
        f"- Converged: {summary['converged']}",
        f"- Convergence rate: {summary['convergence_rate']:.2%}",
        "",
    ]

    if fit_df.empty:
        lines.extend(["No patient rows were available.", ""])
        return "\n".join(lines)

    lines.extend(
        [
            "## Patient Results",
            "",
            "| Patient | N obs | Dose (mg) | Converged | Objective | MAP ke | MAP Vd |",
            "|---|---:|---:|:---:|---:|---:|---:|",
        ]
    )

    for _, row in fit_df.sort_values("patient_id").iterrows():
        lines.append(
            f"| {row['patient_id']} | {int(row['n_obs'])} | {float(row['dose_mg']):.1f} | "
            f"{'Yes' if bool(row['converged']) else 'No'} | {float(row['obj_value']):.4f} | "
            f"{float(row['map_ke']):.4f} | {float(row['map_Vd']):.4f} |"
        )

    lines.append("")
    return "\n".join(lines)


def write_tdm_fit_markdown_report(fit_df: pd.DataFrame, drug_name: str, output_path: str | Path) -> str:
    report = build_tdm_fit_markdown_report(fit_df=fit_df, drug_name=drug_name)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    return str(out)

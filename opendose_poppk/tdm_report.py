from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
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


def write_tdm_prediction_plot(
    pred_df: pd.DataFrame, output_path: str | Path, title: str = "Observed vs Predicted"
) -> str:
    if pred_df.empty:
        raise ValueError("Prediction table is empty")
    required = {"obs_conc", "pred_conc"}
    missing = required.difference(pred_df.columns)
    if missing:
        raise ValueError(f"Prediction table missing columns: {sorted(missing)}")

    x = pred_df["obs_conc"].to_numpy(dtype=float)
    y = pred_df["pred_conc"].to_numpy(dtype=float)
    lo = float(min(x.min(), y.min()))
    hi = float(max(x.max(), y.max()))

    fig, ax = plt.subplots(figsize=(5.0, 4.0))
    ax.scatter(x, y, alpha=0.8)
    ax.plot([lo, hi], [lo, hi], linestyle="--")
    ax.set_xlabel("Observed concentration")
    ax.set_ylabel("Predicted concentration")
    ax.set_title(title)
    ax.grid(alpha=0.2)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(out)

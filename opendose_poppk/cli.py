from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from . import CovariateModel, MAPEstimator, PDModel, PKModel, PopulationSimulator
from .database import DrugDatabase
from .population_fit import bootstrap_population_pk, fit_population_pk
from .tdm import load_tdm_csv, summarize_tdm, write_tdm_template_csv
from .tdm_fit import (
    build_tdm_prediction_table,
    fit_tdm_patients,
    summarize_fit_table,
    summarize_prediction_table,
)
from .tdm_report import write_tdm_fit_markdown_report


def _default_dataset() -> str:
    return str(Path("datasets") / "drugs_parameters.csv")


def _parse_csv_floats(values: str) -> np.ndarray:
    return np.array([float(v.strip()) for v in values.split(",") if v.strip() != ""], dtype=float)


def _print_json(data: dict) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def cmd_list_drugs(args: argparse.Namespace) -> int:
    db = DrugDatabase(args.dataset)
    for name in db.list_drugs():
        print(name)
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    db = DrugDatabase(args.dataset)
    drug = db.get_drug(args.drug)
    dose = args.dose if args.dose is not None else drug.dose

    pk = PKModel(**drug.pk_kwargs)
    pd = None
    if drug.has_pd and not args.no_pd:
        pd = PDModel(drug.EC50, drug.n_hill)

    sim = PopulationSimulator(pk=pk, pd=pd, covariate_model=CovariateModel(pk), dose=dose)
    result = sim.run(
        n_subjects=args.n_subjects,
        t_max=args.t_max,
        n_points=args.n_points,
        seed=args.seed,
    )

    t = result["t"]
    p5 = result["percentiles_pk"][5]
    p50 = result["percentiles_pk"][50]
    p95 = result["percentiles_pk"][95]

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        header = "time,p5,p50,p95"
        data = np.column_stack([t, p5, p50, p95])
        np.savetxt(out, data, delimiter=",", header=header, comments="")

    _print_json(
        {
            "command": "simulate",
            "drug": drug.name,
            "dose": float(dose),
            "n_subjects": int(args.n_subjects),
            "t_max": float(args.t_max),
            "n_points": int(args.n_points),
            "median_cmax": float(np.max(p50)),
            "pi90_cmax_low": float(np.max(p5)),
            "pi90_cmax_high": float(np.max(p95)),
            "output": str(args.output) if args.output else None,
        }
    )
    return 0


def cmd_fit(args: argparse.Namespace) -> int:
    times = _parse_csv_floats(args.times)
    obs = _parse_csv_floats(args.obs)
    if times.shape[0] != obs.shape[0]:
        raise ValueError("times and obs must have the same length")
    if times.shape[0] == 0:
        raise ValueError("times and obs cannot be empty")

    db = DrugDatabase(args.dataset)
    drug = db.get_drug(args.drug)
    dose = args.dose if args.dose is not None else drug.dose
    pk = PKModel(**drug.pk_kwargs)
    cov = CovariateModel(pk)
    est = MAPEstimator(pk=pk, covariate_model=cov, sigma_obs=args.sigma_obs)

    patient_covariates = {}
    if args.weight is not None:
        patient_covariates["weight"] = float(args.weight)
    if args.crcl is not None:
        patient_covariates["crcl"] = float(args.crcl)
    if args.age is not None:
        patient_covariates["age"] = float(args.age)

    res = est.fit(
        times=times,
        obs=obs,
        patient_covariates=patient_covariates,
        dose=dose,
        n_iter=args.n_iter,
    )
    _print_json(
        {
            "command": "fit",
            "drug": drug.name,
            "dose": float(dose),
            "converged": bool(res["converged"]),
            "obj_value": float(res["obj_value"]),
            "params_map": {k: float(v) for k, v in res["params_map"].items()},
            "eta_map": {k: float(v) for k, v in res["eta_map"].items()},
        }
    )
    return 0


def cmd_validate_tdm(args: argparse.Namespace) -> int:
    df = load_tdm_csv(args.input)
    if args.output_clean:
        out = Path(args.output_clean)
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out, index=False)
    _print_json(
        {
            "command": "validate-tdm",
            "input": str(args.input),
            "output_clean": str(args.output_clean) if args.output_clean else None,
            **summarize_tdm(df),
        }
    )
    return 0


def cmd_fit_tdm(args: argparse.Namespace) -> int:
    df = load_tdm_csv(args.input)
    db = DrugDatabase(args.dataset)
    drug = db.get_drug(args.drug)
    pk = PKModel(**drug.pk_kwargs)

    fit_df = fit_tdm_patients(df, pk=pk, sigma_obs=args.sigma_obs, n_iter=args.n_iter)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        fit_df.to_csv(out, index=False)

    pred_summary = {}
    predictions_csv = None
    if args.predictions_csv:
        pred_df = build_tdm_prediction_table(df=df, fit_df=fit_df)
        pred_out = Path(args.predictions_csv)
        pred_out.parent.mkdir(parents=True, exist_ok=True)
        pred_df.to_csv(pred_out, index=False)
        predictions_csv = str(pred_out)
        pred_summary = summarize_prediction_table(pred_df)

    report_md = None
    if args.report_md:
        report_md = write_tdm_fit_markdown_report(fit_df=fit_df, drug_name=drug.name, output_path=args.report_md)

    _print_json(
        {
            "command": "fit-tdm",
            "input": str(args.input),
            "drug": drug.name,
            "sigma_obs": float(args.sigma_obs),
            "n_iter": int(args.n_iter),
            "output": str(args.output) if args.output else None,
            "predictions_csv": predictions_csv,
            "report_md": report_md,
            **summarize_fit_table(fit_df),
            **pred_summary,
        }
    )
    return 0


def cmd_fit_population(args: argparse.Namespace) -> int:
    df = load_tdm_csv(args.input)
    init = None
    if args.init_F is not None or args.init_ka is not None or args.init_ke is not None or args.init_Vd is not None:
        init = {
            "F": args.init_F if args.init_F is not None else 0.8,
            "ka": args.init_ka if args.init_ka is not None else 1.8,
            "ke": args.init_ke if args.init_ke is not None else 0.28,
            "Vd": args.init_Vd if args.init_Vd is not None else 65.0,
        }

    fit = fit_population_pk(df=df, init=init, maxiter=args.maxiter)
    payload = {
        "command": "fit-population",
        "input": str(args.input),
        "maxiter": int(args.maxiter),
        "output_json": str(args.output_json) if args.output_json else None,
        **fit,
    }
    if args.bootstrap_n > 0:
        payload["bootstrap"] = bootstrap_population_pk(
            df=df,
            n_boot=args.bootstrap_n,
            seed=args.bootstrap_seed,
            init=init,
            maxiter=args.maxiter,
        )

    if args.output_json:
        out = Path(args.output_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    _print_json(payload)
    return 0


def cmd_init_tdm_template(args: argparse.Namespace) -> int:
    path = write_tdm_template_csv(args.output)
    _print_json({"command": "init-tdm-template", "output": path})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="opendose", description="OpenDose-PopPK CLI")
    parser.add_argument(
        "--dataset",
        default=_default_dataset(),
        help="CSV dataset path (default: datasets/drugs_parameters.csv)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list-drugs", help="List available drugs from dataset")
    p_list.set_defaults(func=cmd_list_drugs)

    p_sim = sub.add_parser("simulate", help="Run population simulation for one drug")
    p_sim.add_argument("--drug", required=True, help="Drug name from dataset")
    p_sim.add_argument("--dose", type=float, default=None, help="Dose override")
    p_sim.add_argument("--n-subjects", type=int, default=1000, help="Population size")
    p_sim.add_argument("--t-max", type=float, default=24.0, help="Simulation horizon (hours)")
    p_sim.add_argument("--n-points", type=int, default=200, help="Number of points in profile")
    p_sim.add_argument("--seed", type=int, default=42, help="Random seed")
    p_sim.add_argument("--no-pd", action="store_true", help="Disable PD simulation")
    p_sim.add_argument("--output", default=None, help="Optional CSV output path for PK percentiles")
    p_sim.set_defaults(func=cmd_simulate)

    p_fit = sub.add_parser("fit", help="Run MAP fit for one drug and observed concentrations")
    p_fit.add_argument("--drug", required=True, help="Drug name from dataset")
    p_fit.add_argument("--times", required=True, help="Comma-separated times (hours), e.g. 1,2,4,6")
    p_fit.add_argument("--obs", required=True, help="Comma-separated observations matching --times")
    p_fit.add_argument("--dose", type=float, default=None, help="Dose override")
    p_fit.add_argument("--sigma-obs", type=float, default=0.8, help="Observation noise sigma")
    p_fit.add_argument("--n-iter", type=int, default=3000, help="Maximum optimizer iterations")
    p_fit.add_argument("--weight", type=float, default=None, help="Patient weight (kg)")
    p_fit.add_argument("--crcl", type=float, default=None, help="Patient CrCl (mL/min)")
    p_fit.add_argument("--age", type=float, default=None, help="Patient age (years)")
    p_fit.set_defaults(func=cmd_fit)

    p_tdm = sub.add_parser("validate-tdm", help="Validate and summarize TDM CSV input")
    p_tdm.add_argument("--input", required=True, help="Path to TDM CSV")
    p_tdm.add_argument("--output-clean", default=None, help="Optional path to save cleaned CSV")
    p_tdm.set_defaults(func=cmd_validate_tdm)

    p_fit_tdm = sub.add_parser("fit-tdm", help="Run MAP fit per patient from validated TDM CSV")
    p_fit_tdm.add_argument("--input", required=True, help="Path to TDM CSV")
    p_fit_tdm.add_argument("--drug", required=True, help="Drug name from dataset")
    p_fit_tdm.add_argument("--sigma-obs", type=float, default=0.8, help="Observation noise sigma")
    p_fit_tdm.add_argument("--n-iter", type=int, default=3000, help="Maximum optimizer iterations")
    p_fit_tdm.add_argument("--output", default=None, help="Optional CSV output path for patient fit table")
    p_fit_tdm.add_argument(
        "--predictions-csv",
        default=None,
        help="Optional CSV output path with per-observation predictions and residuals",
    )
    p_fit_tdm.add_argument("--report-md", default=None, help="Optional markdown summary report output path")
    p_fit_tdm.set_defaults(func=cmd_fit_tdm)

    p_fit_pop = sub.add_parser("fit-population", help="Naive pooled population PK fit from TDM CSV")
    p_fit_pop.add_argument("--input", required=True, help="Path to TDM CSV")
    p_fit_pop.add_argument("--maxiter", type=int, default=2000, help="Maximum optimizer iterations")
    p_fit_pop.add_argument("--init-F", type=float, default=None, help="Initial guess for F")
    p_fit_pop.add_argument("--init-ka", type=float, default=None, help="Initial guess for ka")
    p_fit_pop.add_argument("--init-ke", type=float, default=None, help="Initial guess for ke")
    p_fit_pop.add_argument("--init-Vd", type=float, default=None, help="Initial guess for Vd")
    p_fit_pop.add_argument("--bootstrap-n", type=int, default=0, help="Bootstrap replicates (0 disables)")
    p_fit_pop.add_argument("--bootstrap-seed", type=int, default=42, help="Bootstrap RNG seed")
    p_fit_pop.add_argument("--output-json", default=None, help="Optional JSON output path")
    p_fit_pop.set_defaults(func=cmd_fit_population)

    p_template = sub.add_parser("init-tdm-template", help="Create an empty TDM CSV template")
    p_template.add_argument("--output", required=True, help="Output CSV path")
    p_template.set_defaults(func=cmd_init_tdm_template)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

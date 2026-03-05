from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from . import CovariateModel, MAPEstimator, PDModel, PKModel, PopulationSimulator
from .database import DrugDatabase
from .tdm import load_tdm_csv, summarize_tdm
from .tdm_fit import fit_tdm_patients, summarize_fit_table


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

    _print_json(
        {
            "command": "fit-tdm",
            "input": str(args.input),
            "drug": drug.name,
            "sigma_obs": float(args.sigma_obs),
            "n_iter": int(args.n_iter),
            "output": str(args.output) if args.output else None,
            **summarize_fit_table(fit_df),
        }
    )
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
    p_fit_tdm.set_defaults(func=cmd_fit_tdm)

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

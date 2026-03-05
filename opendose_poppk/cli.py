from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

import numpy as np

from . import CovariateModel, MAPEstimator, PDModel, PKModel, PopulationSimulator
from .benchmark import benchmark_regimen_across_drugs, write_benchmark_csv
from .database import DrugDatabase
from .dosing import recommend_dose_for_target_auc, recommend_dose_for_target_cmax
from .population_fit import bootstrap_population_pk, fit_population_pk
from .regimen import simulate_regimen, summarize_regimen, write_regimen_csv, write_regimen_plot
from .regimen_dosing import (
    recommend_regimen_dose_for_target_cmax,
    recommend_regimen_dose_for_target_trough,
)
from .tdm import load_tdm_csv, summarize_tdm, write_tdm_template_csv
from .tdm_fit import (
    build_tdm_prediction_table,
    fit_tdm_patients,
    summarize_fit_table,
    summarize_prediction_table,
)
from .tdm_mixed import fit_tdm_mixed_by_drug, summarize_tdm_mixed_fit
from .tdm_report import write_tdm_fit_markdown_report, write_tdm_prediction_plot


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


def cmd_simulate_regimen(args: argparse.Namespace) -> int:
    db = DrugDatabase(args.dataset)
    drug = db.get_drug(args.drug)
    dose = args.dose if args.dose is not None else drug.dose
    pk = PKModel(**drug.pk_kwargs)

    result = simulate_regimen(
        pk=pk,
        dose=float(dose),
        interval_h=float(args.interval_h),
        n_doses=int(args.n_doses),
        t_end=args.t_end,
        n_points=int(args.n_points),
    )

    csv_path = None
    if args.output_csv:
        csv_path = write_regimen_csv(result, args.output_csv)

    plot_path = None
    if args.plot_png:
        plot_path = write_regimen_plot(result, args.plot_png, title=f"Regimen - {drug.name}")

    _print_json(
        {
            "command": "simulate-regimen",
            "drug": drug.name,
            "output_csv": csv_path,
            "plot_png": plot_path,
            **summarize_regimen(result),
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

    pred_df = None
    pred_summary = {}
    predictions_csv = None
    plot_png = None
    if args.predictions_csv or args.plot_png:
        pred_df = build_tdm_prediction_table(df=df, fit_df=fit_df)
        if args.predictions_csv:
            pred_out = Path(args.predictions_csv)
            pred_out.parent.mkdir(parents=True, exist_ok=True)
            pred_df.to_csv(pred_out, index=False)
            predictions_csv = str(pred_out)
        if args.plot_png:
            plot_png = write_tdm_prediction_plot(pred_df, args.plot_png)
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
            "plot_png": plot_png,
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


def cmd_run_tdm_workflow(args: argparse.Namespace) -> int:
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    df = load_tdm_csv(args.input)
    clean_csv = outdir / "tdm_clean.csv"
    df.to_csv(clean_csv, index=False)

    db = DrugDatabase(args.dataset)
    drug = db.get_drug(args.drug)
    pk = PKModel(**drug.pk_kwargs)

    fit_df = fit_tdm_patients(df, pk=pk, sigma_obs=args.sigma_obs, n_iter=args.n_iter)
    fit_csv = outdir / "tdm_fit.csv"
    fit_df.to_csv(fit_csv, index=False)

    pred_df = build_tdm_prediction_table(df=df, fit_df=fit_df)
    pred_csv = outdir / "tdm_predictions.csv"
    pred_df.to_csv(pred_csv, index=False)
    pred_summary = summarize_prediction_table(pred_df)

    report_md = write_tdm_fit_markdown_report(fit_df=fit_df, drug_name=drug.name, output_path=outdir / "tdm_fit_report.md")
    plot_png = write_tdm_prediction_plot(pred_df=pred_df, output_path=outdir / "tdm_obs_vs_pred.png")

    pop_fit = fit_population_pk(df=df, maxiter=args.maxiter_pop)
    if args.bootstrap_n > 0:
        pop_fit["bootstrap"] = bootstrap_population_pk(
            df=df,
            n_boot=args.bootstrap_n,
            seed=args.bootstrap_seed,
            maxiter=args.maxiter_pop,
        )
    pop_json = outdir / "population_fit.json"
    pop_json.write_text(json.dumps(pop_fit, indent=2, sort_keys=True), encoding="utf-8")

    _print_json(
        {
            "command": "run-tdm-workflow",
            "input": str(args.input),
            "drug": drug.name,
            "outdir": str(outdir),
            "clean_csv": str(clean_csv),
            "fit_csv": str(fit_csv),
            "predictions_csv": str(pred_csv),
            "report_md": str(report_md),
            "plot_png": str(plot_png),
            "population_json": str(pop_json),
            **summarize_tdm(df),
            **summarize_fit_table(fit_df),
            **pred_summary,
        }
    )
    return 0


def cmd_benchmark_regimen(args: argparse.Namespace) -> int:
    df = benchmark_regimen_across_drugs(
        dataset=args.dataset,
        drugs=args.drugs,
        interval_h=args.interval_h,
        n_doses=args.n_doses,
        t_end=args.t_end,
        n_points=args.n_points,
        dose_override=args.dose_override,
    )
    output_csv = None
    if args.output_csv:
        output_csv = write_benchmark_csv(df, args.output_csv)

    top = df.iloc[0].to_dict() if not df.empty else None
    _print_json(
        {
            "command": "benchmark-regimen",
            "n_drugs": int(df.shape[0]),
            "interval_h": float(args.interval_h),
            "n_doses": int(args.n_doses),
            "output_csv": output_csv,
            "top_drug_by_cmax": top,
        }
    )
    return 0


def cmd_fit_tdm_mixed(args: argparse.Namespace) -> int:
    df = load_tdm_csv(args.input)
    fit_df = fit_tdm_mixed_by_drug(
        df=df,
        dataset=args.dataset,
        sigma_obs=args.sigma_obs,
        n_iter=args.n_iter,
    )

    output_csv = None
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        fit_df.to_csv(out, index=False)
        output_csv = str(out)

    _print_json(
        {
            "command": "fit-tdm-mixed",
            "input": str(args.input),
            "output": output_csv,
            "sigma_obs": float(args.sigma_obs),
            "n_iter": int(args.n_iter),
            **summarize_tdm_mixed_fit(fit_df),
        }
    )
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    failures = []
    dataset_ok = False
    dataset_drugs = None
    try:
        db = DrugDatabase(args.dataset)
        dataset_drugs = len(db.list_drugs())
        dataset_ok = True
    except Exception as exc:
        failures.append(f"dataset: {exc}")

    pk_ok = False
    try:
        pk = PKModel()
        _ = pk.concentration([0.0, 1.0], D=1000.0)
        pk_ok = True
    except Exception as exc:
        failures.append(f"pk_smoke: {exc}")

    payload = {
        "command": "doctor",
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "dataset": str(args.dataset),
        "dataset_ok": dataset_ok,
        "dataset_drugs": dataset_drugs,
        "pk_smoke_ok": pk_ok,
        "failures": failures,
    }
    _print_json(payload)
    if args.strict and failures:
        return 1
    return 0


def cmd_recommend_dose(args: argparse.Namespace) -> int:
    if args.target_cmax is None and args.target_auc is None:
        raise ValueError("Provide --target-cmax or --target-auc")
    if args.target_cmax is not None and args.target_auc is not None:
        raise ValueError("Use only one target mode at a time (--target-cmax or --target-auc)")

    db = DrugDatabase(args.dataset)
    drug = db.get_drug(args.drug)
    base_pk = PKModel(**drug.pk_kwargs)

    cov_values = {}
    if args.weight is not None:
        cov_values["weight"] = float(args.weight)
    if args.crcl is not None:
        cov_values["crcl"] = float(args.crcl)
    if args.age is not None:
        cov_values["age"] = float(args.age)

    if cov_values:
        cov = CovariateModel(base_pk)
        params = cov.individualize(cov_values, sex=args.sex)
        pk = PKModel(**params)
    else:
        params = dict(drug.pk_kwargs)
        pk = base_pk

    if args.target_cmax is not None:
        rec = recommend_dose_for_target_cmax(
            pk=pk,
            target_cmax=float(args.target_cmax),
            t_end=float(args.t_end),
            n_points=int(args.n_points),
        )
    else:
        rec = recommend_dose_for_target_auc(pk=pk, target_auc=float(args.target_auc))

    payload = {
        "command": "recommend-dose",
        "drug": drug.name,
        "sex": args.sex,
        "covariates": cov_values,
        "pk_params_used": {k: float(v) for k, v in params.items()},
        **rec,
    }
    if args.output_json:
        out = Path(args.output_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    _print_json(payload)
    return 0


def cmd_recommend_regimen_dose(args: argparse.Namespace) -> int:
    if args.target_cmax is None and args.target_trough is None:
        raise ValueError("Provide --target-cmax or --target-trough")
    if args.target_cmax is not None and args.target_trough is not None:
        raise ValueError("Use only one target mode at a time (--target-cmax or --target-trough)")

    db = DrugDatabase(args.dataset)
    drug = db.get_drug(args.drug)
    base_pk = PKModel(**drug.pk_kwargs)

    cov_values = {}
    if args.weight is not None:
        cov_values["weight"] = float(args.weight)
    if args.crcl is not None:
        cov_values["crcl"] = float(args.crcl)
    if args.age is not None:
        cov_values["age"] = float(args.age)

    if cov_values:
        cov = CovariateModel(base_pk)
        params = cov.individualize(cov_values, sex=args.sex)
        pk = PKModel(**params)
    else:
        params = dict(drug.pk_kwargs)
        pk = base_pk

    if args.target_cmax is not None:
        rec = recommend_regimen_dose_for_target_cmax(
            pk=pk,
            target_cmax=float(args.target_cmax),
            interval_h=float(args.interval_h),
            n_doses=int(args.n_doses),
            t_end=args.t_end,
            n_points=int(args.n_points),
        )
    else:
        rec = recommend_regimen_dose_for_target_trough(
            pk=pk,
            target_trough=float(args.target_trough),
            interval_h=float(args.interval_h),
            n_doses=int(args.n_doses),
            t_end=args.t_end,
            n_points=int(args.n_points),
        )

    payload = {
        "command": "recommend-regimen-dose",
        "drug": drug.name,
        "sex": args.sex,
        "covariates": cov_values,
        "pk_params_used": {k: float(v) for k, v in params.items()},
        **rec,
    }
    if args.output_json:
        out = Path(args.output_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    _print_json(payload)
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

    p_reg = sub.add_parser("simulate-regimen", help="Simulate repeated-dose regimen for one drug")
    p_reg.add_argument("--drug", required=True, help="Drug name from dataset")
    p_reg.add_argument("--dose", type=float, default=None, help="Dose override")
    p_reg.add_argument("--interval-h", type=float, required=True, help="Dose interval in hours")
    p_reg.add_argument("--n-doses", type=int, required=True, help="Number of scheduled doses")
    p_reg.add_argument("--t-end", type=float, default=None, help="Simulation horizon in hours")
    p_reg.add_argument("--n-points", type=int, default=400, help="Number of points in profile")
    p_reg.add_argument("--output-csv", default=None, help="Optional CSV output path")
    p_reg.add_argument("--plot-png", default=None, help="Optional regimen plot path")
    p_reg.set_defaults(func=cmd_simulate_regimen)

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
    p_fit_tdm.add_argument("--plot-png", default=None, help="Optional observed-vs-predicted plot path")
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

    p_workflow = sub.add_parser("run-tdm-workflow", help="Run end-to-end TDM pipeline in one command")
    p_workflow.add_argument("--input", required=True, help="Path to TDM CSV")
    p_workflow.add_argument("--drug", required=True, help="Drug name from dataset")
    p_workflow.add_argument("--outdir", required=True, help="Output directory for all workflow artifacts")
    p_workflow.add_argument("--sigma-obs", type=float, default=0.8, help="Observation noise sigma for MAP fitting")
    p_workflow.add_argument("--n-iter", type=int, default=3000, help="Maximum iterations for patient MAP fitting")
    p_workflow.add_argument("--maxiter-pop", type=int, default=2000, help="Maximum iterations for population fit")
    p_workflow.add_argument("--bootstrap-n", type=int, default=0, help="Bootstrap replicates for population fit")
    p_workflow.add_argument("--bootstrap-seed", type=int, default=42, help="Bootstrap RNG seed")
    p_workflow.set_defaults(func=cmd_run_tdm_workflow)

    p_bench = sub.add_parser("benchmark-regimen", help="Compare repeated-dose regimen metrics across drugs")
    p_bench.add_argument("--drugs", default=None, help="Optional comma-separated drug list")
    p_bench.add_argument("--interval-h", type=float, default=12.0, help="Dose interval in hours")
    p_bench.add_argument("--n-doses", type=int, default=4, help="Number of scheduled doses")
    p_bench.add_argument("--t-end", type=float, default=None, help="Simulation horizon in hours")
    p_bench.add_argument("--n-points", type=int, default=400, help="Number of points in each profile")
    p_bench.add_argument("--dose-override", type=float, default=None, help="If set, use same dose for all drugs")
    p_bench.add_argument("--output-csv", default=None, help="Optional CSV output path for benchmark table")
    p_bench.set_defaults(func=cmd_benchmark_regimen)

    p_fit_tdm_mixed = sub.add_parser(
        "fit-tdm-mixed", help="Run MAP fit for mixed-drug TDM table (requires drug column)"
    )
    p_fit_tdm_mixed.add_argument("--input", required=True, help="Path to TDM CSV with drug column")
    p_fit_tdm_mixed.add_argument("--sigma-obs", type=float, default=0.8, help="Observation noise sigma")
    p_fit_tdm_mixed.add_argument("--n-iter", type=int, default=3000, help="Maximum optimizer iterations")
    p_fit_tdm_mixed.add_argument("--output", default=None, help="Optional output CSV path")
    p_fit_tdm_mixed.set_defaults(func=cmd_fit_tdm_mixed)

    p_doctor = sub.add_parser("doctor", help="Run local environment and dataset health checks")
    p_doctor.add_argument("--strict", action="store_true", help="Exit with code 1 if any check fails")
    p_doctor.set_defaults(func=cmd_doctor)

    p_dose = sub.add_parser("recommend-dose", help="Recommend dose to hit target Cmax or AUC")
    p_dose.add_argument("--drug", required=True, help="Drug name from dataset")
    p_dose.add_argument("--target-cmax", type=float, default=None, help="Target Cmax")
    p_dose.add_argument("--target-auc", type=float, default=None, help="Target AUC")
    p_dose.add_argument("--t-end", type=float, default=24.0, help="Time horizon for Cmax search")
    p_dose.add_argument("--n-points", type=int, default=1000, help="Number of points for Cmax search")
    p_dose.add_argument("--weight", type=float, default=None, help="Patient weight (kg)")
    p_dose.add_argument("--crcl", type=float, default=None, help="Patient CrCl (mL/min)")
    p_dose.add_argument("--age", type=float, default=None, help="Patient age (years)")
    p_dose.add_argument("--sex", default="M", help="Patient sex (M/F), used with covariates")
    p_dose.add_argument("--output-json", default=None, help="Optional JSON output path")
    p_dose.set_defaults(func=cmd_recommend_dose)

    p_reg_dose = sub.add_parser(
        "recommend-regimen-dose", help="Recommend repeated-dose amount for target regimen Cmax or trough"
    )
    p_reg_dose.add_argument("--drug", required=True, help="Drug name from dataset")
    p_reg_dose.add_argument("--target-cmax", type=float, default=None, help="Target regimen Cmax")
    p_reg_dose.add_argument("--target-trough", type=float, default=None, help="Target regimen trough")
    p_reg_dose.add_argument("--interval-h", type=float, required=True, help="Dose interval in hours")
    p_reg_dose.add_argument("--n-doses", type=int, required=True, help="Number of scheduled doses")
    p_reg_dose.add_argument("--t-end", type=float, default=None, help="Simulation horizon in hours")
    p_reg_dose.add_argument("--n-points", type=int, default=1000, help="Number of points in regimen profile")
    p_reg_dose.add_argument("--weight", type=float, default=None, help="Patient weight (kg)")
    p_reg_dose.add_argument("--crcl", type=float, default=None, help="Patient CrCl (mL/min)")
    p_reg_dose.add_argument("--age", type=float, default=None, help="Patient age (years)")
    p_reg_dose.add_argument("--sex", default="M", help="Patient sex (M/F), used with covariates")
    p_reg_dose.add_argument("--output-json", default=None, help="Optional JSON output path")
    p_reg_dose.set_defaults(func=cmd_recommend_regimen_dose)

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

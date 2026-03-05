from __future__ import annotations

import json
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import numpy as np

from .database import DrugDatabase
from .pk_model import PKModel


def _validate_profile_args(dose: float, t_end: float, n_points: int) -> None:
    if dose <= 0:
        raise ValueError("dose must be positive")
    if t_end <= 0:
        raise ValueError("t_end must be positive")
    if n_points < 3:
        raise ValueError("n_points must be at least 3")


def _profile_to_svg(t: np.ndarray, conc: np.ndarray, width: int = 780, height: int = 280, pad: int = 24) -> str:
    x = np.asarray(t, dtype=float)
    y = np.asarray(conc, dtype=float)
    if x.size == 0:
        return ""

    x_min, x_max = float(x.min()), float(x.max())
    y_min, y_max = 0.0, float(max(y.max(), 1e-8))
    x_span = max(x_max - x_min, 1e-8)
    y_span = max(y_max - y_min, 1e-8)

    px = pad + (x - x_min) / x_span * (width - 2 * pad)
    py = height - pad - (y - y_min) / y_span * (height - 2 * pad)
    points = " ".join(f"{float(a):.2f},{float(b):.2f}" for a, b in zip(px, py))
    return (
        f"<svg viewBox='0 0 {width} {height}' width='100%' role='img' aria-label='PK concentration profile'>"
        f"<rect x='0' y='0' width='{width}' height='{height}' fill='#f8fafc'/>"
        f"<line x1='{pad}' y1='{height-pad}' x2='{width-pad}' y2='{height-pad}' stroke='#64748b' stroke-width='1'/>"
        f"<line x1='{pad}' y1='{pad}' x2='{pad}' y2='{height-pad}' stroke='#64748b' stroke-width='1'/>"
        f"<polyline fill='none' stroke='#0f766e' stroke-width='2.5' points='{points}'/>"
        "</svg>"
    )


def build_web_app_payload(
    dataset: str,
    drug: str,
    dose: float | None = None,
    t_end: float = 24.0,
    n_points: int = 300,
) -> dict:
    db = DrugDatabase(dataset)
    drug_obj = db.get_drug(drug)
    dose_final = float(dose) if dose is not None else float(drug_obj.dose)
    _validate_profile_args(dose=dose_final, t_end=float(t_end), n_points=int(n_points))

    pk = PKModel(**drug_obj.pk_kwargs)
    t = np.linspace(0.0, float(t_end), int(n_points))
    conc = pk.concentration(t, D=dose_final)
    idx = int(np.nanargmax(conc))

    return {
        "drug": str(drug_obj.name),
        "dose": dose_final,
        "t_end": float(t_end),
        "n_points": int(n_points),
        "t": t.tolist(),
        "conc": conc.tolist(),
        "cmax": float(conc[idx]),
        "tmax": float(t[idx]),
        "auc_0_tend": float(np.trapezoid(conc, t)),
        "available_drugs": db.list_drugs(),
    }


def render_web_app_html(payload: dict) -> str:
    t = np.asarray(payload["t"], dtype=float)
    conc = np.asarray(payload["conc"], dtype=float)
    svg = _profile_to_svg(t, conc)
    drug = escape(str(payload["drug"]))
    drugs = ", ".join(payload.get("available_drugs", []))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>OpenDose-PopPK Web App</title>
  <style>
    body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin: 24px; color: #0f172a; background: #f1f5f9; }}
    .card {{ background: white; border: 1px solid #cbd5e1; border-radius: 12px; padding: 16px; max-width: 980px; }}
    .kpi {{ display: inline-block; min-width: 170px; margin-right: 12px; margin-top: 6px; }}
    code {{ background: #e2e8f0; padding: 2px 6px; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>OpenDose-PopPK Web App (Baseline)</h1>
  <div class="card">
    <p><strong>Drug:</strong> {drug} | <strong>Dose:</strong> {payload["dose"]:.2f}</p>
    <p>Available drugs in dataset: <code>{escape(drugs)}</code></p>
    <div class="kpi"><strong>Cmax</strong><br>{payload["cmax"]:.4f}</div>
    <div class="kpi"><strong>Tmax (h)</strong><br>{payload["tmax"]:.4f}</div>
    <div class="kpi"><strong>AUC 0→t_end</strong><br>{payload["auc_0_tend"]:.4f}</div>
    <div style="margin-top: 18px;">{svg}</div>
  </div>
</body>
</html>
"""


def write_web_app_html(payload: dict, output_path: str | Path) -> str:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_web_app_html(payload), encoding="utf-8")
    return str(out)


def run_web_app_server(  # pragma: no cover
    dataset: str,
    host: str = "127.0.0.1",
    port: int = 8000,
    default_drug: str = "Paracetamol",
    default_dose: float | None = None,
    default_t_end: float = 24.0,
    default_n_points: int = 300,
) -> None:
    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                body = json.dumps({"status": "ok"}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if parsed.path != "/":
                self.send_error(404, "Not found")
                return

            q = parse_qs(parsed.query)
            drug = q.get("drug", [default_drug])[0]
            dose_raw = q.get("dose", [default_dose])[0]
            t_end_raw = q.get("t_end", [default_t_end])[0]
            n_points_raw = q.get("n_points", [default_n_points])[0]

            try:
                dose = None if dose_raw is None else float(dose_raw)
                t_end = float(t_end_raw)
                n_points = int(n_points_raw)
                payload = build_web_app_payload(
                    dataset=dataset,
                    drug=drug,
                    dose=dose,
                    t_end=t_end,
                    n_points=n_points,
                )
                body = render_web_app_html(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as exc:
                body = f"<h1>Invalid request</h1><pre>{escape(str(exc))}</pre>".encode("utf-8")
                self.send_response(400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        def log_message(self, format, *args):
            return

    server = ThreadingHTTPServer((host, int(port)), _Handler)
    print(f"OpenDose web app running at http://{host}:{int(port)}")
    server.serve_forever()

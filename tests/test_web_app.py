from pathlib import Path

import pytest

from opendose_poppk import build_web_app_payload, render_web_app_html, write_web_app_html
import opendose_poppk.web_app as web_app_mod


def test_web_app_payload_render_and_write(tmp_path):
    payload = build_web_app_payload(
        dataset="datasets/drugs_parameters.csv",
        drug="Paracetamol",
        dose=500.0,
        t_end=12.0,
        n_points=60,
    )
    assert payload["drug"] == "Paracetamol"
    assert payload["dose"] == pytest.approx(500.0)
    assert payload["n_points"] == 60
    assert len(payload["t"]) == 60
    assert len(payload["conc"]) == 60

    html = render_web_app_html(payload)
    assert "<svg" in html
    assert "Paracetamol" in html

    out = tmp_path / "web_app.html"
    path = write_web_app_html(payload, out)
    assert path == str(out)
    assert out.exists()
    assert "<!doctype html>" in out.read_text(encoding="utf-8")


def test_web_app_payload_default_dose_and_validation():
    payload = build_web_app_payload(
        dataset="datasets/drugs_parameters.csv",
        drug="Paracetamol",
        dose=None,
        t_end=8.0,
        n_points=40,
    )
    assert payload["dose"] > 0

    with pytest.raises(ValueError, match="dose must be positive"):
        build_web_app_payload("datasets/drugs_parameters.csv", "Paracetamol", dose=0.0)
    with pytest.raises(ValueError, match="t_end must be positive"):
        build_web_app_payload("datasets/drugs_parameters.csv", "Paracetamol", t_end=0.0)
    with pytest.raises(ValueError, match="n_points must be at least 3"):
        build_web_app_payload("datasets/drugs_parameters.csv", "Paracetamol", n_points=2)


def test_web_app_svg_empty_profile():
    assert web_app_mod._profile_to_svg([], []) == ""

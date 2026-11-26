"""Comprobaciones de la predicción de demanda (ejecutar tras run_pipeline.py)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from cuidacerca.forecast import horizonte_amortiguado  # noqa: E402

P = ROOT / "data" / "processed"


def test_horizonte_amortiguado():
    assert horizonte_amortiguado(5, 1.0) == 5
    assert 0 < horizonte_amortiguado(5, 0.85) < 5
    assert horizonte_amortiguado(100, 0.85) < 0.85 / 0.15 + 1e-9


def test_cuantiles_ordenados_y_completos():
    p = pd.read_csv(P / "prediccion_unidades.csv")
    u = pd.read_csv(P / "unidades.csv")
    assert set(p["anio"]) == {2030, 2035} and len(p) == 2 * len(u)
    assert (p["p10"] <= p["p50"]).all() and (p["p50"] <= p["p90"]).all() and (p["p10"] >= 0).all()


def test_escenarios_coherentes_con_total_regional():
    e = pd.read_csv(P / "escenarios_demanda.csv.gz")
    r = pd.read_csv(P / "prediccion_regional.csv").set_index("anio")
    for a in (2030, 2035):
        tot = e[e["anio"] == a].drop(columns=["escenario", "anio"]).sum(axis=1)
        assert abs(np.median(tot) / r.loc[a, "p50"] - 1) < 0.02


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f()
            print("OK", n)

"""Comprobaciones del cálculo de accesibilidad (E2SFCA)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from cuidacerca.coverage import e2sfca, gini_ponderado, peso_gaussiano  # noqa: E402


def test_peso_gaussiano_limites():
    w = peso_gaussiano(np.array([0.0, 10.0, 30.0, 31.0]), 30.0)
    assert abs(w[0] - 1) < 1e-9 and 0 < w[1] < 1 and abs(w[2]) < 1e-9 and w[3] == 0


def test_e2sfca_conserva_plazas():
    # Todas las plazas alcanzables se reparten: sum(A_u * D_u) == plazas totales
    u = pd.DataFrame({"x": [0, 5000, 40000], "y": [0, 0, 0], "demanda": [100, 50, 30]})
    c = pd.DataFrame({"x": [1000, 39000], "y": [0, 0], "plazas": [40, 10]})
    a = e2sfca(u, c, 20.0)
    assert abs((a * u["demanda"]).sum() - 50) < 1e-6


def test_gini_igualdad_y_desigualdad():
    assert abs(gini_ponderado(np.ones(5), np.ones(5))) < 1e-9
    assert gini_ponderado(np.array([0, 0, 0, 0, 1.0]), np.ones(5)) > 0.7


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f()
            print("OK", n)

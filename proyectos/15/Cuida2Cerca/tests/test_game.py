"""Comprobaciones de los juegos cooperativos de costes."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from cuidacerca.game import JuegoLocalizacion, analizar, shapley_exacto, shapley_montecarlo  # noqa: E402


def juego(n=5, seed=0):
    rng = np.random.default_rng(seed)
    xy = rng.uniform(0, 20, size=(n, 2))
    D = np.hypot(*(xy[:, None] - xy[None]).transpose(2, 0, 1))
    return JuegoLocalizacion([f"m{i}" for i in range(n)], rng.uniform(2, 20, n), D, F=50, c=1, tau=0.2)


def test_eficiencia_y_subaditividad():
    j = juego()
    c = j.costes()
    phi = shapley_exacto(c, j.n)
    assert abs(phi.sum() - c[-1]) < 1e-9
    for S in range(1, len(c)):
        T = (S - 1) & S
        while T:
            assert c[S] <= c[T] + c[S ^ T] + 1e-9
            T = (T - 1) & S


def test_simetria_jugadores_identicos():
    D = np.zeros((3, 3))
    j = JuegoLocalizacion(["a", "b", "c"], np.array([10.0, 10, 10]), D, F=30, c=1, tau=0)
    phi = shapley_exacto(j.costes(), 3)
    assert np.allclose(phi, phi[0]) and abs(phi[0] - 20) < 1e-9


def test_montecarlo_aproxima_exacto():
    j = juego(6, 1)
    c = j.costes()
    mc = shapley_montecarlo(lambda S: c[S], 6, permutaciones=4000)
    assert np.abs(mc - shapley_exacto(c, 6)).max() < 0.05 * c[-1] / 6


def test_nucleo_coherente():
    r = analizar(juego(6, 2))
    assert abs(sum(r["reparto_nucleo"]) - r["coste_total"]) < 1e-6
    assert r["coste_total"] <= r["coste_por_separado"] + 1e-9


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f()
            print("OK", n)

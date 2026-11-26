"""Etapa 5: reparto del coste de los centros nuevos entre municipios (juegos cooperativos de costes).

Juego de localización de instalaciones (facility location game). Jugadores: municipios con necesidad q_i
(plazas) y punto de referencia. Una coalición S puede financiar centros propios; un centro en el municipio k
que atiende a un grupo T cuesta
    coste_centro(T, k) = F + c * sum_{i in T} q_i + tau * sum_{i in T} q_i * d_ik
(coste fijo de apertura, coste por plaza y coste de desplazamiento de los usuarios). El coste de la
coalición es el de la mejor forma de organizarse en uno o varios centros:
    c(S) = min( min_{k in S} coste_centro(S, k),  min_{T subset S} c(T) + c(S minus T) )
lo que hace el juego subaditivo: cooperar nunca cuesta más que actuar por separado.

Repartos calculados:
  - valor de Shapley (exacto hasta ~14 jugadores; Monte Carlo para más);
  - núcleo mínimo (least core) por programación lineal: si epsilon <= 0 el núcleo no está vacío y existe un
    reparto que ningún subgrupo tiene incentivos a abandonar;
  - repartos de referencia: igualitario y proporcional a la necesidad.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import factorial

import numpy as np
from ortools.linear_solver import pywraplp


@dataclass
class JuegoLocalizacion:
    nombres: list[str]
    q: np.ndarray          # necesidad de cada jugador (plazas)
    D: np.ndarray          # distancias entre jugadores (km)
    F: float = 1.0         # coste fijo de abrir un centro
    c: float = 0.0         # coste por plaza
    tau: float = 0.0       # coste por plaza y km

    @property
    def n(self) -> int:
        return len(self.q)

    def costes(self) -> np.ndarray:
        """c(S) para todas las coaliciones (índice = máscara de bits). DP sobre subconjuntos, O(3^n)."""
        n = self.n
        N = 1 << n
        q, D = np.asarray(self.q, float), np.asarray(self.D, float)
        # coste de un único centro en el mejor municipio de la coalición
        miembros = ((np.arange(N)[:, None] >> np.arange(n)) & 1).astype(bool)   # (N, n)
        Q = miembros @ q
        transp = (miembros * q) @ D                                            # (N, k): sum_i q_i d_ik
        transp = np.where(miembros, transp, np.inf)
        mejor_k = transp.min(axis=1)
        mejor_k[0] = 0.0
        uno = self.F + self.c * Q + self.tau * mejor_k
        uno[0] = 0.0
        coste = uno.copy()
        for S in range(1, N):  # partición en dos subcoaliciones (enumeración de submáscaras)
            T = (S - 1) & S
            mejor = coste[S]
            while T:
                if T < (S ^ T):  # cada partición una vez
                    v = coste[T] + coste[S ^ T]
                    if v < mejor:
                        mejor = v
                T = (T - 1) & S
            coste[S] = mejor
        return coste

    def coste_individual(self) -> np.ndarray:
        return self.F + self.c * np.asarray(self.q, float)


def shapley_exacto(coste: np.ndarray, n: int) -> np.ndarray:
    N = 1 << n
    tam = np.array([bin(S).count("1") for S in range(N)])
    peso = np.array([factorial(s) * factorial(n - s - 1) / factorial(n) for s in range(n)])
    phi = np.zeros(n)
    for i in range(n):
        bit = 1 << i
        S = np.arange(N)[(np.arange(N) & bit) == 0]
        phi[i] = (peso[tam[S]] * (coste[S | bit] - coste[S])).sum()
    return phi


def shapley_montecarlo(coste_fn, n: int, permutaciones: int = 2000, semilla: int = 0) -> np.ndarray:
    """Estimación por muestreo de permutaciones; coste_fn(mascara) -> coste."""
    rng = np.random.default_rng(semilla)
    phi = np.zeros(n)
    for _ in range(permutaciones):
        S, cS = 0, 0.0
        for i in rng.permutation(n):
            S2 = S | (1 << int(i))
            c2 = coste_fn(S2)
            phi[i] += c2 - cS
            S, cS = S2, c2
    return phi / permutaciones


def nucleo_minimo(coste: np.ndarray, n: int) -> tuple[float, np.ndarray]:
    """Least core: min eps s.a. sum_{i in S} x_i <= c(S) + eps (S propia, no vacía), sum x = c(N).
    Devuelve (eps, x). eps <= 0 implica núcleo no vacío."""
    s = pywraplp.Solver.CreateSolver("GLOP")
    x = [s.NumVar(-s.infinity(), s.infinity(), f"x{i}") for i in range(n)]
    eps = s.NumVar(-s.infinity(), s.infinity(), "eps")
    N = (1 << n) - 1
    for S in range(1, N):
        s.Add(sum(x[i] for i in range(n) if S >> i & 1) <= float(coste[S]) + eps)
    s.Add(sum(x) == float(coste[N]))
    s.Minimize(eps)
    if s.Solve() != pywraplp.Solver.OPTIMAL:
        raise RuntimeError("LP del núcleo mínimo sin solución óptima")
    return eps.solution_value(), np.array([v.solution_value() for v in x])


def max_exceso(coste: np.ndarray, n: int, x: np.ndarray) -> tuple[float, int]:
    """Mayor exceso sum_{i in S} x_i - c(S): si es > 0, la coalición S estaría mejor por su cuenta."""
    N = 1 << n
    miembros = ((np.arange(N)[:, None] >> np.arange(n)) & 1).astype(bool)
    exc = miembros @ x - coste
    exc[0] = exc[N - 1] = -np.inf
    S = int(np.argmax(exc))
    return float(exc[S]), S


def analizar(j: JuegoLocalizacion) -> dict:
    """Resumen completo del juego para la web y los informes."""
    cost = j.costes()
    n, N = j.n, (1 << j.n) - 1
    phi = shapley_exacto(cost, n)
    eps, xc = nucleo_minimo(cost, n)
    exc, S = max_exceso(cost, n, phi)
    total, solos = cost[N], j.coste_individual()
    q = np.asarray(j.q, float)
    return {"jugadores": j.nombres, "q": q.tolist(), "coste_total": float(total),
            "coste_por_separado": float(solos.sum()), "ahorro_pct": float(100 * (1 - total / solos.sum())),
            "coste_individual": solos.tolist(), "shapley": phi.tolist(),
            "proporcional": (total * q / q.sum()).tolist(), "igualitario": [total / n] * n,
            "nucleo_epsilon": float(eps), "nucleo_no_vacio": bool(eps <= 1e-6), "reparto_nucleo": xc.tolist(),
            "shapley_en_nucleo": bool(exc <= 1e-6), "shapley_max_exceso": float(exc),
            "coalicion_bloqueante": [j.nombres[i] for i in range(n) if S >> i & 1] if exc > 1e-6 else []}

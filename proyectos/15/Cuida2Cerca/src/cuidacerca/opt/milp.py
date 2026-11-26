"""Modelo exacto: programa estocástico en dos etapas, forma extensiva sobre S escenarios (SAA).

    min  (1/S) sum_s [ sum_u (w_u * r1_us + (w_u + P) * r2_us) + lambda * sum_(u,j) d_uj * x_ujs ]
    s.a. sum_j x_ujs + r1_us + r2_us = need_us                para todo u, s
         r1_us <= (1 - cmin) * need_us                        (cobertura mínima blanda)
         sum_u x_ujs <= cap_j + module * k_j                   para todo j, s
         min_new * y_j <= module * k_j <= capmax_j * y_j        para todo j
         sum_j F_j * y_j + c_j * module * k_j <= B
         k_j entero >= 0, y_j binaria, x, r >= 0
Primera etapa (k, y): dónde y cuántas plazas abrir. Segunda etapa (x, r): uso de las plazas en cada escenario.
"""
from __future__ import annotations

import time

import numpy as np
from ortools.linear_solver import pywraplp

from .instance import Instance
from .solution import Solution


def resolver_milp(inst: Instance, solver: str = "SCIP", limite_s: float = 120.0, gap: float = 1e-3,
                  verbose: bool = False) -> Solution:
    t0 = time.time()
    s = pywraplp.Solver.CreateSolver(solver)
    if s is None:
        raise RuntimeError(f"Solver {solver} no disponible en OR-Tools")
    s.SetTimeLimit(int(limite_s * 1000))
    if verbose:
        s.EnableOutput()
    S, n, m = inst.S, inst.n, inst.m
    cand = inst.candidates
    kmax = (inst.cap_new_max // inst.module).astype(int)
    k = {j: s.IntVar(0, int(kmax[j]), f"k{j}") for j in cand}
    y = {j: s.BoolVar(f"y{j}") for j in cand}
    for j in cand:
        s.Add(inst.module * k[j] <= inst.cap_new_max[j] * y[j])
        if inst.min_new > 0:
            s.Add(inst.module * k[j] >= inst.min_new * y[j])
    s.Add(sum(inst.fixed_cost[j] * y[j] + inst.unit_cost[j] * inst.module * k[j] for j in cand) <= inst.budget)

    arcs_u = [np.flatnonzero(inst.arc_u == u) for u in range(n)]
    arcs_j = [np.flatnonzero(inst.arc_j == j) for j in range(m)]
    obj = s.Objective()
    for sc in range(S):
        x = [s.NumVar(0, s.infinity(), "") for _ in range(len(inst.arc_u))]
        for a, var in enumerate(x):
            obj.SetCoefficient(var, inst.dist_penalty * inst.arc_d[a] / S)
        for u in range(n):
            # necesidad sin plaza en dos tramos: tolerada (hasta (1 - cmin) * need) y por debajo del mínimo
            r1 = s.NumVar(0, float(inst.need[sc, u]) * (1 - inst.coverage_min), "")
            obj.SetCoefficient(r1, inst.unmet_weight[u] / S)
            if inst.coverage_min > 0:
                r2 = s.NumVar(0, s.infinity(), "")
                obj.SetCoefficient(r2, (inst.unmet_weight[u] + inst.coverage_penalty) / S)
                s.Add(sum(x[a] for a in arcs_u[u]) + r1 + r2 == float(inst.need[sc, u]))
            else:
                s.Add(sum(x[a] for a in arcs_u[u]) + r1 == float(inst.need[sc, u]))
        for j in range(m):
            if len(arcs_j[j]) == 0:
                continue
            rhs = float(inst.cap_existing[j])
            if j in k:
                s.Add(sum(x[a] for a in arcs_j[j]) - inst.module * k[j] <= rhs)
            else:
                s.Add(sum(x[a] for a in arcs_j[j]) <= rhs)
    obj.SetMinimization()
    params = pywraplp.MPSolverParameters()
    params.SetDoubleParam(params.RELATIVE_MIP_GAP, gap)
    t_mod = time.time() - t0
    estado = s.Solve(params)
    if estado not in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        raise RuntimeError(f"El MILP no encontró solución (estado {estado})")
    new = np.zeros(m, dtype=np.int64)
    for j in cand:
        new[j] = int(round(k[j].solution_value())) * inst.module
    cota = s.Objective().BestBound()
    val = s.Objective().Value()
    return Solution(new, f"milp_{solver.lower()}", {
        "estado": "optimo" if estado == pywraplp.Solver.OPTIMAL else "factible (límite de tiempo)",
        "objetivo_saa": val, "cota_inferior": cota, "gap_pct": 100 * (val - cota) / max(abs(val), 1e-9),
        "segundos": time.time() - t0, "segundos_modelado": t_mod, "escenarios": S,
        "variables": s.NumVariables(), "restricciones": s.NumConstraints()})

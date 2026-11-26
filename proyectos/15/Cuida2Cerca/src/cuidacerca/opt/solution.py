"""Soluciones y evaluador de segunda etapa.

Una solución es el vector de plazas nuevas por sitio (múltiplos del módulo). Dada una solución, la
segunda etapa de cada escenario (qué zona usa qué plazas) es un flujo de coste mínimo:

  origen -> zona u          capacidad need[s,u], coste 0
  zona u -> sitio j         capacidad ilimitada, coste dist_penalty * d_uj      (solo arcos dentro del radio)
  zona u -> sumidero        capacidad (1 - cmin) * need[s,u], coste w_u        (necesidad sin plaza tolerada)
  zona u -> sumidero        capacidad ilimitada, coste w_u + P                  (por debajo de la cobertura mínima)
  sitio j -> sumidero       capacidad cap_existing[j] + new[j], coste 0

Se resuelve exactamente con OR-Tools (SimpleMinCostFlow) en milisegundos, lo que permite evaluar
cientos de escenarios dentro de una metaheurística (simheurística).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from ortools.graph.python import min_cost_flow

from .instance import Instance


def gini_ponderado(valores: np.ndarray, pesos: np.ndarray) -> float:
    """Gini de un indicador por zona ponderado por la necesidad de cada zona (0 = igualdad perfecta)."""
    orden = np.argsort(valores)
    v, p = np.asarray(valores, float)[orden], np.asarray(pesos, float)[orden]
    if p.sum() <= 0 or (v * p).sum() <= 0:
        return 0.0
    cp = np.cumsum(p) / p.sum()
    cv = np.cumsum(v * p) / (v * p).sum()
    return float(1 - np.sum((cp - np.r_[0, cp[:-1]]) * (cv + np.r_[0, cv[:-1]])))

ESCALA_FLUJO = 10      # décimas de plaza
ESCALA_COSTE = 1000


@dataclass
class Solution:
    new_cap: np.ndarray            # (m,) plazas nuevas por sitio
    algoritmo: str = ""
    info: dict | None = None

    def key(self) -> bytes:
        return self.new_cap.astype(np.int32).tobytes()

    def copy(self) -> "Solution":
        return Solution(self.new_cap.copy(), self.algoritmo, dict(self.info or {}))


def coste(inst: Instance, sol: Solution) -> float:
    abiertos = sol.new_cap > 0
    return float((inst.fixed_cost * abiertos).sum() + (inst.unit_cost * sol.new_cap).sum())


def es_factible(inst: Instance, sol: Solution) -> bool:
    return (coste(inst, sol) <= inst.budget + 1e-9 and (sol.new_cap >= 0).all()
            and (sol.new_cap <= inst.cap_new_max).all() and (sol.new_cap % inst.module == 0).all()
            and not ((sol.new_cap > 0) & (sol.new_cap < inst.min_new)).any())


def vacia(inst: Instance) -> Solution:
    return Solution(np.zeros(inst.m, dtype=np.int64), "sin_actuacion")


class Evaluador:
    """Evalúa soluciones sobre un conjunto de escenarios (por defecto, todos), con caché."""

    def __init__(self, inst: Instance, escenarios: np.ndarray | None = None):
        self.inst = inst
        self.esc = np.arange(inst.S) if escenarios is None else np.asarray(escenarios)
        self.n_eval = 0
        self._cache: dict[tuple, dict] = {}
        n, m = inst.n, inst.m
        self.src, self.snk = 0, n + m + 1
        A = len(inst.arc_u)
        tails = np.concatenate([np.zeros(n, int), 1 + inst.arc_u, 1 + np.arange(n), 1 + np.arange(n), 1 + n + np.arange(m)])
        heads = np.concatenate([1 + np.arange(n), 1 + n + inst.arc_j, np.full(n, self.snk), np.full(n, self.snk),
                                np.full(m, self.snk)])
        big = int(inst.need.max() * ESCALA_FLUJO * n + 1)
        caps = np.concatenate([np.zeros(n, int), np.full(A, big), np.zeros(n, int), np.full(n, big), np.zeros(m, int)])
        costs = np.concatenate([np.zeros(n), np.round(inst.dist_penalty * inst.arc_d * ESCALA_COSTE),
                                np.round(inst.unmet_weight * ESCALA_COSTE),
                                np.round((inst.unmet_weight + inst.coverage_penalty) * ESCALA_COSTE),
                                np.zeros(m)]).astype(int)
        self.mcf = min_cost_flow.SimpleMinCostFlow()
        self.arcs = self.mcf.add_arcs_with_capacity_and_unit_cost(tails, heads, caps, costs)
        self.a_src = self.arcs[:n]
        self.a_arc = self.arcs[n:n + A]
        self.a_unmet = self.arcs[n + A:2 * n + A]
        self.a_viol = self.arcs[2 * n + A:3 * n + A]
        self.a_site = self.arcs[3 * n + A:]

    def _resolver(self, s: int, cap_total: np.ndarray) -> tuple[float, np.ndarray, float]:
        inst, mcf = self.inst, self.mcf
        q = np.round(inst.need[s] * ESCALA_FLUJO).astype(int)
        mcf.set_arc_capacities(self.a_src, q)
        mcf.set_arc_capacities(self.a_unmet, np.floor(q * (1 - inst.coverage_min)).astype(int))
        mcf.set_arc_capacities(self.a_site, np.round(cap_total * ESCALA_FLUJO).astype(int))
        tot = int(q.sum())
        sup = np.zeros(inst.n + inst.m + 2, dtype=int)
        sup[self.src], sup[self.snk] = tot, -tot
        mcf.set_nodes_supplies(np.arange(len(sup)), sup)
        if mcf.solve() != mcf.OPTIMAL:
            raise RuntimeError("Flujo de coste mínimo no óptimo")
        viol = mcf.flows(self.a_viol) / ESCALA_FLUJO
        unmet = mcf.flows(self.a_unmet) / ESCALA_FLUJO + viol
        dist = float((mcf.flows(self.a_arc) * inst.arc_d).sum() / ESCALA_FLUJO)
        self._ultimo_flujo = mcf.flows(self.a_arc) / ESCALA_FLUJO
        return mcf.optimal_cost() / (ESCALA_FLUJO * ESCALA_COSTE), unmet, dist, float(viol.sum())

    def accesibilidad(self, sol: Solution, detalle: bool = False) -> dict:
        """Indicadores espaciales de la etapa 2 (E2SFCA con decaimiento gaussiano en el radio de la instancia),
        sobre la necesidad media. No dependen de cómo se reparten las plazas en el flujo."""
        inst = self.inst
        R = max(float(inst.arc_d.max()), 1e-9)
        g = (np.exp(-0.5 * (inst.arc_d / R) ** 2) - np.exp(-0.5)) / (1 - np.exp(-0.5))
        need_u = inst.need.mean(axis=0)
        cap = inst.cap_existing + sol.new_cap
        dem_j = np.bincount(inst.arc_j, weights=g * need_u[inst.arc_u], minlength=inst.m)
        ratio = np.divide(cap, dem_j, out=np.zeros(inst.m), where=dem_j > 0)
        acc = np.bincount(inst.arc_u, weights=g * ratio[inst.arc_j], minlength=inst.n)
        media = cap.sum() / need_u.sum()
        r = {"acc_gini": gini_ponderado(acc, need_u),
             "acc_personas_bajo_mitad": float(need_u[acc < 0.5 * media].sum()),
             "acc_zonas_bajo_mitad": int((acc < 0.5 * media).sum()),
             "acc_min": float(acc.min() / media)}
        if detalle:
            r["acc_por_zona"] = acc
        return r

    def evaluar(self, sol: Solution, escenarios: np.ndarray | None = None, detalle: bool = False) -> dict:
        esc = self.esc if escenarios is None else np.asarray(escenarios)
        clave = (sol.key(), esc.tobytes(), detalle)
        if clave in self._cache:
            return self._cache[clave]
        self.n_eval += 1
        cap_total = self.inst.cap_existing + sol.new_cap
        obj, unmet_tot, unmet_u, dist, viol = [], [], np.zeros(self.inst.n), 0.0, 0.0
        flujo = np.zeros(len(self.inst.arc_u))
        for s in esc:
            o, un, d, v = self._resolver(int(s), cap_total)
            flujo += self._ultimo_flujo
            obj.append(o)
            unmet_tot.append(un.sum())
            unmet_u += un
            dist += d
            viol += v
        need = self.inst.need[esc].sum(axis=1)
        need_u = self.inst.need[esc].mean(axis=0)
        unmet_u /= len(esc)
        cob_u = np.clip(np.where(need_u > 0, 1 - unmet_u / np.maximum(need_u, 1e-12), 1.0), 0, 1)
        r = {"objetivo": float(np.mean(obj)), "objetivo_sd": float(np.std(obj)),
             "cobertura_min_zona": float(cob_u.min()),
             "gini_cobertura": gini_ponderado(cob_u, need_u),
             "personas_en_zonas_bajo_50": float(need_u[cob_u < 0.5].sum() / max(need_u.sum(), 1e-12) * need.mean()),
             "zonas_bajo_50": int((cob_u < 0.5).sum()),
             "deficit_cobertura_minima": float(viol / len(esc)),
             "sin_plaza": float(np.mean(unmet_tot)), "sin_plaza_p90": float(np.percentile(unmet_tot, 90)),
             "cobertura_pct": float(100 * (1 - np.sum(unmet_tot) / need.sum())),
             "km_medio": float(dist / max(need.sum() - np.sum(unmet_tot), 1e-9)),
             "coste": coste(self.inst, sol), "centros_nuevos": int((sol.new_cap > 0).sum()),
             "plazas_nuevas": int(sol.new_cap.sum())}
        r.update(self.accesibilidad(sol, detalle))
        if detalle:
            r["sin_plaza_por_zona"] = unmet_u
            r["cobertura_por_zona"] = cob_u
            r["flujo_medio_arco"] = flujo / len(esc)
        self._cache[clave] = r
        return r

"""Algoritmos heurísticos con una interfaz común:

    algoritmo(inst: Instance, ev: Evaluador, **parametros) -> Solution

El evaluador decide sobre qué escenarios se mide la calidad (todos, o una submuestra en una
simheurística), de modo que los algoritmos no dependen de cómo se generó la demanda.

Contenido:
  reparto_proporcional   línea base administrativa
  voraz_exacto           voraz perezoso (CELF) con evaluación exacta de cada movimiento
  construccion_grasp     constructiva semialeatorizada con criterio de ratio (alfa = 0: voraz por ratio)
  vnd                    descenso por vecindarios variables (traslado de bloque, traslado de centro,
                         cierre y redistribución, cierre y apertura) hasta óptimo local en todos los vecindarios
  grasp_vnd              GRASP: construcción semialeatorizada + VND, multiarranque con límite de tiempo
"""
from __future__ import annotations

import heapq
import time
from typing import Callable

import numpy as np

from .instance import Instance
from .solution import Evaluador, Solution, coste, es_factible, vacia


def _coste_extra(inst: Instance, sol: Solution, j: int, plazas: int) -> float:
    return (inst.fixed_cost[j] if sol.new_cap[j] == 0 else 0.0) + inst.unit_cost[j] * plazas


def _redondear_modulo(inst: Instance, x: float) -> int:
    return int(np.ceil(max(x, 0) / inst.module) * inst.module)


def reparto_proporcional(inst: Instance, ev: Evaluador, **_) -> Solution:
    """Regla administrativa sencilla: cubrir el déficit local (necesidad media menos capacidad propia) de las
    zonas con más déficit, sin tener en cuenta a los vecinos ni la equidad."""
    deficit = np.clip(inst.need.mean(axis=0) - inst.cap_existing, 0, None)
    sol = vacia(inst)
    for j in np.argsort(-deficit):
        if deficit[j] <= 0:
            break
        p = int(min(max(_redondear_modulo(inst, deficit[j]), inst.min_new), inst.cap_new_max[j]))
        while p >= max(inst.min_new, inst.module) and coste(inst, sol) + _coste_extra(inst, sol, j, p) > inst.budget:
            p -= inst.module
        if p >= max(inst.min_new, inst.module):
            sol.new_cap[j] = p
    sol.algoritmo = "reparto_proporcional"
    return sol


class CriterioRatio:
    """Puntuación de cada sitio candidato como ratio entre dos magnitudes:

        beneficio_j = min( sum_u w'_u * nocub_u * (1 - d_uj / R),  b_j * max_u w'_u )
        coste_j     = coste fijo (si el sitio está cerrado) + coste por plaza * b_j
        ratio_j     = beneficio_j / coste_j

    nocub_u es la necesidad sin plaza de la zona u con la solución actual (salida del flujo de segunda
    etapa, que ya tiene en cuenta la competencia entre zonas vecinas); w'_u es su peso de equidad, más la
    penalización de cobertura mínima si la zona está por debajo; b_j es el bloque de plazas que se añadiría
    en j, ajustado a la necesidad no cubierta alcanzable y al presupuesto restante.
    """

    def __init__(self, inst: Instance):
        self.inst = inst
        self.R = max(float(inst.arc_d.max()), 1e-9)
        self.decay = np.clip(1 - inst.arc_d / self.R, 0, 1)

    def puntuar(self, sol: Solution, det: dict, bloque_max: int = 10**9) -> tuple[np.ndarray, np.ndarray]:
        inst = self.inst
        nocub = det["sin_plaza_por_zona"]
        w = inst.unmet_weight + inst.coverage_penalty * (det["cobertura_por_zona"] < inst.coverage_min)
        alcanzable = np.bincount(inst.arc_j, weights=nocub[inst.arc_u], minlength=inst.m)
        beneficio_bruto = np.bincount(inst.arc_j, weights=w[inst.arc_u] * nocub[inst.arc_u] * self.decay, minlength=inst.m)
        wmax = np.zeros(inst.m)
        np.maximum.at(wmax, inst.arc_j, np.where(nocub[inst.arc_u] > 0, w[inst.arc_u], 0))
        restante = inst.budget - coste(inst, sol)
        bloque = np.zeros(inst.m, dtype=int)
        ratio = np.zeros(inst.m)
        for j in inst.candidates:
            libre = int(inst.cap_new_max[j] - sol.new_cap[j])
            fijo = inst.fixed_cost[j] if sol.new_cap[j] == 0 else 0.0
            asequible = int(((restante - fijo) // inst.unit_cost[j]) // inst.module * inst.module) if restante > fijo else 0
            b = min(_redondear_modulo(inst, alcanzable[j]), libre, asequible, bloque_max)
            if sol.new_cap[j] == 0:  # un centro nuevo debe alcanzar el tamaño mínimo
                b = max(b, inst.min_new) if min(libre, asequible) >= inst.min_new else 0
            if b < inst.module or beneficio_bruto[j] <= 0:
                continue
            bloque[j] = b
            ratio[j] = min(beneficio_bruto[j], b * wmax[j]) / (fijo + inst.unit_cost[j] * b)
        return ratio, bloque


def construccion_grasp(inst: Instance, ev: Evaluador, alfa: float = 0.3, rng=None, inicial: Solution | None = None,
                       criterio: CriterioRatio | None = None, **_) -> Solution:
    """Fase constructiva de GRASP con lista restringida de candidatos por valor:
    RCL = {j : ratio_j >= ratio_max - alfa * (ratio_max - ratio_min)}. Con alfa > 0 también se aleatoriza el
    tamaño del bloque. alfa = 0 equivale al voraz puro."""
    rng = rng or np.random.default_rng(0)
    crit = criterio or CriterioRatio(inst)
    sol = (inicial or vacia(inst)).copy()
    while True:
        ratio, bloque = crit.puntuar(sol, ev.evaluar(sol, detalle=True))
        cand = np.flatnonzero(ratio > 0)
        if len(cand) == 0:
            break
        rmax, rmin = ratio[cand].max(), ratio[cand].min()
        rcl = cand[ratio[cand] >= rmax - alfa * (rmax - rmin)]
        j = int(rng.choice(rcl))
        b = int(bloque[j])
        if alfa > 0:  # también se aleatoriza el tamaño del bloque (entre la mitad y el bloque completo)
            minimo = inst.min_new if sol.new_cap[j] == 0 else inst.module
            b = max(minimo, inst.module, int(round(b * rng.uniform(0.5, 1.0) / inst.module)) * inst.module)
        sol.new_cap[j] += b
    sol.algoritmo = "voraz_ratio" if alfa == 0 else f"grasp_construccion_a{alfa:g}"
    return sol


def voraz_ratio(inst: Instance, ev: Evaluador, **kw) -> Solution:
    t0 = time.time()
    s = construccion_grasp(inst, ev, alfa=0.0, **kw)
    s.info = {"segundos": time.time() - t0}
    return s


def voraz_exacto(inst: Instance, ev: Evaluador, paso: int = 25, **_) -> Solution:
    """Voraz perezoso (CELF): añade el bloque con mayor mejora exacta del objetivo por unidad de coste."""
    t0 = time.time()
    paso = max(inst.module, (paso // inst.module) * inst.module)
    sol = vacia(inst)
    f = ev.evaluar(sol)["objetivo"]
    cola = []
    for j in inst.candidates:
        t = sol.copy(); t.new_cap[j] += paso
        heapq.heappush(cola, (-(f - ev.evaluar(t)["objetivo"]) / _coste_extra(inst, sol, j, paso), int(j), 0))
    ronda = 0
    while cola:
        g_neg, j, r = heapq.heappop(cola)
        if -g_neg <= 0:
            break
        p = min(paso, int(inst.cap_new_max[j] - sol.new_cap[j]))
        while p > 0 and coste(inst, sol) + _coste_extra(inst, sol, j, p) > inst.budget:
            p -= inst.module
        if p <= 0:
            continue
        c = _coste_extra(inst, sol, j, p)
        if r < ronda:
            t = sol.copy(); t.new_cap[j] += p
            heapq.heappush(cola, (-(f - ev.evaluar(t)["objetivo"]) / c, j, ronda))
            continue
        sol.new_cap[j] += p
        f = ev.evaluar(sol)["objetivo"]
        ronda += 1
        heapq.heappush(cola, (g_neg, j, -1))
    sol.algoritmo = "voraz_exacto"
    sol.info = {"segundos": time.time() - t0}
    return sol


# ---------------------------------------------------------------- vecindarios (primera mejora)
def _destinos(crit: CriterioRatio, ev: Evaluador, sol: Solution, top_k: int) -> np.ndarray:
    ratio, _ = crit.puntuar(sol, ev.evaluar(sol, detalle=True))
    orden = np.argsort(-ratio)
    return orden[ratio[orden] > 0][:top_k]


def n_traslado_bloque(inst, ev, sol, f, crit, rng, bloques=(25, 10, 5), top_k=10, vecinos=15, t_fin=np.inf, **_):
    """Mueve un bloque de plazas de un sitio con capacidad nueva a otro sitio. Destinos: los top_k sitios
    con mejor ratio (dónde falta capacidad) y los 'vecinos' sitios más cercanos al origen (ajustes finos de
    localización que reducen distancias)."""
    prometedores = _destinos(crit, ev, sol, top_k)
    for a in rng.permutation(np.flatnonzero(sol.new_cap > 0)):
        cercanos = np.argsort(np.hypot(*(inst.site_xy - inst.site_xy[a]).T))[1:vecinos + 1]
        destinos = list(dict.fromkeys([*prometedores.tolist(), *cercanos.tolist()]))
        for b in sorted({max(inst.module, (x // inst.module) * inst.module) for x in bloques}, reverse=True):
            if b > sol.new_cap[a]:
                continue
            for j in destinos:
                if time.time() > t_fin:
                    return None
                if j == a or sol.new_cap[j] + b > inst.cap_new_max[j]:
                    continue
                t = sol.copy(); t.new_cap[a] -= b; t.new_cap[j] += b
                if es_factible(inst, t) and (ft := ev.evaluar(t)["objetivo"]) < f - 1e-6:
                    return t, ft
    return None


def n_traslado_centro(inst, ev, sol, f, crit, rng, top_k=10, vecinos=15, t_fin=np.inf, **_):
    """Traslada todas las plazas nuevas de un sitio a un sitio hoy sin plazas nuevas."""
    prometedores = [j for j in _destinos(crit, ev, sol, 3 * top_k) if sol.new_cap[j] == 0][:top_k]
    for a in rng.permutation(np.flatnonzero(sol.new_cap > 0)):
        cercanos = [j for j in np.argsort(np.hypot(*(inst.site_xy - inst.site_xy[a]).T))[1:vecinos + 1]
                    if sol.new_cap[j] == 0]
        for j in dict.fromkeys([*prometedores, *cercanos]):
            if time.time() > t_fin:
                return None
            if sol.new_cap[a] > inst.cap_new_max[j]:
                continue
            t = sol.copy(); t.new_cap[j] = t.new_cap[a]; t.new_cap[a] = 0
            if es_factible(inst, t) and (ft := ev.evaluar(t)["objetivo"]) < f - 1e-6:
                return t, ft
    return None


def n_cierre_redistribucion(inst, ev, sol, f, crit, rng, t_fin=np.inf, **_):
    """Cierra un sitio (libera su coste fijo) y reconstruye con el voraz por ratio."""
    for a in rng.permutation(np.flatnonzero(sol.new_cap > 0)):
        if time.time() > t_fin:
            return None
        t = sol.copy(); t.new_cap[a] = 0
        t = construccion_grasp(inst, ev, alfa=0.0, inicial=t, criterio=crit)
        if es_factible(inst, t) and (ft := ev.evaluar(t)["objetivo"]) < f - 1e-6:
            return t, ft
    return None


def n_cierre_apertura(inst, ev, sol, f, crit, rng, top_k=10, t_fin=np.inf, **_):
    """Cierra un sitio, abre otro sitio cerrado con el bloque que sugiere el criterio y reconstruye el resto
    del presupuesto con el voraz por ratio (movimiento compuesto: permite repartir un centro en dos)."""
    for a in rng.permutation(np.flatnonzero(sol.new_cap > 0)):
        base = sol.copy(); base.new_cap[a] = 0
        ratio, bloque = crit.puntuar(base, ev.evaluar(base, detalle=True))
        cerrados = [j for j in np.argsort(-ratio) if ratio[j] > 0 and base.new_cap[j] == 0 and j != a][:top_k]
        for j in cerrados:
            if time.time() > t_fin:
                return None
            t = base.copy(); t.new_cap[j] = bloque[j]
            t = construccion_grasp(inst, ev, alfa=0.0, inicial=t, criterio=crit)
            if es_factible(inst, t) and (ft := ev.evaluar(t)["objetivo"]) < f - 1e-6:
                return t, ft
    return None


VECINDARIOS: list[Callable] = [n_traslado_bloque, n_traslado_centro, n_cierre_redistribucion, n_cierre_apertura]


def vnd(inst: Instance, ev: Evaluador, inicial: Solution, vecindarios=VECINDARIOS, max_segundos: float = 120.0,
        semilla: int = 0, **kw) -> Solution:
    """Descenso por vecindarios variables: tras una mejora se vuelve al primer vecindario; termina cuando la
    solución es óptimo local en todos los vecindarios (o se agota el tiempo)."""
    t0 = time.time()
    rng = np.random.default_rng(semilla)
    crit = CriterioRatio(inst)
    sol = inicial.copy()
    f = ev.evaluar(sol)["objetivo"]
    k, mejoras = 0, [0] * len(vecindarios)
    while k < len(vecindarios) and time.time() - t0 < max_segundos:
        r = vecindarios[k](inst, ev, sol, f, crit, rng, t_fin=t0 + max_segundos, **kw)
        if r is not None:
            sol, f = r
            mejoras[k] += 1
            k = 0
        else:
            k += 1
    sol.algoritmo = f"{inicial.algoritmo}+vnd"
    sol.info = {"segundos": time.time() - t0, "mejoras_por_vecindario": mejoras,
                "optimo_local": k >= len(vecindarios), "objetivo_entrenamiento": f}
    return sol


def busqueda_local(inst: Instance, ev: Evaluador, inicial: Solution | None = None, **kw) -> Solution:
    """Compatibilidad: VND sobre la solución inicial (por defecto, el voraz por ratio)."""
    return vnd(inst, ev, inicial or voraz_ratio(inst, ev), **kw)


def grasp_vnd(inst: Instance, ev: Evaluador, alfa: float = 0.3, max_segundos: float = 120.0,
              max_iter: int = 1000, semilla: int = 0, vnd_segundos: float = 60.0, **kw) -> Solution:
    """GRASP multiarranque: construcción semialeatorizada con el criterio de ratio + VND."""
    t0 = time.time()
    rng = np.random.default_rng(semilla)
    crit = CriterioRatio(inst)
    mejor, f_mejor, historial = None, np.inf, []
    it = 0
    while it < max_iter and time.time() - t0 < max_segundos:
        s = construccion_grasp(inst, ev, alfa=alfa, rng=rng, criterio=crit)
        f_c = ev.evaluar(s)["objetivo"]
        restante = max_segundos - (time.time() - t0)
        s = vnd(inst, ev, s, max_segundos=min(vnd_segundos, max(restante, 0)), semilla=int(rng.integers(1e9)), **kw)
        f = ev.evaluar(s)["objetivo"]
        historial.append((round(f_c, 3), round(f, 3)))
        if f < f_mejor:
            mejor, f_mejor = s, f
        it += 1
    mejor = mejor.copy()
    mejor.algoritmo = f"grasp_a{alfa:g}+vnd"
    mejor.info = {"segundos": time.time() - t0, "iteraciones": it, "historial": historial,
                  "objetivo_entrenamiento": f_mejor}
    return mejor


def construccion_semivoraz(inst: Instance, ev: Evaluador, alfa: float = -1.0, iters_sin_anadir: int = 5,
                           rng=None, inicial: Solution | None = None, **_) -> Solution:
    """Construcción semivoraz con la estructura de SemigreedyConstructiveGreedyRect (BPP_TabuSearch):

    - Elementos: zonas con necesidad sin cubrir, ordenadas por necesidad ponderada (w_u * nocub_u), de mayor a
      menor; se atiende siempre la primera (como los rectángulos en el BPP).
    - Posiciones: sitios que alcanzan esa zona, ordenados por el ratio beneficio/coste; se elige al azar dentro
      de la RCL por umbral g_max - alfa * (g_max - g_min) (como las celdas).
    - Si añadir en el sitio elegido no es posible (presupuesto, capacidad, tamaño mínimo) se prueba otro, hasta
      iters_sin_anadir intentos fallidos; entonces la zona se descarta.
    - Tras cada inserción solo se actualizan los candidatos afectados: la necesidad sin cubrir de las zonas al
      alcance del sitio se reduce localmente (las más cercanas primero), sin recalcular el flujo completo.
      El flujo exacto se evalúa una vez al inicio; la solución final se evalúa con el evaluador.
    alfa < 0: se sortea un alfa en [0, 1] en cada construcción.
    """
    rng = rng or np.random.default_rng(0)
    a = rng.random() if alfa < 0 else alfa
    sol = (inicial or vacia(inst)).copy()
    det = ev.evaluar(sol, detalle=True)
    nocub = det["sin_plaza_por_zona"].astype(float).copy()
    w = inst.unmet_weight + inst.coverage_penalty * (det["cobertura_por_zona"] < inst.coverage_min)
    R = max(float(inst.arc_d.max()), 1e-9)
    decay = np.clip(1 - inst.arc_d / R, 0, 1)
    arcos_u = [np.flatnonzero(inst.arc_u == u) for u in range(inst.n)]
    arcos_j = [np.flatnonzero(inst.arc_j == j) for j in range(inst.m)]
    gastado = coste(inst, sol)

    def bloque_y_ratio(j):
        libre = int(inst.cap_new_max[j] - sol.new_cap[j])
        fijo = inst.fixed_cost[j] if sol.new_cap[j] == 0 else 0.0
        restante = inst.budget - gastado - fijo
        if restante < inst.unit_cost[j] * inst.module or libre < inst.module:
            return 0, 0.0
        asequible = int((restante // inst.unit_cost[j]) // inst.module * inst.module)
        aj = arcos_j[j]
        alcanzable = nocub[inst.arc_u[aj]].sum()
        b = min(_redondear_modulo(inst, alcanzable), libre, asequible)
        if sol.new_cap[j] == 0:
            if min(libre, asequible) < inst.min_new:
                return 0, 0.0
            b = max(b, inst.min_new)
        if b < inst.module:
            return 0, 0.0
        beneficio = min((w[inst.arc_u[aj]] * nocub[inst.arc_u[aj]] * decay[aj]).sum(), b * w[inst.arc_u[aj]].max())
        return b, beneficio / (fijo + inst.unit_cost[j] * b)

    zonas = [int(u) for u in np.argsort(-(w * nocub)) if nocub[u] >= 0.5]
    while zonas:
        u = zonas.pop(0)
        sitios = inst.arc_j[arcos_u[u]]
        cand = []
        for j in sitios:
            if inst.cap_new_max[j] <= 0:
                continue
            b, r = bloque_y_ratio(int(j))
            if r > 0:
                cand.append((r, int(j), b))
        cand.sort(reverse=True)
        anadido, fallos = False, 0
        while cand and not anadido and fallos < iters_sin_anadir:
            gmax, gmin = cand[0][0], cand[-1][0]
            umbral = gmax - a * (gmax - gmin)
            limite = sum(1 for c in cand if c[0] >= umbral)
            r, j, b = cand.pop(int(rng.integers(limite)))
            extra = _coste_extra(inst, sol, j, b)
            if gastado + extra <= inst.budget + 1e-9 and sol.new_cap[j] + b <= inst.cap_new_max[j]:
                sol.new_cap[j] += b
                gastado += extra
                anadido = True
                # actualización local de candidatos: repartir las plazas entre las zonas al alcance, cercanas primero
                aj = arcos_j[j][np.argsort(inst.arc_d[arcos_j[j]])]
                resto = float(b)
                for arc in aj:
                    v = inst.arc_u[arc]
                    tom = min(resto, nocub[v])
                    nocub[v] -= tom
                    resto -= tom
                    if resto <= 0:
                        break
            else:
                fallos += 1
        if anadido and nocub[u] >= 0.5:
            zonas.append(u)
        zonas = sorted((z for z in zonas if nocub[z] >= 0.5), key=lambda z: -(w[z] * nocub[z]))
        if inst.budget - gastado < inst.unit_cost.min() * inst.module:
            break
    sol.algoritmo = f"semivoraz_a{'aleat' if alfa < 0 else f'{alfa:g}'}"
    return sol


def grasp_semivoraz_vnd(inst: Instance, ev: Evaluador, alfa: float = -1.0, iters_sin_anadir: int = 5,
                        max_segundos: float = 120.0, max_iter: int = 1000, semilla: int = 0,
                        vnd_segundos: float = 60.0, **kw) -> Solution:
    """GRASP con la construcción semivoraz (estructura de BPP_TabuSearch) + VND, multiarranque con límite de tiempo."""
    t0 = time.time()
    rng = np.random.default_rng(semilla)
    mejor, f_mejor, historial, it = None, np.inf, [], 0
    while it < max_iter and time.time() - t0 < max_segundos:
        s = construccion_semivoraz(inst, ev, alfa=alfa, iters_sin_anadir=iters_sin_anadir, rng=rng)
        f_c = ev.evaluar(s)["objetivo"]
        restante = max_segundos - (time.time() - t0)
        s = vnd(inst, ev, s, max_segundos=min(vnd_segundos, max(restante, 0)), semilla=int(rng.integers(1e9)), **kw)
        f = ev.evaluar(s)["objetivo"]
        historial.append((round(f_c, 3), round(f, 3)))
        if f < f_mejor:
            mejor, f_mejor = s, f
        it += 1
    mejor = mejor.copy()
    mejor.algoritmo = f"grasp_semivoraz_a{'aleat' if alfa < 0 else f'{alfa:g}'}+vnd"
    mejor.info = {"segundos": time.time() - t0, "iteraciones": it, "historial": historial, "objetivo_entrenamiento": f_mejor}
    return mejor


ALGORITMOS = {"reparto_proporcional": reparto_proporcional, "voraz_exacto": voraz_exacto,
              "voraz_ratio": voraz_ratio, "grasp_vnd": grasp_vnd, "grasp_semivoraz_vnd": grasp_semivoraz_vnd}
# alias de la versión anterior
voraz = voraz_exacto

"""Etapa 4: experimento de optimización de plazas de centro de día.

Protocolo (aproximación por media muestral con validación fuera de muestra):
  1. Construye la instancia con los parámetros indicados y la guarda en data/instances/.
  2. Optimiza cada algoritmo sobre una submuestra de escenarios de entrenamiento.
  3. Evalúa todas las soluciones sobre los 500 escenarios (fuera de muestra).
Genera data/processed/soluciones.csv, data/processed/resultados_optimizacion.csv y reports/optimizacion.md.

Uso:  python -m cuidacerca.optimize [--presupuesto 1000] [--meta 5.8] [--anio 2030] [--escenarios 20]
"""
from __future__ import annotations

import argparse
import time

import numpy as np
import pandas as pd

from .config import DATA_PROCESSED, REPORTS, ROOT
from .opt.heuristics import busqueda_local, reparto_proporcional, voraz
from .opt.instance import Instance, ParametrosInstancia, construir_instancia
from .opt.milp import resolver_milp
from .opt.solution import Evaluador, es_factible, vacia


def experimento(p: ParametrosInstancia, n_train: int = 20, limite_milp: float = 180.0,
                limite_bl: float = 60.0, semilla: int = 1) -> tuple[pd.DataFrame, pd.DataFrame, Instance]:
    inst = construir_instancia(p)
    (ROOT / "data" / "instances").mkdir(parents=True, exist_ok=True)
    inst.save(ROOT / "data" / "instances" / inst.nombre)
    print(inst.resumen())
    train = inst.subsample(n_train, seed=semilla)
    ev_train, ev_test = Evaluador(train), Evaluador(inst)

    sols = {"sin_actuacion": vacia(inst)}
    t = time.time(); sols["reparto_proporcional"] = reparto_proporcional(train, ev_train); sols["reparto_proporcional"].info = {"segundos": time.time() - t}
    sols["voraz"] = voraz(train, ev_train)
    sols["proporcional+busqueda_local"] = busqueda_local(train, ev_train, inicial=sols["reparto_proporcional"], max_segundos=limite_bl, semilla=semilla)
    sols["voraz+busqueda_local"] = busqueda_local(train, ev_train, inicial=sols["voraz"], max_segundos=limite_bl, semilla=semilla)
    try:
        sols["milp"] = resolver_milp(train, solver="SCIP", limite_s=limite_milp)
    except RuntimeError as e:
        print(f"MILP sin solución: {e}")

    filas, asign = [], []
    base = ev_test.evaluar(sols["sin_actuacion"])
    for nombre, s in sols.items():
        assert es_factible(inst, s), nombre
        rt, rv = ev_train.evaluar(s), ev_test.evaluar(s)
        info = s.info or {}
        filas.append({"algoritmo": nombre, "objetivo_entrenamiento": rt["objetivo"], "objetivo_500": rv["objetivo"],
                      "sin_plaza_500": rv["sin_plaza"], "sin_plaza_p90": rv["sin_plaza_p90"],
                      "cobertura_pct": rv["cobertura_pct"], "personas_atendidas_extra": base["sin_plaza"] - rv["sin_plaza"],
                      "km_medio": rv["km_medio"], "centros_nuevos": rv["centros_nuevos"], "plazas_nuevas": rv["plazas_nuevas"],
                      "coste": rv["coste"], "segundos": info.get("segundos", 0.0), "gap_milp_pct": info.get("gap_pct")})
        for j in np.flatnonzero(s.new_cap > 0):
            asign.append({"algoritmo": nombre, "id_unidad": inst.site_ids[j], "nombre": inst.meta["nombres_zona"][j],
                          "plazas_nuevas": int(s.new_cap[j]), "plazas_existentes": float(inst.cap_existing[j])})
    return pd.DataFrame(filas), pd.DataFrame(asign), inst


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--presupuesto", type=float, default=1000.0)
    ap.add_argument("--meta", type=float, default=5.8)
    ap.add_argument("--anio", type=int, default=2030)
    ap.add_argument("--escenarios", type=int, default=20)
    ap.add_argument("--limite-milp", type=float, default=180.0)
    ap.add_argument("--limite-bl", type=float, default=60.0)
    a = ap.parse_args()
    p = ParametrosInstancia(anio=a.anio, meta_por_100=a.meta, presupuesto=a.presupuesto)
    res, asign, inst = experimento(p, n_train=a.escenarios, limite_milp=a.limite_milp,
                                   limite_bl=a.limite_bl)
    res.round(3).to_csv(DATA_PROCESSED / "resultados_optimizacion.csv", index=False)
    asign.to_csv(DATA_PROCESSED / "soluciones.csv", index=False)

    L = ["# Optimización de plazas de centro de día", "", inst.resumen(), "",
         f"Entrenamiento con {a.escenarios} escenarios; evaluación fuera de muestra con {inst.S}. "
         "Objetivo: personas sin plaza accesible (media sobre escenarios) + 0,01 por persona-km.", "",
         "| Algoritmo | Objetivo (500 esc.) | Sin plaza (media) | Sin plaza (p90) | Personas atendidas extra | Centros | Plazas | Segundos |",
         "|---|---|---|---|---|---|---|---|"]
    for _, r in res.iterrows():
        L.append(f"| {r['algoritmo']} | {r['objetivo_500']:,.1f} | {r['sin_plaza_500']:,.0f} | {r['sin_plaza_p90']:,.0f} | "
                 f"{r['personas_atendidas_extra']:,.0f} | {r['centros_nuevos']} | {r['plazas_nuevas']} | {r['segundos']:.1f} |")
    if "milp" in set(res["algoritmo"]):
        m = res.set_index("algoritmo").loc["milp"]
        L += ["", f"Gap del MILP sobre la muestra de entrenamiento: {m['gap_milp_pct']:.2f} %."]
    mejor = res.loc[res["objetivo_500"].idxmin(), "algoritmo"]
    L += ["", f"## Plan con menor objetivo fuera de muestra: {mejor}"]
    for _, r in asign[asign["algoritmo"] == mejor].sort_values("plazas_nuevas", ascending=False).iterrows():
        L.append(f"- {r['nombre']}: +{r['plazas_nuevas']} plazas (hoy {r['plazas_existentes']:.0f} con financiación pública).")
    (REPORTS / "optimizacion.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()

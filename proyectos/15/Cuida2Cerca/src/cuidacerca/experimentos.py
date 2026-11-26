"""Experimentos de la etapa 4: comparación de algoritmos y compromiso eficiencia-equidad.

Cada configuración fija los pesos de equidad (beta) y la cobertura mínima (cmin). Cada algoritmo optimiza
sobre una submuestra de escenarios (entrenamiento) y se evalúa fuera de muestra con los 500 escenarios:
  - con el objetivo de su propio modelo (para comparar algoritmos entre sí), y
  - con un evaluador neutral (pesos 1, sin cobertura mínima) e indicadores de equidad comunes (para comparar
    configuraciones entre sí sin que el reparto de la segunda etapa dependa de los pesos).
Los resultados se añaden de forma incremental, de modo que se puede ejecutar por partes.

Uso:
  python -m cuidacerca.experimentos --config base --algoritmos proporcional,voraz_ratio,vnd,grasp,milp
  python -m cuidacerca.experimentos --informe
"""
from __future__ import annotations

import argparse
import json
import time
from dataclasses import replace

import numpy as np
import pandas as pd

from .config import DATA_PROCESSED, REPORTS
from .opt.heuristics import grasp_vnd, reparto_proporcional, voraz_exacto, voraz_ratio, vnd
from .opt.instance import Instance, ParametrosInstancia, construir_instancia
from .opt.milp import resolver_milp
from .opt.solution import Evaluador, Solution, es_factible

CONFIGS = {
    "base": dict(beta_equidad=0, cobertura_minima=0),
    "beta1": dict(beta_equidad=1, cobertura_minima=0),
    "beta2": dict(beta_equidad=2, cobertura_minima=0),
    "beta4": dict(beta_equidad=4, cobertura_minima=0),
    "beta8": dict(beta_equidad=8, cobertura_minima=0),
    "cmin50": dict(beta_equidad=0, cobertura_minima=0.5),
    "beta4_cmin50": dict(beta_equidad=4, cobertura_minima=0.5),
}
DIR = DATA_PROCESSED / "experimentos"
N_TRAIN, SEMILLA = 20, 1


def neutral(inst: Instance) -> Instance:
    return replace(inst, unmet_weight=np.ones(inst.n), coverage_min=0.0)


def ejecutar(nombre_config: str, algoritmos: list[str], t_grasp=45.0, t_vnd=40.0, t_milp=90.0) -> None:
    p = ParametrosInstancia(**CONFIGS[nombre_config])
    inst = construir_instancia(p)
    train = inst.subsample(N_TRAIN, seed=SEMILLA)
    ev_tr, ev_te, ev_neu = Evaluador(train), Evaluador(inst), Evaluador(neutral(inst))
    DIR.mkdir(parents=True, exist_ok=True)
    for alg in algoritmos:
        t0 = time.time()
        if alg == "proporcional":
            s = reparto_proporcional(train, ev_tr)
        elif alg == "voraz_exacto":
            s = voraz_exacto(train, ev_tr)
        elif alg == "voraz_ratio":
            s = voraz_ratio(train, ev_tr)
        elif alg == "vnd":
            s = vnd(train, ev_tr, voraz_ratio(train, ev_tr), max_segundos=t_vnd)
        elif alg == "grasp":
            s = grasp_vnd(train, ev_tr, alfa=0.3, max_segundos=t_grasp, vnd_segundos=t_vnd, semilla=SEMILLA)
        elif alg == "milp":
            s = resolver_milp(train, solver="SCIP", limite_s=t_milp)
        else:
            raise ValueError(alg)
        seg = time.time() - t0
        assert es_factible(inst, s), alg
        rm, rn = ev_te.evaluar(s), ev_neu.evaluar(s)
        fila = {"config": nombre_config, **CONFIGS[nombre_config], "algoritmo": s.algoritmo or alg,
                "objetivo_modelo_train": ev_tr.evaluar(s)["objetivo"], "objetivo_modelo_500": rm["objetivo"],
                "deficit_cobertura_minima": rm["deficit_cobertura_minima"], "segundos": seg,
                "gap_milp_pct": (s.info or {}).get("gap_pct"),
                **{f"{k}": v for k, v in rn.items() if not isinstance(v, np.ndarray) and k not in ("objetivo", "objetivo_sd")}}
        f = DIR / "resultados.csv"
        df = pd.DataFrame([fila])
        if f.exists():
            prev = pd.read_csv(f)
            prev = prev[~((prev["config"] == nombre_config) & (prev["algoritmo"] == fila["algoritmo"]))]
            df = pd.concat([prev, df], ignore_index=True)
        df.to_csv(f, index=False)
        sol = pd.DataFrame({"config": nombre_config, "algoritmo": fila["algoritmo"], "id_unidad": inst.site_ids,
                            "nombre": inst.meta["nombres_zona"], "plazas_nuevas": s.new_cap,
                            "plazas_existentes": inst.cap_existing})
        sol = sol[sol["plazas_nuevas"] > 0]
        fs = DIR / "soluciones.csv"
        if fs.exists():
            prev = pd.read_csv(fs)
            prev = prev[~((prev["config"] == nombre_config) & (prev["algoritmo"] == fila["algoritmo"]))]
            sol = pd.concat([prev, sol], ignore_index=True)
        sol.to_csv(fs, index=False)
        print(f"[{nombre_config}] {fila['algoritmo']}: objetivo {rm['objetivo']:.2f} | sin plaza {rn['sin_plaza']:.0f} | "
              f"zonas <50 % {rn['zonas_bajo_50']} | Gini acc {rn['acc_gini']:.3f} | {seg:.1f} s")


def informe() -> None:
    r = pd.read_csv(DIR / "resultados.csv")
    s = pd.read_csv(DIR / "soluciones.csv")
    L = ["# Optimización de plazas de centro de día: algoritmos y compromiso eficiencia-equidad", "",
         f"Instancia: 2030, meta 5,8 plazas/100, radio 15 km, presupuesto 1.000 plazas equivalentes "
         f"(coste fijo 20 por centro nuevo). Entrenamiento con {N_TRAIN} escenarios, evaluación con 500.", "",
         "## Comparación de algoritmos (objetivo del propio modelo, 500 escenarios)", ""]
    for cfg, g in r.groupby("config", sort=False):
        ref = g["objetivo_modelo_500"].min()
        L += [f"### {cfg} (beta = {g['beta_equidad'].iat[0]:g}, cobertura mínima = {g['cobertura_minima'].iat[0]:g})", "",
              "| Algoritmo | Objetivo (500) | Diferencia con el mejor | Segundos |", "|---|---|---|---|"]
        for _, x in g.sort_values("objetivo_modelo_500").iterrows():
            L.append(f"| {x['algoritmo']} | {x['objetivo_modelo_500']:,.2f} | "
                     f"{(x['objetivo_modelo_500'] / ref - 1) * 100:+.2f} % | {x['segundos']:.1f} |")
        L.append("")
    L += ["## Compromiso eficiencia-equidad (mejor solución de cada configuración, evaluador neutral)", "",
          "| Configuración | Personas sin plaza | Zonas con cobertura < 50 % | Necesidad en esas zonas | "
          "Gini de accesibilidad | Zonas con accesibilidad < mitad de la media | Km medio | Centros nuevos |",
          "|---|---|---|---|---|---|---|---|"]
    mejor = r.loc[r.groupby("config")["objetivo_modelo_500"].idxmin()].set_index("config").reindex(
        [c for c in CONFIGS if c in set(r["config"])])
    for cfg, x in mejor.iterrows():
        L.append(f"| {cfg} | {x['sin_plaza']:,.0f} | {x['zonas_bajo_50']:.0f} | {x['personas_en_zonas_bajo_50']:,.0f} | "
                 f"{x['acc_gini']:.3f} | {x['acc_zonas_bajo_mitad']:.0f} | {x['km_medio']:.2f} | {x['centros_nuevos']:.0f} |")
    L += ["", "## Dónde van las plazas (mejor solución de cada configuración)"]
    for cfg, x in mejor.iterrows():
        g = s[(s["config"] == cfg) & (s["algoritmo"] == x["algoritmo"])].sort_values("plazas_nuevas", ascending=False)
        L.append(f"- {cfg}: " + "; ".join(f"{n} +{int(p)}" for n, p in zip(g["nombre"], g["plazas_nuevas"])))
    (REPORTS / "optimizacion.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    mejor.reset_index().to_csv(DATA_PROCESSED / "frontera_equidad.csv", index=False)
    print("\n".join(L))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="base")
    ap.add_argument("--algoritmos", default="proporcional,voraz_ratio,vnd,grasp,milp")
    ap.add_argument("--t-grasp", type=float, default=45.0)
    ap.add_argument("--t-milp", type=float, default=90.0)
    ap.add_argument("--informe", action="store_true")
    a = ap.parse_args()
    if a.informe:
        informe()
    else:
        ejecutar(a.config, a.algoritmos.split(","), t_grasp=a.t_grasp, t_milp=a.t_milp)

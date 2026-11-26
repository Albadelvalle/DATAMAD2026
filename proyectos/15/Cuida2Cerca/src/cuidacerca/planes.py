"""Precalcula planes de plazas de centro de día para la web: varios presupuestos y configuraciones de
equidad, resueltos con el voraz por ratio + VND y evaluados con el evaluador neutral sobre 500 escenarios.
Para cada centro nuevo se guarda qué municipios usarían sus plazas (flujo medio atribuible a las plazas
nuevas), que son los jugadores del juego de reparto de costes.

Uso (incremental):  python -m cuidacerca.planes --presupuestos 500,1000 --configs base,beta4
"""
from __future__ import annotations

import argparse
import json
import time

import numpy as np

from .config import DATA_PROCESSED
from .experimentos import CONFIGS, N_TRAIN, SEMILLA, neutral
from .opt.heuristics import voraz_ratio, vnd
from .opt.instance import ParametrosInstancia, construir_instancia
from .opt.solution import Evaluador, es_factible

FICHERO = DATA_PROCESSED / "planes.json"
PRESUPUESTOS = (500, 1000, 2000)


def calcular(presupuesto: float, config: str, t_vnd: float = 30.0, radio: float = 15.0) -> dict:
    t0 = time.time()
    p = ParametrosInstancia(presupuesto=presupuesto, radio_km=radio, **CONFIGS[config])
    inst = construir_instancia(p)
    tr = inst.subsample(N_TRAIN, seed=SEMILLA)
    ev = Evaluador(tr)
    s = vnd(tr, ev, voraz_ratio(tr, ev), max_segundos=t_vnd)
    assert es_factible(inst, s)
    r = Evaluador(neutral(inst)).evaluar(s, detalle=True)
    cod = [i.split("-")[0] for i in inst.unit_ids]  # municipio de cada zona (los distritos -> Madrid)
    nombres = inst.meta["nombres_zona"]
    centros = []
    for j in np.flatnonzero(s.new_cap > 0):
        arcos = np.flatnonzero(inst.arc_j == j)
        cuota_nueva = s.new_cap[j] / (inst.cap_existing[j] + s.new_cap[j])
        usuarios: dict[str, dict] = {}
        for a in arcos:
            f = r["flujo_medio_arco"][a] * cuota_nueva
            if f < 0.05:
                continue
            u = inst.arc_u[a]
            m = cod[u]
            nombre = "Madrid" if m == "28079" else nombres[u]
            e = usuarios.setdefault(m, {"cod_ine": m, "nombre": nombre, "plazas": 0.0, "zona_ref": int(u)})
            e["plazas"] += float(f)
        centros.append({"sitio": int(j), "id_unidad": str(inst.site_ids[j]), "nombre": nombres[j],
                        "plazas_nuevas": int(s.new_cap[j]), "plazas_existentes": float(inst.cap_existing[j]),
                        "usuarios": sorted(usuarios.values(), key=lambda e: -e["plazas"])})
    metricas = {k: (float(v) if isinstance(v, (float, np.floating)) else int(v))
                for k, v in r.items() if not isinstance(v, np.ndarray)}
    sufijo = "" if radio == 15 else f"_R{int(radio)}"
    return {"id": f"{config}_B{int(presupuesto)}{sufijo}", "config": config, **CONFIGS[config], "presupuesto": presupuesto,
            "radio_km": radio,
            "algoritmo": s.algoritmo, "segundos": time.time() - t0, "optimo_local": s.info.get("optimo_local"),
            "metricas": metricas, "centros": centros,
            "cobertura_por_zona": np.round(r["cobertura_por_zona"], 4).tolist(),
            "acc_por_zona": np.round(r["acc_por_zona"] * 100, 3).tolist()}


def frente(planes: list[dict]) -> None:
    """Marca los planes no dominados (por presupuesto y radio) en personas sin plaza y zonas con cobertura < 50 %."""
    for p in planes:
        a = (p["metricas"]["sin_plaza"], p["metricas"]["zonas_bajo_50"])
        p["no_dominado"] = not any(
            o["presupuesto"] == p["presupuesto"] and o.get("radio_km", 15) == p.get("radio_km", 15) and o is not p
            and (o["metricas"]["sin_plaza"] <= a[0] and o["metricas"]["zonas_bajo_50"] <= a[1])
            and (o["metricas"]["sin_plaza"] < a[0] or o["metricas"]["zonas_bajo_50"] < a[1])
            for o in planes)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--presupuestos", default=",".join(map(str, PRESUPUESTOS)))
    ap.add_argument("--configs", default="base,beta2,beta4,beta8,cmin50,beta4_cmin50")
    ap.add_argument("--t-vnd", type=float, default=30.0)
    ap.add_argument("--radio", type=float, default=15.0)
    a = ap.parse_args()
    planes = json.loads(FICHERO.read_text()) if FICHERO.exists() else []
    for b in map(float, a.presupuestos.split(",")):
        for c in a.configs.split(","):
            nuevo = calcular(b, c, a.t_vnd, a.radio)
            planes = [p for p in planes if p["id"] != nuevo["id"]] + [nuevo]
            frente(planes)
            FICHERO.write_text(json.dumps(planes, ensure_ascii=False))
            m = nuevo["metricas"]
            print(f"{nuevo['id']}: sin plaza {m['sin_plaza']:.0f}, zonas<50 {m['zonas_bajo_50']}, "
                  f"centros {m['centros_nuevos']}, {nuevo['segundos']:.0f} s")


if __name__ == "__main__":
    main()

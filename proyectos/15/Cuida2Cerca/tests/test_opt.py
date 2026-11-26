"""Comprobaciones del módulo de optimización sobre una instancia sintética pequeña."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from cuidacerca.opt.heuristics import (busqueda_local, grasp_vnd, reparto_proporcional, voraz,  # noqa: E402
                                       voraz_ratio, vnd)
from cuidacerca.opt.instance import Instance  # noqa: E402
from cuidacerca.opt.milp import resolver_milp  # noqa: E402
from cuidacerca.opt.solution import Evaluador, Solution, es_factible, vacia  # noqa: E402


def instancia_juguete(S=4, seed=0) -> Instance:
    rng = np.random.default_rng(seed)
    xy = np.array([[0, 0], [5000, 0], [10000, 0], [40000, 0]], float)
    D = np.hypot(*(xy[:, None, :] - xy[None, :, :]).transpose(2, 0, 1)) / 1000
    au, aj = np.nonzero(D <= 12)
    need = rng.uniform(20, 40, size=(S, 4))
    return Instance("juguete", np.array(list("abcd")), xy, np.array(list("abcd")), xy.copy(),
                    cap_existing=np.array([30.0, 0, 0, 0]), cap_new_max=np.full(4, 60.0),
                    arc_u=au, arc_j=aj, arc_d=D[au, aj], need=need,
                    fixed_cost=np.full(4, 10.0), unit_cost=np.ones(4), budget=80.0, module=5)


def test_evaluador_sin_actuacion():
    inst = instancia_juguete()
    r = Evaluador(inst).evaluar(vacia(inst))
    # la zona d (aislada) no tiene ninguna plaza: toda su necesidad queda sin cubrir
    assert r["sin_plaza"] >= inst.need[:, 3].mean() - 1e-6


def test_milp_coincide_con_evaluador_y_domina_heuristicas():
    inst = instancia_juguete()
    ev = Evaluador(inst)
    m = resolver_milp(inst, limite_s=30)
    assert es_factible(inst, m)
    assert abs(ev.evaluar(m)["objetivo"] - m.info["objetivo_saa"]) < 0.05
    for alg in (reparto_proporcional, voraz):
        assert ev.evaluar(alg(inst, ev))["objetivo"] >= m.info["cota_inferior"] - 0.05


def test_busqueda_local_no_empeora():
    inst = instancia_juguete()
    ev = Evaluador(inst)
    ini = reparto_proporcional(inst, ev)
    bl = busqueda_local(inst, ev, inicial=ini, max_segundos=10)
    assert es_factible(inst, bl) and ev.evaluar(bl)["objetivo"] <= ev.evaluar(ini)["objetivo"] + 1e-9


def test_grasp_vnd_alcanza_optimo_en_juguete():
    inst = instancia_juguete()
    ev = Evaluador(inst)
    m = resolver_milp(inst, limite_s=30)
    g = grasp_vnd(inst, ev, alfa=0.3, max_segundos=10, max_iter=10)
    v = vnd(inst, ev, voraz_ratio(inst, ev), max_segundos=10)
    assert es_factible(inst, g) and es_factible(inst, v) and v.info["optimo_local"]
    assert ev.evaluar(g)["objetivo"] <= m.info["objetivo_saa"] * 1.01


def test_cobertura_minima_coherente_milp_evaluador():
    from dataclasses import replace
    inst = replace(instancia_juguete(), coverage_min=0.5, coverage_penalty=10.0, unmet_weight=np.array([1, 1, 1, 3.0]))
    m = resolver_milp(inst, limite_s=30)
    assert abs(Evaluador(inst).evaluar(m)["objetivo"] - m.info["objetivo_saa"]) < 0.05


def test_persistencia_instancia(tmp=Path("/tmp")):
    inst = instancia_juguete()
    inst.save(tmp / "inst_juguete")
    otra = Instance.load(tmp / "inst_juguete")
    assert np.allclose(otra.need, inst.need) and otra.budget == inst.budget


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f()
            print("OK", n)

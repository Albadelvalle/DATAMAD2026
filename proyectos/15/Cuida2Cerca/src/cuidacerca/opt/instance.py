"""Formato de instancia genérico para problemas de localización de plazas bajo demanda incierta.

Una instancia contiene todo lo que necesita un algoritmo y nada más:
  - n zonas de demanda con su necesidad de plazas en S escenarios: need[s, u]
  - m sitios (existentes y/o candidatos) con capacidad actual y capacidad nueva máxima
  - arcos zona-sitio con su distancia (solo dentro del radio de captación)
  - costes: fijo por abrir capacidad nueva en un sitio y variable por plaza, y un presupuesto
  - penalizaciones: por persona sin plaza (ponderable por zona), por persona-km recorrido y por persona por
    debajo de una cobertura mínima de cada zona (restricción blanda)
Las unidades de coste son libres (plazas equivalentes, euros...): el modelo solo exige coherencia.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import DATA_PROCESSED
from ..geo import dist_km


@dataclass
class Instance:
    nombre: str
    unit_ids: np.ndarray          # (n,) identificadores de zona
    unit_xy: np.ndarray           # (n, 2) coordenadas UTM
    site_ids: np.ndarray          # (m,)
    site_xy: np.ndarray           # (m, 2)
    cap_existing: np.ndarray      # (m,) plazas actuales
    cap_new_max: np.ndarray       # (m,) plazas nuevas máximas (0 = no candidato)
    arc_u: np.ndarray             # (a,) índice de zona
    arc_j: np.ndarray             # (a,) índice de sitio
    arc_d: np.ndarray             # (a,) distancia en km
    need: np.ndarray              # (S, n) plazas necesarias por escenario
    fixed_cost: np.ndarray        # (m,) coste fijo por añadir capacidad en el sitio
    unit_cost: np.ndarray         # (m,) coste por plaza nueva
    budget: float
    module: int = 5               # granularidad de la capacidad nueva (plazas)
    unmet_weight: np.ndarray | None = None   # (n,) penalización por persona sin plaza (pesos de equidad)
    dist_penalty: float = 0.01    # penalización por persona-km (desempata a favor de la cercanía)
    coverage_min: float = 0.0     # cobertura mínima exigida a cada zona (fracción de su necesidad)
    coverage_penalty: float = 10.0  # penalización adicional por persona por debajo de la cobertura mínima
    min_new: int = 0              # tamaño mínimo de un centro nuevo (plazas); 0 = sin mínimo
    meta: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.unmet_weight is None:
            self.unmet_weight = np.ones(len(self.unit_ids))

    # ---- tamaños
    @property
    def n(self) -> int:
        return len(self.unit_ids)

    @property
    def m(self) -> int:
        return len(self.site_ids)

    @property
    def S(self) -> int:
        return self.need.shape[0]

    @property
    def candidates(self) -> np.ndarray:
        return np.flatnonzero(self.cap_new_max > 0)

    def subsample(self, k: int, seed: int = 0) -> "Instance":
        """Instancia con k escenarios elegidos al azar (aproximación por media muestral, SAA)."""
        idx = np.random.default_rng(seed).choice(self.S, size=min(k, self.S), replace=False)
        d = {f: getattr(self, f) for f in self.__dataclass_fields__}
        d["need"] = self.need[np.sort(idx)]
        d["meta"] = {**self.meta, "escenarios": np.sort(idx).tolist()}
        return Instance(**d)

    # ---- persistencia
    def save(self, ruta: Path) -> None:
        ruta = Path(ruta)
        arrays = {f: getattr(self, f) for f in self.__dataclass_fields__
                  if isinstance(getattr(self, f), np.ndarray)}
        np.savez_compressed(ruta.with_suffix(".npz"), **arrays)
        escalares = {f: getattr(self, f) for f in self.__dataclass_fields__ if f not in arrays}
        ruta.with_suffix(".json").write_text(json.dumps(escalares, indent=2, ensure_ascii=False, default=float))

    @classmethod
    def load(cls, ruta: Path) -> "Instance":
        ruta = Path(ruta)
        z = np.load(ruta.with_suffix(".npz"), allow_pickle=True)
        d = json.loads(ruta.with_suffix(".json").read_text())
        d.update({k: z[k] for k in z.files})
        return cls(**d)

    def resumen(self) -> str:
        nec = self.need.sum(axis=1)
        return (f"{self.nombre}: {self.n} zonas, {self.m} sitios ({len(self.candidates)} candidatos), "
                f"{len(self.arc_d)} arcos, {self.S} escenarios; necesidad media {nec.mean():,.0f} plazas "
                f"(p10 {np.percentile(nec, 10):,.0f}, p90 {np.percentile(nec, 90):,.0f}); "
                f"capacidad actual {self.cap_existing.sum():,.0f}; presupuesto {self.budget:,.0f}.")


# ---------------------------------------------------------------- constructor desde los datos del proyecto
@dataclass
class ParametrosInstancia:
    servicio: str = "centro_dia"          # 'centro_dia' o 'residencia'
    anio: int = 2030                      # 2030 o 2035 (escenarios de la etapa 3)
    meta_por_100: float = 5.8             # plazas objetivo por cada 100 personas mayores con discapacidad
    solo_financiacion_publica: bool = True
    radio_km: float = 15.0
    presupuesto: float = 1000.0           # en unidades de coste (por defecto, plazas equivalentes)
    coste_fijo: float = 20.0              # coste de abrir capacidad nueva en un sitio
    coste_plaza: float = 1.0
    max_plazas_nuevas_por_sitio: int = 150
    modulo: int = 5
    penalizacion_distancia: float = 0.01
    beta_equidad: float = 0.0             # peso extra de las zonas hoy peor atendidas: w_u = 1 + beta * deficit_u
    cobertura_minima: float = 0.0         # fracción mínima de la necesidad de cada zona (restricción blanda)
    penalizacion_cobertura: float = 10.0
    min_plazas_centro: int = 20           # un centro nuevo tiene 0 o al menos este número de plazas


def construir_instancia(p: ParametrosInstancia = ParametrosInstancia()) -> Instance:
    """Instancia con zonas = unidades de demanda; sitios = puntos de referencia de las zonas.

    La capacidad existente de cada centro se agrega al sitio más cercano (su propia zona), y cada zona es
    candidata a recibir un centro nuevo. Así el tamaño es manejable y la instancia sigue siendo genérica.
    """
    u = pd.read_csv(DATA_PROCESSED / "unidades.csv", dtype={"cod_ine": str})
    of = pd.read_csv(DATA_PROCESSED / "oferta_centros.csv", dtype={"cod_ine": str})
    esc = pd.read_csv(DATA_PROCESSED / "escenarios_demanda.csv.gz")
    esc = esc[esc["anio"] == p.anio].drop(columns=["escenario", "anio"])[u["id_unidad"]]

    xy = u[["x", "y"]].to_numpy(float)
    of = of[of["categoria"] == p.servicio]
    if p.solo_financiacion_publica:
        of = of[of["financiacion_publica"]]
    d_c = dist_km(of["x"].values[:, None], of["y"].values[:, None], xy[None, :, 0], xy[None, :, 1])
    cap = np.bincount(d_c.argmin(axis=1), weights=of["plazas"].values, minlength=len(u))

    # Déficit relativo actual de cada zona (accesibilidad E2SFCA de la etapa 2 frente a la media regional,
    # con el mismo radio de cercanía que la instancia cuando está calculado):
    # 0 si la zona está en la media o por encima, 1 si no tiene ninguna plaza accesible.
    cob = pd.read_csv(DATA_PROCESSED / "cobertura.csv").set_index("id_unidad").loc[u["id_unidad"]]
    col = f"acc_{p.servicio}_{'publica' if p.solo_financiacion_publica else 'total'}"
    if f"{col}_r{int(p.radio_km)}" in cob.columns:  # accesibilidad calculada con el mismo radio de cercanía
        col = f"{col}_r{int(p.radio_km)}"
    media = np.average(cob[col], weights=np.maximum(cob["demanda"], 1e-9))
    deficit_rel = np.clip(1 - cob[col].to_numpy() / media, 0, 1)
    pesos = 1.0 + p.beta_equidad * deficit_rel

    D = dist_km(xy[:, None, 0], xy[:, None, 1], xy[None, :, 0], xy[None, :, 1])
    au, aj = np.nonzero(D <= p.radio_km)
    m = len(u)
    return Instance(
        nombre=(f"{p.servicio}_{p.anio}_meta{p.meta_por_100:g}_R{p.radio_km:g}_B{p.presupuesto:g}"
                f"_beta{p.beta_equidad:g}_cmin{p.cobertura_minima:g}_min{p.min_plazas_centro}"),
        unit_ids=u["id_unidad"].to_numpy(str), unit_xy=xy,
        site_ids=u["id_unidad"].to_numpy(str), site_xy=xy.copy(),
        cap_existing=cap.round(0), cap_new_max=np.full(m, float(p.max_plazas_nuevas_por_sitio)),
        arc_u=au, arc_j=aj, arc_d=D[au, aj].round(3),
        need=esc.to_numpy(float) * p.meta_por_100 / 100.0,
        fixed_cost=np.full(m, float(p.coste_fijo)), unit_cost=np.full(m, float(p.coste_plaza)),
        budget=float(p.presupuesto), module=p.modulo, dist_penalty=p.penalizacion_distancia,
        unmet_weight=pesos, coverage_min=p.cobertura_minima, coverage_penalty=p.penalizacion_cobertura,
        min_new=p.min_plazas_centro,
        meta={"parametros": asdict(p), "nombres_zona": u["nombre"].tolist(), "deficit_relativo": deficit_rel.tolist()})

"""Comprobaciones básicas de las salidas del preprocesamiento (ejecutar tras run_pipeline.py)."""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from cuidacerca.geo import utm30_to_lonlat  # noqa: E402

P = ROOT / "data" / "processed"


def test_conversion_utm_puerta_del_sol():
    # Puerta del Sol: aprox. X=440 316, Y=4 474 260 (EPSG:25830) -> -3.7038, 40.4168
    lon, lat = utm30_to_lonlat([440316], [4474260])
    assert abs(lon[0] + 3.7038) < 0.002 and abs(lat[0] - 40.4168) < 0.002


def test_municipios_completos():
    m = pd.read_csv(P / "municipios.csv", dtype={"cod_ine": str})
    assert len(m) == 179 and m["cod_ine"].is_unique
    assert m[["x", "y", "lon", "lat"]].notna().all().all()
    assert m["lat"].between(39.8, 41.2).all() and m["lon"].between(-4.6, -3.0).all()


def test_demanda_panel_completo():
    d = pd.read_csv(P / "demanda_municipal.csv", dtype={"cod_ine": str})
    assert len(d) == 179 * d["anio"].nunique()
    assert d["disc_65_total"].notna().all() and (d["disc_65_total"] >= 0).all()
    assert not d.duplicated(["cod_ine", "anio"]).any()


def test_oferta_valida():
    o = pd.read_csv(P / "oferta_centros.csv", dtype={"cod_ine": str})
    m = pd.read_csv(P / "municipios.csv", dtype={"cod_ine": str})
    assert o["id"].is_unique and (o["plazas"] > 0).all()
    assert set(o["categoria"]) == {"residencia", "centro_dia"}
    assert o["cod_ine"].isin(m["cod_ine"]).all()
    assert o[["lon", "lat"]].notna().all().all()


if __name__ == "__main__":
    for nombre, f in list(globals().items()):
        if nombre.startswith("test_"):
            f()
            print("OK", nombre)

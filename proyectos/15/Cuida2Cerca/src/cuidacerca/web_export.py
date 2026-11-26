"""Exporta los resultados del pipeline a web/data/datos.json para la aplicación web estática."""
from __future__ import annotations

import json
from datetime import date

import numpy as np
import pandas as pd

from .config import DATA_PROCESSED, ROOT
from .experimentos import neutral
from .opt.instance import ParametrosInstancia, construir_instancia
from .opt.solution import Evaluador, vacia

WEB = ROOT / "web"

# Costes ilustrativos por defecto (editables en la web). No proceden de los datos abiertos.
COSTES_DEFECTO = {"fijo": 400000, "por_plaza": 20000, "desplazamiento": 500}

FUENTES = [
    ("Registro de centros de atención social", "https://datos.comunidad.madrid/dataset/atencion_social_registro_centros"),
    ("Personas con discapacidad por edad y sexo. Municipios", "https://datos.comunidad.madrid/dataset/personas_discapacidad_por_edad_y_sexo"),
    ("Centros, servicios y establecimientos sanitarios", "https://datos.comunidad.madrid/dataset/centros_servicios_establecimientos_sanitarios"),
    ("Centros de servicios sociales por tipo. Municipios", "https://datos.comunidad.madrid/dataset/centros_servicios_sociales_por_tipo"),
    ("Solicitudes y resoluciones del sistema de dependencia", "https://datos.comunidad.madrid/dataset/1914360"),
    ("Beneficiarios y prestaciones del sistema de dependencia", "https://datos.comunidad.madrid/dataset/1914361"),
    ("Proyecciones de población por sexo", "https://datos.comunidad.madrid/dataset/proyecciones_poblacion_por_sexo"),
    ("Padrón municipal (Ayuntamiento de Madrid)", "https://datos.madrid.es/dataset/200076-0-padron"),
]


def r(x, d=3):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), d)


def main() -> None:
    u = pd.read_csv(DATA_PROCESSED / "unidades.csv", dtype={"cod_ine": str})
    cob = pd.read_csv(DATA_PROCESSED / "cobertura.csv").set_index("id_unidad")
    pred = pd.read_csv(DATA_PROCESSED / "prediccion_unidades.csv").set_index(["id_unidad", "anio"])
    mun = pd.read_csv(DATA_PROCESSED / "municipios.csv", dtype={"cod_ine": str})
    inst = construir_instancia()
    cap_cd = dict(zip(inst.site_ids, inst.cap_existing))

    zonas = []
    for _, z in u.iterrows():
        c = cob.loc[z["id_unidad"]]
        p30, p35 = pred.loc[(z["id_unidad"], 2030)], pred.loc[(z["id_unidad"], 2035)]
        zonas.append({
            "id": z["id_unidad"], "nombre": z["nombre"], "cod_ine": z["cod_ine"], "tipo": z["tipo"],
            "lat": r(z["lat"], 5), "lon": r(z["lon"], 5), "mancomunidad": z["mancomunidad"] if isinstance(z["mancomunidad"], str) else None,
            "demanda_2025": int(z["demanda"]),
            "demanda_2030": [r(p30["p10"], 0), r(p30["p50"], 0), r(p30["p90"], 0)],
            "demanda_2035": [r(p35["p10"], 0), r(p35["p50"], 0), r(p35["p90"], 0)],
            "acc_cd_publica": r(c["acc_centro_dia_publica"], 2), "acc_cd_total": r(c["acc_centro_dia_total"], 2),
            "acc_cd_publica_r5": r(c["acc_centro_dia_publica_r5"], 2), "acc_cd_total_r5": r(c["acc_centro_dia_total_r5"], 2),
            "acc_res_publica": r(c["acc_residencia_publica"], 2), "acc_res_total": r(c["acc_residencia_total"], 2),
            "dist_cd_km": r(c["dist_centro_dia_km"], 1), "dist_res_km": r(c["dist_residencia_km"], 1),
            "deficit_cd_publica": r(c["deficit_centro_dia_publica"], 1),
            "plazas_cd_publicas": int(cap_cd.get(z["id_unidad"], 0))})

    of = pd.read_csv(DATA_PROCESSED / "oferta_centros.csv", dtype={"cod_ine": str})
    centros = [{"n": x["nombre"], "c": x["categoria"], "p": int(x["plazas"]), "f": x["financiacion"],
                "lat": r(x["lat"], 5), "lon": r(x["lon"], 5), "m": x["municipio"]} for _, x in of.iterrows()]

    reg = pd.read_csv(DATA_PROCESSED / "prediccion_regional.csv")
    dep = pd.read_csv(DATA_PROCESSED / "dependencia_cam.csv")
    planes = json.loads((DATA_PROCESSED / "planes.json").read_text())
    for p in planes:
        p.pop("segundos", None)
    for p in planes:
        p.setdefault("radio_km", 15.0)
    # Situación sin actuación (referencia de los planes), para cada radio de cercanía
    sin_actuacion = {}
    for radio in sorted({p["radio_km"] for p in planes}):
        ir = construir_instancia(ParametrosInstancia(radio_km=radio))
        rb = Evaluador(neutral(ir)).evaluar(vacia(ir), detalle=True)
        sin_actuacion[f"{radio:g}"] = {
            "id": "sin_actuacion", "config": "sin_actuacion", "presupuesto": 0, "radio_km": radio, "centros": [],
            "metricas": {k: float(v) for k, v in rb.items() if not isinstance(v, np.ndarray)},
            "cobertura_por_zona": np.round(rb["cobertura_por_zona"], 4).tolist(),
            "acc_por_zona": np.round(rb["acc_por_zona"] * 100, 3).tolist()}

    municipios = {m["cod_ine"]: {"nombre": m["nombre"], "lat": r(m["lat"], 5), "lon": r(m["lon"], 5)}
                  for _, m in mun.iterrows()}

    datos = {
        "meta": {"generado": date.today().isoformat(), "anio_base": 2025, "fuentes": FUENTES,
                 "costes_defecto": COSTES_DEFECTO,
                 "parametros_planes": {"servicio": "centro de día", "anio": 2030, "meta_por_100": 5.8, "radio_km": 15, "radios_km": [15, 5],
                                       "unidad_presupuesto": "plazas equivalentes (coste fijo de un centro nuevo = 20 plazas)",
                                       "min_plazas_centro": 20}},
        "zonas": zonas, "centros": centros, "municipios": municipios,
        "regional": {"anio": reg["anio"].tolist(), "observado": [r(v, 0) for v in reg["observado"]],
                     "p10": [r(v, 0) for v in reg["p10"]], "p50": [r(v, 0) for v in reg["p50"]],
                     "p90": [r(v, 0) for v in reg["p90"]]},
        "dependencia": {k: [r(v, 0) for v in dep[k]] for k in
                        ["anio", "beneficiarios_con_derecho", "prest_residencial", "prest_centro_dia",
                         "prest_ayuda_domicilio", "prest_teleasistencia", "prest_cuidados_familiares",
                         "prest_vinculada_servicio"]},
        "planes": planes, "sin_actuacion": sin_actuacion,
        "etiquetas_config": {"base": "Solo eficiencia", "beta2": "Equidad moderada (×3)", "beta4": "Equidad alta (×5)",
                             "beta8": "Equidad máxima (×9)", "cmin50": "Mínimo 50 % por zona",
                             "beta4_cmin50": "Equidad alta + mínimo 50 %"},
        "descripciones_config": {
            "base": "Todas las personas cuentan igual: las plazas van donde atienden a más gente por euro.",
            "beta2": "Una persona sin plaza en una zona sin ningún centro al alcance cuenta 3 veces más que en una zona bien servida.",
            "beta4": "Una persona sin plaza en una zona sin ningún centro al alcance cuenta 5 veces más que en una zona bien servida.",
            "beta8": "Una persona sin plaza en una zona sin ningún centro al alcance cuenta 9 veces más que en una zona bien servida.",
            "cmin50": "Todas las personas cuentan igual, pero cada zona debe tener cubierta al menos la mitad de su necesidad.",
            "beta4_cmin50": "Equidad alta (×5) y, además, cada zona debe tener cubierta al menos la mitad de su necesidad."},
    }
    (WEB / "data").mkdir(parents=True, exist_ok=True)
    f = WEB / "data" / "datos.json"
    texto = json.dumps(datos, ensure_ascii=False, separators=(",", ":"))
    f.write_text(texto)
    # Copia como script para poder abrir index.html directamente (file://) sin servidor
    (WEB / "data" / "datos.js").write_text("window.DATOS = " + texto + ";\n")
    print(f"web/data/datos.json: {f.stat().st_size / 1024:.0f} KB, {len(zonas)} zonas, {len(centros)} centros, {len(planes)} planes")


if __name__ == "__main__":
    main()

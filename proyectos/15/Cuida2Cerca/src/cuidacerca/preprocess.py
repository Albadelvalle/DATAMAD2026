"""Etapa 1: preprocesamiento de los datos abiertos de la Comunidad de Madrid.

Genera en data/processed/:
  - municipios.csv            maestro de los 179 municipios con punto de referencia (UTM y lon/lat)
  - demanda_municipal.csv     personas con discapacidad reconocida por municipio y año (2011-2025)
  - oferta_centros.csv        residencias y centros de día para mayores, con plazas, financiación y coordenadas
  - dependencia_cam.csv       serie regional de solicitudes, resoluciones y prestaciones de dependencia
  - proyecciones_cam.csv      proyecciones regionales de población por edad (2026-2041)
y un informe de calidad en reports/calidad_datos.md.

Uso:  python -m cuidacerca.preprocess      (con src/ en el PYTHONPATH)
"""
from __future__ import annotations

import re
import unicodedata

import numpy as np
import pandas as pd

from .config import (BBOX_UTM, CATEGORIA_SUBTIPO, DATA_PROCESSED, DATA_RAW, FINANCIACION, RAW,
                     REPORTS)
from .geo import utm30_to_lonlat

# Rango de los valores ocultos por secreto estadístico, inferido de los propios datos
SECRETO_MIN, SECRETO_MAX = 1, 4

LOG: list[str] = []


def log(msg: str) -> None:
    LOG.append(msg)
    print(msg)


# ---------------------------------------------------------------- utilidades
def leer(clave: str) -> pd.DataFrame:
    return pd.read_csv(DATA_RAW / RAW[clave], sep=";", encoding="utf-8-sig", dtype=str)


def normaliza_nombre(s) -> str:
    """Clave de cruce para nombres de municipio ('Álamo (El)', 'Álamo, El' -> 'el alamo')."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower().strip()
    m = re.match(r"^(.*)\s*\((el|la|los|las)\)$", s) or re.match(r"^(.*),\s*(el|la|los|las)$", s)
    if m:
        s = f"{m.group(2)} {m.group(1).strip()}"
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", "", s)).strip()


def a_numero(serie: pd.Series) -> pd.Series:
    """Convierte a número; '-' (dato protegido o no disponible) pasa a NaN."""
    return pd.to_numeric(serie.str.replace(",", ".", regex=False), errors="coerce")


def en_bbox(x: pd.Series, y: pd.Series) -> pd.Series:
    xmin, ymin, xmax, ymax = BBOX_UTM
    return x.between(xmin, xmax) & y.between(ymin, ymax)


def anade_lonlat(df: pd.DataFrame) -> pd.DataFrame:
    ok = df["x"].notna() & df["y"].notna()
    df["lon"], df["lat"] = np.nan, np.nan
    lon, lat = utm30_to_lonlat(df.loc[ok, "x"], df.loc[ok, "y"])
    df.loc[ok, "lon"], df.loc[ok, "lat"] = np.round(lon, 6), np.round(lat, 6)
    return df


# ---------------------------------------------------------------- municipios
def construir_municipios() -> pd.DataFrame:
    d = leer("discapacidad_mun")
    mun = (d[d["Tipo territorio"] == "Municipios"][["Código territorio", "Territorio"]]
           .drop_duplicates().rename(columns={"Código territorio": "cod_cam", "Territorio": "nombre"}))
    mun = mun[mun["nombre"] != "Sin municipio asignado"].copy()
    mun["cod_ine"] = "28" + mun["cod_cam"].str[:3]
    mun["clave"] = mun["nombre"].map(normaliza_nombre)
    log(f"Municipios: {len(mun)} (excluida la categoría 'Sin municipio asignado').")

    # Punto de referencia: mediana de los centros de salud y consultorios de atención primaria del
    # municipio (aproxima el núcleo de población mejor que el centroide geométrico del término).
    s = leer("sanitarios").drop_duplicates("centro_nro_registro")
    s["x"], s["y"] = a_numero(s["localizacion_coordenada_x"]), a_numero(s["localizacion_coordenada_y"])
    s = s[s["municipio_nombre"].notna() & en_bbox(s["x"], s["y"])]
    s["clave"] = s["municipio_nombre"].map(normaliza_nombre)
    ap = s[s["centro_tipo"].isin(["Centro de salud", "Consultorio de atención primaria"])]
    ref = ap.groupby("clave")[["x", "y"]].median().assign(origen_ref="atencion_primaria")
    resto = s[~s["clave"].isin(ref.index)].groupby("clave")[["x", "y"]].median().assign(origen_ref="centros_sanitarios")
    ref = pd.concat([ref, resto])
    mun = mun.merge(ref, left_on="clave", right_index=True, how="left")

    # Respaldo: mediana de los centros del registro de atención social del municipio
    r = leer("registro_centros")
    r["x"], r["y"] = a_numero(r["direccion_coor_x"]), a_numero(r["direccion_coor_y"])
    social = r[en_bbox(r["x"], r["y"])].groupby("municipio_codigo")[["x", "y"]].median()
    falta = mun["x"].isna()
    cod3 = mun.loc[falta, "cod_ine"].str[2:]
    mun.loc[falta, "x"] = cod3.map(social["x"]).values
    mun.loc[falta, "y"] = cod3.map(social["y"]).values
    mun.loc[falta & mun["x"].notna(), "origen_ref"] = "centros_sociales"
    for origen, n in mun["origen_ref"].value_counts().items():
        log(f"Punto de referencia desde {origen}: {n} municipios.")
    if mun["x"].isna().any():
        log(f"AVISO: sin punto de referencia: {', '.join(mun.loc[mun['x'].isna(), 'nombre'])}.")

    # Mancomunidad de servicios sociales (dato del registro de centros, cuando existe)
    manc = (r.dropna(subset=["direccion_mancomunidad"])
            .groupby("municipio_codigo")["direccion_mancomunidad"].agg(lambda v: v.mode().iat[0]))
    mun["mancomunidad"] = mun["cod_ine"].str[2:].map(manc)
    log(f"Municipios con mancomunidad de servicios sociales: {mun['mancomunidad'].notna().sum()}.")

    mun[["x", "y"]] = mun[["x", "y"]].round(0)
    mun = anade_lonlat(mun)
    return mun[["cod_ine", "cod_cam", "nombre", "clave", "x", "y", "lon", "lat", "origen_ref", "mancomunidad"]] \
        .sort_values("cod_ine").reset_index(drop=True)


# ---------------------------------------------------------------- demanda
def construir_demanda(mun: pd.DataFrame) -> pd.DataFrame:
    d = leer("discapacidad_mun")
    d = d[(d["Tipo territorio"] == "Municipios") & d["Territorio"].ne("Sin municipio asignado")].copy()
    d["valor"] = a_numero(d["Valor"])
    d["anio"] = d["Año"].astype(int)
    edad = {"65 años y más": "65", "De 0 a 64 años": "0_64", "Total": "total"}
    sexo = {"Total": "total", "Hombres": "hombres", "Mujeres": "mujeres"}
    d = d[d["Edad"].isin(edad)]
    d["var"] = "disc_" + d["Edad"].map(edad) + "_" + d["Sexo"].map(sexo)
    w = d.pivot_table(index=["Código territorio", "anio"], columns="var", values="valor", aggfunc="first")
    w = w.reset_index().rename(columns={"Código territorio": "cod_cam"})
    cols = [c for c in w.columns if c.startswith("disc_")]

    # Valores protegidos ('-', secreto estadístico desde 2019). La Comunidad no publica el umbral; en los 67
    # casos en que el valor oculto puede deducirse por diferencia con el total, siempre está entre 1 y 4
    # (el 0 sí se publica). Se interpolan en el tiempo dentro de cada municipio y se acotan a [1, 4];
    # si el municipio no tiene valores vecinos se asigna 2.
    n_prot = int(w[cols].isna().sum().sum())
    w = w.sort_values(["cod_cam", "anio"])
    for c in cols:
        oculto = w[c].isna()
        w[f"{c}_imputado"] = oculto
        interp = w.groupby("cod_cam")[c].transform(lambda s: s.interpolate(limit_direction="both"))
        w.loc[oculto, c] = interp[oculto].clip(SECRETO_MIN, SECRETO_MAX).fillna(2)
        w[c] = w[c].round(0)
    log_txt = (f"Demanda: {n_prot} valores protegidos ('-') imputados en todas las desagregaciones; en la variable "
               f"principal (65+, ambos sexos) son {int(w['disc_65_total_imputado'].sum())} de {len(w)} municipio-año.")
    w["imputado"] = w["disc_65_total_imputado"]
    w = w.drop(columns=[f"{c}_imputado" for c in cols])
    log(log_txt)

    # Coherencia: la suma municipal debe aproximar el total publicado para la Comunidad
    tot = leer("discapacidad_mun")
    tot = tot[(tot["Tipo territorio"] == "Comunidad de Madrid") & (tot["Edad"] == "65 años y más") & (tot["Sexo"] == "Total")]
    tot = tot.assign(anio=tot["Año"].astype(int), cam=a_numero(tot["Valor"])).set_index("anio")["cam"]
    suma = w.groupby("anio")["disc_65_total"].sum()
    dif = ((suma - tot) / tot * 100).round(2)
    log(f"Suma municipal de 65+ frente al total regional (diferencia %, por año): mín {dif.min()}, máx {dif.max()}.")

    w = w.merge(mun[["cod_cam", "cod_ine", "nombre"]], on="cod_cam", how="left")
    return w[["cod_ine", "nombre", "anio", "disc_65_total", "disc_65_hombres", "disc_65_mujeres",
              "disc_0_64_total", "disc_total_total", "imputado"]].rename(columns={"disc_total_total": "disc_total"})


# ---------------------------------------------------------------- oferta
def construir_oferta(mun: pd.DataFrame) -> pd.DataFrame:
    r = leer("registro_centros")
    log(f"Registro de centros de atención social: {len(r)} centros, {r['numero_registro'].duplicated().sum()} duplicados.")
    alt = leer("registro_centros_alt")
    extra = alt[~alt["numero_registro"].isin(r["numero_registro"])]
    log(f"El fichero alternativo del registro tiene {len(extra)} centros que no están en el principal "
        f"({(extra['sector'] == 'Personas mayores').sum()} de mayores); no se incorporan por no estar en el registro vigente.")

    m = r[(r["sector"] == "Personas mayores")].copy()
    log(f"Centros para personas mayores: {len(m)}.")
    m["categoria"] = m["subtipo"].map(CATEGORIA_SUBTIPO)
    excl = m[m["categoria"].isna()]["subtipo"].value_counts()
    log("Excluidos por no ser plazas de cuidados a dependientes: " + "; ".join(f"{k} ({v})" for k, v in excl.items()))
    m = m[m["categoria"].notna()].copy()

    m["plazas"] = a_numero(m["plazas_autorizadas_numero"])
    sin_plazas = m["plazas"].isna() | (m["plazas"] <= 0)
    log(f"Eliminados sin plazas autorizadas válidas: {int(sin_plazas.sum())}.")
    m = m[~sin_plazas]
    reservado = m["municipio_codigo"].eq("RESERVADO")
    if reservado.any():
        log(f"Eliminados con ubicación reservada: {int(reservado.sum())}.")
        m = m[~reservado]

    m["financiacion"] = m["tipo_gestion"].map(FINANCIACION).fillna("desconocida")
    m["financiacion_publica"] = m["financiacion"].isin(["publica", "concertada", "privada_pevs"])
    m["cod_ine"] = "28" + m["municipio_codigo"]

    # Coordenadas: se descartan las que caen fuera de la Comunidad y se imputan las que faltan con la
    # mediana de los centros del mismo código postal o, en su defecto, el punto de referencia municipal.
    m["x"], m["y"] = a_numero(m["direccion_coor_x"]), a_numero(m["direccion_coor_y"])
    fuera = m["x"].notna() & ~en_bbox(m["x"], m["y"])
    m.loc[fuera, ["x", "y"]] = np.nan
    m["origen_coord"] = np.where(m["x"].notna(), "registro", None)
    todos = r.assign(x=a_numero(r["direccion_coor_x"]), y=a_numero(r["direccion_coor_y"]))
    todos = todos[en_bbox(todos["x"], todos["y"])]
    cp = todos.groupby("direccion_codigo_postal")[["x", "y"]].median()
    falta = m["x"].isna()
    por_cp = m.loc[falta, "direccion_codigo_postal"].map(cp["x"]).notna()
    idx_cp = por_cp[por_cp].index
    m.loc[idx_cp, "x"] = m.loc[idx_cp, "direccion_codigo_postal"].map(cp["x"])
    m.loc[idx_cp, "y"] = m.loc[idx_cp, "direccion_codigo_postal"].map(cp["y"])
    m.loc[idx_cp, "origen_coord"] = "codigo_postal"
    falta = m["x"].isna()
    ref = mun.set_index("cod_ine")
    m.loc[falta, "x"] = m.loc[falta, "cod_ine"].map(ref["x"])
    m.loc[falta, "y"] = m.loc[falta, "cod_ine"].map(ref["y"])
    m.loc[falta, "origen_coord"] = "municipio"
    log(f"Coordenadas: {int(fuera.sum())} fuera de la Comunidad descartadas; imputadas {len(idx_cp)} por código postal "
        f"y {int(falta.sum())} por municipio.")

    dup = m.duplicated(["denominacion", "x", "y", "categoria"])
    if dup.any():
        log(f"Eliminados duplicados (mismo nombre, ubicación y tipo): {int(dup.sum())}.")
        m = m[~dup]

    m = anade_lonlat(m)
    out = m.rename(columns={"numero_registro": "id", "denominacion": "nombre", "municipio_nombre": "municipio",
                            "direccion_area": "area", "direccion_zonass": "zona_servicios_sociales",
                            "direccion_distrito": "distrito", "entidad_naturaleza": "naturaleza_entidad"})
    out["nombre"] = out["nombre"].str.strip().str.replace(r"\s+", " ", regex=True)
    cols = ["id", "nombre", "categoria", "subtipo", "plazas", "financiacion", "financiacion_publica", "tipo_gestion",
            "naturaleza_entidad", "cod_ine", "municipio", "area", "distrito", "zona_servicios_sociales",
            "x", "y", "lon", "lat", "origen_coord"]
    out = out[cols].sort_values(["cod_ine", "categoria", "id"]).reset_index(drop=True)
    for cat, g in out.groupby("categoria"):
        log(f"  {cat}: {len(g)} centros, {int(g['plazas'].sum())} plazas "
            f"({int(g.loc[g['financiacion_publica'], 'plazas'].sum())} en centros con financiación pública).")
    return out


def validar_oferta(oferta: pd.DataFrame, mun: pd.DataFrame) -> None:
    """Contrasta el número de residencias por municipio con la estadística oficial más reciente."""
    c = leer("centros_ss_mun")
    c = c[(c["Tipo territorio"] == "Municipios") & (c["Tipo"] == "Personas mayores: Residencias")]
    ultimo = c["Año"].max()
    c = c[c["Año"] == ultimo].assign(oficial=lambda t: a_numero(t["Valor"]))
    c = c.merge(mun[["cod_cam", "cod_ine"]], left_on="Código territorio", right_on="cod_cam")
    reg = oferta[oferta["categoria"] == "residencia"].groupby("cod_ine").size().rename("registro")
    cmp_ = c.set_index("cod_ine")[["oficial"]].join(reg).fillna(0)
    iguales = (cmp_["oficial"] == cmp_["registro"]).mean() * 100
    log(f"Validación con 'Centros de servicios sociales por tipo' ({ultimo}): residencias por municipio coinciden en "
        f"el {iguales:.0f} % de municipios; total oficial {int(cmp_['oficial'].sum())} frente a {int(cmp_['registro'].sum())} en el registro "
        f"(la estadística oficial puede contar también residencias de autónomos).")


# ---------------------------------------------------------------- contexto regional
def construir_dependencia() -> pd.DataFrame:
    claves = [
        (r"^Solicitudes", "solicitudes"),
        (r"^Resoluciones de las solicitudes", "resoluciones"),
        (r"^Resoluciones sin Grado", "resoluciones_sin_grado"),
        (r"^Total resoluciones con Grado I ", "resoluciones_grado_I"),
        (r"^Total resoluciones con Grado II ", "resoluciones_grado_II"),
        (r"^Total resoluciones con Grado III ", "resoluciones_grado_III"),
        (r"^Total beneficiarios/as con derecho", "beneficiarios_con_derecho"),
        (r"^Total beneficiarios/as que reciben", "beneficiarios_que_reciben"),
        (r"^Total prestaciones", "prestaciones_total"),
        (r"^Prestaciónes de atención residencial", "prest_residencial"),
        (r"^Prestaciónes de centros de día", "prest_centro_dia"),
        (r"^Prestaciónes de ayuda a domicilio", "prest_ayuda_domicilio"),
        (r"^Prestaciónes de teleasistencia", "prest_teleasistencia"),
        (r"^Prestación económica para cuidados en el entorno familiar", "prest_cuidados_familiares"),
        (r"^Prestación económica vinculada al servicio", "prest_vinculada_servicio"),
    ]
    filas = []
    for clave in ("dep_solicitudes", "dep_prestaciones"):
        df = leer(clave)
        for patron, nombre in claves:
            sel = df[df["Concepto"].str.contains(patron, regex=True)]
            filas.append(sel.assign(variable=nombre, anio=sel["Año"].astype(int), valor=a_numero(sel["Valor"]))
                         [["anio", "variable", "valor"]])
    dep = pd.concat(filas).pivot_table(index="anio", columns="variable", values="valor", aggfunc="first").reset_index()
    dep["en_espera_de_prestacion"] = dep["beneficiarios_con_derecho"] - dep["beneficiarios_que_reciben"]
    ult = dep.dropna(subset=["beneficiarios_con_derecho"]).iloc[-1]
    log(f"Dependencia ({int(ult['anio'])}): {int(ult['beneficiarios_con_derecho'])} personas con derecho, "
        f"{int(ult['en_espera_de_prestacion'])} aún sin prestación.")
    return dep


def construir_proyecciones() -> pd.DataFrame:
    p = leer("proyecciones")
    p = p[p["Concepto"].str.startswith("Proyecciones de población de personas de")].copy()
    rango = p["Concepto"].str.extract(r"de (\d+)\s*(?:a\s+(\d+)|años y más)")
    p["edad_min"] = rango[0].astype(int)
    p["edad_max"] = pd.to_numeric(rango[1], errors="coerce")
    p["anio"], p["valor"] = p["Año"].astype(int), a_numero(p["Valor"])
    p["sexo"] = p["Sexo"].str.lower()
    out = p[["anio", "sexo", "edad_min", "edad_max", "valor"]].sort_values(["anio", "sexo", "edad_min"]).reset_index(drop=True)
    t = out[out["sexo"] == "total"]
    for a in (out["anio"].min(), 2030, 2035, out["anio"].max()):
        log(f"Proyección {a}: {int(t[(t.anio == a) & (t.edad_min >= 65)].valor.sum())} personas de 65+ "
            f"({int(t[(t.anio == a) & (t.edad_min >= 80)].valor.sum())} de 80+).")
    return out


# ---------------------------------------------------------------- principal
def main() -> None:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    log("# Informe de calidad y preprocesamiento de datos\n")
    log("## Municipios")
    mun = construir_municipios()
    log("\n## Demanda (personas con discapacidad reconocida)")
    dem = construir_demanda(mun)
    log("\n## Oferta (residencias y centros de día para mayores)")
    ofe = construir_oferta(mun)
    validar_oferta(ofe, mun)
    log("\n## Contexto regional")
    dep = construir_dependencia()
    pro = construir_proyecciones()

    salidas = {"municipios": mun, "demanda_municipal": dem, "oferta_centros": ofe,
               "dependencia_cam": dep, "proyecciones_cam": pro}
    log("\n## Ficheros generados")
    for nombre, df in salidas.items():
        df.to_csv(DATA_PROCESSED / f"{nombre}.csv", index=False, encoding="utf-8")
        log(f"- data/processed/{nombre}.csv: {len(df)} filas x {df.shape[1]} columnas")

    log("\n## Limitaciones conocidas")
    log("- El umbral de secreto estadístico (1-4) está inferido de los datos; la Comunidad no lo publica.")
    log("- La demanda usa la discapacidad reconocida en mayores de 65 como aproximación de la dependencia.")
    log("- Madrid capital es un único municipio en la demanda; el desglose por distrito requiere otra fuente.")
    log("- El registro indica si un centro tiene plazas concertadas o PEVS, pero no cuántas.")
    (REPORTS / "calidad_datos.md").write_text("\n".join(m if m.startswith(("#", "-", "\n")) or m == "" else f"- {m}"
                                                       for m in LOG) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

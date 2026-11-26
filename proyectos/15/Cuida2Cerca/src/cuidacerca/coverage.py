"""Etapa 2: diagnóstico de cobertura de plazas de cuidados para mayores.

Unidades de demanda: los 179 municipios; Madrid capital se divide en sus 21 distritos cuando está el
padrón del Ayuntamiento en data/raw (fichero *padron*.csv).

Indicador principal: accesibilidad espacial en dos pasos con decaimiento gaussiano (E2SFCA,
Luo y Qi, 2009). Para cada centro j con P_j plazas:
    R_j = P_j / sum_u w(d_uj) * D_u
y para cada unidad u con demanda D_u:
    A_u = sum_j w(d_uj) * R_j      (plazas accesibles por persona mayor con discapacidad)
con w(d) = 1 en d = 0, decreciente hasta 0 en el radio de captación d0.

Genera data/processed/unidades.csv, data/processed/cobertura.csv y reports/diagnostico.md.
"""
from __future__ import annotations

import glob

import numpy as np
import pandas as pd

from .config import DATA_PROCESSED, DATA_RAW, REPORTS
from .geo import dist_km, utm30_to_lonlat

ANIO_BASE = 2025
# Radio de captación (km): distancia razonable para residencia y para un centro de día de uso diario
RADIO_KM = {"residencia": 30.0, "centro_dia": 15.0}
# Radios alternativos de "cerca" para el análisis de sensibilidad (columnas con sufijo _r<km>)
RADIOS_ALT = {"centro_dia": (5.0,)}
COD_MADRID = "28079"
# Diferencias de nombre de distrito entre el padrón del Ayuntamiento y el registro de la Comunidad
ALIAS_DISTRITO = {"sanblascanillejas": "sanblas"}


# ---------------------------------------------------------------- unidades de demanda
def leer_padron_distritos() -> pd.DataFrame | None:
    """Población de 65+ por distrito de Madrid a partir del padrón del Ayuntamiento (datos.madrid.es)."""
    ficheros = sorted(glob.glob(str(DATA_RAW / "*padron*.csv")))
    if not ficheros:
        return None
    f = ficheros[-1]
    for enc in ("utf-8-sig", "latin-1"):
        try:
            p = pd.read_csv(f, sep=";", encoding=enc, dtype=str)
            break
        except UnicodeDecodeError:
            continue
    p.columns = [c.strip().upper() for c in p.columns]
    col_edad = next(c for c in p.columns if "EDAD" in c)
    col_dist = next(c for c in p.columns if c.startswith("DESC_DISTRITO"))
    cols_pob = [c for c in p.columns if c.startswith(("ESPANOLES", "EXTRANJEROS"))]
    p["edad"] = pd.to_numeric(p[col_edad].str.strip(), errors="coerce")
    p["pob"] = p[cols_pob].apply(lambda s: pd.to_numeric(s.str.strip(), errors="coerce")).fillna(0).sum(axis=1)
    p["distrito"] = p[col_dist].str.strip()
    out = p[p["edad"] >= 65].groupby("distrito")["pob"].sum().rename("pob_65").reset_index()
    print(f"Padrón de Madrid ({f.rsplit('/', 1)[-1]}): {len(out)} distritos, {int(out['pob_65'].sum())} personas de 65+.")
    return out


def puntos_distritos() -> pd.DataFrame:
    """Punto de referencia de cada distrito: mediana de los centros de atención social del distrito."""
    r = pd.read_csv(DATA_RAW / "atencion_social_registro_centros.csv", sep=";", encoding="utf-8-sig", dtype=str)
    r = r[r["municipio_codigo"] == COD_MADRID[2:]].copy()
    r["x"] = pd.to_numeric(r["direccion_coor_x"], errors="coerce")
    r["y"] = pd.to_numeric(r["direccion_coor_y"], errors="coerce")
    return r.dropna(subset=["x", "y"]).groupby("direccion_distrito")[["x", "y"]].median().round(0)


def normaliza(s: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().replace(" ", "").replace("-", "")


def construir_unidades(anio: int = ANIO_BASE) -> pd.DataFrame:
    mun = pd.read_csv(DATA_PROCESSED / "municipios.csv", dtype={"cod_ine": str})
    dem = pd.read_csv(DATA_PROCESSED / "demanda_municipal.csv", dtype={"cod_ine": str})
    dem = dem[dem["anio"] == anio][["cod_ine", "disc_65_total", "imputado"]]
    u = mun.merge(dem, on="cod_ine")
    u = u.assign(id_unidad=u["cod_ine"], tipo="municipio", municipio=u["nombre"], demanda=u["disc_65_total"])

    padron = leer_padron_distritos()
    if padron is not None:
        pts = puntos_distritos()
        pts["nombre_distrito"] = pts.index
        pts.index = pts.index.map(normaliza)
        padron["clave"] = padron["distrito"].map(normaliza).replace(ALIAS_DISTRITO)
        padron = padron.merge(pts, left_on="clave", right_index=True, how="left")
        if padron["x"].isna().any():
            raise ValueError(f"Distritos sin punto de referencia: {padron.loc[padron['x'].isna(), 'distrito'].tolist()}")
        madrid = u[u["cod_ine"] == COD_MADRID].iloc[0]
        # Supuesto: la prevalencia de discapacidad entre los mayores de 65 es la misma en todos los distritos
        padron["demanda"] = (madrid["demanda"] * padron["pob_65"] / padron["pob_65"].sum()).round(0)
        dist = pd.DataFrame({
            "id_unidad": COD_MADRID + "-" + padron["clave"], "tipo": "distrito_madrid", "cod_ine": COD_MADRID,
            "nombre": "Madrid - " + padron["nombre_distrito"], "municipio": "Madrid",
            "x": padron["x"], "y": padron["y"], "demanda": padron["demanda"], "imputado": False,
            "mancomunidad": np.nan})
        u = pd.concat([u[u["cod_ine"] != COD_MADRID], dist], ignore_index=True)

    u["lon"], u["lat"] = utm30_to_lonlat(u["x"], u["y"])
    return u[["id_unidad", "tipo", "cod_ine", "nombre", "municipio", "mancomunidad", "x", "y", "lon", "lat",
              "demanda", "imputado"]].reset_index(drop=True)


# ---------------------------------------------------------------- accesibilidad
def peso_gaussiano(d: np.ndarray, d0: float) -> np.ndarray:
    """Decaimiento gaussiano normalizado: 1 en d=0 y 0 a partir del radio d0."""
    g = (np.exp(-0.5 * (d / d0) ** 2) - np.exp(-0.5)) / (1 - np.exp(-0.5))
    return np.where(d <= d0, g, 0.0)


def e2sfca(unidades: pd.DataFrame, centros: pd.DataFrame, d0: float) -> np.ndarray:
    """Plazas accesibles por persona en cada unidad (E2SFCA)."""
    d = dist_km(unidades["x"].values[:, None], unidades["y"].values[:, None],
                centros["x"].values[None, :], centros["y"].values[None, :])
    w = peso_gaussiano(d, d0)
    demanda_ponderada = (w * unidades["demanda"].values[:, None]).sum(axis=0)
    ratio = np.divide(centros["plazas"].values, demanda_ponderada,
                      out=np.zeros(len(centros)), where=demanda_ponderada > 0)
    return w @ ratio


def distancia_minima(unidades: pd.DataFrame, centros: pd.DataFrame) -> np.ndarray:
    if centros.empty:
        return np.full(len(unidades), np.inf)
    d = dist_km(unidades["x"].values[:, None], unidades["y"].values[:, None],
                centros["x"].values[None, :], centros["y"].values[None, :])
    return d.min(axis=1)


def gini_ponderado(valores: np.ndarray, pesos: np.ndarray) -> float:
    """Índice de Gini de la accesibilidad, ponderado por la demanda de cada unidad."""
    orden = np.argsort(valores)
    v, p = valores[orden], pesos[orden]
    cp = np.cumsum(p) / p.sum()
    cv = np.cumsum(v * p) / (v * p).sum()
    return float(1 - np.sum((cp - np.r_[0, cp[:-1]]) * (cv + np.r_[0, cv[:-1]])))


def calcular_cobertura(unidades: pd.DataFrame, oferta: pd.DataFrame, radios: dict = RADIO_KM) -> pd.DataFrame:
    c = unidades.copy()
    D = c["demanda"].sum()
    for cat, d0 in radios.items():
        for etiqueta, sel in (("total", oferta["categoria"] == cat),
                              ("publica", (oferta["categoria"] == cat) & oferta["financiacion_publica"])):
            centros = oferta[sel]
            acc = e2sfca(c, centros, d0)
            media = centros["plazas"].sum() / D
            c[f"acc_{cat}_{etiqueta}"] = acc * 100  # plazas por cada 100 personas
            c[f"deficit_{cat}_{etiqueta}"] = np.clip(media - acc, 0, None) * c["demanda"]
        c[f"dist_{cat}_km"] = distancia_minima(c, oferta[oferta["categoria"] == cat]).round(1)
    for cat, radios_alt in RADIOS_ALT.items():
        for d0 in radios_alt:
            for etiqueta, sel in (("total", oferta["categoria"] == cat),
                                  ("publica", (oferta["categoria"] == cat) & oferta["financiacion_publica"])):
                centros = oferta[sel]
                acc = e2sfca(c, centros, d0)
                media = centros["plazas"].sum() / D
                c[f"acc_{cat}_{etiqueta}_r{int(d0)}"] = acc * 100
                c[f"deficit_{cat}_{etiqueta}_r{int(d0)}"] = np.clip(media - acc, 0, None) * c["demanda"]
    return c


# ---------------------------------------------------------------- informe
def informe(c: pd.DataFrame, oferta: pd.DataFrame, unidades: pd.DataFrame) -> list[str]:
    L = ["# Diagnóstico de cobertura de plazas de cuidados para mayores", "",
         f"Año base: {ANIO_BASE}. Demanda: personas de 65+ con discapacidad reconocida. "
         f"Radios de captación: residencia {RADIO_KM['residencia']:.0f} km, centro de día {RADIO_KM['centro_dia']:.0f} km. "
         f"Unidades: {len(c)} ({(c['tipo'] == 'distrito_madrid').sum()} distritos de Madrid).", ""]
    D = c["demanda"].sum()
    L.append("## Indicadores regionales")
    for cat in RADIO_KM:
        for et in ("total", "publica"):
            col = f"acc_{cat}_{et}"
            plazas = oferta.loc[(oferta.categoria == cat) & ((et == "total") | oferta.financiacion_publica), "plazas"].sum()
            L.append(f"- {cat}, plazas {et}: media regional {plazas / D * 100:.1f} plazas por 100 personas; "
                     f"Gini de accesibilidad {gini_ponderado(c[col].values, c['demanda'].values):.2f}; "
                     f"plazas que faltan para que ninguna unidad quede por debajo de la media: "
                     f"{int(c[f'deficit_{cat}_{et}'].sum())}.")
    L += ["", "## Personas lejos de una plaza"]
    nombre_cat = {"residencia": "de la residencia más cercana", "centro_dia": "del centro de día más cercano"}
    for cat, umbrales in (("residencia", (10, 20)), ("centro_dia", (5, 10))):
        for u in umbrales:
            m = c[f"dist_{cat}_km"] > u
            L.append(f"- A más de {u} km {nombre_cat[cat]}: {int(c.loc[m, 'demanda'].sum())} personas "
                     f"en {int(m.sum())} unidades.")
    mun = c[c["tipo"] == "municipio"]
    pl = oferta.groupby("cod_ine")["plazas"].sum()
    sin = mun[~mun["cod_ine"].isin(pl.index)]
    L.append(f"- Municipios sin residencia ni centro de día propios: {len(sin)} ({int(sin['demanda'].sum())} personas).")

    L += ["", "## Unidades con mayor déficit de plazas de residencia con financiación pública"]
    top = c.sort_values("deficit_residencia_publica", ascending=False).head(10)
    for _, r in top.iterrows():
        L.append(f"- {r['nombre']}: {int(r['demanda'])} personas, {r['acc_residencia_publica']:.1f} plazas/100 accesibles, "
                 f"faltan {int(r['deficit_residencia_publica'])} plazas para la media.")

    L += ["", "## Unidades con mayor déficit de plazas de centro de día con financiación pública"]
    for _, r in c.sort_values("deficit_centro_dia_publica", ascending=False).head(10).iterrows():
        L.append(f"- {r['nombre']}: {int(r['demanda'])} personas, {r['acc_centro_dia_publica']:.1f} plazas/100 accesibles, "
                 f"centro más cercano a {r['dist_centro_dia_km']} km, faltan {int(r['deficit_centro_dia_publica'])} plazas.")

    L += ["", "## Sensibilidad al radio de captación (residencias, plazas con financiación pública)"]
    for d0 in (15, 20, 30, 45):
        acc = e2sfca(unidades, oferta[(oferta.categoria == "residencia") & oferta.financiacion_publica], d0) * 100
        L.append(f"- Radio {d0} km: Gini {gini_ponderado(acc, unidades['demanda'].values):.2f}; "
                 f"personas en unidades por debajo de la mitad de la media: "
                 f"{int(unidades['demanda'][acc < 0.5 * np.average(acc, weights=unidades['demanda'])].sum())}.")
    L += ["", "## Supuestos y limitaciones",
          "- Distancias en línea recta entre puntos de referencia; no se usa la red de carreteras.",
          "- La demanda de cada distrito de Madrid reparte la del municipio según su población de 65+.",
          "- 'Financiación pública' incluye centros públicos, concertados y los que admiten la prestación vinculada (PEVS); "
          "el registro no indica cuántas plazas de cada centro están concertadas."]
    return L


def main() -> None:
    oferta = pd.read_csv(DATA_PROCESSED / "oferta_centros.csv", dtype={"cod_ine": str})
    unidades = construir_unidades()
    cob = calcular_cobertura(unidades, oferta)
    unidades.to_csv(DATA_PROCESSED / "unidades.csv", index=False)
    cob.round(3).to_csv(DATA_PROCESSED / "cobertura.csv", index=False)
    texto = informe(cob, oferta, unidades)
    (REPORTS / "diagnostico.md").write_text("\n".join(texto) + "\n", encoding="utf-8")
    print("\n".join(texto))


if __name__ == "__main__":
    main()

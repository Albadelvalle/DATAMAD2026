"""Etapa 3: predicción de la demanda (personas de 65+ con discapacidad) a 2030 y 2035 con incertidumbre.

Modelo en dos niveles:
1. Total regional = demanda 2025 x crecimiento de la población de 65+ (proyecciones oficiales de la
   Comunidad) x deriva de la prevalencia exp(delta * h). delta recoge que la discapacidad reconocida
   ha crecido más deprisa que la población mayor; se estima con la serie 2015-2025 y se simula entre 0
   (solo envejecimiento) y su valor histórico (la tendencia continúa).
2. Reparto entre municipios: cuota de cada municipio en el total, con tendencia log-lineal 2015-2025.
   Las pendientes se contraen hacia 0 con un estimador empírico bayesiano (los municipios pequeños son
   ruidosos). Madrid capital se reparte entre distritos según su población de 65+ (padrón).

La incertidumbre se propaga por Monte Carlo (deriva de prevalencia, ruido regional y ruido de cuotas).
Los escenarios simulados alimentan la optimización robusta de la etapa 4.

Genera data/processed/prediccion_regional.csv, prediccion_unidades.csv, escenarios_demanda.csv.gz y
reports/prediccion.md.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import DATA_PROCESSED, REPORTS

ANIO_BASE = 2025
VENTANA = (2015, 2025)
HORIZONTES = (2030, 2035)
N_ESCENARIOS = 500
SEMILLA = 2026
PHIS = (1.0, 0.95, 0.9, 0.85, 0.8, 0.7)


# ---------------------------------------------------------------- nivel regional
def poblacion_65() -> pd.Series:
    p = pd.read_csv(DATA_PROCESSED / "proyecciones_cam.csv")
    p65 = p[(p["sexo"] == "total") & (p["edad_min"] >= 65)].groupby("anio")["valor"].sum()
    # 2025 no está en las proyecciones: se retropola con el crecimiento 2026-2027
    p65.loc[ANIO_BASE] = p65[2026] ** 2 / p65[2027]
    return p65.sort_index()


def parametros_regionales(serie: pd.Series, p65: pd.Series, ventana=VENTANA) -> dict:
    """Crecimiento histórico de la demanda, crecimiento demográfico y deriva de prevalencia (anuales, log)."""
    s = np.log(serie.loc[ventana[0]:ventana[1]])
    crec_demanda = (s.iloc[-1] - s.iloc[0]) / (len(s) - 1)
    sigma = float(s.diff().dropna().std(ddof=1))
    # Supuesto: el crecimiento de la población de 65+ en el pasado reciente fue similar al proyectado
    # para 2026-2031 (las proyecciones no cubren años anteriores).
    crec_pob = float(np.log(p65[2031] / p65[2026]) / 5)
    return {"crec_demanda": float(crec_demanda), "crec_pob": crec_pob,
            "delta_hist": max(0.0, float(crec_demanda) - crec_pob), "sigma": sigma}


def simular_total_regional(d_base: float, p65: pd.Series, par: dict, anios, rng, n=N_ESCENARIOS) -> np.ndarray:
    """Matriz (n, len(anios)) de totales regionales simulados."""
    delta = rng.uniform(0.0, par["delta_hist"], size=n)
    out = np.empty((n, len(anios)))
    ruido = np.zeros(n)
    previo = ANIO_BASE
    for k, a in enumerate(anios):
        # ruido de paseo aleatorio en log con la volatilidad interanual observada, descontada la tendencia
        ruido = ruido + rng.normal(0, par["sigma"] * 0.5, size=n) * np.sqrt(a - previo)
        previo = a
        out[:, k] = d_base * p65[a] / p65[ANIO_BASE] * np.exp(delta * (a - ANIO_BASE) + ruido)
    return out


# ---------------------------------------------------------------- nivel municipal
def ajustar_cuotas(panel: pd.DataFrame, ventana=VENTANA) -> pd.DataFrame:
    """Tendencia log-lineal de la cuota de cada municipio con contracción empírica bayesiana de la pendiente."""
    w = panel.pivot(index="cod_ine", columns="anio", values="disc_65_total").loc[:, ventana[0]:ventana[1]]
    cuota = w / w.sum()
    t = np.array(cuota.columns, dtype=float)
    tc = t - t.mean()
    y = np.log(cuota.values + 0.5 / w.sum().values)  # +0,5 personas evita log(0)
    b = (y - y.mean(axis=1, keepdims=True)) @ tc / (tc @ tc)
    a = y.mean(axis=1)
    resid = y - (a[:, None] + b[:, None] * tc)
    s2 = (resid ** 2).sum(axis=1) / (len(t) - 2)
    se2 = s2 / (tc @ tc)
    tau2 = max(np.var(b, ddof=1) - se2.mean(), 1e-8)
    factor = tau2 / (tau2 + se2)
    b_ast = b * factor
    nivel_final = a + b_ast * tc[-1]  # nivel ajustado en el último año (suaviza el ruido)
    return pd.DataFrame({"cod_ine": cuota.index, "log_cuota_final": nivel_final, "pendiente": b_ast,
                         "pendiente_mco": b, "contraccion": factor, "sigma": np.sqrt(s2),
                         "se_pendiente": np.sqrt(se2), "anio_final": ventana[1]})


def horizonte_amortiguado(h, phi: float):
    """Efecto acumulado de la tendencia con amortiguación (Gardner y McKenzie, 1985): sum_{i=1..h} phi^i."""
    h = np.asarray(h, dtype=float)
    return h if phi >= 1 else phi * (1 - phi ** h) / (1 - phi)


def simular_cuotas(cuotas: pd.DataFrame, anios, rng, n=N_ESCENARIOS, deterministico=False,
                   phi: float = 1.0, kappa: float = 1.0) -> np.ndarray:
    """Array (n, len(anios), municipios) de cuotas simuladas que suman 1.

    phi: amortiguación de la tendencia; kappa: factor de calibración de la incertidumbre.
    """
    m = len(cuotas)
    out = np.empty((n, len(anios), m))
    for k, a in enumerate(anios):
        h = a - cuotas["anio_final"].values
        hd = horizonte_amortiguado(h, phi)
        mu = cuotas["log_cuota_final"].values + cuotas["pendiente"].values * hd
        if deterministico:
            z = np.tile(mu, (n, 1))
        else:
            sd = kappa * np.sqrt(cuotas["sigma"].values ** 2 + (cuotas["se_pendiente"].values * hd) ** 2)
            z = mu + rng.normal(size=(n, m)) * sd
        e = np.exp(z)
        out[:, k, :] = e / e.sum(axis=1, keepdims=True)
    return out


# ---------------------------------------------------------------- unidades (municipios + distritos)
def matriz_reparto(cuotas: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    """Matriz municipios -> unidades: Madrid se reparte entre distritos según su peso actual."""
    u = pd.read_csv(DATA_PROCESSED / "unidades.csv", dtype={"cod_ine": str})
    cod = cuotas["cod_ine"].tolist()
    M = np.zeros((len(cod), len(u)))
    # Municipios con demanda 0 en 2025 (p. ej., Robregordo) reciben su cuota íntegra
    peso = u.groupby("cod_ine")["demanda"].transform(
        lambda s: s / s.sum() if s.sum() > 0 else pd.Series(1.0 / len(s), index=s.index)).values
    for j, c in enumerate(u["cod_ine"]):
        M[cod.index(c), j] = peso[j]
    return u, M


# ---------------------------------------------------------------- validación
def _pliegue(panel: pd.DataFrame, corte: int, objetivo: int):
    cuotas = ajustar_cuotas(panel, ventana=(VENTANA[0], corte))
    real = panel[panel["anio"] == objetivo].set_index("cod_ine").loc[cuotas["cod_ine"], "disc_65_total"].values
    w = panel.pivot(index="cod_ine", columns="anio", values="disc_65_total").loc[cuotas["cod_ine"]]
    ingenuo = (w[corte] / w[corte].sum()).values * real.sum()
    return cuotas, real, ingenuo


def _error(pred, real) -> float:
    return float(np.abs(pred - real).sum() / 2)  # personas mal asignadas entre municipios


def calibrar(panel: pd.DataFrame, corte=2019, objetivo=2024) -> tuple[float, float]:
    """Elige la amortiguación phi y el factor de incertidumbre kappa en un pliegue de calibración."""
    cuotas, real, _ = _pliegue(panel, corte, objetivo)
    mejor = min(PHIS, key=lambda f: _error(simular_cuotas(cuotas, [objetivo], None, 1, True, phi=f)[0, 0] * real.sum(), real))
    h = objetivo - corte
    hd = horizonte_amortiguado(h, mejor)
    mu = cuotas["log_cuota_final"].values + cuotas["pendiente"].values * hd
    mu = mu - np.log(np.exp(mu).sum())
    sd = np.sqrt(cuotas["sigma"].values ** 2 + (cuotas["se_pendiente"].values * hd) ** 2)
    z = (np.log(real / real.sum() + 1e-9) - mu) / sd
    kappa = float(np.quantile(np.abs(z), 0.8) / 1.2816)
    return mejor, max(kappa, 1.0)


def backtest(panel: pd.DataFrame, phi: float, kappa: float, corte=2020, objetivo=2025) -> dict:
    """Evalúa en un pliegue distinto del de calibración: ajusta hasta 'corte' y predice 'objetivo'."""
    cuotas, real, ingenuo = _pliegue(panel, corte, objetivo)
    total = real.sum()
    pred = simular_cuotas(cuotas, [objetivo], None, 1, True, phi=phi)[0, 0] * total
    sin_amort = simular_cuotas(cuotas, [objetivo], None, 1, True, phi=1.0)[0, 0] * total
    sims = simular_cuotas(cuotas, [objetivo], np.random.default_rng(1), n=1000, phi=phi, kappa=kappa)[:, 0, :] * total
    lo, hi = np.percentile(sims, 10, axis=0), np.percentile(sims, 90, axis=0)
    i = cuotas["cod_ine"].tolist().index("28079")
    return {"corte": corte, "objetivo": objetivo, "error_modelo": _error(pred, real),
            "error_sin_amortiguar": _error(sin_amort, real), "error_ingenuo": _error(ingenuo, real),
            "cobertura_80": float(((real >= lo) & (real <= hi)).mean()),
            "error_madrid_modelo": float(pred[i] - real[i]), "error_madrid_ingenuo": float(ingenuo[i] - real[i])}


def backtest_regional(serie: pd.Series, corte=2020, objetivo=2025) -> dict:
    s = np.log(serie.loc[VENTANA[0]:corte])
    g = (s.iloc[-1] - s.iloc[0]) / (len(s) - 1)
    pred = float(np.exp(s.iloc[-1] + g * (objetivo - corte)))
    return {"pred": pred, "real": float(serie[objetivo]), "error_pct": (pred / serie[objetivo] - 1) * 100}


# ---------------------------------------------------------------- principal
def main() -> None:
    rng = np.random.default_rng(SEMILLA)
    panel = pd.read_csv(DATA_PROCESSED / "demanda_municipal.csv", dtype={"cod_ine": str})
    serie = panel.groupby("anio")["disc_65_total"].sum()
    p65 = poblacion_65()
    par = parametros_regionales(serie, p65)
    anios = list(range(ANIO_BASE + 1, 2042))

    total = simular_total_regional(serie[ANIO_BASE], p65, par, anios, rng)
    reg = pd.DataFrame({"anio": anios,
                        "p10": np.percentile(total, 10, axis=0), "p50": np.percentile(total, 50, axis=0),
                        "p90": np.percentile(total, 90, axis=0),
                        "solo_envejecimiento": [serie[ANIO_BASE] * p65[a] / p65[ANIO_BASE] for a in anios],
                        "tendencia_historica": [serie[ANIO_BASE] * p65[a] / p65[ANIO_BASE] * np.exp(par["delta_hist"] * (a - ANIO_BASE)) for a in anios]})
    reg = pd.concat([pd.DataFrame({"anio": serie.index, "observado": serie.values}), reg], ignore_index=True)

    phi, kappa = calibrar(panel)
    cuotas = ajustar_cuotas(panel)
    idx_h = [anios.index(a) for a in HORIZONTES]
    sh = simular_cuotas(cuotas, HORIZONTES, rng, phi=phi, kappa=kappa)                       # (n, H, municipios)
    dem_mun = sh * total[:, idx_h][:, :, None]
    unidades, M = matriz_reparto(cuotas)
    dem_uni = dem_mun @ M                                                # (n, H, unidades)

    filas, esc = [], []
    for k, a in enumerate(HORIZONTES):
        q = np.percentile(dem_uni[:, k, :], [10, 50, 90], axis=0)
        filas.append(pd.DataFrame({"id_unidad": unidades["id_unidad"], "nombre": unidades["nombre"], "anio": a,
                                   "demanda_2025": unidades["demanda"], "p10": q[0], "p50": q[1], "p90": q[2]}))
        e = pd.DataFrame(dem_uni[:, k, :].round(1), columns=unidades["id_unidad"])
        e.insert(0, "anio", a)
        e.insert(0, "escenario", np.arange(len(e)))
        esc.append(e)
    pred = pd.concat(filas, ignore_index=True)
    pred["crec_p50_pct"] = (pred["p50"] / pred["demanda_2025"].where(pred["demanda_2025"] > 0) - 1) * 100

    reg.round(1).to_csv(DATA_PROCESSED / "prediccion_regional.csv", index=False)
    pred.round(1).to_csv(DATA_PROCESSED / "prediccion_unidades.csv", index=False)
    pd.concat(esc).to_csv(DATA_PROCESSED / "escenarios_demanda.csv.gz", index=False, compression="gzip")
    cuotas.round(5).to_csv(DATA_PROCESSED / "modelo_cuotas.csv", index=False)

    bt, btr = backtest(panel, phi, kappa), backtest_regional(serie)
    L = ["# Predicción de la demanda de cuidados (personas de 65+ con discapacidad)", "",
         f"Base {ANIO_BASE}: {int(serie[ANIO_BASE])} personas. Ventana de ajuste {VENTANA[0]}-{VENTANA[1]}. "
         f"{N_ESCENARIOS} escenarios Monte Carlo (semilla {SEMILLA}).", "", "## Parámetros regionales",
         f"- Crecimiento anual histórico de la demanda: {par['crec_demanda'] * 100:.2f} %.",
         f"- Crecimiento anual proyectado de la población de 65+ (2026-2031): {par['crec_pob'] * 100:.2f} %.",
         f"- Deriva anual de la prevalencia (diferencia): {par['delta_hist'] * 100:.2f} %; se simula entre 0 y este valor.",
         f"- Volatilidad interanual (desviación típica del crecimiento): {par['sigma'] * 100:.2f} %.", "",
         "## Total regional"]
    for a in HORIZONTES:
        r = reg[reg["anio"] == a].iloc[0]
        L.append(f"- {a}: {r['p50']:,.0f} personas (intervalo 80 %: {r['p10']:,.0f}-{r['p90']:,.0f}); "
                 f"solo por envejecimiento {r['solo_envejecimiento']:,.0f}; si sigue la tendencia {r['tendencia_historica']:,.0f}. "
                 f"Crecimiento central frente a 2025: {(r['p50'] / serie[ANIO_BASE] - 1) * 100:.0f} %.")
    L += ["", "## Unidades que más crecen hasta 2035 (mediana, unidades con más de 300 personas)"]
    p35 = pred[(pred["anio"] == 2035) & (pred["demanda_2025"] > 300)].sort_values("crec_p50_pct", ascending=False)
    for _, r in p35.head(10).iterrows():
        L.append(f"- {r['nombre']}: {r['demanda_2025']:.0f} -> {r['p50']:.0f} (+{r['crec_p50_pct']:.0f} %; 80 %: {r['p10']:.0f}-{r['p90']:.0f}).")
    L += ["", "## Validación (backtest)",
          f"- Total regional: con datos hasta {2020} se predice {btr['pred']:,.0f} para 2025 frente a {btr['real']:,.0f} reales "
          f"(error {btr['error_pct']:+.1f} %).",
          f"- Calibración (ajuste hasta 2019, predicción de 2024): amortiguación de la tendencia phi = {phi}, "
          f"factor de incertidumbre kappa = {kappa:.2f}.",
          f"- Evaluación en otro pliegue (ajuste hasta 2020, predicción de 2025). Personas mal asignadas entre municipios: "
          f"modelo {bt['error_modelo']:,.0f}; tendencia sin amortiguar {bt['error_sin_amortiguar']:,.0f}; "
          f"cuota constante {bt['error_ingenuo']:,.0f} ({(1 - bt['error_modelo'] / bt['error_ingenuo']) * 100:.0f} % menos error que la cuota constante).",
          f"- Madrid capital: error del modelo {bt['error_madrid_modelo']:+,.0f} personas; cuota constante {bt['error_madrid_ingenuo']:+,.0f}.",
          f"- Cobertura real de los intervalos del 80 % (calibrados): {bt['cobertura_80'] * 100:.0f} % de los municipios.",
          "", "## Supuestos y limitaciones",
          "- El crecimiento pasado de la población de 65+ se aproxima con el proyectado para 2026-2031.",
          "- La prevalencia de discapacidad entre los mayores se supone igual en todos los distritos de Madrid.",
          "- Los distritos de Madrid mantienen su peso actual dentro de la ciudad (no hay proyecciones por distrito).",
          "- La discapacidad reconocida es una aproximación de la necesidad de cuidados; no es la dependencia."]
    (REPORTS / "prediccion.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()

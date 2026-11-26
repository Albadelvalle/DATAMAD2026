# CuidaCerca

Dónde vives no debería decidir qué cuidados recibes. CuidaCerca cruza datos abiertos de la Comunidad de Madrid
para detectar déficits de plazas de residencia y centro de día para personas mayores, predecir su evolución,
optimizar dónde crear plazas y proponer cómo cofinanciarlas entre municipios.

Proyecto presentado a DATAMAD 2026.

## Aplicación web

Abrir `web/index.html` directamente en el navegador (no necesita servidor), o servirla con
`python -m http.server -d web 8000` y entrar en http://localhost:8000. Pestañas:

1. **Diagnóstico**: accesibilidad a centros de día y residencias por municipio y distrito de Madrid.
2. **Futuro**: previsión de la necesidad a 2030-2035 con incertidumbre.
3. **Planificador**: frente eficiencia-equidad de planes óptimos; clic en un punto para ver el plan en el mapa.
4. **Reparto de costes**: juego cooperativo por centro (valor de Shapley y núcleo), con costes editables.

Publicación en GitHub Pages: el flujo `.github/workflows/pages.yml` publica `web/` en cada push a `main`
(activar en Settings > Pages > Source: GitHub Actions).

## Ejecución

```bash
pip install -r requirements.txt
python run_pipeline.py                    # datos, diagnóstico, previsión y exportación a la web
python -m cuidacerca.planes               # planes óptimos para la web (desde src/; varios minutos)
python -m cuidacerca.experimentos --informe   # comparación de algoritmos (tras ejecutar --config ...)
for t in tests/test_*.py; do python $t; done  # comprobaciones
```

## Estructura

```
data/raw/         datos originales descargados del Portal de Datos Abiertos de la Comunidad de Madrid
data/processed/   datos limpios generados por el pipeline
src/cuidacerca/   código: preprocess, coverage, forecast, opt/ (instancia, evaluador, MILP, heurísticas),
                  experimentos, planes, game (teoría de juegos), web_export
web/              aplicación web estática (HTML + JS, Leaflet incluido en web/vendor)
reports/          informe de calidad de datos
tests/            comprobaciones
```

## Fuentes (Portal de Datos Abiertos de la Comunidad de Madrid)

- Registro de centros de atención social
- Personas con discapacidad por edad y sexo. Municipios
- Centros, servicios y establecimientos sanitarios
- Centros de servicios sociales por tipo. Municipios
- Solicitudes y resoluciones del sistema para la autonomía y atención a la dependencia
- Beneficiarios y prestaciones del sistema para la autonomía y atención a la dependencia
- Proyecciones de población por sexo
- Padrón municipal del Ayuntamiento de Madrid (datos.madrid.es), para repartir Madrid por distritos

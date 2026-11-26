# Cuida2Cerca

**Plazas de centro de día para personas mayores, donde se necesitan.**

Cuida2Cerca cruza datos abiertos de la Comunidad de Madrid para detectar dónde faltan plazas de centro de día
para personas mayores, prever cómo crecerá la necesidad hasta 2035, decidir dónde abrir plazas con un
presupuesto limitado y repartir su coste entre los municipios que las comparten.

- **Aplicación web:** <https://sergiop3rez.github.io/Cuida2Cerca/>
- **Concurso:** DATAMAD 2026 · Datos abiertos de la Comunidad de Madrid
- **Autores:** Elena del Carmen Gavilán García · Sergio Pérez Peló

# Demo GIF

![Demo](https://kommodo.ai/i/5Yu1ONll8L7UxStuH7m4)
---

## Qué hace

La web tiene cuatro pestañas, pensadas para que la use quien decide sin necesidad de saber de algoritmos:

| Pestaña | Pregunta | Qué muestra |
|---|---|---|
| **1 · Diagnóstico** | ¿Dónde falta hoy? | Plazas accesibles por cada 100 personas en los 178 municipios y los 21 distritos de Madrid, frente a la media regional. Se puede elegir el servicio (centro de día o residencia), el tipo de financiación y qué se considera «cerca» (15 o 5 km). |
| **2 · Futuro** | ¿Cuánto faltará? | Previsión de la necesidad para 2030 y 2035, con intervalos de incertidumbre obtenidos de 500 escenarios simulados. |
| **3 · Planificador** | ¿Dónde abrir plazas? | Planes óptimos para varios presupuestos y pesos de la equidad, en un gráfico eficiencia frente a equidad. Al hacer clic en un plan se ven en el mapa los centros que abre o amplía. |
| **4 · Reparto de costes** | ¿Quién paga? | Para cada centro, cuánto pagaría cada municipio usuario según el valor de Shapley, si el acuerdo es estable (núcleo) y cuánto ahorran frente a ir solos. Los costes son editables. |

La pestaña **Metodología y datos** resume los supuestos y enlaza las fuentes.

## Datos

Todos los datos son abiertos y están incluidos en `data/raw/`, así que no hace falta descargarlos para
reproducir los resultados.

| Conjunto de datos | Fuente | Para qué se usa |
|---|---|---|
| [Registro de centros de atención social](https://datos.comunidad.madrid/dataset/atencion_social_registro_centros) | Comunidad de Madrid | Oferta: plazas, tipo de centro, financiación y ubicación |
| [Personas con discapacidad por edad y sexo. Municipios](https://datos.comunidad.madrid/dataset/personas_discapacidad_por_edad_y_sexo) | Comunidad de Madrid | Demanda: personas de 65 años o más con discapacidad reconocida |
| [Centros, servicios y establecimientos sanitarios](https://datos.comunidad.madrid/dataset/centros_servicios_establecimientos_sanitarios) | Comunidad de Madrid | Punto de referencia de dónde vive la población de cada municipio |
| [Centros de servicios sociales por tipo. Municipios](https://datos.comunidad.madrid/dataset/centros_servicios_sociales_por_tipo) | Comunidad de Madrid | Validación cruzada de la oferta |
| [Solicitudes y resoluciones del sistema de dependencia](https://datos.comunidad.madrid/dataset/1914360) | Comunidad de Madrid | Tendencia de la demanda |
| [Beneficiarios y prestaciones del sistema de dependencia](https://datos.comunidad.madrid/dataset/1914361) | Comunidad de Madrid | Evolución de las prestaciones (residencia, centro de día, ayuda a domicilio…) |
| [Proyecciones de población por sexo](https://datos.comunidad.madrid/dataset/proyecciones_poblacion_por_sexo) | Comunidad de Madrid | Crecimiento de la población mayor hasta 2035 |
| [Padrón municipal](https://datos.madrid.es/dataset/200076-0-padron) | Ayuntamiento de Madrid | Reparto de la ciudad de Madrid en sus 21 distritos |

Desde 2019, los datos de discapacidad ocultan por secreto estadístico los valores entre 1 y 4. El
preprocesado los imputa por interpolación, limitados a ese rango; el detalle está en
`reports/calidad_datos.md`.

## Uso

### Ver la aplicación en local

La web es estática (HTML + JavaScript, con Leaflet incluido en `web/vendor/`) y los datos ya están
generados en `web/data/`. Basta con servirla:

```bash
python -m http.server -d web 8000
```

y abrir <http://localhost:8000>. También funciona abriendo `web/index.html` directamente en el navegador.
Los mapas de fondo se cargan de OpenStreetMap, así que hace falta conexión a internet.

### Reproducir los resultados

Requisitos: Python 3.10 o superior.

```bash
python -m venv .venv
source .venv/bin/activate            # en Windows: .venv\Scripts\activate
pip install -r requirements.txt      # pandas, numpy, ortools
```

1. **Datos, diagnóstico, previsión y exportación a la web** (unos minutos):

   ```bash
   python run_pipeline.py
   ```

   Genera `data/processed/`, los informes de `reports/` y `web/data/datos.js`.

2. **Planes óptimos para el Planificador** (lo más costoso; varios minutos por plan). Se guardan de forma
   incremental en `data/processed/planes.json`, así que se puede ejecutar por partes:

   ```bash
   cd src
   python -m cuidacerca.planes                          # radio de 15 km
   python -m cuidacerca.planes --radio 5                # radio de 5 km
   python -m cuidacerca.planes --presupuestos 1000 --configs base,beta4_cmin50   # solo algunos
   cd ..
   ```

   Configuraciones disponibles: `base` (solo eficiencia), `beta2`, `beta4`, `beta8` (equidad x3, x5, x9),
   `cmin50` (mínimo del 50 % de cobertura por zona) y `beta4_cmin50`.

3. **Volver a exportar a la web** para incorporar los planes:

   ```bash
   python run_pipeline.py
   ```

4. **Comparación de algoritmos** (opcional; reproduce `reports/optimizacion.md`):

   ```bash
   cd src
   python -m cuidacerca.experimentos --config base --algoritmos proporcional,voraz_ratio,vnd,grasp,milp
   python -m cuidacerca.experimentos --informe
   ```

5. **Comprobaciones:**

   ```bash
   for t in tests/test_*.py; do python "$t"; done
   ```

## Despliegue

### GitHub Pages (recomendado)

El workflow `.github/workflows/pages.yml` publica la carpeta `web/` en cada push a `master` o `main`.

1. Sube el repositorio a GitHub.
2. En **Settings → Pages → Build and deployment → Source**, elige **GitHub Actions**.
3. Haz un push (o lanza el workflow a mano desde la pestaña **Actions → Publicar web → Run workflow**).
4. La web quedará en `https://<usuario>.github.io/<repositorio>/`.

Si no quieres publicar la web desde un repositorio (por ejemplo, una copia), no actives Pages y elimina
`.github/` o cambia el disparador del workflow a solo `workflow_dispatch`.

### Cualquier otro alojamiento estático

Copia el contenido de `web/` a cualquier servidor de ficheros estáticos (Netlify, Vercel, un bucket S3, un
servidor Apache o Nginx…). No necesita backend ni base de datos.

## Metodología

- **Unidades de análisis:** 199 zonas (178 municipios y los 21 distritos de Madrid). La demanda son las
  personas de 65 años o más con discapacidad reconocida.
- **Accesibilidad:** método de dos pasos con decaimiento por distancia (E2SFCA, gaussiano), con radio de 15 km
  (también 5 km para centros de día) y 30 km para residencias. Distancias en línea recta.
- **Previsión:** el total regional crece con las proyecciones de población mayor de la Comunidad; el reparto
  entre zonas sigue tendencias municipales suavizadas (contracción bayesiana empírica y tendencia amortiguada).
  Se simulan 500 escenarios. En la validación con datos pasados reduce un 60 % el error frente a mantener
  constante el peso de cada zona.
- **Optimización:** programación estocástica en dos etapas. La primera decide dónde abrir o ampliar centros
  (módulos de 5 plazas, mínimo 20 por centro nuevo, máximo 150 por sitio) con un presupuesto en plazas
  equivalentes (una plaza cuesta 1 y abrir o ampliar un centro, 20 más). La segunda asigna personas a plazas
  en cada escenario como un flujo de coste mínimo. La equidad entra con pesos mayores para las zonas peor
  atendidas y, opcionalmente, con una cobertura mínima por zona. Se resuelve con un voraz por ratio seguido de
  búsqueda local VND, validado frente a un modelo exacto (MILP con OR-Tools/SCIP): queda a menos del 0,1 % del
  óptimo.
- **Reparto de costes:** juego cooperativo de localización por centro. Se calcula el valor de Shapley exacto y
  se comprueba la estabilidad con el núcleo (*least core*). Los costes por defecto (400.000 € de coste fijo,
  20.000 € por plaza y 500 € por plaza y km) son **ilustrativos** y se pueden cambiar en la web.

## Estructura

```
data/raw/            datos originales (Portal de Datos Abiertos de la Comunidad de Madrid y padrón de Madrid)
data/processed/      datos generados por el pipeline (cobertura, previsión, escenarios, planes)
data/instances/      instancias de optimización serializadas
src/cuidacerca/      código
  preprocess.py        limpieza, unión y secreto estadístico
  coverage.py          accesibilidad E2SFCA y diagnóstico
  forecast.py          previsión y escenarios de demanda
  opt/                 instancia, evaluador (flujo de coste mínimo), MILP y heurísticas
  experimentos.py      comparación de algoritmos
  planes.py            planes precalculados para la web
  game.py              teoría de juegos: Shapley y núcleo
  web_export.py        exportación de datos a la web
web/                 aplicación web estática
reports/             informes de calidad de datos, diagnóstico, previsión y optimización
tests/               comprobaciones
run_pipeline.py      ejecución reproducible de todo el pipeline (salvo la optimización)
```

## Limitaciones

- Distancias en línea recta, no por carretera ni en transporte público.
- La demanda de cada distrito de Madrid reparte la del municipio según su población de 65 años o más.
- «Financiación pública» incluye centros públicos, concertados y los que admiten la prestación vinculada; el
  registro no indica cuántas plazas de cada centro están concertadas.
- Los costes económicos no proceden de los datos abiertos: son parámetros que cada administración debe ajustar.
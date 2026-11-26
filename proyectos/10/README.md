# Cascada

**En qué momento llega la amenaza a quien no puede protegerse.**

Equipo 10 · José Ignacio Atance Álvarez

Cascada cruza las capas de peligrosidad del **Catálogo de Riesgos Potenciales de la Comunidad de Madrid** con los **5.630 centros** donde se concentra la población con menor capacidad de autoprotección: centros educativos, hospitales y centros de diálisis, y centros de atención social. Ante un **incendio forestal** o la **rotura de una presa**, simula minuto a minuto durante 24 horas cómo avanza la amenaza y a qué hora llega a cada centro, población, carretera y tren.

## Para verlo en 5 minutos

1. **Presentación ultraejecutiva** (4 diapositivas): [Cascada_presentacion_ultraejecutiva.pdf](Cascada_presentacion_ultraejecutiva.pdf)
2. **Tres clips de 15 segundos**, sin sonido:
   - [Incendio](Cascada_incendio%20%2815seg%29.mp4): incendio junto a Torrejón de la Calzada, de la ignición a las 24 horas.
   - [Rotura de presa, en el mapa](Cascada_presa_mapa%20%2815seg%29.mp4): presa de Santillana; la cámara sigue el frente del agua por el Manzanares.
   - [Rotura de presa, en 3D](Cascada_presa_3D%20%2815seg%29.mp4): la misma rotura sobre el relieve.
3. Si hay más tiempo: el [vídeo completo de la demostración](Cascada_demo_completa%20%283min%29.mp4) (3 min 30 s) y la [presentación completa](Cascada_presentacion_completa.pdf).

## Contenido de esta carpeta

- **Presentación ultraejecutiva** (formato de la entrega: título, problema y datos, resultados, y pantallazo del sistema): [Cascada_presentacion_ultraejecutiva.pdf](Cascada_presentacion_ultraejecutiva.pdf)
- **Presentación completa** (7 diapositivas: problema, alcance del proyecto y del demostrador, datos, modelos y valor diferencial): [Cascada_presentacion_completa.pdf](Cascada_presentacion_completa.pdf)
- **Clips de 15 segundos:** incendio y rotura de presa, en el mapa y en 3D (enlaces arriba)
- **Vídeo de la demostración** (3 min 30 s): [Cascada_demo_completa (3min).mp4](Cascada_demo_completa%20%283min%29.mp4), también en YouTube: https://youtu.be/g9kXkLE636I
- **Código fuente y documentación:** carpeta [codigo/](codigo/), copia de la versión entregada (commit 2a149b7), y en https://github.com/JIAA68/cascada. Licencia EUPL 1.2

## Alcance: el proyecto y el demostrador

**El proyecto** diseña tres capacidades complementarias sobre los mismos mapas, datos y motores de cálculo:

- **Riesgo basal (siempre).** Para cada celda de 1 km y cada centro, qué riesgos del catálogo le afectan, con la matriz peligrosidad × vulnerabilidad del propio catálogo.
- **Prealerta (próximos 7 días).** Con la previsión y los avisos de AEMET en los 179 municipios, qué centros quedan expuestos y qué peligros del catálogo activa el tiempo.
- **Gestión de crisis (ante una alerta).** Evolución de la amenaza y hora de llegada a cada centro, con el efecto cascada en instalaciones Seveso y conducciones, y los avisos a la población.

**El demostrador** que se entrega implementa una parte, sin cerrar el paso al resto:

- **Análisis basal, en versión reducida.** Para cada celda de 1 km de la rejilla europea y para cada centro, qué riesgos del catálogo le afectan, con su población (Censo 2021) y el riesgo calculado con la matriz del catálogo.
- **Crisis por incendio forestal.** Una alerta en un punto (clic en el mapa o foco de calor de satélite) arranca una simulación de 24 horas con un modelo de Rothermel propio: combustibles de la Comunidad de Madrid, relieve del IGN y viento de AEMET, en celdas de 50 m. El visor reproduce el avance, el humo, los centros alcanzados, el efecto cascada en instalaciones Seveso y conducciones de hidrocarburos, y las carreteras y trenes afectados, y genera un ES-Alert y un mensaje para redes sociales ficticios. Contrastado con siete incendios reales de la Comunidad.
- **Crisis por rotura de presa.** 15 presas deducidas de la capa de rotura de presas del catálogo. El agua baja por la zona inundable con una onda que se frena con la distancia, calibrada con la zona de la primera media hora del propio catálogo.
- Vista en 3D sobre el relieve del IGN.

Se ejecuta en local con un servidor en Python y un visor web (MapLibre). Un solo comando descarga las fuentes oficiales y regenera todos los datos. Instalación y uso en [codigo/README.md](codigo/README.md).

## Datos abiertos de la Comunidad de Madrid

- Catálogo de Riesgos Potenciales, capas de peligrosidad (geoportal IDEM): https://idem.comunidad.madrid/recursos_cat_geo/Catalogo/recursos/ZonasRiesgo/PCivil/
- Centros educativos: https://datos.comunidad.madrid/dataset/c750856d-3166-4dac-8e80-d1b824c968b5
- Centros, servicios y establecimientos sanitarios: https://datos.comunidad.madrid/dataset/d8a0a444-adf5-4c04-8999-0eac3de52cb7
- Registro de centros de atención social: https://datos.comunidad.madrid/dataset/b8cdb7f7-3185-4938-800a-fefda72333f5
- Municipios y distritos (2020): https://datos.comunidad.madrid/dataset/6c63b14c-9f5d-414f-958f-b8a9c53d69fc
- Mapa de modelos de combustibles (IDEM, servicio WFS de zonas de riesgo)
- Base Topográfica Armonizada: red viaria y ferroviaria (IDEM, servicio WFS)
- Red de Calidad del Aire, datos meteorológicos: https://datos.comunidad.madrid/dataset/7f3699fc-d646-4efa-9387-1f5aed4a45b6

## Otras fuentes

INE (Censo 2021 en rejilla de 1 km), IGN (mapa base, ortofoto PNOA, modelo digital del terreno y Nomenclátor), AEMET OpenData (viento), Copernicus EFFIS (combustibles y áreas quemadas), NASA FIRMS (focos de calor), Renfe (trenes en tiempo real y horarios), Ayuntamiento de Madrid (tráfico) y DGT (incidencias). Licencias y atribuciones completas en [codigo/README.md](codigo/README.md).

# Cascada

**Cuándo llega la amenaza a quien no puede protegerse.**

Equipo 10 · José Ignacio Atance Álvarez

Cascada cruza las capas de peligrosidad del **Catálogo de Riesgos Potenciales de la Comunidad de Madrid** con los **5.630 centros** donde se concentra la población con menor capacidad de autoprotección: centros educativos, hospitales y centros de diálisis, y centros de atención social. Ante un **incendio forestal** o la **rotura de una presa**, simula minuto a minuto durante 24 horas cómo avanza la amenaza y a qué hora llega a cada centro, población, carretera y tren.

## Enlaces

- **Código fuente y documentación:** en la carpeta [codigo/](codigo/), copia de la versión entregada (commit 2a149b7), y en https://github.com/JIAA68/cascada. Licencia EUPL 1.2
- **Vídeo de la demostración** (3 min 30 s): [cascada_demostracion.mp4](cascada_demostracion.mp4), en esta carpeta, y en YouTube: https://youtu.be/g9kXkLE636I
- **Presentación:** [cascada_presentacion.pdf](cascada_presentacion.pdf), en esta carpeta

## Qué hace

- **Riesgo basal.** Para cada celda de 1 km de la rejilla europea y para cada centro, qué riesgos del catálogo le afectan, con su población (Censo 2021) y el riesgo calculado con la matriz peligrosidad × vulnerabilidad del propio catálogo.
- **Incendio forestal.** Una alerta en un punto (clic en el mapa o foco de calor de satélite) arranca una simulación de 24 horas con un modelo de Rothermel propio: combustibles de la Comunidad de Madrid, relieve del IGN y viento de AEMET, en celdas de 50 m. El visor reproduce el avance, el humo, los centros alcanzados, el efecto cascada en instalaciones Seveso y conducciones de hidrocarburos, carreteras y trenes cortados, y genera un ES-Alert y un mensaje para redes sociales ficticios. Contrastado con siete incendios reales de la Comunidad.
- **Rotura de presa.** 15 presas deducidas de la capa de rotura de presas del catálogo. El agua baja por la zona inundable con una onda que se frena con la distancia, calibrada con la zona de la primera media hora del propio catálogo.
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

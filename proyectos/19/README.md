# BARómetro
 
**¿Habrá negocio aquí? Mira los datos antes de firmar.**
 
Autora: Mengying Xia Ruan (participante individual)
 
BARómetro ayuda a quien va a abrir o traspasar un bar, una cafetería o un restaurante en la Comunidad de Madrid. Para cualquier dirección, mira lo que hay a 300 metros y responde a cuatro preguntas: quién pasa, cuándo tendrías más clientes según tu tipo de local, qué te conviene ofrecer y a qué precios. Siempre dice si cada respuesta es un dato o una estimación y cuánto te puedes fiar.
 
## Enlaces
 
- **Aplicación (demo):** https://barometro-madrid.streamlit.app/
- **Repositorio con todo el código, los datos procesados y la documentación:** https://github.com/Mengying04/barometro
- **Presentación:** `BARometro_DATAMAD2026.pdf` (en esta carpeta)

## Datos
 
15 conjuntos del Portal de Datos Abiertos de la Comunidad de Madrid, todos usados en los cálculos, más el Instituto Nacional de Estadística, el censo de locales del Ayuntamiento de Madrid, los horarios y la demanda del Consorcio Regional de Transportes, OpenStreetMap y CartoCiudad. La lista completa, con enlaces, licencias y fechas, está en `docs/fuentes.md` del repositorio.
 
## Reproducibilidad
 
Código abierto con licencia MIT. Todo se regenera con los programas del repositorio, hay un fichero Docker y cada lunes un proceso automático vuelve a descargar los datos, los procesa y pasa 38 comprobaciones de calidad.

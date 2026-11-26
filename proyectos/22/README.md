# Respira MAD

**¿Puedo salir ahora?** Una app web que dice a quien tiene asma o alergia al polen, a las personas
mayores y a quien cuida de niños pequeños si es seguro salir ahora en la Comunidad de Madrid,
combinando calidad del aire, polen y tiempo, solo con datos abiertos oficiales.

- **App:** https://respira-mad.onrender.com
- **Código (repositorio original):** https://github.com/meganbougle/respira-mad
- **Presentación:** `Respira_MAD_Entrega_DataMad_2026.pdf` (en esta carpeta)
- **Autora:** Megan Bougle

## Qué hay en esta carpeta

| Ruta | Qué es |
|---|---|
| `Respira_MAD_Entrega_DataMad_2026.pdf` | La presentación del proyecto |
| `respira-mad/` | El proyecto completo: código, modelos entrenados, datos de respaldo e informes |
| `respira-mad/README.md` | Qué hace la app y cómo ejecutarla |
| `respira-mad/PROYECTO.md` | Todo el proyecto en un documento |
| `respira-mad/MODEL_REPORT.md` | Cómo predecimos el polen y la calidad del aire, con los resultados de las pruebas |
| `respira-mad/DATA_AUDIT.md` | Auditoría de los datos abiertos utilizados |

## Qué hace

- **Resultado de ahora** para tu punto y tu perfil (general, asma, persona mayor, niño/a):
  «Puedes salir», «Precaución» o «Mejor quédate en casa», con su causa y la recomendación oficial
  citada literalmente (BOE para el aire, Comunidad de Madrid para el polen).
- **Próximas 24 horas, mejores franjas para salir, planificador de 5 días** y gráfico de evolución
  y previsión.
- **Previsiones propias** hechas solo con datos oficiales: calidad del aire hora a hora en 52
  estaciones hasta 96 horas (menos error que «la misma hora de ayer» en las 120 horas probadas) y
  polen por tipo hasta 5 días (60 % de acierto del nivel oficial en 2025, frente al 47 % de la
  referencia).
- **Asistente con IA** que responde solo con los datos de la app y los textos oficiales.

## Datos abiertos utilizados

**Comunidad de Madrid** (datos.comunidad.madrid): `calidad_aire_datos_dia`,
`calidad_aire_estaciones`, `calidad_aire_datos_historico`, `mediciones_polen`,
`mediciones_polen_historico`, `captadores_polen`.

**Ayuntamiento de Madrid** (datos.madrid.es): 212531 calidad del aire en tiempo real, 212629
estaciones de control, 201200 datos horarios.

Además: Índice Nacional de Calidad del Aire (BOE-A-2020-10426), folleto de polen de la Comunidad de
Madrid y tiempo de Open-Meteo (CC BY 4.0).

## Cómo ejecutarla

Ver `respira-mad/README.md`. En resumen, con Python 3.13, dentro de `respira-mad/`:
`pip install -r requirements.txt` y `uvicorn api:app --port 8000`, y abrir http://localhost:8000.

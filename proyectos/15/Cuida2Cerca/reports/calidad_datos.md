# Informe de calidad y preprocesamiento de datos

## Municipios
- Municipios: 179 (excluida la categoría 'Sin municipio asignado').
- Punto de referencia desde atencion_primaria: 178 municipios.
- Punto de referencia desde centros_sociales: 1 municipios.
- Municipios con mancomunidad de servicios sociales: 100.

## Demanda (personas con discapacidad reconocida)
- Demanda: 9614 valores protegidos ('-') imputados en todas las desagregaciones; en la variable principal (65+, ambos sexos) son 103 de 2685 municipio-año.
- Suma municipal de 65+ frente al total regional (diferencia %, por año): mín -0.1, máx 0.0.

## Oferta (residencias y centros de día para mayores)
- Registro de centros de atención social: 2633 centros, 0 duplicados.
- El fichero alternativo del registro tiene 66 centros que no están en el principal (5 de mayores); no se incorporan por no estar en el registro vigente.
- Centros para personas mayores: 1072.
- Excluidos por no ser plazas de cuidados a dependientes: HOGARES Y CLUBES (230); PISOS TUTELADOS (10); RESIDENCIAS DE PERSONAS MAYORES AUTONOMAS (8); VIVIENDAS COMUNITARIAS (7); CENTROS DE ATENCIÓN (1)
- Eliminados sin plazas autorizadas válidas: 2.
- Coordenadas: 0 fuera de la Comunidad descartadas; imputadas 27 por código postal y 1 por municipio.
-   centro_dia: 322 centros, 16991 plazas (11188 en centros con financiación pública).
-   residencia: 492 centros, 56571 plazas (52774 en centros con financiación pública).
- Validación con 'Centros de servicios sociales por tipo' (2026): residencias por municipio coinciden en el 93 % de municipios; total oficial 518 frente a 492 en el registro (la estadística oficial puede contar también residencias de autónomos).

## Contexto regional
- Dependencia (2025): 220017 personas con derecho, 10056 aún sin prestación.
- Proyección 2026: 1377485 personas de 65+ (424175 de 80+).
- Proyección 2030: 1531180 personas de 65+ (481871 de 80+).
- Proyección 2035: 1738170 personas de 65+ (541508 de 80+).
- Proyección 2041: 2008370 personas de 65+ (636965 de 80+).

## Ficheros generados
- data/processed/municipios.csv: 179 filas x 10 columnas
- data/processed/demanda_municipal.csv: 2685 filas x 9 columnas
- data/processed/oferta_centros.csv: 814 filas x 19 columnas
- data/processed/dependencia_cam.csv: 18 filas x 17 columnas
- data/processed/proyecciones_cam.csv: 336 filas x 5 columnas

## Limitaciones conocidas
- El umbral de secreto estadístico (1-4) está inferido de los datos; la Comunidad no lo publica.
- La demanda usa la discapacidad reconocida en mayores de 65 como aproximación de la dependencia.
- Madrid capital es un único municipio en la demanda; el desglose por distrito requiere otra fuente.
- El registro indica si un centro tiene plazas concertadas o PEVS, pero no cuántas.

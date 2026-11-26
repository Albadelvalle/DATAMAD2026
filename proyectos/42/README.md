# 42 · Pulso Laboral Madrid

**Detección temprana de subidas inusuales del paro registrado en los 179 municipios de la Comunidad de Madrid.**

- **Aplicación:** https://pulso-laboral-madrid.streamlit.app/
- **Repositorio completo** (código, datos publicados, validación y documentación): https://github.com/romanmen-dev/pulso-laboral-madrid
- **Presentación:** `Pulso_Laboral_Madrid_DATAMAD_2026.pdf` (también en `.pptx`, con el guion en las notas)

## Equipo

- **Rodrigo Mendoza García:** datos, ingeniería y aplicación.
- **Roman Mendoza García:** método estadístico y validación.

## Qué hace

Cada mes compara el cambio del paro registrado de cada municipio con los cambios del mismo mes en los cinco años anteriores (mediana y MAD) y marca una **alerta experimental** cuando la subida supera claramente lo habitual. Cada alerta se explica: cuánto sube, frente a qué límite, qué grupo de edad concentra la subida y si es **local** (destaca también frente al resto de la Comunidad) o **regional** (compatible con la evolución del resto). Son etiquetas estadísticas, no causas.

Ayuda a los técnicos de empleo a priorizar qué municipios revisar primero. No predice el paro ni sustituye su criterio.

**Ejemplo:** en octubre de 2026 el paro de Madrid subió 2.130 personas, cuando lo habitual en octubre era +61 y el límite de alerta, +826. Ese mes hubo 15 alertas, de las que 2 son locales (Soto del Real y Alameda del Valle).

## Validación

Sin información futura y sin una lista oficial de anomalías con la que comparar:

- **Episodio conocido:** en abril de 2020 saltó la alerta en el 67,5 % de los municipios evaluables, frente al 5,5 % en los abriles de 2017-2019.
- **Sensibilidad ante subidas sintéticas (2015-2019):** una subida del 10 % se detecta en el 94,8 % de los municipios con más paro y en el 8,4 % de los de menos.
- **Tasa de alertas en calma (2017-2019):** 5,5 % de los meses evaluables; una alerta pide revisar el caso, no confirma un deterioro.
- **Comparación con tres métodos alternativos**, entre ellos un quasi-Poisson tipo Farrington (vigilancia de brotes en salud pública).

Detalle en `docs/validacion.md` y `docs/metodologia.md` del repositorio.

## Conjuntos de datos

| Conjunto | Uso |
|---|---|
| [Paro registrado por edad y municipio](https://datos.comunidad.madrid/dataset/paro_registrado_edad_municipio) | Serie principal (enero de 2005 – octubre de 2026) |
| [Contratos de trabajo por municipio](https://datos.comunidad.madrid/dataset/contratos_trabajo_municipio) | Contexto aparte en la ficha; se cuentan por centro de trabajo y no intervienen en el detector |
| [Municipios de la Comunidad de Madrid](https://datos.comunidad.madrid/dataset/municipio_comunidad_madrid) | Códigos INE para cruzar el mapa |
| [Límites municipales (Geoportal IDEM)](https://idem.comunidad.madrid/catalogocartografia/srv/spa/catalog.search#/metadata/spacm_divisionesadmin) | Mapa interactivo |

Datos con licencia CC BY 4.0 (Comunidad de Madrid). Descarga reproducible verificada con SHA-256; las incidencias de la fuente se documentan sin corregirlas. Código con licencia MIT.

## Cómo ejecutarlo

Instrucciones completas en el README del repositorio. En resumen:

```bash
git clone https://github.com/romanmen-dev/pulso-laboral-madrid
cd pulso-laboral-madrid
pip install -r requirements.txt
streamlit run app.py
```

Pulso Laboral Madrid es un proyecto independiente: no es una herramienta oficial de la Comunidad de Madrid.

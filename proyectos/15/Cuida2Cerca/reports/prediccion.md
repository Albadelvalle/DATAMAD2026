# Predicción de la demanda de cuidados (personas de 65+ con discapacidad)

Base 2025: 193492 personas. Ventana de ajuste 2015-2025. 500 escenarios Monte Carlo (semilla 2026).

## Parámetros regionales
- Crecimiento anual histórico de la demanda: 4.15 %.
- Crecimiento anual proyectado de la población de 65+ (2026-2031): 2.64 %.
- Deriva anual de la prevalencia (diferencia): 1.50 %; se simula entre 0 y este valor.
- Volatilidad interanual (desviación típica del crecimiento): 2.57 %.

## Total regional
- 2030: 228,589 personas (intervalo 80 %: 217,998-238,515); solo por envejecimiento 220,529; si sigue la tendencia 237,756. Crecimiento central frente a 2025: 18 %.
- 2035: 269,306 personas (intervalo 80 %: 251,203-290,227); solo por envejecimiento 250,341; si sigue la tendencia 290,979. Crecimiento central frente a 2025: 39 %.

## Unidades que más crecen hasta 2035 (mediana, unidades con más de 300 personas)
- Arroyomolinos: 371 -> 751 (+102 %; 80 %: 601-933).
- Fuenlabrada: 5605 -> 10438 (+86 %; 80 %: 8633-12617).
- Rivas-Vaciamadrid: 1389 -> 2532 (+82 %; 80 %: 2262-2854).
- Paracuellos de Jarama: 429 -> 750 (+75 %; 80 %: 525-1054).
- Mejorada del Campo: 541 -> 930 (+72 %; 80 %: 825-1073).
- Humanes de Madrid: 456 -> 784 (+72 %; 80 %: 660-922).
- Villanueva de la Cañada: 452 -> 773 (+71 %; 80 %: 682-871).
- San Martín de la Vega: 434 -> 720 (+66 %; 80 %: 613-845).
- Colmenar Viejo: 1393 -> 2248 (+61 %; 80 %: 1912-2627).
- Alpedrete: 359 -> 574 (+60 %; 80 %: 463-683).

## Validación (backtest)
- Total regional: con datos hasta 2020 se predice 209,436 para 2025 frente a 193,492 reales (error +8.2 %).
- Calibración (ajuste hasta 2019, predicción de 2024): amortiguación de la tendencia phi = 0.85, factor de incertidumbre kappa = 3.27.
- Evaluación en otro pliegue (ajuste hasta 2020, predicción de 2025). Personas mal asignadas entre municipios: modelo 3,429; tendencia sin amortiguar 4,396; cuota constante 8,648 (60 % menos error que la cuota constante).
- Madrid capital: error del modelo +1,351 personas; cuota constante +7,655.
- Cobertura real de los intervalos del 80 % (calibrados): 65 % de los municipios.

## Supuestos y limitaciones
- El crecimiento pasado de la población de 65+ se aproxima con el proyectado para 2026-2031.
- La prevalencia de discapacidad entre los mayores se supone igual en todos los distritos de Madrid.
- Los distritos de Madrid mantienen su peso actual dentro de la ciudad (no hay proyecciones por distrito).
- La discapacidad reconocida es una aproximación de la necesidad de cuidados; no es la dependencia.

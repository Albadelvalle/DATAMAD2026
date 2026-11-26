# Optimización de plazas de centro de día: algoritmos y compromiso eficiencia-equidad

Instancia: 2030, meta 5,8 plazas/100, radio 15 km, presupuesto 1.000 plazas equivalentes (coste fijo 20 por centro nuevo). Entrenamiento con 20 escenarios, evaluación con 500.

## Comparación de algoritmos (objetivo del propio modelo, 500 escenarios)

### base (beta = 0, cobertura mínima = 0)

| Algoritmo | Objetivo (500) | Diferencia con el mejor | Segundos |
|---|---|---|---|
| milp_scip | 1,391.26 | +0.00 % | 50.8 |
| voraz_ratio+vnd | 1,391.46 | +0.01 % | 30.0 |
| reparto_proporcional | 1,400.17 | +0.64 % | 0.0 |
| grasp_a0.3+vnd | 1,411.27 | +1.44 % | 45.1 |
| voraz_ratio | 1,423.35 | +2.31 % | 0.4 |
| voraz_exacto | 1,423.99 | +2.35 % | 28.4 |

### beta1 (beta = 1, cobertura mínima = 0)

| Algoritmo | Objetivo (500) | Diferencia con el mejor | Segundos |
|---|---|---|---|
| milp_scip | 1,446.75 | +0.00 % | 90.9 |
| voraz_ratio+vnd | 1,459.33 | +0.87 % | 28.8 |
| reparto_proporcional | 1,482.02 | +2.44 % | 0.0 |
| voraz_ratio | 1,484.26 | +2.59 % | 0.4 |
| grasp_a0.3+vnd | 1,491.20 | +3.07 % | 45.0 |

### beta2 (beta = 2, cobertura mínima = 0)

| Algoritmo | Objetivo (500) | Diferencia con el mejor | Segundos |
|---|---|---|---|
| milp_scip | 1,475.41 | +0.00 % | 81.6 |
| voraz_ratio+vnd | 1,489.18 | +0.93 % | 40.9 |
| voraz_ratio | 1,513.61 | +2.59 % | 0.6 |
| reparto_proporcional | 1,518.29 | +2.91 % | 0.0 |
| grasp_a0.3+vnd | 1,519.47 | +2.99 % | 45.0 |

### beta4 (beta = 4, cobertura mínima = 0)

| Algoritmo | Objetivo (500) | Diferencia con el mejor | Segundos |
|---|---|---|---|
| milp_scip | 1,488.41 | +0.00 % | 121.7 |
| voraz_ratio+vnd | 1,527.39 | +2.62 % | 40.7 |
| voraz_ratio | 1,561.88 | +4.94 % | 0.7 |
| grasp_a0.3+vnd | 1,564.08 | +5.08 % | 45.0 |
| reparto_proporcional | 1,587.36 | +6.65 % | 0.0 |

### beta8 (beta = 8, cobertura mínima = 0)

| Algoritmo | Objetivo (500) | Diferencia con el mejor | Segundos |
|---|---|---|---|
| voraz_ratio+vnd | 1,512.49 | +0.00 % | 41.1 |
| voraz_ratio | 1,525.90 | +0.89 % | 1.0 |
| milp_scip | 1,543.85 | +2.07 % | 122.1 |
| grasp_a0.3+vnd | 1,559.94 | +3.14 % | 45.0 |
| reparto_proporcional | 1,721.34 | +13.81 % | 0.0 |

### cmin50 (beta = 0, cobertura mínima = 0.5)

| Algoritmo | Objetivo (500) | Diferencia con el mejor | Segundos |
|---|---|---|---|
| milp_scip | 1,453.09 | +0.00 % | 121.2 |
| voraz_ratio+vnd | 1,461.57 | +0.58 % | 40.7 |
| voraz_ratio | 1,485.16 | +2.21 % | 0.9 |
| grasp_a0.3+vnd | 1,489.82 | +2.53 % | 45.1 |
| reparto_proporcional | 1,503.73 | +3.48 % | 0.0 |

### beta4_cmin50 (beta = 4, cobertura mínima = 0.5)

| Algoritmo | Objetivo (500) | Diferencia con el mejor | Segundos |
|---|---|---|---|
| voraz_ratio+vnd | 1,504.49 | +0.00 % | 41.1 |
| voraz_ratio | 1,525.28 | +1.38 % | 1.1 |
| milp_scip | 1,553.15 | +3.23 % | 121.5 |
| grasp_a0.3+vnd | 1,573.41 | +4.58 % | 45.5 |
| reparto_proporcional | 1,698.13 | +12.87 % | 0.0 |

## Compromiso eficiencia-equidad (mejor solución de cada configuración, evaluador neutral)

| Configuración | Personas sin plaza | Zonas con cobertura < 50 % | Necesidad en esas zonas | Gini de accesibilidad | Zonas con accesibilidad < mitad de la media | Km medio | Centros nuevos |
|---|---|---|---|---|---|---|---|
| base | 1,218 | 13 | 162 | 0.096 | 37 | 1.44 | 6 |
| beta1 | 1,218 | 11 | 346 | 0.089 | 33 | 1.56 | 6 |
| beta2 | 1,219 | 11 | 346 | 0.092 | 32 | 1.61 | 6 |
| beta4 | 1,258 | 3 | 329 | 0.086 | 22 | 1.60 | 8 |
| beta8 | 1,278 | 3 | 40 | 0.090 | 22 | 1.53 | 9 |
| cmin50 | 1,258 | 1 | 2 | 0.088 | 21 | 1.50 | 8 |
| beta4_cmin50 | 1,278 | 3 | 40 | 0.090 | 22 | 1.50 | 9 |

## Dónde van las plazas (mejor solución de cada configuración)
- base: Madrid - Carabanchel +150; Madrid - Ciudad Lineal +150; Madrid - Hortaleza +150; Madrid - Retiro +150; Madrid - San Blas +150; Madrid - Puente de Vallecas +130
- beta1: Madrid - Ciudad Lineal +150; Madrid - Fuencarral-El Pardo +150; Madrid - Hortaleza +150; Madrid - Puente de Vallecas +150; Madrid - San Blas +150; Ciempozuelos +130
- beta2: Madrid - Ciudad Lineal +150; Madrid - Fuencarral-El Pardo +150; Madrid - Hortaleza +150; Madrid - Puente de Vallecas +150; Madrid - San Blas +150; Villaconejos +130
- beta4: Madrid - Fuencarral-El Pardo +150; Madrid - Hortaleza +150; Madrid - San Blas +150; Madrid - Villa de Vallecas +150; Ciempozuelos +130; Madrid - Ciudad Lineal +85; Pinilla del Valle +15; Valdemaqueda +10
- beta8: Madrid - Chamberí +150; Madrid - Ciudad Lineal +150; Madrid - Hortaleza +150; Madrid - Salamanca +150; Madrid - Villa de Vallecas +150; Aranjuez +40; Pinilla del Valle +15; Robledo de Chavela +10; Pezuela de las Torres +5
- cmin50: Madrid - Ciudad Lineal +150; Madrid - Hortaleza +150; Madrid - Retiro +150; Madrid - Carabanchel +140; Madrid - San Blas +135; Ciempozuelos +75; Fresnedillas de la Oliva +25; Canencia +15
- beta4_cmin50: Madrid - Ciudad Lineal +150; Madrid - Fuencarral-El Pardo +150; Madrid - Hortaleza +150; Madrid - Salamanca +150; Madrid - San Blas +150; Aranjuez +40; Pinilla del Valle +15; Robledo de Chavela +10; Pezuela de las Torres +5

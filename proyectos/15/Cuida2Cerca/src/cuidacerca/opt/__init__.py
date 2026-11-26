"""Optimización de la localización de plazas de cuidados.

Diseño desacoplado:
  instance.py   formato de instancia genérico (lo único que leen los algoritmos)
  solution.py   representación de soluciones y evaluador de segunda etapa (flujo de coste mínimo)
  milp.py       modelo exacto estocástico en dos etapas (SAA) con OR-Tools
  heuristics.py algoritmos heurísticos con interfaz común (voraz, búsqueda local, ...)
Para añadir un algoritmo basta con una función  algoritmo(inst, evaluador, **params) -> Solution.
"""

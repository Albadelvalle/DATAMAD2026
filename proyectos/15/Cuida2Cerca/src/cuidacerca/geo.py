"""Utilidades geográficas sin dependencias externas (ETRS89 / UTM huso 30N <-> WGS84)."""
import math

import numpy as np

_A = 6378137.0
_F = 1 / 298.257222101  # GRS80
_E2 = _F * (2 - _F)
_K0 = 0.9996
_LON0 = math.radians(-3.0)  # meridiano central del huso 30


def utm30_to_lonlat(x, y):
    """Convierte coordenadas UTM 30N (EPSG:25830) a longitud y latitud (grados).

    Fórmulas inversas de Snyder (1987); error < 1 m en la Comunidad de Madrid.
    """
    x = np.asarray(x, dtype=float) - 500000.0
    y = np.asarray(y, dtype=float)
    ep2 = _E2 / (1 - _E2)
    m = y / _K0
    mu = m / (_A * (1 - _E2 / 4 - 3 * _E2**2 / 64 - 5 * _E2**3 / 256))
    e1 = (1 - math.sqrt(1 - _E2)) / (1 + math.sqrt(1 - _E2))
    phi1 = (mu + (3 * e1 / 2 - 27 * e1**3 / 32) * np.sin(2 * mu)
            + (21 * e1**2 / 16 - 55 * e1**4 / 32) * np.sin(4 * mu)
            + (151 * e1**3 / 96) * np.sin(6 * mu)
            + (1097 * e1**4 / 512) * np.sin(8 * mu))
    n1 = _A / np.sqrt(1 - _E2 * np.sin(phi1) ** 2)
    t1 = np.tan(phi1) ** 2
    c1 = ep2 * np.cos(phi1) ** 2
    r1 = _A * (1 - _E2) / (1 - _E2 * np.sin(phi1) ** 2) ** 1.5
    d = x / (n1 * _K0)
    lat = phi1 - (n1 * np.tan(phi1) / r1) * (
        d**2 / 2 - (5 + 3 * t1 + 10 * c1 - 4 * c1**2 - 9 * ep2) * d**4 / 24
        + (61 + 90 * t1 + 298 * c1 + 45 * t1**2 - 252 * ep2 - 3 * c1**2) * d**6 / 720)
    lon = _LON0 + (d - (1 + 2 * t1 + c1) * d**3 / 6
                   + (5 - 2 * c1 + 28 * t1 - 3 * c1**2 + 8 * ep2 + 24 * t1**2) * d**5 / 120) / np.cos(phi1)
    return np.degrees(lon), np.degrees(lat)


def dist_km(x1, y1, x2, y2):
    """Distancia euclídea en km entre puntos UTM (válida a escala regional)."""
    return np.hypot(np.asarray(x1) - np.asarray(x2), np.asarray(y1) - np.asarray(y2)) / 1000.0

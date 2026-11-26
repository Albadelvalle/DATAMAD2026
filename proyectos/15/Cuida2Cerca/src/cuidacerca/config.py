"""Rutas y constantes del proyecto."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"

# Ficheros originales del Portal de Datos Abiertos de la Comunidad de Madrid
RAW = {
    "registro_centros": "atencion_social_registro_centros.csv",
    "registro_centros_alt": "servicios_sociales_registro_centros.csv",
    "discapacidad_mun": "personas-con-discapacidad-por-edad-y-sexo.-municipios.csv",
    "centros_ss_mun": "centros-de-servicios-sociales-por-tipo.-municipios.csv",
    "sanitarios": "centros_servicios_establecimientos_sanitarios.csv",
    "dep_solicitudes": "solicitudes-y-resoluciones-del-sistema-para-la-autonomia-y-atencion-a-la-dependencia.csv",
    "dep_prestaciones": "beneficiarios-y-prestaciones-del-sistema-para-la-autonomia-y-atencion-a-la-dependencia.csv",
    "proyecciones": "proyecciones-de-poblacion-por-sexo.csv",
}

# Subtipos del registro que constituyen oferta de cuidados para personas mayores dependientes
CATEGORIA_SUBTIPO = {
    "RESIDENCIAS DE PERSONAS MAYORES DEPENDIENTES": "residencia",
    "RESIDENCIAS DE PERSONAS MAYORES MIXTA": "residencia",
    "CENTROS RESIDENCIALES: OTROS": "residencia",
    "CENTROS DE DÍA: OTROS": "centro_dia",
}
# Excluidos (no son plazas de cuidados a dependientes): hogares y clubes, residencias de
# autónomos, pisos tutelados, viviendas comunitarias, centros de atención.

# Financiación de las plazas según el campo tipo_gestion
FINANCIACION = {
    "PROPIA DE GESTIÓN DIRECTA": "publica",
    "PROPIA DE GESTIÓN INDIRECTA": "publica",
    "PRIVADA CON PLAZAS CONCERTADAS": "concertada",
    "PRIVADA CON PLAZAS CONCERTADAS + PEVS": "concertada",
    "PRIVADA + PEVS": "privada_pevs",
    "PRIVADA TOTAL": "privada",
}

# Caja envolvente de la Comunidad de Madrid en ETRS89 / UTM 30N (EPSG:25830)
BBOX_UTM = (360_000, 4_410_000, 500_000, 4_570_000)

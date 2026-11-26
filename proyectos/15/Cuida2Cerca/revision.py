"""Descarga los CSV del Portal de Datos Abiertos de la Comunidad de Madrid
necesarios para revisar la propuesta de plazas de cuidados para mayores y dependientes."""
import os
import requests

DESTINO = "cuidados"
B = "https://datos.comunidad.madrid/dataset/"
URLS = [
    # Oferta: centros y servicios de atención social
    B + "b8cdb7f7-3185-4938-800a-fefda72333f5/resource/0d815439-396e-4975-983e-5bb421f617a0/download/atencion_social_registro_centros.csv",
    B + "b8cdb7f7-3185-4938-800a-fefda72333f5/resource/253e3c3a-9ce1-4d13-a555-4f6ac5cffb93/download/servicios_sociales_registro_centros.csv",
    B + "95c75a5f-40ea-4af7-8b62-860918224c02/resource/1feb4b85-58da-4178-9391-f8821629ed7e/download/atencion_social_registro_servicios.csv",
    B + "c90c2ab4-d8af-4489-9eed-b3c3c0331988/resource/149d2d37-0a94-4ee2-8181-afa6b5c69d94/download/centros-de-servicios-sociales-por-tipo.-municipios.csv",
    B + "3f5861d5-a508-43d0-b77c-e3af08ed85a8/resource/eb02eabe-f51d-4d2b-8782-465b609c2905/download/servicios-sociales-prestados-por-la-comunidad-de-madrid.csv",
    # Demanda: discapacidad, dependencia y proyecciones
    B + "d0ad4071-4cfa-47c5-8740-50f0ebb77530/resource/060b17d5-f651-4e47-92a0-006e385572ea/download/personas-con-discapacidad-por-edad-y-sexo.-municipios.csv",
    B + "e01de9fe-38a4-4786-8ff9-ee1c1dcc66e1/resource/f0c1ebc8-699d-4277-9558-e984712a6943/download/solicitudes-y-resoluciones-del-sistema-para-la-autonomia-y-atencion-a-la-dependencia.csv",
    B + "1b965fe0-63ee-4c47-9725-12875093de2f/resource/cef26e9e-42ff-4f89-9f66-5033984dee33/download/beneficiarios-y-prestaciones-del-sistema-para-la-autonomia-y-atencion-a-la-dependencia.csv",
    B + "c64809e2-26c4-42c6-9fe8-02dbbfabf35a/resource/f7696f29-3be3-4ea6-b4d5-a2f06d65df49/download/proyecciones-de-poblacion-por-sexo.csv",
]

os.makedirs(DESTINO, exist_ok=True)
for u in URLS:
    nombre = u.rsplit("/", 1)[1]
    try:
        r = requests.get(u, timeout=120)
        r.raise_for_status()
        with open(os.path.join(DESTINO, nombre), "wb") as f:
            f.write(r.content)
        print(f"OK     {nombre} ({len(r.content)/1024:.0f} KB)")
    except Exception as e:
        print(f"ERROR  {nombre}: {e}")
print(f"Terminado. Ficheros en ./{DESTINO}/")
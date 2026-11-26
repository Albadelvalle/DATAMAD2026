import csv, requests

BASE = "https://datos.comunidad.madrid/api/3/action/package_search"
GRUPOS = ["salud", "educacion", "demografia", "seguridad",
          "sociedad-bienestar", "medio-ambiente", "transporte", "energia"]

with open("catalogo_cam.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["grupo", "name", "title", "modificado", "formatos", "urls"])
    for g in GRUPOS:
        start = 0
        while True:
            r = requests.get(BASE, params={"fq": f"groups:{g}", "rows": 100, "start": start}).json()
            res = r["result"]["results"]
            for p in res:
                recs = p.get("resources", [])
                w.writerow([g, p["name"], p["title"], p.get("metadata_modified", ""),
                            "|".join(sorted({x.get("format", "") for x in recs})),
                            "|".join(x.get("url", "") for x in recs)])
            start += 100
            if start >= r["result"]["count"]:
                break
print("Hecho: catalogo_cam.csv")
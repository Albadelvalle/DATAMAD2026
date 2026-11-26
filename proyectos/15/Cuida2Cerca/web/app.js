/* CuidaCerca — aplicación web estática. Datos: data/datos.js (generado por src/cuidacerca/web_export.py). */
"use strict";
const D = window.DATOS;
const nf0 = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 0, useGrouping: "always" });
const nf1 = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 1, minimumFractionDigits: 1, useGrouping: "always" });
const eur = new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const $ = (id) => document.getElementById(id);
const SVGNS = "http://www.w3.org/2000/svg";
const zonaPorId = Object.fromEntries(D.zonas.map((z, i) => [z.id, i]));
const etiqueta = (c) => D.etiquetas_config[c] || c;
const descripcion = (c) => (D.descripciones_config || {})[c] || "";

// ------------------------------------------------------------------ utilidades
const tip = $("tooltip");
function mostrarTip(ev, html) {
  tip.innerHTML = html; tip.hidden = false;
  const pt = ev.touches ? ev.touches[0] : ev.changedTouches ? ev.changedTouches[0] : ev;
  let x = pt.clientX + 14, y = pt.clientY + 14;
  if (x + tip.offsetWidth > window.innerWidth - 8) x = Math.max(8, pt.clientX - tip.offsetWidth - 14);
  if (y + tip.offsetHeight > window.innerHeight - 8) y = Math.max(8, pt.clientY - tip.offsetHeight - 14);
  tip.style.left = x + "px"; tip.style.top = y + "px";
}
const ocultarTip = () => { tip.hidden = true; };
function el(tag, attrs = {}, parent) {
  const e = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
}
function ticks(min, max, n = 5) {
  const paso0 = (max - min) / n, mag = Math.pow(10, Math.floor(Math.log10(paso0)));
  const paso = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((p) => p >= paso0);
  const t = []; for (let v = Math.ceil(min / paso) * paso; v <= max + 1e-9; v += paso) t.push(+v.toFixed(10));
  return t;
}
function haversine(a, b) {
  const R = 6371, r = Math.PI / 180;
  const dLat = (b.lat - a.lat) * r, dLon = (b.lon - a.lon) * r;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * r) * Math.cos(b.lat * r) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}
function kpi(cont, valor, etiquetaTxt, delta = "") {
  const d = document.createElement("div"); d.className = "kpi";
  d.innerHTML = `<div class="valor">${valor}</div><div class="etiqueta">${etiquetaTxt}</div>${delta ? `<div class="delta">${delta}</div>` : ""}`;
  cont.appendChild(d);
}
function tabla(t, cab, filas, numCols = []) {
  t.innerHTML = "<thead><tr>" + cab.map((c, i) => `<th class="${numCols.includes(i) ? "num" : ""}">${c}</th>`).join("") + "</tr></thead><tbody>" +
    filas.map((f) => "<tr>" + f.map((c, i) => `<td class="${numCols.includes(i) ? "num" : ""}">${c}</td>`).join("") + "</tr>").join("") + "</tbody>";
}

// Colores de los elementos dibujados sobre el mapa: el mapa base es siempre claro, así que se usa la
// variante clara de la paleta aunque la página esté en modo oscuro.
const MAPA = { "--div-neg2": "#a8302f", "--div-neg1": "#f2a9a5", "--div-mid": "#e4e2dd", "--div-pos1": "#86b6ef",
  "--div-pos2": "#1c5cab", "--s2": "#eb6834", "--surface-1": "#ffffff", "--text-secondary": "#52514e" };
const cm = (v) => MAPA[v];

// Escala divergente respecto a la media regional (rojo = por debajo, azul = por encima, gris = en la media)
function colorRelativo(ratio) {
  if (ratio < 0.5) return cm("--div-neg2");
  if (ratio < 0.9) return cm("--div-neg1");
  if (ratio <= 1.1) return cm("--div-mid");
  if (ratio <= 1.5) return cm("--div-pos1");
  return cm("--div-pos2");
}
function leyendaRelativa(cont, titulo) {
  const items = [["--div-neg2", "< 50 % de la media"], ["--div-neg1", "50–90 %"], ["--div-mid", "90–110 %"], ["--div-pos1", "110–150 %"], ["--div-pos2", "> 150 %"]];
  cont.innerHTML = `<span>${titulo}</span>` + items.map(([v, t]) => `<span><span class="sw" style="background:${cm(v)}"></span>${t}</span>`).join("") +
    `<span>Tamaño del círculo: personas mayores con discapacidad</span>`;
}

// ------------------------------------------------------------------ mapas
// Mapa base: OpenStreetMap estándar (sin clave). Para otro proveedor, cambia la URL y la atribución.
const TESELAS = {
  url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
  atribucion: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
};
const mapas = {};
function crearMapa(id) {
  const m = L.map(id, { zoomControl: true, scrollWheelZoom: false }).setView([40.45, -3.72], 9);
  L.tileLayer(TESELAS.url, { attribution: TESELAS.atribucion, maxZoom: 18 }).addTo(m);
  m.on("click movestart zoomstart", ocultarTip);
  return m;
}
// Tooltip propio para capas del mapa: sigue al ratón, se ajusta a la ventana y funciona con toque.
L.Layer.include({
  conTip(html) {
    this.on("mouseover mousemove", (e) => mostrarTip(e.originalEvent, html));
    this.on("mouseout", ocultarTip);
    this.on("click", (e) => { L.DomEvent.stopPropagation(e); mostrarTip(e.originalEvent, html); });
    return this;
  },
});
const radio = (dem) => Math.max(3, Math.sqrt(dem) * (window.innerWidth < 700 ? 0.2 : 0.32));

// ------------------------------------------------------------------ 1. diagnóstico
let capaDiag, capaCentros;
function pintarDiagnostico() {
  const m = mapas.diag || (mapas.diag = crearMapa("mapa-diag"));
  const serv = $("d-servicio").value, fin = $("d-financiacion").value;
  $("d-radio").disabled = serv !== "cd";
  const radioKm = serv === "cd" ? +$("d-radio").value : 30;
  const campo = `acc_${serv}_${fin}` + (serv === "cd" && radioKm === 5 ? "_r5" : ""), distCampo = serv === "cd" ? "dist_cd_km" : "dist_res_km";
  $("d-nota-radio").textContent = `Plazas al alcance por cada 100 personas mayores con discapacidad, contando como accesibles los centros a menos de ${radioKm} km (con menos peso cuanto más lejos).` +
    (serv === "res" ? " Para residencias se usa siempre 30 km." : "");
  const nombreServ = serv === "cd" ? "centro de día" : "residencia";
  const totDem = D.zonas.reduce((s, z) => s + z.demanda_2025, 0);
  const media = D.zonas.reduce((s, z) => s + z[campo] * z.demanda_2025, 0) / totDem;
  if (capaDiag) capaDiag.remove();
  capaDiag = L.layerGroup().addTo(m);
  [...D.zonas].sort((a, b) => b.demanda_2025 - a.demanda_2025).forEach((z) => {
    const ratio = z[campo] / media;
    L.circleMarker([z.lat, z.lon], { radius: radio(z.demanda_2025), color: cm("--surface-1"), weight: 1.5,
      fillColor: colorRelativo(ratio), fillOpacity: 0.9 })
      .conTip(`<b>${z.nombre}</b><br>${nf0.format(z.demanda_2025)} personas mayores con discapacidad<br>` +
        `${nf1.format(z[campo])} plazas de ${nombreServ} accesibles por 100 personas (${nf0.format(ratio * 100)} % de la media)<br>` +
        `${nombreServ[0].toUpperCase() + nombreServ.slice(1)} más cercano: ${nf1.format(z[distCampo])} km`)
      .addTo(capaDiag);
  });
  if (capaCentros) capaCentros.remove();
  if ($("d-centros").checked) {
    capaCentros = L.layerGroup().addTo(m);
    D.centros.filter((c) => (serv === "cd" ? c.c === "centro_dia" : c.c === "residencia") && (fin === "total" || c.f !== "privada"))
      .forEach((c) => L.circleMarker([c.lat, c.lon], { radius: 2.5, color: cm("--text-secondary"), weight: 1, fillOpacity: 0.8 })
        .conTip(`<b>${c.n}</b><br>${c.m} · ${c.p} plazas · ${c.f.replace("_", " ")}`).addTo(capaCentros));
  }
  leyendaRelativa($("d-leyenda"), `Plazas accesibles frente a la media (${nf1.format(media)} por 100):`);

  const k = $("d-kpis"); k.innerHTML = "";
  const lejos = D.zonas.filter((z) => z[distCampo] > (serv === "cd" ? 5 : 10)).reduce((s, z) => s + z.demanda_2025, 0);
  const bajo = D.zonas.filter((z) => z[campo] < 0.5 * media);
  const municipiosSin = new Set(D.centros.filter((c) => c.c === "centro_dia" || c.c === "residencia").map((c) => c.m));
  kpi(k, nf1.format(media), `plazas de ${nombreServ} accesibles por cada 100 personas (media regional)`);
  kpi(k, nf0.format(bajo.reduce((s, z) => s + z.demanda_2025, 0)), `personas en zonas por debajo de la mitad de la media`, `${bajo.length} zonas`);
  kpi(k, nf0.format(lejos), `personas a más de ${serv === "cd" ? 5 : 10} km del ${nombreServ} más cercano`);
  kpi(k, "61", "municipios sin residencia ni centro de día propios", "unas 2.540 personas");
  const peores = [...D.zonas].filter((z) => z.demanda_2025 >= 100).sort((a, b) => a[campo] - b[campo]).slice(0, 12);
  tabla($("d-tabla"), ["Zona", "Personas", "Plazas/100", "Km al más cercano"],
    peores.map((z) => [z.nombre, nf0.format(z.demanda_2025), nf1.format(z[campo]), nf1.format(z[distCampo])]), [1, 2, 3]);
}

// ------------------------------------------------------------------ gráficos SVG
function graficoLineas(cont, { series, banda, xs, formatoY = nf0.format, yMin, etiquetasDirectas = true, leyenda = true }) {
  cont.innerHTML = "";
  const W = 640, H = 300, m = { l: 56, r: etiquetasDirectas ? 130 : 16, t: 14, b: 28 };
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img" }, cont);
  const todos = series.flatMap((s) => s.y.filter((v) => v != null)).concat(banda ? banda.hi.filter((v) => v != null) : []);
  const ymin = yMin ?? Math.min(...todos) * 0.95, ymax = Math.max(...todos) * 1.03;
  const x = (v) => m.l + ((v - xs[0]) / (xs[xs.length - 1] - xs[0])) * (W - m.l - m.r);
  const y = (v) => H - m.b - ((v - ymin) / (ymax - ymin)) * (H - m.t - m.b);
  const g = el("g", { class: "rejilla" }, svg);
  ticks(ymin, ymax).forEach((t) => { el("line", { x1: m.l, x2: W - m.r, y1: y(t), y2: y(t) }, g);
    el("text", { x: m.l - 6, y: y(t) + 4, "text-anchor": "end" }, svg).textContent = formatoY(t); });
  ticks(xs[0], xs[xs.length - 1], 6).forEach((t) => { el("text", { x: x(t), y: H - 8, "text-anchor": "middle" }, svg).textContent = t; });
  if (banda) {
    const pts = xs.map((v, i) => [v, banda.lo[i], banda.hi[i]]).filter((p) => p[1] != null);
    el("path", { d: "M" + pts.map((p) => `${x(p[0])},${y(p[2])}`).join("L") + "L" + pts.reverse().map((p) => `${x(p[0])},${y(p[1])}`).join("L") + "Z",
      fill: banda.color, opacity: 0.18 }, svg);
  }
  series.forEach((s) => {
    const pts = xs.map((v, i) => [v, s.y[i]]).filter((p) => p[1] != null);
    el("path", { d: "M" + pts.map((p) => `${x(p[0])},${y(p[1])}`).join("L"), fill: "none", stroke: s.color, "stroke-width": 2,
      "stroke-dasharray": s.discontinua ? "5 4" : "none", "stroke-linejoin": "round" }, svg);
    if (etiquetasDirectas) {
      const u = pts[pts.length - 1];
      const t = el("text", { x: x(u[0]) + 6, y: y(u[1]) + 4 }, svg); t.textContent = s.nombre; t.setAttribute("style", `fill:${css("--text-primary")}`);
    }
  });
  // capa de interacción: cruz y tooltip
  const cruz = el("line", { y1: m.t, y2: H - m.b, stroke: css("--text-muted"), "stroke-width": 1, opacity: 0 }, svg);
  const zona = el("rect", { x: m.l, y: m.t, width: W - m.l - m.r, height: H - m.t - m.b, fill: "transparent" }, svg);
  zona.addEventListener("mousemove", (ev) => {
    const r = svg.getBoundingClientRect(), px = ((ev.clientX - r.left) / r.width) * W;
    const i = xs.reduce((b, v, j) => (Math.abs(x(v) - px) < Math.abs(x(xs[b]) - px) ? j : b), 0);
    cruz.setAttribute("x1", x(xs[i])); cruz.setAttribute("x2", x(xs[i])); cruz.setAttribute("opacity", 1);
    let html = `<b>${xs[i]}</b>`;
    series.forEach((s) => { if (s.y[i] != null) html += `<br><span class="sw" style="display:inline-block;width:10px;height:3px;background:${s.color};vertical-align:middle;margin-right:5px"></span>${s.nombre}: ${formatoY(s.y[i])}`; });
    if (banda && banda.lo[i] != null) html += `<br>Intervalo 80 %: ${formatoY(banda.lo[i])} – ${formatoY(banda.hi[i])}`;
    mostrarTip(ev, html);
  });
  zona.addEventListener("mouseleave", () => { cruz.setAttribute("opacity", 0); ocultarTip(); });
  if (leyenda && series.length > 1) {
    const l = document.createElement("div"); l.className = "leyenda";
    l.innerHTML = series.map((s) => `<span><span class="sw" style="background:${s.color}"></span>${s.nombre}</span>`).join("");
    cont.appendChild(l);
  }
}

// ------------------------------------------------------------------ 2. futuro
function pintarFuturo() {
  const R = D.regional;
  const i25 = R.anio.indexOf(2025);
  const p50 = R.p50.map((v, i) => (i === i25 ? R.observado[i] : v));
  graficoLineas($("f-regional"), { xs: R.anio, yMin: 80000, leyenda: false,
    series: [{ nombre: "Observado", y: R.observado, color: css("--s1") }, { nombre: "Previsión", y: p50, color: css("--s1"), discontinua: true }],
    banda: { lo: R.p10.map((v, i) => (i === i25 ? R.observado[i] : v)), hi: R.p90.map((v, i) => (i === i25 ? R.observado[i] : v)), color: css("--s1") } });
  const Dp = D.dependencia, i15 = Dp.anio.indexOf(2015);
  const idx = (k) => Dp[k].map((v, i) => (Dp.anio[i] >= 2015 && v ? (v / Dp[k][i15]) * 100 : null));
  graficoLineas($("f-dependencia"), { xs: Dp.anio.slice(i15), yMin: 50,
    series: [
      { nombre: "Personas con derecho", y: idx("beneficiarios_con_derecho").slice(i15), color: css("--s1") },
      { nombre: "Ayuda a domicilio", y: idx("prest_ayuda_domicilio").slice(i15), color: css("--s2") },
      { nombre: "Centro de día", y: idx("prest_centro_dia").slice(i15), color: css("--s3") },
      { nombre: "Residencia", y: idx("prest_residencial").slice(i15), color: css("--text-secondary") }] });
  const k = $("f-kpis"); k.innerHTML = "";
  const tot = (a) => (a === 2025 ? R.observado[i25] : R.p50[R.anio.indexOf(a)]);
  kpi(k, nf0.format(tot(2025)), "personas mayores con discapacidad en 2025");
  kpi(k, nf0.format(tot(2030)), "previstas en 2030 (mediana)", `+${nf0.format((tot(2030) / tot(2025) - 1) * 100)} %`);
  kpi(k, nf0.format(tot(2035)), "previstas en 2035 (mediana)", `+${nf0.format((tot(2035) / tot(2025) - 1) * 100)} %`);
  const crec = [...D.zonas].filter((z) => z.demanda_2025 > 300).map((z) => ({ z, c: z.demanda_2035[1] / z.demanda_2025 - 1 }))
    .sort((a, b) => b.c - a.c).slice(0, 12);
  tabla($("f-tabla"), ["Zona", "2025", "2035 (mediana)", "Intervalo 80 %", "Crecimiento", "Plazas/100 hoy (centro de día)"],
    crec.map(({ z, c }) => [z.nombre, nf0.format(z.demanda_2025), nf0.format(z.demanda_2035[1]),
      `${nf0.format(z.demanda_2035[0])} – ${nf0.format(z.demanda_2035[2])}`, `+${nf0.format(c * 100)} %`, nf1.format(z.acc_cd_publica)]), [1, 2, 4, 5]);
}

// ------------------------------------------------------------------ 3. planificador
let planActual = null, capaPlan;
const presupuestos = [...new Set(D.planes.map((p) => p.presupuesto))].sort((a, b) => a - b);
const radioDe = (p) => p.radio_km || 15;
const baseDe = (p) => D.sin_actuacion[String(radioDe(p))] || D.sin_actuacion["15"];
function pintarFrente() {
  const B = +$("p-presupuesto").value, R = +$("p-radio").value;
  const planes = D.planes.filter((p) => p.presupuesto === B && radioDe(p) === R);
  const cont = $("p-frente"); cont.innerHTML = "";
  const W = 560, H = 340, m = { l: 56, r: 20, t: 16, b: 42 };
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}` }, cont);
  const xsv = planes.map((p) => p.metricas.sin_plaza), ysv = planes.map((p) => p.metricas.zonas_bajo_50);
  const x0 = Math.min(...xsv) * 0.97, x1 = Math.max(...xsv) * 1.03, y1 = Math.max(...ysv) * 1.12 + 2;
  const x = (v) => m.l + ((v - x0) / (x1 - x0)) * (W - m.l - m.r), y = (v) => H - m.b - (v / y1) * (H - m.t - m.b);
  const g = el("g", { class: "rejilla" }, svg);
  ticks(0, y1).forEach((t) => { el("line", { x1: m.l, x2: W - m.r, y1: y(t), y2: y(t) }, g); el("text", { x: m.l - 6, y: y(t) + 4, "text-anchor": "end" }, svg).textContent = t; });
  ticks(x0, x1, 5).forEach((t) => { el("text", { x: x(t), y: H - m.b + 16, "text-anchor": "middle" }, svg).textContent = nf0.format(t); });
  el("text", { x: (W + m.l) / 2, y: H - 6, "text-anchor": "middle" }, svg).textContent = "Personas sin plaza accesible (media de 500 escenarios)";
  const ty = el("text", { x: 14, y: (H - m.b) / 2, "text-anchor": "middle", transform: `rotate(-90 14 ${(H - m.b) / 2})` }, svg);
  ty.textContent = "Zonas con menos del 50 % cubierto";
  const nd = planes.filter((p) => p.no_dominado).sort((a, b) => a.metricas.sin_plaza - b.metricas.sin_plaza);
  if (nd.length > 1) el("path", { d: "M" + nd.map((p) => `${x(p.metricas.sin_plaza)},${y(p.metricas.zonas_bajo_50)}`).join("L"),
    fill: "none", stroke: css("--s1"), "stroke-width": 2, opacity: 0.5 }, svg);
  // planes con los mismos valores en ambos ejes se dibujan como un único punto
  const grupos = {}, cajas = [];
  planes.forEach((p) => { const k = `${Math.round(p.metricas.sin_plaza)}|${p.metricas.zonas_bajo_50}`; (grupos[k] = grupos[k] || []).push(p); });
  Object.values(grupos).forEach((g) => {  // las etiquetas no deben tapar ningún punto
    const cx = x(g[0].metricas.sin_plaza), cy = y(g[0].metricas.zonas_bajo_50);
    cajas.push({ x: cx - 10, y: cy - 10, width: 20, height: 20 });
  });
  Object.values(grupos).forEach((g) => {
    const p0 = g[0], cx = x(p0.metricas.sin_plaza), cy = y(p0.metricas.zonas_bajo_50);
    const sel = planActual && g.some((p) => p.id === planActual.id), nd = g.some((p) => p.no_dominado);
    const c = el("circle", { cx, cy, r: sel ? 9 : 7, class: "punto-plan", fill: nd ? css("--s1") : css("--surface-1"),
      stroke: sel ? css("--s2") : css("--s1"), "stroke-width": sel ? 3 : 2 }, svg);
    const t = el("text", { x: cx + 11, y: cy - 8 }, svg); t.textContent = g.map((p) => etiqueta(p.config)).join(" / ");
    // evita solapes: prueba arriba, abajo y más abajo hasta encontrar hueco
    for (const [dx, dy] of [[11, 4], [-11, 4], [11, -12], [-11, -12], [11, 20], [-11, 20], [11, -28], [-11, -28],
                            [11, 36], [-11, 36], [11, -44], [-11, -44], [11, 52], [-11, 52]]) {
      t.setAttribute("x", cx + dx); t.setAttribute("text-anchor", dx < 0 ? "end" : "start");
      t.setAttribute("y", cy + dy);
      const bb = t.getBBox();
      const dentro = bb.x >= 0 && bb.x + bb.width <= W - 2 && bb.y >= 0;
      if (dentro && !cajas.some((c) => bb.x < c.x + c.width && c.x < bb.x + bb.width && bb.y < c.y + c.height && c.y < bb.y + bb.height)) break;
    }
    cajas.push(t.getBBox());
    c.addEventListener("mousemove", (ev) => mostrarTip(ev, g.map((p) => `<b>${etiqueta(p.config)}</b><br><span style="color:var(--text-secondary)">${descripcion(p.config)}</span>`).join("<br>") +
      `<br>${nf0.format(p0.metricas.sin_plaza)} personas sin plaza<br>${p0.metricas.zonas_bajo_50} zonas con menos del 50 % cubierto<br>` +
      `${p0.metricas.centros_nuevos} centros nuevos, ${p0.metricas.plazas_nuevas} plazas<br>` + (nd ? "No dominado" : "Dominado por otro plan")));
    c.addEventListener("mouseleave", ocultarTip);
    c.addEventListener("click", () => { const i = g.findIndex((p) => planActual && p.id === planActual.id);
      planActual = g[(i + 1) % g.length]; pintarFrente(); pintarPlan(); });
  });
}
function pintarPlan() {
  const p = planActual, b = baseDe(p);
  $("p-titulo").textContent = `${etiqueta(p.config)} · presupuesto ${nf0.format(p.presupuesto)} · cerca = ${radioDe(p)} km`;
  $("p-descripcion").textContent = descripcion(p.config);
  const k = $("p-kpis"); k.innerHTML = "";
  kpi(k, nf0.format(b.metricas.sin_plaza - p.metricas.sin_plaza), "personas más atendidas", `sin actuación: ${nf0.format(b.metricas.sin_plaza)} sin plaza`);
  kpi(k, `${b.metricas.zonas_bajo_50} → ${p.metricas.zonas_bajo_50}`, "zonas con menos del 50 % cubierto");
  kpi(k, `${p.metricas.centros_nuevos}`, "centros nuevos o ampliados", `${nf0.format(p.metricas.plazas_nuevas)} plazas`);
  kpi(k, `${nf1.format(p.metricas.km_medio)} km`, "distancia media al centro", `sin actuación: ${nf1.format(b.metricas.km_medio)} km`);
  tabla($("p-tabla"), ["Ubicación", "Plazas nuevas", "Plazas actuales", "Municipios atendidos"],
    [...p.centros].sort((a, c) => c.plazas_nuevas - a.plazas_nuevas).map((c) => [c.nombre, c.plazas_nuevas, nf0.format(c.plazas_existentes),
      c.usuarios.length]), [1, 2, 3]);
  const m = mapas.plan || (mapas.plan = crearMapa("mapa-plan"));
  if (capaPlan) capaPlan.remove();
  capaPlan = L.layerGroup().addTo(m);
  const col = (c) => (c < 0.5 ? cm("--div-neg2") : c < 0.8 ? cm("--div-neg1") : c < 0.95 ? cm("--div-mid") : cm("--div-pos1"));
  D.zonas.forEach((z, i) => {
    const c = p.cobertura_por_zona[i], c0 = b.cobertura_por_zona[i];
    L.circleMarker([z.lat, z.lon], { radius: radio(z.demanda_2025), color: cm("--surface-1"), weight: 1, fillColor: col(c), fillOpacity: 0.85 })
      .conTip(`<b>${z.nombre}</b><br>Necesidad cubierta: ${nf0.format(c * 100)} % (sin actuación ${nf0.format(c0 * 100)} %)`).addTo(capaPlan);
  });
  p.centros.forEach((c) => {
    const z = D.zonas[c.sitio];
    L.circleMarker([z.lat, z.lon], { radius: 6 + Math.sqrt(c.plazas_nuevas) * 0.9, color: cm("--surface-1"), weight: 2, fillColor: cm("--s2"), fillOpacity: 1 })
      .conTip(`<b>${c.nombre}</b><br>+${c.plazas_nuevas} plazas nuevas<br>Atiende a: ${c.usuarios.map((u) => `${u.nombre} (${nf1.format(u.plazas)})`).join(", ")}`)
      .addTo(capaPlan);
  });
  $("p-leyenda").innerHTML = [["--div-neg2", "< 50 % de la necesidad cubierta"], ["--div-neg1", "50–80 %"], ["--div-mid", "80–95 %"], ["--div-pos1", "≥ 95 %"]]
    .map(([v, t]) => `<span><span class="sw" style="background:${cm(v)}"></span>${t}</span>`).join("") +
    `<span><span class="sw" style="background:${cm("--s2")};border-radius:50%"></span>Centro nuevo o ampliado</span>`;
  setTimeout(() => m.invalidateSize(), 50);
}

// ------------------------------------------------------------------ 4. reparto de costes (juego cooperativo)
function juegoLocalizacion(q, Dm, F, c, tau) {
  const n = q.length, N = 1 << n, coste = new Float64Array(N);
  for (let S = 1; S < N; S++) {
    let Q = 0, mejor = Infinity;
    for (let i = 0; i < n; i++) if (S >> i & 1) Q += q[i];
    for (let k = 0; k < n; k++) {
      if (!(S >> k & 1)) continue;
      let t = 0; for (let i = 0; i < n; i++) if (S >> i & 1) t += q[i] * Dm[i][k];
      if (t < mejor) mejor = t;
    }
    coste[S] = F + c * Q + tau * mejor;
  }
  for (let S = 1; S < N; S++) {           // subaditividad: mejor partición en subcoaliciones
    let T = (S - 1) & S, mejor = coste[S];
    while (T) { if (T < (S ^ T)) { const v = coste[T] + coste[S ^ T]; if (v < mejor) mejor = v; } T = (T - 1) & S; }
    coste[S] = mejor;
  }
  return coste;
}
function shapley(coste, n) {
  const N = 1 << n, fact = [1]; for (let i = 1; i <= n; i++) fact[i] = fact[i - 1] * i;
  const phi = new Array(n).fill(0);
  for (let i = 0; i < n; i++) {
    const bit = 1 << i;
    for (let S = 0; S < N; S++) {
      if (S & bit) continue;
      let s = 0; for (let x = S; x; x &= x - 1) s++;
      phi[i] += (fact[s] * fact[n - s - 1] / fact[n]) * (coste[S | bit] - coste[S]);
    }
  }
  return phi;
}
function maxExceso(coste, n, x) {
  const N = 1 << n; let mejor = -Infinity, Sm = 0;
  for (let S = 1; S < N - 1; S++) { let v = -coste[S]; for (let i = 0; i < n; i++) if (S >> i & 1) v += x[i]; if (v > mejor) { mejor = v; Sm = S; } }
  return [mejor, Sm];
}
function prepararCostes() {
  const sel = $("c-plan");
  sel.innerHTML = D.planes.filter((p) => p.centros.some((c) => c.usuarios.length > 1))
    .sort((a, b) => radioDe(b) - radioDe(a) || a.presupuesto - b.presupuesto || a.config.localeCompare(b.config))
    .map((p) => `<option value="${p.id}">${etiqueta(p.config)} · presupuesto ${nf0.format(p.presupuesto)} · cerca = ${radioDe(p)} km</option>`).join("");
  const def = D.meta.costes_defecto;
  $("c-fijo").value = def.fijo; $("c-plaza").value = def.por_plaza; $("c-despl").value = def.desplazamiento;
  sel.addEventListener("change", llenarCentros);
  $("c-centro").addEventListener("change", pintarJuego);
  ["c-fijo", "c-plaza", "c-despl"].forEach((id) => $(id).addEventListener("input", pintarJuego));
  llenarCentros();
}
function llenarCentros() {
  const p = D.planes.find((x) => x.id === $("c-plan").value);
  $("c-centro").innerHTML = [...p.centros].sort((a, b) => b.usuarios.length - a.usuarios.length)
    .map((c, i) => `<option value="${p.centros.indexOf(c)}">${c.nombre} (+${c.plazas_nuevas} plazas, ${c.usuarios.length} municipio${c.usuarios.length > 1 ? "s" : ""})</option>`).join("");
  pintarJuego();
}
function pintarJuego() {
  const p = D.planes.find((x) => x.id === $("c-plan").value), c = p.centros[+$("c-centro").value];
  const F = +$("c-fijo").value || 0, cp = +$("c-plaza").value || 0, tau = +$("c-despl").value || 0;
  let jug = c.usuarios.slice(0, 12);
  const q = jug.map((u) => u.plazas), pts = jug.map((u) => D.municipios[u.cod_ine]);
  const Dm = pts.map((a) => pts.map((b) => haversine(a, b)));
  const n = q.length, coste = juegoLocalizacion(q, Dm, F, cp, tau), total = coste[(1 << n) - 1];
  const phi = shapley(coste, n), Q = q.reduce((a, b) => a + b, 0);
  const solo = q.map((qi) => F + cp * qi), prop = q.map((qi) => (total * qi) / Q);
  const [exc, Sb] = maxExceso(coste, n, phi);
  const k = $("c-kpis"); k.innerHTML = "";
  kpi(k, eur.format(total), "coste del acuerdo conjunto", `${nf1.format(Q)} plazas usadas por ${n} municipio${n > 1 ? "s" : ""}`);
  kpi(k, eur.format(solo.reduce((a, b) => a + b, 0)), "coste si cada municipio construye su propio centro");
  kpi(k, `${nf0.format((1 - total / solo.reduce((a, b) => a + b, 0)) * 100)} %`, "ahorro por cooperar");
  tabla($("c-tabla"), ["Municipio", "Plazas", "Por separado", "Shapley", "Proporcional"],
    jug.map((u, i) => [u.nombre, nf1.format(q[i]), eur.format(solo[i]), `<b>${eur.format(phi[i])}</b>`, eur.format(prop[i])]), [1, 2, 3, 4]);
  const av = $("c-nucleo");
  if (n === 1) av.textContent = "Este centro solo atiende a un municipio: no hay coste que repartir.";
  else if (exc <= 1e-6) av.innerHTML = "<b>El reparto de Shapley está en el núcleo.</b> Ningún grupo de municipios pagaría menos organizándose por su cuenta, así que el acuerdo es estable.";
  else av.innerHTML = `<b>El reparto de Shapley no está en el núcleo.</b> El grupo formado por ${jug.filter((_, i) => Sb >> i & 1).map((u) => u.nombre).join(", ")} ` +
    `ahorraría ${eur.format(exc)} saliéndose del acuerdo. Conviene un reparto del núcleo (ver informe) o compensaciones.`;
  // barras agrupadas horizontales
  const cont = $("c-barras"); cont.innerHTML = "";
  const filas = n, alto = 22 * 3 + 14, W = 600, m = { l: 150, r: 70, t: 6, b: 24 }, H = m.t + m.b + filas * alto;
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}` }, cont);
  const vmax = Math.max(...solo, ...phi, ...prop) * 1.05, x = (v) => m.l + (v / vmax) * (W - m.l - m.r);
  const g = el("g", { class: "rejilla" }, svg);
  ticks(0, vmax, 4).forEach((t) => { el("line", { x1: x(t), x2: x(t), y1: m.t, y2: H - m.b }, g);
    el("text", { x: x(t), y: H - 6, "text-anchor": "middle" }, svg).textContent = t >= 1e6 ? `${nf1.format(t / 1e6)} M€` : `${nf0.format(t / 1e3)} k€`; });
  const ser = [["Por separado", solo, css("--s2")], ["Shapley", phi, css("--s1")], ["Proporcional", prop, css("--s3")]];
  jug.forEach((u, i) => {
    const y0 = m.t + i * alto;
    el("text", { x: m.l - 8, y: y0 + alto / 2, "text-anchor": "end" }, svg).textContent = u.nombre.length > 22 ? u.nombre.slice(0, 21) + "…" : u.nombre;
    ser.forEach(([nom, v, col], s) => {
      const yb = y0 + 4 + s * 22, w = Math.max(1, x(v[i]) - m.l);
      const r = el("rect", { x: m.l, y: yb, width: w, height: 18, rx: 3, fill: col }, svg);
      r.addEventListener("mousemove", (ev) => mostrarTip(ev, `<b>${u.nombre}</b><br>${nom}: ${eur.format(v[i])}`));
      r.addEventListener("mouseleave", ocultarTip);
      if (s === 1) el("text", { x: m.l + w + 4, y: yb + 13 }, svg).textContent = eur.format(v[i]);
    });
  });
  const l = document.createElement("div"); l.className = "leyenda";
  l.innerHTML = ser.map(([nom, , col]) => `<span><span class="sw" style="background:${col}"></span>${nom}</span>`).join("");
  cont.appendChild(l);
}

// ------------------------------------------------------------------ metodología
function pintarMetodo() {
  const P = D.meta.parametros_planes;
  $("m-texto").innerHTML = `
  <h2>Qué hace CuidaCerca</h2>
  <ol>
    <li><b>Diagnóstico.</b> Cruza el registro de centros de atención social (plazas, financiación y ubicación) con las personas mayores de 65 años con discapacidad reconocida de cada municipio, y reparte Madrid capital en sus 21 distritos con el padrón municipal. Mide la accesibilidad con el método E2SFCA: las plazas de cada centro se reparten entre la población a su alcance, con un peso que decrece con la distancia.</li>
    <li><b>Previsión.</b> Proyecta la necesidad a 2030 y 2035 combinando las proyecciones oficiales de población de 65+ con la tendencia de cada municipio (tendencia amortiguada y contraída con un estimador empírico bayesiano). La incertidumbre se propaga con 500 escenarios Monte Carlo, calibrados y validados con datos históricos (60 % menos error que mantener el peso actual de cada municipio).</li>
    <li><b>Optimización.</b> Decide dónde abrir o ampliar centros de día con un presupuesto dado (programación estocástica en dos etapas). El presupuesto se mide en plazas equivalentes: crear una plaza cuesta 1 y abrir o ampliar un centro cuesta además 20 (sus costes fijos). El peso de la equidad indica cuántas veces más cuenta una persona sin plaza en una zona sin ningún centro al alcance frente a una zona en la media regional (×1 = solo eficiencia; ×5 = equidad alta). La segunda etapa se resuelve como flujo de coste mínimo. Se comparan un modelo exacto (MILP con OR-Tools/SCIP) y metaheurísticas (voraz por ratio, GRASP y VND). Los pesos de equidad y la cobertura mínima por zona generan el frente eficiencia-equidad del planificador.</li>
    <li><b>Reparto de costes.</b> Juego cooperativo de localización de instalaciones: valor de Shapley y comprobación del núcleo, calculados en el navegador con los costes que introduzcas.</li>
  </ol>
  <h2>Parámetros de los planes</h2>
  <p>Servicio: ${P.servicio}. Año: ${P.anio}. Meta: ${nf1.format(P.meta_por_100)} plazas por cada 100 personas mayores con discapacidad (media regional actual con financiación pública). Radio de «cerca»: ${P.radio_km} km por defecto; también se ofrecen planes con 5 km, más realista para un servicio al que se va cada día. Presupuesto en ${P.unidad_presupuesto}. Tamaño mínimo de un centro nuevo: ${P.min_plazas_centro} plazas.</p>
  <h2>Limitaciones</h2>
  <ul>
    <li>La discapacidad reconocida es una aproximación de la necesidad de cuidados; no es la dependencia.</li>
    <li>Distancias en línea recta entre puntos de referencia de cada zona; no se usa la red de carreteras.</li>
    <li>El registro indica si un centro tiene plazas concertadas o con prestación vinculada, pero no cuántas.</li>
    <li>El umbral de secreto estadístico (valores de 1 a 4) se ha inferido de los datos; la Comunidad no lo publica.</li>
    <li>Los costes del reparto son ilustrativos y editables.</li>
  </ul>
  <h2>Fuentes</h2>
  <ul>${D.meta.fuentes.map(([t, u]) => `<li><a href="${u}" target="_blank" rel="noopener">${t}</a></li>`).join("")}</ul>
  <p class="nota">Datos generados el ${D.meta.generado}. Todo el análisis se reproduce con <code>python run_pipeline.py</code>.</p>`;
}

// ------------------------------------------------------------------ tema claro / oscuro
const oscuroSistema = window.matchMedia("(prefers-color-scheme: dark)");
const temaActual = () => document.documentElement.dataset.theme || (oscuroSistema.matches ? "dark" : "light");
function pintarBotonTema() {
  const oscuro = temaActual() === "dark";
  $("boton-tema").textContent = oscuro ? "☀ Modo claro" : "☾ Modo oscuro";
  $("boton-tema").setAttribute("aria-pressed", String(oscuro));
}
function repintarTodo() {  // los gráficos leen los colores del tema al dibujarse
  pintarFuturo(); pintarFrente(); pintarJuego();
  activar((location.hash || "#diagnostico").slice(1));
}
$("boton-tema").addEventListener("click", () => {
  const nuevo = temaActual() === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = nuevo;
  try { localStorage.setItem("tema", nuevo); } catch (e) { /* sin almacenamiento: el tema dura la sesión */ }
  pintarBotonTema(); repintarTodo();
});
oscuroSistema.addEventListener("change", () => { if (!document.documentElement.dataset.theme) { pintarBotonTema(); repintarTodo(); } });
pintarBotonTema();

// ------------------------------------------------------------------ pestañas e inicio
function activar(tab) {
  document.querySelectorAll(".pestanas button").forEach((b) => b.setAttribute("aria-selected", b.dataset.tab === tab));
  const nav = document.querySelector(".pestanas"), btn = nav.querySelector(`[data-tab="${tab}"]`);
  if (btn) nav.scrollLeft = btn.offsetLeft - (nav.clientWidth - btn.offsetWidth) / 2;  // pestaña activa visible en móvil
  document.querySelectorAll(".panel").forEach((s) => s.classList.toggle("activo", s.id === tab));
  if (tab === "diagnostico") { pintarDiagnostico(); setTimeout(() => mapas.diag.invalidateSize(), 50); }
  if (tab === "plan") { pintarFrente(); pintarPlan(); }
  history.replaceState(null, "", "#" + tab);
}
document.querySelectorAll(".pestanas button").forEach((b) => b.addEventListener("click", () => activar(b.dataset.tab)));
["d-servicio", "d-financiacion", "d-centros", "d-radio"].forEach((id) => $(id).addEventListener("change", pintarDiagnostico));
$("p-presupuesto").innerHTML = presupuestos.map((b) => `<option value="${b}" ${b === 1000 ? "selected" : ""}>${nf0.format(b)} plazas equivalentes</option>`).join("");
function cambiarSeleccionPlan() {
  const B = +$("p-presupuesto").value, R = +$("p-radio").value;
  const mismo = D.planes.find((p) => p.presupuesto === B && radioDe(p) === R && planActual && p.config === planActual.config);
  planActual = mismo || D.planes.filter((p) => p.presupuesto === B && radioDe(p) === R && p.no_dominado)
    .sort((a, b) => a.metricas.zonas_bajo_50 - b.metricas.zonas_bajo_50)[0];
  pintarFrente(); pintarPlan();
}
$("p-presupuesto").addEventListener("change", cambiarSeleccionPlan);
$("p-radio").addEventListener("change", cambiarSeleccionPlan);
planActual = D.planes.find((p) => p.id === "beta4_B1000") || D.planes[0];
pintarDiagnostico(); pintarFuturo(); pintarFrente(); prepararCostes(); pintarMetodo();
activar((location.hash || "#diagnostico").slice(1));
window.addEventListener("scroll", ocultarTip, { passive: true });
window.addEventListener("hashchange", () => activar((location.hash || "#diagnostico").slice(1)));

// Deck del Examen 1 (skill hack-presentacion adaptada). Lo corre `make laminas`.
// Todas las cifras vienen de datos.json, que exporta scripts/12_laminas.py desde salida/.
// Estilo destilado de referencias/original-* (ver ESTILO.md). Colores sin "#".
const pptxgen = require("pptxgenjs");
const D = require("./datos.json");

const T = {
  fondo: "F6F7F9", tarjeta: "FFFFFF", borde: "E6E9EF", tinta: "2B2B2B", suave: "7C88AA",
  marino: "03467B", medio: "6792B4", claro: "C9D8E6", pista: "EEF2F7", rojo: "D92B3A",
  verde: "12A87A", fuente: "Arial", mono: "Courier New",
};
const W = 10, H = 5.625;
const fmt = (n) => n.toLocaleString("en-US");
const f2 = (x) => x.toFixed(2);
const f3 = (x) => x.toFixed(3);
function tinte(hex, t) { // mezcla con blanco; t = proporción de blanco
  const c = [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16));
  return c.map((v) => Math.round(v + (255 - v) * t).toString(16).padStart(2, "0")).join("").toUpperCase();
}
const Q = Object.fromEntries(D.consultas.map((q) => [q.id, q]));
const icono = (k) => `iconos/${k}.png`;

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.title = "Recuperación y extracción de información en las mañaneras";
pres.author = "Diego Moctezuma";
pres.defineSlideMaster({ title: "OSCURA", background: { color: T.marino }, objects: [] });
pres.defineSlideMaster({ title: "CLARA", background: { color: T.fondo }, objects: [] });

let num = 0;
const sombra = () => ({ type: "outer", color: "1A2B4A", opacity: 0.07, blur: 10, offset: 2, angle: 90 });
const txt = (s, t, o) => s.addText(t, { isTextBox: true, fontFace: T.fuente, margin: 0, ...o });

function clara(titulo, apoyo, fuente) {
  num += 1;
  const s = pres.addSlide({ masterName: "CLARA" });
  txt(s, titulo, { x: 0.5, y: 0.3, w: 9, h: 0.6, fontSize: 26, bold: true, color: T.tinta, valign: "middle" });
  if (apoyo) txt(s, apoyo, { x: 0.5, y: 0.88, w: 9, h: 0.35, fontSize: 13, color: T.suave, valign: "middle" });
  pie(s, fuente, T.suave);
  return s;
}
function oscura() {
  num += 1;
  return pres.addSlide({ masterName: "OSCURA" });
}
function pie(s, fuente, color) {
  txt(s, `Diego Moctezuma · Minería de Textos · ${num}`, { x: 6.0, y: 5.25, w: 3.5, h: 0.25, fontSize: 9, color, align: "right" });
  if (fuente) txt(s, `Fuente: ${fuente}`, { x: 0.5, y: 5.25, w: 5.5, h: 0.25, fontSize: 9, color });
}
function tarjeta(s, x, y, w, h, borde) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h, rectRadius: 0.16, fill: { color: T.tarjeta },
    line: borde ? { color: borde, width: 1.25 } : { color: T.borde, width: 0.75 }, shadow: sombra(),
  });
}
function pildora(s, x, y, w, h, color, linea) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h, rectRadius: Math.min(w, h) / 2, fill: { color },
    line: linea ? { color: linea, width: 0.75 } : { type: "none" },
  });
}
function iconoCirculo(s, k, x, y, d, aro) { // ícono sobre un círculo blanco con aro, como en las referencias
  s.addShape(pres.shapes.OVAL, { x: x - 0.03, y: y - 0.03, w: d + 0.06, h: d + 0.06, fill: { color: "FFFFFF" }, line: { color: aro || T.borde, width: 1 } });
  s.addImage({ path: icono(k), x, y, w: d, h: d });
}
function leyenda(s, x, y, items) { // [[color, texto], ...] como pastillas
  let cx = x;
  for (const [color, t] of items) {
    const w = 0.42 + t.length * 0.075;
    pildora(s, cx, y, w, 0.3, "FFFFFF", T.borde);
    s.addShape(pres.shapes.OVAL, { x: cx + 0.12, y: y + 0.09, w: 0.12, h: 0.12, fill: { color }, line: { type: "none" } });
    txt(s, t, { x: cx + 0.3, y, w: w - 0.32, h: 0.3, fontSize: 10, color: T.tinta, valign: "middle" });
    cx += w + 0.12;
  }
}

// ---------------------------------------------------------------- 1. Portada
let s = oscura();
s.addShape(pres.shapes.OVAL, { x: 6.05, y: 0.75, w: 3.5, h: 3.5, fill: { color: tinte(T.marino, 0.12) }, line: { type: "none" } });
s.addImage({ path: icono("amlo"), x: 6.3, y: 1.0, w: 3.0, h: 3.0 });
txt(s, "Recuperación y extracción de información en las mañaneras", { x: 0.6, y: 0.75, w: 5.3, h: 2.1, fontSize: 30, bold: true, color: "FFFFFF", valign: "bottom" });
txt(s, `TF-IDF, BM25 y entidades sobre ${fmt(D.corpus.discursos)} discursos presidenciales`, { x: 0.6, y: 3.05, w: 5.2, h: 0.8, fontSize: 16, color: T.claro, valign: "top" });
txt(s, "Diego Moctezuma", { x: 0.6, y: 4.15, w: 5.2, h: 0.35, fontSize: 15, bold: true, color: "FFFFFF" });
txt(s, "Minería de Textos · Examen 1 · 11 de noviembre de 2026", { x: 0.6, y: 4.5, w: 5.4, h: 0.3, fontSize: 12, color: T.claro });
s.addNotes("Presentación (10 s). Buenas tardes. Presento mi sistema de recuperación y extracción de información sobre las versiones estenográficas de las mañaneras.");

// ---------------------------------------------------------------- 2. Corpus
s = clara(`Seis años de mañaneras en ${fmt(D.corpus.pasajes)} pasajes`, "La unidad de búsqueda es el pasaje, no el discurso completo",
  "salida/01_estadisticas_corpus.json, salida/01_limpieza.json");
const kpis = [
  ["Discursos", fmt(D.corpus.discursos), "", `De ${D.corpus.anio_ini} a ${D.corpus.anio_fin}`],
  ["Palabras por discurso", fmt(D.corpus.palabras_mediana), "mediana", "Una o dos horas de conferencia"],
  ["Ruido eliminado", fmt(D.corpus.acotaciones), "acotaciones", `Más ${D.corpus.duplicados} discursos duplicados`],
  ["Pasajes indexados", fmt(D.corpus.pasajes), "", `200 palabras, paso 150 · ${f2(D.corpus.pct_reporteros)} % de reporteros`],
];
kpis.forEach(([et, cifra, unidad, linea], i) => {
  const x = 0.5 + (i % 2) * 4.6, y = 1.45 + Math.floor(i / 2) * 1.88;
  tarjeta(s, x, y, 4.4, 1.68);
  s.addShape(pres.shapes.OVAL, { x: x + 0.3, y: y + 0.32, w: 0.14, h: 0.14, fill: { color: T.marino }, line: { type: "none" } });
  txt(s, et, { x: x + 0.55, y: y + 0.2, w: 3.6, h: 0.38, fontSize: 15, color: T.suave, valign: "middle" });
  txt(s, [{ text: cifra, options: { fontSize: 34, bold: true, color: T.marino } },
    { text: unidad ? `  ${unidad}` : "", options: { fontSize: 14, color: T.suave } }],
  { x: x + 0.3, y: y + 0.62, w: 3.9, h: 0.6, valign: "middle" });
  txt(s, linea, { x: x + 0.3, y: y + 1.2, w: 3.9, h: 0.3, fontSize: 12, color: T.suave, valign: "middle" });
});
s.addNotes("Corpus (40 s). Son 2,294 versiones estenográficas de 2018 a 2024. Cada discurso dura una o dos horas, con una mediana de 8,500 palabras, así que buscar el discurso completo no sirve. Quité 7,338 acotaciones como inaudible o inicia video y 5 duplicados. Cada intervención se parte en ventanas de 200 palabras con paso 150: quedan 127,739 pasajes.");

// ---------------------------------------------------------------- 3. Consultas
s = clara("Diez preguntas sobre obras y programas", "Cada consulta tiene una ventana de fechas y una pregunta de extracción", "data/consultas.csv");
D.consultas.forEach((q, i) => {
  const x = 0.5 + (i % 5) * 1.86, y = 1.42 + Math.floor(i / 5) * 1.9;
  tarjeta(s, x, y, 1.7, 1.75);
  iconoCirculo(s, q.icono, x + 0.4, y + 0.17, 0.9, q.color);
  txt(s, q.nombre, { x: x + 0.08, y: y + 1.12, w: 1.54, h: 0.36, fontSize: 11, bold: true, color: T.tinta, align: "center", valign: "middle", fit: "shrink" });
  txt(s, `${q.id} · ${q.desde} a ${q.hasta}`, { x: x + 0.08, y: y + 1.45, w: 1.54, h: 0.22, fontSize: 9, color: T.suave, align: "center" });
});
s.addNotes("Consultas (20 s). Las ocho primeras vienen del kit del profesor; la 9 y la 10 las elegí yo: Banco del Bienestar y Tren Interoceánico. Cada una tiene una ventana de fechas y una pregunta: quién participa, dónde, cuánto, cuándo.");

// ---------------------------------------------------------------- 4. Pipeline
s = clara("Del discurso a la respuesta", "Seis pasos automáticos y tres revisiones humanas", "README.md, docs/decisiones.md");
const pasos = ["Corpus", "Pasajes", "Índice", "Ranking", "Entidades", "Respuestas"];
const humanos = { 3: `${D.humano.juicios} juicios`, 4: `Gold de ${D.humano.gold_pasajes} pasajes`, 5: "10 valoraciones" };
pasos.forEach((p, i) => {
  const cx = 1.05 + i * 1.58, cy = 2.2;
  s.addShape(pres.shapes.OVAL, { x: cx - 0.45, y: cy - 0.45, w: 0.9, h: 0.9, fill: { color: T.marino }, line: { type: "none" } });
  txt(s, String(i + 1), { x: cx - 0.45, y: cy - 0.45, w: 0.9, h: 0.9, fontSize: 24, bold: true, color: "FFFFFF", align: "center", valign: "middle" });
  txt(s, p, { x: cx - 0.75, y: cy + 0.55, w: 1.5, h: 0.35, fontSize: 14, bold: true, color: T.tinta, align: "center" });
  if (i < pasos.length - 1) s.addShape(pres.shapes.LINE, { x: cx + 0.52, y: cy, w: 0.52, h: 0, line: { color: T.medio, width: 2, endArrowType: "triangle" } });
  if (humanos[i]) {
    s.addShape(pres.shapes.LINE, { x: cx, y: cy + 0.95, w: 0, h: 0.42, line: { color: T.medio, width: 1.25, dashType: "dash" } });
    pildora(s, cx - 0.72, cy + 1.4, 1.44, 0.42, T.claro);
    txt(s, humanos[i], { x: cx - 0.72, y: cy + 1.4, w: 1.44, h: 0.42, fontSize: 11, bold: true, color: T.marino, align: "center", valign: "middle" });
  }
});
txt(s, "Pastillas: trabajo hecho a mano en la app, sin ver lo que predice el sistema", { x: 0.5, y: 4.55, w: 9, h: 0.3, fontSize: 12, color: T.suave, align: "center" });
s.addNotes("Pipeline (30 s). Corpus, pasajes, índice invertido, ranking con dos modelos, extracción de entidades y tablas de respuesta. Las pastillas son trabajo humano: juzgué 176 pares de relevancia, anoté un gold de 20 pasajes sin ver predicciones y valoré las diez tablas.");

// ---------------------------------------------------------------- 5. Índice
s = clara("Huachicol es el término más discriminante", "Índice invertido propio: raíz → pasajes con su frecuencia",
  "salida/02_postings.md · idf = ln(1 + (N − df + 0.5) / (df + 0.5))");
tarjeta(s, 0.5, 1.4, 9, 3.6);
const iconoTermino = { tren: ["q1", "Q1"], vacuna: ["q2", "Q2"], "refinería": ["q3", "Q3"], huachicol: ["q6", "Q6"] };
const maxIdf = Math.max(...D.postings.map((p) => p.idf));
D.postings.forEach((p, i) => {
  const y = 1.7 + i * 0.78, [k, qid] = iconoTermino[p.termino] || ["q1", "Q1"], color = Q[qid].color;
  txt(s, p.termino, { x: 0.8, y, w: 1.3, h: 0.56, fontSize: 15, color: T.suave, align: "right", valign: "middle" });
  const w = 1.2 + (p.idf / maxIdf) * 4.0;
  pildora(s, 2.3, y, w, 0.56, color);
  iconoCirculo(s, k, 2.34, y + 0.04, 0.48, color);
  txt(s, `idf ${f2(p.idf)}`, { x: 2.95, y, w: w - 0.7, h: 0.56, fontSize: 15, bold: true, color: "FFFFFF", valign: "middle" });
  const pct = (100 * p.df) / D.corpus.pasajes;
  txt(s, `${fmt(p.df)} pasajes (${f2(pct)} %)`, { x: 2.45 + w, y, w: 2.6, h: 0.56, fontSize: 12, color: T.suave, valign: "middle" });
});
s.addNotes("Índice (30 s). Normalizo, quito stopwords con una lista ampliada para la estenográfica y aplico stemming. Huachicol aparece en 714 pasajes, 0.56 %: su idf es el más alto, 5.19. Tren aparece en más de 5 mil pasajes y vale 3.19. La marca del interlocutor no se indexa para que presidente o secretario no dominen los rankings.");

// ---------------------------------------------------------------- 6. MAP
s = clara("BM25 con filtro de fecha recupera mejor", `MAP sobre ${D.humano.juicios} juicios humanos de relevancia`, "resultados_ir.csv (relevancia temática)");
tarjeta(s, 0.5, 1.4, 9, 3.6);
const variantes = [
  ["bm25_con_filtro", "BM25 con filtro", T.marino], ["bm25_sin_filtro", "BM25 sin filtro", T.medio],
  ["tfidf_con_filtro", "TF-IDF con filtro", "9DB8D2"], ["tfidf_sin_filtro", "TF-IDF sin filtro", T.claro],
];
variantes.forEach(([m, nombre, color], i) => {
  const y = 1.8 + i * 0.72;
  pildora(s, 0.9, y, 3.6, 0.52, "FFFFFF", i === 0 ? T.marino : T.borde);
  s.addShape(pres.shapes.OVAL, { x: 1.1, y: y + 0.18, w: 0.16, h: 0.16, fill: { color }, line: { type: "none" } });
  txt(s, nombre, { x: 1.4, y, w: 2.0, h: 0.52, fontSize: 14, color: T.tinta, valign: "middle", bold: i === 0 });
  txt(s, f3(D.map[m]), { x: 3.4, y, w: 0.95, h: 0.52, fontSize: 14, bold: true, color: T.marino, align: "right", valign: "middle" });
});
const cxR = 7.0, cyR = 3.2;
variantes.forEach(([m, , color], i) => {
  const r = 1.55 - i * 0.3, d = 2 * r, grosor = 0.2 / r;
  s.addShape(pres.shapes.BLOCK_ARC, { x: cxR - r, y: cyR - r, w: d, h: d, angleRange: [0, 359.9], arcThicknessRatio: grosor, fill: { color: T.pista }, line: { type: "none" } });
  const fin = (270 + 360 * D.map[m]) % 360;
  s.addShape(pres.shapes.BLOCK_ARC, { x: cxR - r, y: cyR - r, w: d, h: d, angleRange: [270, fin], arcThicknessRatio: grosor, fill: { color }, line: { type: "none" } });
});
txt(s, f3(D.map.bm25_con_filtro), { x: cxR - 0.6, y: cyR - 0.25, w: 1.2, h: 0.5, fontSize: 20, bold: true, color: T.marino, align: "center", valign: "middle" });
s.addNotes("IR (40 s). BM25 con filtro es el mejor: MAP 0.484 frente a 0.295 de TF-IDF con filtro. La explicación probable es que BM25 satura la frecuencia y normaliza por longitud. Los juicios los hice viendo solo el tema, sin saber qué modelo recuperó cada pasaje.");

// ---------------------------------------------------------------- 7. AP por consulta
const ganaBm25 = D.consultas.filter((q) => q.ap_bm25 > q.ap_tfidf).length;
s = clara(`BM25 gana en ${ganaBm25} de 10 consultas`, "Precisión promedio (AP) por consulta, ambos con filtro de fecha", "salida/05_ir_ganador_por_consulta.csv");
tarjeta(s, 0.5, 1.35, 9, 3.75);
leyenda(s, 6.1, 1.5, [[T.claro, "TF-IDF (claro)"], [T.marino, "BM25 (oscuro)"]]);
const base = 4.25, alto = 2.25;
[0, 0.5, 1].forEach((v) => {
  const y = base - v * alto;
  txt(s, v.toFixed(1), { x: 0.6, y: y - 0.12, w: 0.4, h: 0.24, fontSize: 10, color: T.suave, align: "right" });
  s.addShape(pres.shapes.LINE, { x: 1.1, y, w: 8.2, h: 0, line: { color: T.pista, width: 0.75, dashType: "dash" } });
});
D.consultas.forEach((q, i) => {
  const cx = 1.55 + i * 0.8, wb = 0.24;
  [[q.ap_tfidf, tinte(q.color, 0.6), cx - wb - 0.02], [q.ap_bm25, q.color, cx + 0.02]].forEach(([ap, color, x]) => {
    const h = Math.max(wb, ap * alto);
    pildora(s, x, base - h, wb, h, color);
    if (h > 0.62) txt(s, f2(ap), { x: x - 0.25, y: base - h + 0.08 + (h - 0.2) / 2 - 0.2, w: 0.74, h: 0.24, fontSize: 9, bold: true, color: "FFFFFF", align: "center", valign: "middle", rotate: 270 });
  });
  iconoCirculo(s, q.icono, cx - 0.22, base + 0.07, 0.44, q.color);
  txt(s, q.id, { x: cx - 0.3, y: base + 0.56, w: 0.6, h: 0.2, fontSize: 9, color: T.suave, align: "center" });
});
s.addNotes("AP por consulta (40 s). BM25 gana en 8 de 10. En Tren Maya TF-IDF casi no encuentra nada (AP 0.025) porque el stemmer convierte Maya y mayo en la misma raíz. La más difícil es Dos Bocas: el corpus también la llama refinería Olmeca y ese nombre no está en la consulta; ahí ayudarían embeddings densos.");

// ---------------------------------------------------------------- 8. IE F1
const ie = D.ie;
s = clara(`Reglas y modelo juntos: F1 ${f2(ie.combinado.TODOS.f1)}`, `Gold anotado a mano: ${D.humano.gold_pasajes} pasajes, ${D.humano.gold_entidades} entidades`,
  "resultados_ie.csv · s/c: el modelo no detecta FECHA ni MONTO");
tarjeta(s, 0.5, 1.35, 9, 3.75);
leyenda(s, 4.75, 1.48, [[T.claro, "Reglas"], [T.medio, "Modelo"], [T.marino, "Combinado"]]);
["PER", "ORG", "LOC", "FECHA", "MONTO", "TODOS"].forEach((t, i) => {
  const y = 1.95 + i * 0.5;
  txt(s, [{ text: t, options: { bold: t === "TODOS", color: T.tinta } }, { text: `  ${ie.combinado[t].gold}`, options: { color: T.suave, fontSize: 10 } }],
    { x: 0.7, y, w: 1.3, h: 0.38, fontSize: 13, valign: "middle" });
  let x = 2.05;
  [["regla", T.claro, T.marino], ["modelo", T.medio, "FFFFFF"], ["combinado", T.marino, "FFFFFF"]].forEach(([m, color, tc]) => {
    const sc = m === "modelo" && (t === "FECHA" || t === "MONTO");
    const w = sc ? 0.62 : Math.max(0.62, ie[m][t].f1 * 2.35);
    if (sc) {
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: 0.38, rectRadius: 0.19, fill: { color: "FFFFFF" }, line: { color: T.medio, width: 0.75, dashType: "dash" } });
      txt(s, "s/c", { x, y, w, h: 0.38, fontSize: 10, color: T.suave, align: "center", valign: "middle" });
    } else {
      pildora(s, x, y, w, 0.38, color);
      txt(s, f2(ie[m][t].f1), { x: x + 0.14, y, w: w - 0.2, h: 0.38, fontSize: 11, bold: true, color: tc, valign: "middle" });
    }
    x += w + 0.1;
  });
});
s.addNotes(`Extracción (50 s). Combino reglas (regex de fechas y montos, gazetteers de 152 organizaciones y 102 lugares, y el nombre de la marca de interlocutor) con un BERT en español. Las reglas las congelé con una etiqueta de git antes de anotar el gold. F1 total: reglas ${f2(ie.regla.TODOS.f1)}, modelo ${f2(ie.modelo.TODOS.f1)}, combinado ${f2(ie.combinado.TODOS.f1)}; combinar sube el recall de ${f2(ie.regla.TODOS.r)} a ${f2(ie.combinado.TODOS.r)}. El modelo no detecta fechas ni montos.`);

// ---------------------------------------------------------------- 9. Errores
s = clara("El modelo parte nombres escritos en mayúsculas", "Tres errores reales del gold", "salida/09_analisis_errores.csv");
const casos = [
  ["amlo", "Nombre partido en la marca", Q.Q1.color === "" ? T.marino : "B57D02"],
  ["q2", "Entidad partida", Q.Q2.color],
  ["q1", "Obra marcada como ORG", Q.Q1.color],
];
D.errores.forEach((e, i) => {
  const x = 0.5 + i * 3.07, y = 1.45, [k, titulo, aro] = casos[i];
  tarjeta(s, x, y, 2.86, 3.55);
  iconoCirculo(s, k, x + 0.28, y + 0.28, 0.72, aro);
  txt(s, titulo, { x: x + 1.15, y: y + 0.3, w: 1.6, h: 0.7, fontSize: 13, bold: true, color: T.tinta, valign: "middle" });
  txt(s, "Gold", { x: x + 0.3, y: y + 1.25, w: 2.3, h: 0.25, fontSize: 10, color: T.suave });
  txt(s, `${e.gold}  (${e.tipo})`, { x: x + 0.3, y: y + 1.5, w: 2.35, h: 0.62, fontSize: 13, bold: true, color: T.marino, valign: "top" });
  txt(s, "Predicción", { x: x + 0.3, y: y + 2.2, w: 2.3, h: 0.25, fontSize: 10, color: T.suave });
  txt(s, e.pred, { x: x + 0.3, y: y + 2.45, w: 2.35, h: 0.45, fontSize: 15, bold: true, color: T.rojo, valign: "top" });
  txt(s, `Pasaje ${e.pasaje}`, { x: x + 0.3, y: y + 3.1, w: 2.3, h: 0.25, fontSize: 10, color: T.suave });
});
s.addNotes(`Errores (30 s). El peor resultado es PER del modelo (F1 ${f2(ie.modelo.PER.f1)}): en la marca, escrita en mayúsculas, el modelo parte los nombres; de ANDRÉS MANUEL LÓPEZ OBRADOR predice MAN. También parte Pfizer-BioNTech y marca el Tren Maya como organización cuando la convención lo trata como lugar. No afirmo que la causa sean las mayúsculas: sin el experimento de capitalización solo sé dónde ocurre.`);

// ---------------------------------------------------------------- 10. Respuestas
const totalResp = D.consultas.reduce((a, q) => a + q.respaldados, 0);
const vacios = D.consultas.flatMap((q) => q.sin_evidencia.map((c) => `${q.id} ${c}`));
s = clara("Cada respuesta cita el pasaje que la respalda", "«Respaldado»: el texto lo afirma junto al valor, no que sea verdad", "salida/respuestas.csv");
tarjeta(s, 0.5, 1.35, 9, 3.75);
leyenda(s, 0.8, 1.5, [[T.marino, "Respaldado (oscuro)"], [T.claro, "Ambiguo (claro)"]]);
pildora(s, 5.55, 1.48, 3.75, 0.34, "FFF1F2", "F6C9CD");
txt(s, `Sin evidencia: ${vacios.join(" · ")}`, { x: 5.65, y: 1.48, w: 3.6, h: 0.34, fontSize: 9, color: T.rojo, valign: "middle", fit: "shrink" });
const maxTot = Math.max(...D.consultas.map((q) => q.respaldados + q.ambiguos));
const baseR = 4.25, altoR = 2.1;
D.consultas.forEach((q, i) => {
  const cx = 1.3 + i * 0.83, wb = 0.42;
  const hr = (q.respaldados / maxTot) * altoR, ha = (q.ambiguos / maxTot) * altoR;
  s.addShape(pres.shapes.RECTANGLE, { x: cx - wb / 2, y: baseR - hr, w: wb, h: hr, fill: { color: q.color }, line: { type: "none" } });
  if (ha > 0) s.addShape(pres.shapes.RECTANGLE, { x: cx - wb / 2, y: baseR - hr - ha - 0.02, w: wb, h: ha, fill: { color: tinte(q.color, 0.7) }, line: { type: "none" } });
  txt(s, String(q.respaldados), { x: cx - 0.3, y: baseR - hr - ha - 0.3, w: 0.6, h: 0.24, fontSize: 10, bold: true, color: T.tinta, align: "center" });
  iconoCirculo(s, q.icono, cx - 0.22, baseR + 0.07, 0.44, q.color);
  txt(s, q.id, { x: cx - 0.3, y: baseR + 0.56, w: 0.6, h: 0.2, fontSize: 9, color: T.suave, align: "center" });
});
s.addNotes(`Respuestas (30 s). Para cada pregunta, un valor es respaldado si su oración contiene la relación que se pide; si no, queda ambiguo con su cita. Hay ${totalResp} valores respaldados en total. Dos campos quedaron sin evidencia en el top-10. Respaldado significa que el texto lo dice, no que sea verdad. Las diez tablas tienen mi valoración en el reporte.`);

// ---------------------------------------------------------------- 11. Demo
s = oscura();
txt(s, "Demo en vivo", { x: 0.6, y: 0.45, w: 6, h: 0.7, fontSize: 30, bold: true, color: "FFFFFF" });
s.addShape(pres.shapes.OVAL, { x: 6.55, y: 1.2, w: 2.9, h: 2.9, fill: { color: tinte(T.marino, 0.12) }, line: { type: "none" } });
s.addImage({ path: icono("q3"), x: 6.75, y: 1.4, w: 2.5, h: 2.5 });
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 1.45, w: 5.3, h: 0.75, rectRadius: 0.14, fill: { color: "0B2440" }, line: { type: "none" } });
txt(s, "$ make demo Q=Q3", { x: 0.85, y: 1.45, w: 5, h: 0.75, fontFace: T.mono, fontSize: 22, color: "FFFFFF", valign: "middle" });
["Top-10 de TF-IDF y BM25", "Entidades de cada pasaje", "Tabla con su evidencia"].forEach((t, i) => {
  const y = 2.6 + i * 0.7;
  s.addShape(pres.shapes.OVAL, { x: 0.6, y, w: 0.5, h: 0.5, fill: { color: T.claro }, line: { type: "none" } });
  txt(s, String(i + 1), { x: 0.6, y, w: 0.5, h: 0.5, fontSize: 16, bold: true, color: T.marino, align: "center", valign: "middle" });
  txt(s, t, { x: 1.3, y, w: 4.6, h: 0.5, fontSize: 18, color: "FFFFFF", valign: "middle" });
});
txt(s, "Q3 · refinería de Dos Bocas en Tabasco · 2019 a 2022", { x: 5.6, y: 4.25, w: 4.4, h: 0.3, fontSize: 11, color: T.claro, align: "center" });
pie(s, "", T.claro);
s.addNotes("Demo (2 min). Comando: make demo Q=Q3. 1) Panel con consulta, ventana y pregunta. 2) TF-IDF a la izquierda y BM25 a la derecha; en Q3 comparten 5 de 10 pasajes. 3) Entidades por pasaje: color por tipo; negrita cuando reglas y modelo coinciden; aquí se ve MAN como persona. 4) Tabla de respuesta: verde respaldado, amarillo ambiguo. Consulta libre: make demo CONSULTA=\"...\" DESDE=... HASTA=... (NER en caliente, 20 a 40 s, sin métricas). Respaldo si falla la máquina: laminas/demo_Q3_salida_guardada.txt, anunciado como salida guardada.");

// ---------------------------------------------------------------- 12. Límites y cierre
s = oscura();
txt(s, "Lo que falta para confiar más", { x: 0.6, y: 0.45, w: 8.8, h: 0.7, fontSize: 30, bold: true, color: "FFFFFF" });
const limites = [
  [`${D.humano.gold_pasajes}`, "pasajes en el gold", `${ie.combinado.FECHA.gold} FECHA y ${ie.combinado.MONTO.gold} MONTO: cifras poco estables`],
  [f2(ie.modelo.PER.f1), "F1 de PER del modelo", "Fragmenta nombres en mayúsculas"],
  ["NER", "por criterio técnico", "Sin conjunto de selección para comparar modelos"],
];
limites.forEach(([cifra, et, linea], i) => {
  const x = 0.6 + i * 3.0;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.5, w: 2.8, h: 2.4, rectRadius: 0.16, fill: { color: "FFFFFF", transparency: 90 }, line: { color: tinte(T.marino, 0.35), width: 0.75 } });
  txt(s, cifra, { x: x + 0.3, y: 1.75, w: 2.3, h: 0.75, fontSize: 36, bold: true, color: "FFFFFF", valign: "middle" });
  txt(s, et, { x: x + 0.3, y: 2.5, w: 2.3, h: 0.35, fontSize: 14, bold: true, color: T.claro });
  txt(s, linea, { x: x + 0.3, y: 2.9, w: 2.3, h: 0.8, fontSize: 12, color: "FFFFFF", valign: "top" });
});
txt(s, "Gracias", { x: 0.6, y: 4.3, w: 4, h: 0.5, fontSize: 22, bold: true, color: "FFFFFF" });
pie(s, "reporte/reporte.pdf, sección 7", T.claro);
s.addNotes("Cierre (20 s). El gold es pequeño, así que las cifras de FECHA y MONTO son poco estables; el modelo falla en nombres en mayúsculas; y elegí el NER por criterio técnico sin un conjunto para comparar modelos. Todo se reproduce desde un clon limpio en unos dos minutos. Gracias.");

pres.writeFile({ fileName: "../laminas.pptx" }).then(() => console.log(`laminas/laminas.pptx: ${num} diapositivas`));

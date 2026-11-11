# Guía de defensa

Para estudiar antes de la presentación. El profesor puede preguntar por cualquier función del
paquete `src/mtx/`. Cada módulo tiene qué hace, sus funciones clave y un ejemplo real.

## Fórmulas clave

| Fórmula | Expresión | Dónde |
| --- | --- | --- |
| idf de BM25 | idf(t) = ln(1 + (N − df + 0.5) / (df + 0.5)) | `indice.Indice.idf_bm25` |
| Puntaje BM25 | Σ_t idf(t) · tf·(k1+1) / (tf + k1·(1 − b + b·|d|/avgdl)), k1 = 1.5, b = 0.75 | `ranking.BM25.puntajes` |
| TF-IDF sublineal | w = (1 + ln tf) · (ln((1+N)/(1+df)) + 1), vector normalizado L2 | `ranking.ajustar_tfidf` |
| Coseno | cos(q, d) = q·d / (‖q‖‖d‖); con vectores L2 es solo el producto punto | `ranking.Tfidf.puntajes` |
| P@k | relevantes en los primeros k / k | `kit/evaluar.py` |
| AP | (1/R) Σ_{k relevante} P@k, con R = relevantes de la consulta en el pool | `kit/evaluar.py` |
| MAP | promedio de AP sobre las 10 consultas | `kit/evaluar.py` |
| P, R, F1 | P = TP/(TP+FP), R = TP/(TP+FN), F1 = 2PR/(P+R); TP solo si coinciden pasaje, tipo, inicio y fin | `kit/evaluar.py ie` |

Por qué el idf de BM25 lleva "1 +": así nunca es negativo, aunque un término aparezca en más de
la mitad de los pasajes. `rank_bm25` usa ln((N − df + 0.5)/(df + 0.5)) con un piso epsilon; por
eso las pruebas lo comparan con una subclase que usa mi idf (tolerancia 1e-6).

Por qué BM25 satura: tf·(k1+1)/(tf + k1·…) crece cada vez menos con tf y tiende a k1+1; un
término repetido 20 veces no vale 20 veces más. El factor b penaliza pasajes más largos que el
promedio (avgdl = 72.2 tokens).

## Módulos

### corpus.py · carga, limpieza y segmentación (script 01)
- `cargar()` lee el snapshot de Hugging Face; `limpiar_ruido()` quita acotaciones entre corchetes,
  repara fechas y canoniza las marcas de interlocutor a una intervención por línea.
- El formato real no era el del kit: las marcas venían como `~~~ETIQUETA` o `NOMBRE, CARGO:` en
  línea; el reconocedor del kit no encontraba ninguna.
- `detectar_duplicados()` encuentra duplicados exactos y casi duplicados (4 y 1).
- `partir_canonico()` separa intervenciones; la ventana de 200/150/40 viene del kit.
- `es_reportero()` marca PREGUNTA, INTERLOCUTOR, etc.
- Ejemplo: un discurso se convierte en decenas de pasajes, cada uno con `PRESIDENTE ...:` al
  inicio e `inicio_cuerpo` apuntando al primer carácter después de la marca.

### preproceso.py · tokenización para IR (script 02)
- NFC, minúsculas, tokens alfanuméricos con guion interno, stoplist (NLTK + estenográfica, 336),
  descarta tokens de 2 letras o menos salvo números, stemming Snowball.
- `tokenizar_pasaje(texto, inicio_cuerpo)` solo ve el cuerpo: la marca no entra al índice.
- Ejemplo: `tokenizar("refinería de Dos Bocas en Tabasco")` → `['refin', 'dos', 'boc', 'tabasc']`.

### indice.py · índice invertido (script 02)
- `construir(ids, tokens)` arma `postings[raíz] = {pasaje: tf}`, la longitud de cada pasaje y avgdl.
- `idf_bm25(t)` usa la fórmula de arriba; `muestra_postings()` genera `salida/02_postings.md`.
- Ejemplo: `huachicol` → df = 714, idf = 5.186.

### ranking.py · TF-IDF, BM25 y filtro de fecha (script 03)
- `BM25.puntajes(tokens)`: recorre solo los postings de cada término de la consulta (rápido).
- `Tfidf`: `TfidfVectorizer` de scikit-learn con `sublinear_tf=True`, `norm="l2"`; puntaje = producto
  punto con la consulta.
- `mascara_fecha(fechas, desde, hasta)` compara por día; `top_k()` desempata por `doc_id` y
  posición, así el orden es determinista.
- `Buscador.buscar()` es la búsqueda libre de la demo; `variantes_oficiales()` produce las 4
  variantes de `ranking.csv`.

### pool.py · pool y juicios (script 04)
- `construir_pool()`: unión sin duplicados de los cuatro top-10 por consulta (176 pares); el orden
  se baraja con semilla 42 y se oculta la variante al anotador.
- `validar_juicios()`: columnas exactas, solo 0 o 1, todos los pares del pool juzgados.

### evaluacion.py · evaluación de IR (script 05)
- La cifra oficial la da `kit/evaluar.py ir`; este módulo hace la vista con ventana
  (`relevante AND en_ventana`), tablas por consulta y figuras.
- `elegir_mejor_modelo()`: argmax del MAP entre TF-IDF y BM25 con filtro → BM25 (0.484).

### consultas.py, descubrimiento.py, ambito.py
- `consultas.construir()`: Q1 a Q8 del kit tal cual más Q9 (Banco del Bienestar) y Q10 (Tren
  Interoceánico), que elegiste tú con la señal de `descubrimiento.py`.
- `ambito.ambito_ie()`: los pares (consulta, pasaje) del top-10 de BM25 con filtro (99 pasajes);
  sobre ellos corre la extracción.

### reglas.py · regex y gazetteers (script 06)
- `buscar_fechas()`: fechas absolutas, mes y año, años con contexto e intervalos; incluye
  "próximo", excluye "el" o "en".
- `buscar_montos()`: cifra + escala + moneda o `$`; porcentajes y dosis van a
  `buscar_auxiliares()`, nunca a MONTO.
- Gazetteer: patrones escapados y ordenados por longitud, límites de palabra con acentos, siglas
  cortas sensibles a mayúsculas (PAN no casa con "pan").
- Regla de marca: quita el cargo con una lista y deja el nombre como PER.
- Colisiones: gana el span más largo; empate por jerarquía fecha > monto > LOC > ORG > marca.
- Ejemplo: "anunció 2 mil 500 millones de pesos el próximo 15 de enero en Tabasco para Pemex" →
  MONTO `2 mil 500 millones de pesos`, FECHA `próximo 15 de enero`, LOC `Tabasco`, ORG `Pemex`.

### ner_modelo.py · NER con BERT (script 07)
- Modelo `mrm8488/bert-spanish-cased-finetuned-ner` con revisión fija; PER, ORG, LOC; MISC se
  descarta y se cuenta.
- `ventanas()`: parte el pasaje en ventanas de subtokens con solapamiento para no pasar del
  límite del modelo; `inferir_pasaje()` proyecta los offsets al texto original.
- Caché en `data/cache_ner/`: la clave incluye el hash del texto y la revisión; no se reinfiere.
- `posprocesar()`: recorta puntuación, une pedazos de la misma palabra y spans contiguos del mismo
  tipo (registrados en `salida/07_uniones_spans.csv`).

### fusion.py y normalizacion.py · fusión y normalización (script 08)
- `fusionar_unicas()`: misma (pasaje, tipo, inicio, fin) en ambas fuentes → `ambos`; si no,
  `regla` o `modelo`. Los solapes parciales no se resuelven: se guardan ambas filas.
- `entidades.csv` tiene exactamente 8 columnas; lo demás va a `entidades_enriquecidas.csv`.
- `normalizar_fecha(texto, ancla)` → ISO con precisión (día, mes, año); "31 de febrero" queda
  no resoluble. `normalizar_monto(texto)` → `Decimal`, escala, moneda (MXN, USD o vacía).

### muestreo.py y gold.py · gold (scripts 08b y app)
- `sortear()`: 20 pasajes, 2 por consulta, uno del rango 1-5 y otro del 6-10, semilla 42, sin
  repetir pasajes entre consultas (emparejamiento global).
- `gold.validar_gold()`: 20 cerrados, offsets válidos, sin duplicados y la etiqueta
  `reglas-congeladas` anterior al primer commit del gold.
- Modo ciego: este módulo no lee predicciones; la app no las muestra hasta el cierre.

### evaluacion_ie.py · evaluación de IE (script 09)
- Corre `kit/evaluar.py ie`; `detalle()` agrega TP, FP, FN y soporte; FECHA y MONTO del modelo
  salen como "sin cobertura".
- `analizar_errores()`: frontera (incluye entidad partida), tipo (incluye obra LOC u ORG), sigla
  no reconocida, en marca, omisión, espuria.
- Ejemplo real: pasaje 1122_3, gold `ANDRÉS MANUEL LÓPEZ OBRADOR`, el modelo predice `MAN` → FP
  de frontera en la marca.

### respuestas.py · tablas de respuesta (script 10)
- `excluir()`: quita entidades de la marca y las variantes del nombre del presidente en campos PER.
- `contexto()`: ±60 caracteres más la oración del span; `responder_campo()` marca
  `respaldado_en_texto` si aparecen todos los patrones del campo, si no `ambiguo`.
- `agregar()`: agrupa por nombre canónico, cuenta discursos distintos, hasta 8 valores por campo.
- Las valoraciones son tuyas y guardan la huella de la tabla; si la tabla cambia, se invalidan.

### manifiesto.py, entrega.py, adaptadores_kit.py
- `manifiesto.registrar()`: hashes de entradas y salidas, commit y tiempos de cada paso.
- `entrega.validar()`: las 15 condiciones de `make validar`.
- `adaptadores_kit`: único módulo que toca `kit/`; corre el evaluador como subproceso sin editarlo.

### app/ · app Streamlit (make app)
- Pestañas Estado, Juicios, Gold, Gazetteer y Valoraciones; escritura atómica (archivo temporal
  y luego renombrar) con número de revisión para detectar dos pestañas abiertas.
- Juicios sin modelo, rango ni puntaje; gold sin predicciones hasta el cierre.

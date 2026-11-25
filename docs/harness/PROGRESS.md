# Progreso — Sistema de recuperación y extracción de información sobre discursos presidenciales

## Estado actual (2026-11-12)

**Entregado.** H0 a H9 cerrados. Repo público en GitHub
(`https://github.com/DiegoMoctezuma/Examen_Mineria_Textos`), etiqueta `v1.0-entrega` en `431f1c0`
(2026-11-11, antes de las 20:00 CDMX). Entrega en equipo (equipo Datisa: Carpio Angeles Leo Yahir,
Mera Montiel Gonzalo Sebastian, Moctezuma Ramirez Diego Rafael, Ramirez Maza Luis). `make validar`:
14 OK, 1 falla (condición 12: el guion no registra «Tiempo medido: m:ss»).

## Fase v2 (desde 2026-11-14) · estado al 2026-11-24, 21:05

Proyecto final en equipo; entrega el 2026-11-25 antes de las 18:00. Plan en
`PRD_v2_proyecto_final.md`; progreso por paquete en `docs/harness/progreso/<wp>.md`. Rama
`proyecto-final` en GitHub; `main` intacto. Equipo de 5: Leo Yahir Carpio Angeles, Arturo
Jaramillo Salmerón, Gonzalo Sebastian Mera Montiel, Diego Rafael Moctezuma Ramirez y Luis Ramirez
Maza (Bruno salió el 22). Recortes 1, 2 y 3 aplicados el 23.

Hecho el 24 (todo lo del calendario del 24 y parte del 25):
- **Cierres:** gold v2 a las 19:26 (`b61ae3d`) y juicios v2 a las 19:27 (`6709211`, 320 pares con
  3 juicios válidos). Orden verificado por la condición 17: `v2-inicio` → `reglas-fecha-v2` → NER v2
  (`3287efb`) → cierre del gold.
- **Cifras v2 (`make all-v2`):** κ de Fleiss 0.4753; ganador BM25 con raíz y filtro, MAP 0.5356
  (IC95 0.4329 a 0.6407), lema 0.5070 (p = 0.07); F1 combinado 0.8273 (IC95 0.7714 a 0.8818),
  techo humano 0.8533, línea base 0.6543, parcial 0.9259; 248 de 375 datos respaldados. Detalle
  en `docs/decisiones.md`.
- **Raíz promovida a v2** (`make promover-v2`, D28); condiciones 2 a 8 contra fuentes v2; objetivos
  v1 que escriben en la raíz bloqueados (v1 vive en `salida/`, `anotaciones/` y `v1.0-entrega`).
  Excepción registrada para la condición 12.
- **Reconstrucción v2 desde clon limpio:** 18 min 33 s, todo byte a byte
  (`docs/reproducibilidad.md`).
- WP-07 (booleano), WP-16 (14 figuras v2), guion v2 y guía de defensa con cifras (aprobados por
  Diego), instrucción de la revisión ciega, mapa de Q11 a Q15 aprobado.
- PR #4 de Leo (demo web) integrado; reporte v2 de Gonzalo integrado con correcciones;
  `make reporte-v2` compila a 6 páginas con 6 pendientes ⟦…⟧.
- `make validar --parcial --sin-pruebas`: 19 OK, 3 pendientes (13, 21 y 22). `make test`: 742.

Pendiente, en orden (mié 25):
1. Temprano: Gonzalo confirma los `[VALIDAR]` de `config/v2/estilo.yaml` → `make figuras-v2` si
   cambia algo. Leo reinicia la demo publicada (si no lo hizo el 24) y pasa la dirección.
2. 9:00 a 11:00: valoraciones v2 (Gonzalo, Arturo y Luis) → integrar sus ramas → condición 21.
3. Láminas (Gonzalo y Arturo) con `salida/v2/figuras/` → revisión ciega (Arturo,
   `docs/revision_ciega_prompt.md`) → `docs/revision_ciega_respuesta.md`.
4. Reporte v2: cerrar los ⟦…⟧ con las valoraciones, la revisión ciega y la cifra de `make test`
   (Gonzalo) → `make reporte-v2` → commit del PDF. README v2 (Luis): equipo con «Leo Yahir»,
   cifras v2, demo web y Uso de IA; Luis valida la lámina 16 y las secciones 4 y 5 del reporte.
5. 14:00: ensayo cronometrado → `Tiempo medido: m:ss` en `laminas/guion_v2.md` → condición 22.
6. 16:00: `make validar` completo, `v2.0-entrega` desde clon limpio, merge a `main`.

Bloqueos v2: ninguno técnico; todo lo que falta es trabajo humano del 25.

## Completado

- H0 a H8 (2026-11-04 a 2026-11-11): corpus y pasajes (127,739), índice, TF-IDF y BM25, pool de
  176 pares, juicios del alumno, `mejor_modelo` = BM25 con filtro (MAP 0.484), reglas congeladas,
  NER `mrm8488` por criterio técnico, gold de 20 pasajes en modo ciego, fusión y evaluación IE
  (F1 combinado 0.784), tablas de respuesta y 10 valoraciones del alumno.
- H9 (2026-11-11):
  - Reporte de 5 páginas (`reporte/reporte.md` → PDF con pandoc arm64 y Chrome; sin XeLaTeX).
  - README de 10 secciones con Uso de IA y `requirements.txt` exportado con `--frozen`.
  - Demo `make demo Q=Q3` (0.2 s) y consulta libre con NER en caliente (unos 10 s, sin red).
  - Reconstrucción desde clon limpio (unos 2 min, seis CSV idénticos), en `docs/reproducibilidad.md`.
  - `docs/guia_defensa.md`.
- Presentación final y guion hechos a mano por el equipo: `laminas/Presentacion_Mineria_de_Textos.pptx`
  y `laminas/guion.md`. El deck automático (pptxgenjs, `laminas/deck/`) quedó como
  `make laminas-generadas`; `make laminas` ya no regenera nada.
- Pestaña Estado de la app: resultados IR y caché NER ya tienen validador (13 de 13 en verde).

## Pendiente

1. Equipo: ensayar con cronómetro y agregar `Tiempo medido: m:ss` al guion (cierra la condición 12).
   El alumno pidió no tocar la presentación ni el guion: solo agregar esa línea si él da el tiempo.
2. Decidir si `v1.0-entrega` se mueve a `f9cc3ee` (ajustes del equipo a la presentación, subidos
   el 2026-11-12, después de la etiqueta). Por defecto no se mueve.
3. Confirmar con el alumno que sí consultó a Gemini (así lo declaran el README y el reporte).
4. Opcional: usar los juicios del otro integrante como segundo anotador (acuerdo 115 de 176,
   kappa ≈ 0.31) sin cambiar las cifras oficiales.

## Decisiones

Ver `docs/decisiones.md`. Las no obvias de esta sesión:
- Más de 5 láminas por decisión del alumno (el enunciado dice máximo 5); la condición 12 lo acepta
  por la excepción registrada.
- No se mezcló el repo del compañero (MAP 0.615): mismo `ranking.csv`, mismo pool y mismo NER; la
  diferencia de MAP viene solo de juicios distintos. Elegir juicios por el MAP sería ajustar la
  evaluación al resultado.
- `reglas_congeladas_vigentes()` ignora archivos agregados a `config/` después de la etiqueta
  (solo cuentan modificados, renombrados o borrados).
- Remoto: GitHub del alumno; el GitLab anterior se desligó.

## Bloqueos

- Ninguno técnico. Para renderizar láminas, LibreOffice funciona con
  `soffice --headless -env:UserInstallation=file://<scratch>` en segundo plano; Keynote no exporta
  desde la sesión.

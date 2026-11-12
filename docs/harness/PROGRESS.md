# Progreso — Sistema de recuperación y extracción de información sobre discursos presidenciales

## Estado actual (2026-11-12)

**Entregado.** H0 a H9 cerrados. Repo público en GitHub
(`https://github.com/DiegoMoctezuma/Examen_Mineria_Textos`), etiqueta `v1.0-entrega` en `431f1c0`
(2026-11-11, antes de las 20:00 CDMX). Entrega en equipo (equipo Datisa: Carpio Angeles Leo Yair,
Mera Montiel Gonzalo Sebastian, Moctezuma Ramirez Diego Rafael, Ramirez Maza Luis). `make validar`:
14 OK, 1 falla (condición 12: el guion no registra «Tiempo medido: m:ss»).

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
3. Revisar el guion: menciona a "Jaramillo Salmerón, Arturo", que no está en la lista de
   integrantes que dio el alumno.
4. Confirmar con el alumno que sí consultó a Gemini (así lo declaran el README y el reporte).
5. Opcional: usar los juicios del otro integrante como segundo anotador (acuerdo 115 de 176,
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

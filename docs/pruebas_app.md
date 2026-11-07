# Prueba manual de la app (PRD §7)

El alumno la recorre una vez y anota fecha y resultado. Los pasos 1 a 5 aplican desde H3; los
pasos 6 a 10 se habilitan cuando existan las pestañas Gold y Gazetteer (H5 y H6).

Para no mezclar estas pruebas con los juicios reales, los pasos 3 a 5 se hacen con una carpeta
de anotaciones temporal:

```bash
MTX_ANOTACIONES=/tmp/prueba_anotaciones make app
```

| # | Acción | Resultado esperado | Fecha y resultado |
| ---: | --- | --- | --- |
| 1 | `make app` | Se abre `http://localhost:8501` en la página Estado, sin red y sin cargar el modelo NER. | |
| 2 | Revisar Estado | Ningún artefacto aparece válido solo por existir: criterio y juicios en 🟡 pendiente humano mientras falten; juicios exportados y resultados IR en ⚪ pendiente técnico. | |
| 3 | En Juicios: Relevante (`1`), No relevante (`0`), Omitir (`O`) y Anterior (`←`) | Cada clic guarda al momento; el omitido aparece como "Omitido por ahora" y no como 0; Anterior muestra el valor guardado; no aparecen puntajes, rangos ni modelos. | |
| 4 | Cerrar el navegador y la terminal; volver a `make app` | Retoma en el primer pendiente de cada consulta con el mismo progreso. | |
| 5 | Abrir Juicios en dos pestañas, juzgar en la primera y luego en la segunda | La segunda muestra "Editado desde otra pestaña o proceso: recarga antes de guardar" y no escribe; con "Recargar desde disco" vuelve a funcionar. | |
| 6 | Gold: buscar un texto que aparece dos veces en el pasaje (H6) | Muestra ambas apariciones con 40 caracteres de contexto y deja elegir; nunca toma la primera por defecto. | |
| 7 | Gold: seleccionar por tokens un monto con `$` y punto final (H6) | Recorta la puntuación final y conserva el `$`. | |
| 8 | Gold: agregar dos veces la misma entidad (H6) | La segunda se rechaza con un error visible. | |
| 9 | Gazetteer: aceptar, corregir y descartar una sigla (H5) | `config/gazetteer_extendido.csv` cambia en consecuencia; tras `make congelar` la pestaña bloquea la escritura. | |
| 10 | Gold: cerrar el gold con todos los pasajes revisados (H6) | Escribe `anotaciones/cierre_gold.json` solo si `validar_gold()` pasa; antes, ninguna vista muestra predicciones de la muestra. | |

Alternativa sin Streamlit: `make app-cli` (juicios por terminal con las mismas teclas: `1`, `0`,
`o`, `a`, más `c` para cambiar de consulta, `g` para comprobar el guardado y `s` para salir).

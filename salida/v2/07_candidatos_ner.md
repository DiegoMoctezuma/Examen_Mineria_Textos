# Candidatos NER v2 (D34, WP-10)

- Fecha: 2026-11-24T14:39:03
- Entorno: Python 3.11.18, CPU

| Candidato | Revisión | Motor | Licencia | Parámetros | Etiquetas reales | Límite | Ejemplo sintético | Resultado |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mrm8488/bert-spanish-cased-finetuned-ner | `b11721d41d9e` | transformers | no declarada (candidato obligatorio de D34) | 109 M | LOC, MISC, ORG, PER | 510 | PER «Jorge Alcocer Varela»; PER «Andrés Manuel López Obrador»; LOC «Tabasco»; LOC «Dos Bocas de Pemex» | ✔ |
| Davlan/xlm-roberta-base-ner-hrl | `253f557bd824` | transformers | afl-3.0 | 277 M | DATE, LOC, ORG, PER | 510 | PER «Jorge Alcocer Varela»; PER «Andrés Manuel López Obrador»; LOC «Tabasco»; LOC «Dos Bocas»; LOC «Pemex» | ✔ |
| Davlan/xlm-roberta-large-ner-hrl | `1f929ffad9b7` | transformers | afl-3.0 | 559 M | DATE, LOC, ORG, PER | 510 | PER «Jorge Alcocer Varela»; PER «Andrés Manuel López Obrador»; LOC «Tabasco»; ORG «Pemex» | ✔ |
| es_core_news_lg | `3.8.0` | spacy | gpl-3.0 | — | LOC, MISC, ORG, PER | 1,000,000 caracteres | PER «Salud»; PER «Jorge Alcocer Varela»; PER «Andrés Manuel López Obrador»; LOC «Tabasco»; LOC «Dos Bocas»; ORG «Pemex» | ✔ |

Descartados al verificar (2026-11-24): `PlanTL-GOB-ES/roberta-base-bne-capitel-ner` (ya no está publicado en Hugging Face; solo quedan copias de terceros sin procedencia verificable) y `MMG/xlm-roberta-large-ner-spanish` (no declara licencia).

El mapa de cada candidato a PER, ORG y LOC y sus etiquetas descartadas están en `config/ner.yaml`.

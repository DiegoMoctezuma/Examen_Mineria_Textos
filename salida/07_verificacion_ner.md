# Verificación técnica del NER (P06): `mrm8488/bert-spanish-cased-finetuned-ner`

- Fecha: 2026-11-08T18:48:07
- Revisión fija: `b11721d41d9e948da32fcdabeeef4fb0f3ebcdf7`
- Entorno: Python 3.11.18, transformers 5.22.1, torch 2.15.0 (CPU, device=-1)
- Carga del modelo y el pipeline: 2.0 s

| Comprobación | Resultado | Detalle |
| --- | --- | --- |
| Pesos de clasificación de tokens (cabeza NER) | ✔ | BertForTokenClassification |
| Mapa real de etiquetas (`id2label`) | ✔ | B-LOC, B-MISC, B-ORG, B-PER, I-LOC, I-MISC, I-ORG, I-PER, O |
| Etiquetas del mapa del proyecto presentes en el modelo | ✔ | mapa {'PER': 'PER', 'ORG': 'ORG', 'LOC': 'LOC'}; descartadas ['MISC'] |
| Tokenizador rápido con `offset_mapping` | ✔ | is_fast=True |
| Límite real coincide con `config/ner.yaml` | ✔ | min(max_position_embeddings, model_max_length) − especiales = 510 |
| Ejemplo de desarrollo 1 (sintético, fuera de la muestra gold) | ✔ | PER «Jorge Alcocer Varela»; PER «Andrés Manuel López Obrador»; LOC «Tabasco»; LOC «Dos Bocas de Pemex» |
| Ejemplo de desarrollo 2 (sintético, fuera de la muestra gold) | ✔ | ORG «Comisión Federal de Electricidad»; ORG «IMSS»; LOC «Mérida»; LOC «Yucatán» |

Resultado: **aprobado**.

# Booleano contra BM25: «Huachicol»

Consulta: «combate al huachicol y robo de combustible», con su ventana de fechas. Exploratorio (PRD v2 D30): no entra al pool ni compite por el ganador.

| palabra | término | fragmentos (df) | idf (BM25) |
| --- | --- | ---: | ---: |
| «combate» | `combat` | 2,842 | 3.81 |
| «huachicol» | `huachicol` | 714 | 5.19 |
| «robo» | `rob` | 5,984 | 3.06 |
| «combustible» | `combust` | 2,993 | 3.75 |

- **AND** (todas las palabras): 14 fragmentos en la ventana, sin orden.
- **OR** (cualquier palabra): 1,485 fragmentos en la ventana, sin orden. De ellos, 224 tienen `huachicol` y 1,261 no lo tienen: un fragmento que solo dice `rob` entra igual que uno que dice `huachicol`, porque el booleano no usa el idf.
- **BM25** devuelve 10 fragmentos ordenados; 10 de ellos tienen `huachicol`, porque su idf pesa más.

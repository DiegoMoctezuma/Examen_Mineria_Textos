# Stem frente a lema

Mismo pipeline (NFC, `RE_TOKEN`, stoplist y longitud mínima sobre la superficie); solo cambia la raíz: Snowball en v1, lema de spaCy `es_core_news_md` en v2 (PRD v2 D26).

| | stem (v1) | lema (v2) |
| --- | ---: | ---: |
| Pasajes | 127,739 | 127,739 |
| Vocabulario | 35,891 | 68,482 |
| Tokens por pasaje (avgdl) | 72.21 | 72.21 |
| Pasajes sin tokens | 0 | 0 |

Lematizar el corpus tomó 15.4 min.

## Pares de palabras

| palabra | stem (v1) | lema (v2) |
| --- | --- | --- |
| maya | `may` (df 6,504) | `maya` (df 4,344) |
| mayo | `may` (df 6,504) | `mayo` (df 2,151) |
| vacunas | `vacun` (df 4,552) | `vacuna` (df 3,451) |
| vacuna | `vacun` (df 4,552) | `vacuna` (df 3,451) |
| refinería | `refin` (df 2,069) | `refinería` (df 1,923) |
| refinerías | `refin` (df 2,069) | `refinería` (df 1,923) |
| presidente | (se descarta) | (se descarta) |
| presidencia | `president` (df 5,337) | `presidencia` (df 2,475) |
| programa | `program` (df 12,803) | `programa` (df 11,923) |
| programas | `program` (df 12,803) | `programa` (df 11,923) |
| elecciones | `eleccion` (df 3,864) | `elección` (df 3,861) |
| electoral | `electoral` (df 2,962) | `electoral` (df 2,943) |

## Términos de cada consulta

idf con la fórmula de BM25, ln(1 + (N - df + 0.5) / (df + 0.5)).

| consulta | stem (v1): término (idf) | lema (v2): término (idf) |
| --- | --- | --- |
| Q1: avances en la construcción del Tren Maya | `avanc` (3.29), `construccion` (3.12), `tren` (3.19), `may` (2.98) | `avance` (3.34), `construcción` (3.12), `tren` (3.19), `maya` (3.38) |
| Q2: llegada y aplicación de vacunas contra el COVID-19 | `lleg` (1.79), `aplic` (2.96), `vacun` (3.33), `covid-19` (4.84) | `llegada` (5.16), `aplicación` (4.63), `vacuna` (3.61), `covid-19` (4.84) |
| Q3: refinería de Dos Bocas en Tabasco | `refin` (4.12), `dos` (1.62), `boc` (4.63), `tabasc` (3.62) | `refinería` (4.20), `dos` (1.62), `bocas` (5.04), `tabasco` (3.62) |
| Q4: aeropuerto Felipe Ángeles en Santa Lucía | `aeropuert` (3.56), `felip` (3.89), `angel` (4.15), `sant` (4.03), `luc` (4.84) | `aeropuerto` (3.56), `felipe` (3.90), `ángeles` (4.48), `santa` (4.15), `lucía` (5.20) |
| Q5: programa Sembrando Vida y apoyo a campesinos | `program` (2.30), `sembr` (4.15), `vid` (2.50), `apoy` (1.95), `campesin` (3.99) | `programa` (2.37), `sembrar` (4.30), `vida` (2.50), `apoyo` (2.35), `campesino` (4.04) |
| Q6: combate al huachicol y robo de combustible | `combat` (3.81), `huachicol` (5.19), `rob` (3.06), `combust` (3.75) | `combatir` (4.36), `huachicol` (5.19), `robo` (3.90), `combustible` (3.78) |
| Q7: pensión universal para adultos mayores | `pension` (3.65), `universal` (4.08), `adult` (3.43), `mayor` (2.10) | `pensión` (3.68), `universal` (4.09), `adulto` (3.45), `mayor` (2.45) |
| Q8: aumento al salario mínimo y acuerdo con empresarios | `aument` (3.04), `salari` (3.78), `minim` (4.22), `acuerd` (2.24), `empresari` (3.66) | `aumento` (4.19), `salario` (3.78), `mínimo` (4.15), `acuerdo` (2.38), `empresario` (3.67) |
| Q9: operación y apertura de sucursales del Banco del Bienestar | `oper` (2.78), `apertur` (5.56), `sucursal` (4.73), `banc` (3.49), `bienest` (2.79) | `operación` (3.46), `apertura` (5.65), `sucursal` (4.73), `banco` (3.57), `bienestar` (2.79) |
| Q10: construcción y operación del Tren Interoceánico del Istmo de Tehuantepec | `construccion` (3.12), `oper` (2.78), `tren` (3.19), `interocean` (6.09), `istmo` (4.63), `tehuantepec` (5.62) | `construcción` (3.12), `operación` (3.46), `tren` (3.19), `interoceánico` (6.09), `istmo` (4.63), `tehuantepec` (5.62) |
| Q11: despliegue de la Guardia Nacional en los estados | `desplieg` (5.30), `guardi` (3.14), `nacional` (1.94) | `despliegue` (5.37), `guardia` (3.15), `nacional` (1.96) |
| Q12: atención médica gratuita del IMSS-Bienestar | `atencion` (2.77), `medic` (2.84), `gratuit` (4.09), `imss-bienest` (4.45) | `atención` (2.77), `médico` (2.86), `gratuito` (4.10), `imss-bienestar` (4.45) |
| Q13: reforma eléctrica y fortalecimiento de la CFE | `reform` (2.66), `electr` (3.28), `fortalec` (3.62), `cfe` (5.43) | `reforma` (2.73), `eléctrico` (3.66), `fortalecimiento` (5.20), `cfe` (5.43) |
| Q14: becas para aprendices de Jóvenes Construyendo el Futuro | `bec` (3.74), `aprendic` (5.24), `joven` (2.94), `constru` (2.86), `futur` (3.95) | `beca` (3.78), `aprendices` (5.28), `jóvenes` (4.78), `construir` (2.92), `futuro` (3.95) |
| Q15: daños y reconstrucción de Acapulco tras el huracán Otis | `dañ` (3.57), `reconstruccion` (5.32), `acapulc` (4.56), `tras` (5.28), `huracan` (4.98), `otis` (6.69) | `daño` (3.85), `reconstrucción` (5.32), `acapulco` (4.56), `tras` (5.28), `huracán` (4.98), `otis` (6.69) |

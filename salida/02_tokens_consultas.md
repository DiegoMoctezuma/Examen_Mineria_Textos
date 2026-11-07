# Tokens de las consultas

Cadena de PRD §6.2: NFC y minúsculas, `RE_TOKEN`, stoplist, longitud mínima 3 (salvo números) y Snowball en español. Cada token final indica su df en el índice (N = 127,739 pasajes); df 0 significa que el término no puntúa.

## Q1: avances en la construcción del Tren Maya

- Palabras originales: avances, en, la, construcción, del, tren, maya
- Retiradas (stoplist o longitud): en, la, del
- Tras stoplist, sin stemming: avances, construcción, tren, maya
- Tokens finales: `avanc` (df 4,741), `construccion` (df 5,648), `tren` (df 5,261), `may` (df 6,504)

## Q2: llegada y aplicación de vacunas contra el COVID-19

- Palabras originales: llegada, y, aplicación, de, vacunas, contra, el, covid-19
- Retiradas (stoplist o longitud): y, de, contra, el
- Tras stoplist, sin stemming: llegada, aplicación, vacunas, covid-19
- Tokens finales: `lleg` (df 21,262), `aplic` (df 6,637), `vacun` (df 4,552), `covid-19` (df 1,006)

## Q3: refinería de Dos Bocas en Tabasco

- Palabras originales: refinería, de, dos, bocas, en, tabasco
- Retiradas (stoplist o longitud): de, en
- Tras stoplist, sin stemming: refinería, dos, bocas, tabasco
- Tokens finales: `refin` (df 2,069), `dos` (df 25,300), `boc` (df 1,243), `tabasc` (df 3,433)

## Q4: aeropuerto Felipe Ángeles en Santa Lucía

- Palabras originales: aeropuerto, felipe, ángeles, en, santa, lucía
- Retiradas (stoplist o longitud): en
- Tras stoplist, sin stemming: aeropuerto, felipe, ángeles, santa, lucía
- Tokens finales: `aeropuert` (df 3,643), `felip` (df 2,602), `angel` (df 2,010), `sant` (df 2,262), `luc` (df 1,005)

## Q5: programa Sembrando Vida y apoyo a campesinos

- Palabras originales: programa, sembrando, vida, y, apoyo, a, campesinos
- Retiradas (stoplist o longitud): y, a
- Tras stoplist, sin stemming: programa, sembrando, vida, apoyo, campesinos
- Tokens finales: `program` (df 12,803), `sembr` (df 2,011), `vid` (df 10,468), `apoy` (df 18,238), `campesin` (df 2,352)

## Q6: combate al huachicol y robo de combustible

- Palabras originales: combate, al, huachicol, y, robo, de, combustible
- Retiradas (stoplist o longitud): al, y, de
- Tras stoplist, sin stemming: combate, huachicol, robo, combustible
- Tokens finales: `combat` (df 2,842), `huachicol` (df 714), `rob` (df 5,984), `combust` (df 2,993)

## Q7: pensión universal para adultos mayores

- Palabras originales: pensión, universal, para, adultos, mayores
- Retiradas (stoplist o longitud): para
- Tras stoplist, sin stemming: pensión, universal, adultos, mayores
- Tokens finales: `pension` (df 3,332), `universal` (df 2,161), `adult` (df 4,125), `mayor` (df 15,615)

## Q8: aumento al salario mínimo y acuerdo con empresarios

- Palabras originales: aumento, al, salario, mínimo, y, acuerdo, con, empresarios
- Retiradas (stoplist o longitud): al, y, con
- Tras stoplist, sin stemming: aumento, salario, mínimo, acuerdo, empresarios
- Tokens finales: `aument` (df 6,098), `salari` (df 2,909), `minim` (df 1,885), `acuerd` (df 13,558), `empresari` (df 3,302)

## Q9: operación y apertura de sucursales del Banco del Bienestar

- Palabras originales: operación, y, apertura, de, sucursales, del, banco, del, bienestar
- Retiradas (stoplist o longitud): y, de, del, del
- Tras stoplist, sin stemming: operación, apertura, sucursales, banco, bienestar
- Tokens finales: `oper` (df 7,891), `apertur` (df 492), `sucursal` (df 1,127), `banc` (df 3,914), `bienest` (df 7,828)

## Q10: construcción y operación del Tren Interoceánico del Istmo de Tehuantepec

- Palabras originales: construcción, y, operación, del, tren, interoceánico, del, istmo, de, tehuantepec
- Retiradas (stoplist o longitud): y, del, del, de
- Tras stoplist, sin stemming: construcción, operación, tren, interoceánico, istmo, tehuantepec
- Tokens finales: `construccion` (df 5,648), `oper` (df 7,891), `tren` (df 5,261), `interocean` (df 288), `istmo` (df 1,241), `tehuantepec` (df 461)


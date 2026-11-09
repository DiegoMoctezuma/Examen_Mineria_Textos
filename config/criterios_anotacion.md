# Criterios de anotación de entidades

Aplican al gold, al conjunto de selección y al extractor. Se fijan antes de anotar y no cambian
después.

## Offsets

Los offsets son índices de carácter Python sobre el `texto` completo e inmutable del pasaje
(incluida la marca de interlocutor reinyectada): `inicio` inclusivo y `fin` exclusivo. Para toda
entidad: `0 <= inicio < fin <= len(texto)` y `texto[inicio:fin] == texto_entidad`.

## Tipos

| Tipo | Qué se anota | Convenciones |
| --- | --- | --- |
| PER | Nombres de funcionarios, empresarios, periodistas | Nombre completo presente en el texto como una sola entidad; se excluye el cargo adyacente: "secretario de Salud, Jorge Alcocer Varela" → `Jorge Alcocer Varela` |
| ORG | Dependencias, empresas, partidos, organismos internacionales, organizaciones empresariales | Nombre o sigla tal como aparece. Farmacéuticas y marcas de vacuna son ORG (D14). Entidad completa cuando contiene un lugar: ORG `Secretaría de Salud de Tabasco` sin LOC interno |
| LOC | Estados, municipios, países y obras con nombre propio | Tren Maya, AIFA, Dos Bocas, refinería Olmeca son LOC (enunciado, p. 3) |
| FECHA | Absolutas y relativas resolubles | Núcleo completo con modificador relativo cuando lo hay: `próximo 15 de enero`, `diciembre de 2021`, `15 de diciembre de 2023`; sin preposiciones ni artículos introductorios. `en 2019` → `2019` con precisión de año; un número de cuatro cifras sin contexto temporal no es FECHA. Un intervalo explícito (`del 1 al 15 de enero`) es una sola entidad; una enumeración produce entidades separadas |
| MONTO | Cantidades en pesos o dólares con su unidad | Incluye cifra, escala y moneda o símbolo: `20 mil millones de pesos`, `$1,200 millones`. No se recorta el `$`. Porcentajes, dosis, litros y elementos **no** son MONTO: van a cantidades auxiliares (D11) |

## Marca de interlocutor

Las entidades dentro de la marca de interlocutor se anotan igual que en el cuerpo:
`SECRETARIO DE SALUD, JORGE ALCOCER VARELA:` → PER `JORGE ALCOCER VARELA`. `PREGUNTA`,
`INTERLOCUTOR`, `INTERLOCUTORA` y otras marcas genéricas no contienen entidades. Así el gold mide
el efecto de las mayúsculas.

## Solapes y excepciones

Spans que no se contienen pueden coexistir. Cualquier excepción se escribe en esta guía antes de
cerrar el gold.

---

Fuente: propuesta del PRD §3.6 (con D11, D13 y D14), transcrita sin cambios a pedido del alumno
el 2026-11-08. Queda congelada con la etiqueta `reglas-congeladas` (D15), antes de abrir el gold.

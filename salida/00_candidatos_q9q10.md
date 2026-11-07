# Candidatos para Q9 y Q10

Señal calculada sobre `data/pasajes.parquet` (127 mil pasajes, cuerpo sin la marca de interlocutor, búsqueda sin acentos ni mayúsculas). **Esto no elige nada**: el alumno decide dos temas distintos entre sí y de Q1 a Q8, y redacta consulta, ventana y pregunta. La redacción final queda `[VALIDAR]`.

## Consultas obligatorias (no se tocan)

- Q1: avances en la construcción del Tren Maya (2020-01-01 a 2023-12-31)
- Q2: llegada y aplicación de vacunas contra el COVID-19 (2020-12-01 a 2021-12-31)
- Q3: refinería de Dos Bocas en Tabasco (2019-01-01 a 2022-12-31)
- Q4: aeropuerto Felipe Ángeles en Santa Lucía (2019-01-01 a 2022-06-30)
- Q5: programa Sembrando Vida y apoyo a campesinos (2019-01-01 a 2024-12-31)
- Q6: combate al huachicol y robo de combustible (2018-12-01 a 2019-06-30)
- Q7: pensión universal para adultos mayores (2018-12-01 a 2024-12-31)
- Q8: aumento al salario mínimo y acuerdo con empresarios (2018-12-01 a 2024-01-31)

## Resumen

| Candidato | Pasajes (todo el corpus) | Pasajes en ventana | Con 2 o más términos | Discursos en ventana |
| --- | ---: | ---: | ---: | ---: |
| Guardia Nacional | 8,850 | 3,183 | 752 | 670 |
| Insabi y sistema de salud | 3,353 | 1,827 | 153 | 496 |
| Tren Interoceánico del Istmo | 2,249 | 1,809 | 579 | 563 |
| Reforma eléctrica y litio | 3,427 | 1,049 | 90 | 294 |
| Aranceles y acuerdo migratorio con EUA | 9,181 | 721 | 91 | 118 |
| Banco del Bienestar | 1,284 | 1,096 | 617 | 494 |
| Mexicana de Aviación | 2,197 | 601 | 42 | 236 |
| Caso Ayotzinapa | 686 | 560 | 59 | 249 |

## Guardia Nacional

- Términos semilla: guardia nacional, despliegue, elementos
- Ventana sugerida: 2019-01-01 a 2020-12-31
- Pregunta sugerida: Qué dependencias la integran, en qué estados se despliega, cuántos elementos y qué fechas
- Pasajes por término (todo el corpus): `guardia nacional` 5,132, `despliegue` 599, `elementos` 5,419
- Discursos distintos: 1,579 en todo el corpus, 670 en la ventana
- Pasajes por año: 2018: 60, 2019: 1,710, 2020: 1,473, 2021: 1,573, 2022: 1,794, 2023: 1,404, 2024: 836

Ejemplos (primeros 300 caracteres del cuerpo):

- `1292_27` (2020-12-31): Con su permiso, señor presidente. Buenos días. Por parte de la Guardia Nacional los avances más importantes durante el presente año son los que voy a mostrar a continuación: En el rubro del despliegue, sí, la fuerza operativa que tiene la Guardia Nacional, en enero de este año tendríamos un efectivo
- `1292_28` (2020-12-31): coordinaciones que se tenían programadas para este año, entonces, llevamos 200 y quedan para el próximo año establecer 66 para llegar a la meta establecida de los primeros tres años, de tener 266 coordinaciones regionales de la Guardia Nacional. En cuestión del reclutamiento, que es lo que nos permi
- `1293_19` (2020-12-30): los efectos del frente frío. Muchas gracias, almirante. Gracias, además por la compañía que hicimos en la atención a los huracanes. La aplicación del Plan Marina COVID-19, provocada por la pandemia, a partir del 31 de marzo de 2020 dirigido a la población en casos y zonas de emergencia o desastre en

## Insabi y sistema de salud

- Términos semilla: insabi, seguro popular, medicamentos
- Ventana sugerida: 2019-06-01 a 2021-12-31
- Pregunta sugerida: Qué instituciones participan, qué funcionarios, qué montos y qué fechas de arranque
- Pasajes por término (todo el corpus): `insabi` 528, `seguro popular` 339, `medicamentos` 2,753
- Discursos distintos: 933 en todo el corpus, 496 en la ventana
- Pasajes por año: 2018: 14, 2019: 639, 2020: 958, 2021: 446, 2022: 570, 2023: 427, 2024: 299

Ejemplos (primeros 300 caracteres del cuerpo):

- `1067_7` (2021-08-18): existía el Seguro Popular, pero no era para todos y tenía que pagarse una cuota; hoy la pensión y los medicamentos son gratuitos para todas y todos los mexicanos que la soliciten. Pero aclaramos, el Coneval hizo dos preguntas sobre salud en una encuesta sobre pobreza multidimensional: Una, pregunta 
- `1547_24` (2020-05-15): hice una gira por 80 hospitales del programa IMSS-Bienestar, que son los hospitales que atienden a la población más pobre de México, están ubicados en las zonas más marginadas. Se decidió… Bueno, el otro tema el cuarto fue el compromiso de regularizar la situación laboral de los trabajadores de la s
- `1689_52` (2020-01-21): Muchas gracias, presidente. Buenos días. Yo tengo dos preguntas. Una ya usted refería, que hay que dejar que los plazos se venzan en cuestión de los estados, pero hay una situación que creo que sí es importante que el gobierno federal esté responsabilizándose. A los estados hubo si no mal recuerdo… 

## Tren Interoceánico del Istmo

- Términos semilla: interoceanico, istmo, salina cruz, coatzacoalcos
- Ventana sugerida: 2020-01-01 a 2024-06-30
- Pregunta sugerida: Qué dependencias y empresas, qué lugares conecta, qué montos y fechas de inauguración
- Pasajes por término (todo el corpus): `interoceanico` 283, `istmo` 1,242, `salina cruz` 808, `coatzacoalcos` 989
- Discursos distintos: 741 en todo el corpus, 563 en la ventana
- Pasajes por año: 2018: 19, 2019: 268, 2020: 256, 2021: 337, 2022: 465, 2023: 568, 2024: 336

Ejemplos (primeros 300 caracteres del cuerpo):

- `228_7` (2024-01-24): ‘Para servir a México debemos demostrar que la modernidad puede ser forjada desde abajo y sin excluir a nadie, y que el desarrollo no tiene por qué ser contrario a la justicia social’, licenciado Andrés Manuel López Obrador, presidente constitucional de los Estados Unidos Mexicanos y comandante supr
- `256_13` (2023-12-22): Chivela con la parte más norte de la ruta utilizando el río Coatzacoalcos. Diversas expediciones para construir un canal interoceánico, incluso utilizando el río Grijalva como canal natural, el cual implicaba ser la entrada por el río Mezcalapa en Tabasco, y la conexión al Pacifico a través del río 
- `256_20` (2023-12-22): Como ya hemos informado en otras ocasiones, el proyecto del Corredor Interoceánico es un proyecto prioritario del Gobierno de México por las razones que ya se han expuesto, esto implica la rehabilitación de mil 197 kilómetros de vías férreas en tres líneas. También vamos a modernizar cuatro puertos:

## Reforma eléctrica y litio

- Términos semilla: reforma electrica, litio, cfe, generacion
- Ventana sugerida: 2021-09-01 a 2022-12-31
- Pregunta sugerida: Qué organizaciones, qué funcionarios, qué porcentajes y montos
- Pasajes por término (todo el corpus): `reforma electrica` 256, `litio` 325, `cfe` 569, `generacion` 2,488
- Discursos distintos: 1,161 en todo el corpus, 294 en la ventana
- Pasajes por año: 2018: 9, 2019: 431, 2020: 364, 2021: 672, 2022: 750, 2023: 632, 2024: 569

Ejemplos (primeros 300 caracteres del cuerpo):

- `869_6` (2022-03-09): menos recursos por parte de la Secretaría de Hacienda y Crédito Público para subsidiar tarifas eléctricas. Esto lo dice México Evalúa, pero es falso. La Comisión Federal de Electricidad tuvo un déficit debido al incremento de precios en la energía eléctrica provocado por una onda invernal ártica que
- `869_7` (2022-03-09): darle prioridad a la generación de electricidad de la empresa paraestatal, como plantea la contrarreforma eléctrica, los costos aumentarán. Además, se desconoce si los consumidores lo pagarán vía tarifas eléctricas o los contribuyentes a través de subsidios. Ambos argumentos que utiliza la organizac
- `933_33` (2021-12-21): En una segunda pregunta quisiera saber, en caso de ser aprobada la reforma eléctrica, me gustaría saber cómo funcionaría lo del litio. ¿Se haría una empresa que dependiera de la Comisión Federal de Electricidad o sería una empresa aparte de la Pemex y de la CFE?

## Aranceles y acuerdo migratorio con EUA

- Términos semilla: aranceles, trump, guardia, migrantes
- Ventana sugerida: 2019-05-01 a 2019-07-31
- Pregunta sugerida: Qué países y funcionarios, qué porcentajes, qué fechas y cifras de migrantes
- Pasajes por término (todo el corpus): `aranceles` 238, `trump` 1,100, `guardia` 5,877, `migrantes` 2,372
- Discursos distintos: 1,686 en todo el corpus, 118 en la ventana
- Pasajes por año: 2018: 53, 2019: 2,026, 2020: 1,419, 2021: 1,533, 2022: 1,691, 2023: 1,434, 2024: 1,025

Ejemplos (primeros 300 caracteres del cuerpo):

- `1948_7` (2019-07-23): Hay recursos suficientes para albergues y la atención a migrantes. Cuando se creó el equipo para cumplir los compromisos que se hicieron con el gobierno de Estados Unidos y evitar que nos aplicaran aranceles se integró un equipo que lo coordina Marcelo Ebrard y que tiene cuatro áreas o cinco. Tiene 
- `1949_69` (2019-07-22): Presidente de México, muy buenos días; secretario, procurador. Su servidor Carlos Pozos, de la revista Petróleo y Energía. Señor secretario. El 62 por ciento de reducción de migrantes desde su óptica de vista, ¿pasamos la prueba -esa sería mi pregunta- pasamos la prueba que nos quiere imponer el pre
- `1972_4` (2019-07-09): Gracias, buenos días. A propósito de los policías federales, ¿ha habido algún gobernador interesado en que los efectivos que no pasen la prueba la para la Guardia Nacional, pero que quieran seguir en activo, por así denominarlo, pudieran ser trasladados a los estados en donde, por ejemplo, no hay po

## Banco del Bienestar

- Términos semilla: banco del bienestar, sucursales
- Ventana sugerida: 2019-01-01 a 2023-12-31
- Pregunta sugerida: Qué institución, cuántas sucursales, en qué estados, con qué montos
- Pasajes por término (todo el corpus): `banco del bienestar` 1,046, `sucursales` 940
- Discursos distintos: 560 en todo el corpus, 494 en la ventana
- Pasajes por año: 2019: 198, 2020: 242, 2021: 188, 2022: 197, 2023: 271, 2024: 188

Ejemplos (primeros 300 caracteres del cuerpo):

- `243_18` (2023-01-06): Vamos también a seguir entregando todos los apoyos a través de las sucursales del Banco del Bienestar. Aquí me acompaña el general Loza, que es el director de los ingenieros militares. Ellos nos han ayudado mucho, porque no sólo nos apoyan para garantizar la paz, la tranquilidad en el país, sino que
- `243_19` (2023-01-06): año pasado, antepasado, padeció mucho de una sequía y ahora se hizo un acueducto para llevarle cinco mil litros por segundo, ya no van a padecer por falta de agua. Y ese acueducto estuvo a cargo de los ingenieros militares. Y ellos, entre otras cosas, nos ayudaron a construir, ya terminamos, dos mil
- `243_20` (2023-01-06): Bienestar, porque llega hasta los pueblos más apartados. Nada más voy a buscar aquí el dato para que tengamos presente. ¿Saben cuántas sucursales del Banco del Bienestar se edificaron en el estado de Puebla? Doscientas treinta y cinco sucursales del Banco del Bienestar. Si son 217 municipios, quiere

## Mexicana de Aviación

- Términos semilla: mexicana de aviacion, aerolinea, marca
- Ventana sugerida: 2023-01-01 a 2024-06-30
- Pregunta sugerida: Qué dependencias, qué montos de compra, qué fechas y rutas
- Pasajes por término (todo el corpus): `mexicana de aviacion` 116, `aerolinea` 188, `marca` 1,953
- Discursos distintos: 940 en todo el corpus, 236 en la ventana
- Pasajes por año: 2018: 13, 2019: 360, 2020: 378, 2021: 391, 2022: 366, 2023: 418, 2024: 271

Ejemplos (primeros 300 caracteres del cuerpo):

- `382_2` (2023-08-10): la Coalición de Empleados de Confianza. Les damos la bienvenida a este espacio. Informar que hoy se alcanza un acuerdo histórico para lograr justicia a siete mil 407 trabajadores y trabajadoras de Mexicana de Aviación, pilotos, sobrecargos, personal de tierra, trabajadores de confianza y jubilados, 
- `382_3` (2023-08-10): quiebra a la que fuera la aerolínea más importante de México. En agosto de 2010 se anunció la suspensión indefinida de la venta de boletos. Y el 28 de agosto suspendieron sus operaciones aéreas debido a las diferentes deudas para después proceder al concurso mercantil, dejando en el desamparo a ocho
- `405_48` (2023-06-28): ‘Las mujeres que luchan’. Ahí, enfrente hay un hotel, y ese era de este Gascón, Gastón Azcárraga, del Grupo Posadas, y apoyaba a Fox, y en ese hotel se hospedaba Fox cuando era candidato, y era apoyador de Fox. Cuando Fox llega a la Presidencia, le entrega Mexicana, que era una empresa pública, ahí 

## Caso Ayotzinapa

- Términos semilla: ayotzinapa, normalistas, comision de la verdad
- Ventana sugerida: 2018-12-01 a 2023-12-31
- Pregunta sugerida: Qué organismos y funcionarios, qué fechas y qué lugares
- Pasajes por término (todo el corpus): `ayotzinapa` 621, `normalistas` 100, `comision de la verdad` 33
- Discursos distintos: 301 en todo el corpus, 249 en la ventana
- Pasajes por año: 2018: 7, 2019: 101, 2020: 106, 2021: 66, 2022: 153, 2023: 127, 2024: 126

Ejemplos (primeros 300 caracteres del cuerpo):

- `680_46` (2022-08-31): Presidente, sobre justo la no repetición de estos crímenes, en el caso del crimen de Estado de Ayotzinapa, en este informe que presentó la Comisión de la Verdad y que están importante y con tantas revelaciones, destacar el caso de seis jueces, un tribunal de distrito y una magistrada, que se mencion
- `697_69` (2022-08-19): Bueno, okey. Bueno, sobre la conclusión de la Comisión de la Verdad sobre el caso Ayotzinapa, que determina fue un crimen de Estado, presidente. Si con esta conclusión quedaría ya cubierto uno de los compromisos que usted hizo en el Zócalo capitalino o faltaría todavía la extradición de Tomás Zerón,
- `258_76` (2023-12-21): Pero esa desinformación que le han pasado es verificable, y usted puede comprobar que no. Por eso le decía la importancia de hablar con estas organizaciones o personas. En el caso del Centro Prodh, por ejemplo, el Centro Prodh nunca, nunca hasta la fecha asumió ninguna defensa legal o jurídica con l

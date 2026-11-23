# Candidatos para Q11 a Q15

Señal calculada sobre `data/pasajes.parquet` (127 mil pasajes, cuerpo sin la marca de interlocutor, búsqueda sin acentos ni mayúsculas). **Esto no elige nada**: el alumno decide cinco temas distintos entre sí y de Q1 a Q10, con al menos uno de nombre alterno (D25), y redacta consulta, ventana y pregunta. La redacción final queda `[VALIDAR]`.

## Consultas obligatorias (no se tocan)

- Q1: avances en la construcción del Tren Maya (2020-01-01 a 2023-12-31)
- Q2: llegada y aplicación de vacunas contra el COVID-19 (2020-12-01 a 2021-12-31)
- Q3: refinería de Dos Bocas en Tabasco (2019-01-01 a 2022-12-31)
- Q4: aeropuerto Felipe Ángeles en Santa Lucía (2019-01-01 a 2022-06-30)
- Q5: programa Sembrando Vida y apoyo a campesinos (2019-01-01 a 2024-12-31)
- Q6: combate al huachicol y robo de combustible (2018-12-01 a 2019-06-30)
- Q7: pensión universal para adultos mayores (2018-12-01 a 2024-12-31)
- Q8: aumento al salario mínimo y acuerdo con empresarios (2018-12-01 a 2024-01-31)
- Q9: operación y apertura de sucursales del Banco del Bienestar (2019-01-01 a 2023-12-31)
- Q10: construcción y operación del Tren Interoceánico del Istmo de Tehuantepec (2020-01-01 a 2024-06-30)

## Resumen

| Candidato | Pasajes (todo el corpus) | Pasajes en ventana | Con 2 o más términos | Discursos en ventana |
| --- | ---: | ---: | ---: | ---: |
| Guardia Nacional | 8,850 | 3,183 | 752 | 670 |
| Insabi e IMSS-Bienestar (nombre alterno) | 2,241 | 2,155 | 153 | 601 |
| Rifa y venta del avión presidencial (TP-01, "José María Morelos y Pavón") | 1,580 | 1,385 | 105 | 623 |
| Segalmex (Seguridad Alimentaria Mexicana), Diconsa y Liconsa | 303 | 300 | 76 | 140 |
| Caso Ayotzinapa (43 normalistas de Iguala) | 932 | 932 | 124 | 385 |
| Nacionalización del litio (LitioMx) | 4,021 | 1,873 | 88 | 425 |
| Reforma eléctrica y CFE | 4,985 | 1,400 | 152 | 332 |
| Aranceles y acuerdo migratorio con Estados Unidos (2019) | 3,536 | 491 | 51 | 94 |
| Jóvenes Construyendo el Futuro | 1,439 | 1,421 | 334 | 773 |
| Huracán Otis en Acapulco | 2,334 | 941 | 228 | 120 |
| Mexicana de Aviación | 4,113 | 1,306 | 105 | 375 |
| Operativo de Culiacán y Ovidio Guzmán ("culiacanazo", nombre alterno) | 729 | 578 | 24 | 242 |

## Guardia Nacional

- Términos semilla: guardia nacional, despliegue, elementos
- Ventana sugerida: 2019-01-01 a 2020-12-31
- Pregunta sugerida: Qué dependencias la integran, en qué estados se despliega, cuántos elementos y qué fechas
- Pasajes por término (todo el corpus): `guardia nacional` 5,132, `despliegue` 599, `elementos` 5,419
- Discursos distintos: 1,579 en todo el corpus, 670 en la ventana
- Pasajes por año: 2018: 60, 2019: 1,710, 2020: 1,473, 2021: 1,573, 2022: 1,794, 2023: 1,404, 2024: 836

Ejemplos al azar de la ventana, sin pasajes del gold (primeros 300 caracteres):

- `1507_37` (2020-06-24): el servicio eléctrico en todo el territorio, 139 personas albergadas en 12 albergues, cuatro daños a la infraestructura carretera, un evento en una instalación estratégica, que es la refinería ‘Antonio Dovalí Jaime’ donde tuvimos un conato de incendio que los compañeros de Petróleos Mexicanos atendi
- `1551_73` (2020-05-11): rango supremo y ahí sí la economía asunto de los economistas, como si fuese algo tan complejo, inalcanzable. ¿Cómo le hace la gente para estirar su presupuesto? Esos sí son buenos economistas, sobre todo las mujeres que reciben el salario y hacen milagros. ¿Qué economistas buenos pueden ser estos te
- `2160_2` (2019-03-07): Son muy buenos los dos y son mujeres, porque ahora ya para el béisbol y todos los deportes están participando muchas mujeres y eso es muy bueno. Entonces, el equipo va muy bien, tenemos nueve elementos y tenemos buena banca, buen picheo de relevo, buen manager. Vamos bien. Vamos a ganar la temporada

## Insabi e IMSS-Bienestar (nombre alterno)

- Términos semilla: insabi, imss-bienestar, imss bienestar, seguro popular
- Ventana sugerida: 2019-06-01 a 2024-09-30
- Pregunta sugerida: Qué instituciones participan, en qué estados, qué funcionarios, qué montos y qué fechas
- Pasajes por término (todo el corpus): `insabi` 528, `imss-bienestar` 1,498, `imss bienestar` 31, `seguro popular` 339
- Discursos distintos: 653 en todo el corpus, 601 en la ventana
- Pasajes por año: 2018: 1, 2019: 483, 2020: 424, 2021: 145, 2022: 402, 2023: 395, 2024: 391

Ejemplos al azar de la ventana, sin pasajes del gold (primeros 300 caracteres):

- `650_3` (2022-10-04): Nayarit, en Colima 55, en Campeche 54, en Baja California Sur 30, en Zacatecas 10, en Sonora 17, en Oaxaca 61, en Veracruz siete y en Tlaxcala 26 médicas y médicos especialistas cubanos. El 13 de octubre arribarán 84 más, para llegar a un total de 436. Agradecer al Ministerio de Salud y a la Agencia
- `1552_38` (2020-05-08): desde luego que lo cobraron, pero eso ya corresponde investigarlo a ustedes. De todas maneras ellos, los exsecretarios de Salud, tienen todo el derecho de opinar, de manifestarse, de criticar, de disentir, pero es la gente la que tiene que opinar sobre esto. Yo decía, lo voy a repetir, que eso que l
- `1859_67` (2019-09-17): Estamos en eso. Y vamos a seguir insistiendo en la necesidad de que se limpie el Poder Judicial, pero con respeto a su autonomía, ellos mismos van a tener que emprender este proceso de renovación. Yo tengo confianza en el presidente de la Suprema Corte de Justicia. Y creo que van a ellos a ser recep

## Rifa y venta del avión presidencial (TP-01, "José María Morelos y Pavón")

- Términos semilla: avion presidencial, rifa, tp-01, jose maria morelos
- Ventana sugerida: 2018-12-01 a 2023-06-30
- Pregunta sugerida: Qué dependencias y compradores, qué montos, qué fechas y dónde estuvo el avión
- Pasajes por término (todo el corpus): `avion presidencial` 620, `rifa` 962, `tp-01` 7, `jose maria morelos` 101
- Discursos distintos: 726 en todo el corpus, 623 en la ventana
- Pasajes por año: 2018: 6, 2019: 486, 2020: 391, 2021: 227, 2022: 204, 2023: 136, 2024: 130

Ejemplos al azar de la ventana, sin pasajes del gold (primeros 300 caracteres):

- `729_90` (2022-07-20): Donald Trump, el trato. El presidente Biden siempre menciona su respeto a nuestra soberanía y siempre habla de que el trato entre México y Estados Unidos lo considera en pie de igualdad, siempre. Pero ellos tienen estos datos, no así Iberdrola. Bueno, también tiene los datos, nada más que ellos está
- `877_84` (2022-02-28): A ver, tráemelo. ¿Cuál es? Ah, no, este me sirve mucho. Bueno, ahora es muy importante que nos ayuden, que nos sigan ayudando. Es un terreno —ya conocen ustedes la historia— que compraron en el gobierno de Calderón, que lo pagaron en 120 millones de dólares, en Fonatur. Se llama Playa Espíritu, en S
- `1918_12` (2019-08-09): compensaciones, y de ahí para abajo. ¿Para qué estamos bajando arriba los sueldos? Porque vamos a aumentar los sueldos de los de abajo. Bajamos los ingresos de los de arriba para aumentarle a los de abajo. Justicia laboral. También ya no hay pensión para los expresidentes. ¿Saben cuánto se entregaba

## Segalmex (Seguridad Alimentaria Mexicana), Diconsa y Liconsa

- Términos semilla: segalmex, seguridad alimentaria mexicana, diconsa, liconsa
- Ventana sugerida: 2019-01-01 a 2024-09-30
- Pregunta sugerida: Qué organismos y funcionarios, qué montos del desfalco, qué fechas y qué lugares
- Pasajes por término (todo el corpus): `segalmex` 179, `seguridad alimentaria mexicana` 8, `diconsa` 136, `liconsa` 84
- Discursos distintos: 143 en todo el corpus, 140 en la ventana
- Pasajes por año: 2018: 3, 2019: 112, 2020: 26, 2021: 15, 2022: 54, 2023: 69, 2024: 24

Ejemplos al azar de la ventana, sin pasajes del gold (primeros 300 caracteres):

- `948_20` (2021-12-07): Con su permiso, señor presidente. Muy buenos días a todas y todos ustedes, los saludo con mucho afecto, ingeniero Enrique Alfaro, a todos a quienes nos siguen por los diferentes medios de comunicación. Como cada semana, continuamos con la actualización en la distribución de medicamentos adquiridos p
- `1814_14` (2019-10-15): 400 pesos mensuales, de acuerdo al informe que me están entregando. Y hay 250 jóvenes de Pinos que no estudiaban ni tenían empleo y que están contratados, trabajando como aprendices en el programa Jóvenes Construyendo el Futuro, y se les está pagando tres mil 600 pesos mensuales, capacitándose en em
- `2013_9` (2019-06-16): una depuración de esos padrones, porque también lo que queremos es que el apoyo llegue de manera directa, personalizada, ya no a través de intermediarios. Nada de que: ‘Soy de la organización Francisco Villa y dame a mí el dinero y yo voy a entregarlo a la gente’. No, primo hermano, eso ya se acabó.

## Caso Ayotzinapa (43 normalistas de Iguala)

- Términos semilla: ayotzinapa, normalistas, comision de la verdad, iguala
- Ventana sugerida: 2018-12-01 a 2024-09-30
- Pregunta sugerida: Qué organismos y funcionarios, qué fechas y qué lugares
- Pasajes por término (todo el corpus): `ayotzinapa` 621, `normalistas` 100, `comision de la verdad` 33, `iguala` 316
- Discursos distintos: 385 en todo el corpus, 385 en la ventana
- Pasajes por año: 2018: 8, 2019: 125, 2020: 132, 2021: 110, 2022: 207, 2023: 157, 2024: 193

Ejemplos al azar de la ventana, sin pasajes del gold (primeros 300 caracteres):

- `79_105` (2024-07-26): ese hecho, que es un indicio de delincuencia organizada, se solicita la orden de aprehensión contra este coronel. Pero resulta que esa grabación, además, que no pertenece a Iguala, sino a Altamirano —quienes son de Guerrero saben las diferencias que hay entre Iguala y Altamirano—, se da esa grabació
- `1171_5` (2021-04-26): en 19 pesos con nueve centavos en Charcas; San Luis Potosí en 19 pesos con 85 centavos; los más caros, en Iguala de la Independencia, Guerrero, en 23 pesos con 20 centavos y en Santa María Tonameca, Oaxaca, en 23 pesos con un centavo. Continuamos monitoreando las condiciones en las que se encuentran
- `1845_2` (2019-09-26): Con su autorización, señor presidente. Bueno, hoy, al cumplirse el quinto aniversario de estos lamentables hechos de la noche del 24 y 25 de septiembre de 2014 en la ciudad de Iguala, vamos a hacer un proceso de rendición de cuentas, no solamente en esta conferencia de prensa. El día de hoy se trans

## Nacionalización del litio (LitioMx)

- Términos semilla: litio, litiomx, sonora
- Ventana sugerida: 2021-10-01 a 2023-12-31
- Pregunta sugerida: Qué organismos y empresas, en qué estados, qué montos y qué fechas
- Pasajes por término (todo el corpus): `litio` 325, `litiomx` 3, `sonora` 3,810
- Discursos distintos: 992 en todo el corpus, 425 en la ventana
- Pasajes por año: 2018: 3, 2019: 448, 2020: 660, 2021: 786, 2022: 981, 2023: 705, 2024: 438

Ejemplos al azar de la ventana, sin pasajes del gold (primeros 300 caracteres):

- `758_30` (2022-06-23): Se está trabajando mucho en Sonora, hay un grupo especial para garantizar la paz, la tranquilidad en Sonora. Yo creo que Ricardo tiene información que ahora va a transmitir. Y sí nos está preocupando y ocupando el caso de Sonora en violencia, pero sí se está atendiendo. A ver si puedes informar.
- `856_38` (2022-03-23): Presidente, en otro tema, si bien el lunes fijó una postura sobre los señalamientos del exconsejero jurídico Julio Scherer, usted dijo que era un asunto jurídico y que no se iba a meter; sin embargo, son personajes de su entorno más cercano. Esto, por un lado. Y dos, aprovechando que está un tema de
- `933_34` (2021-12-21): Lo estamos analizando. Acerca del litio, sí ya ha quedado muy claro de que no queremos que se privatice, tiene que quedar como un mineral de la nación, no se van a entregar concesiones ni contratos para la explotación del litio, lo va a manejar el Estado mexicano, tenemos nada más que ver qué instit

## Reforma eléctrica y CFE

- Términos semilla: reforma electrica, cfe, comision federal de electricidad, generacion
- Ventana sugerida: 2021-09-01 a 2022-12-31
- Pregunta sugerida: Qué organizaciones, qué funcionarios, qué porcentajes y montos
- Pasajes por término (todo el corpus): `reforma electrica` 256, `cfe` 569, `comision federal de electricidad` 2,232, `generacion` 2,488
- Discursos distintos: 1,365 en todo el corpus, 332 en la ventana
- Pasajes por año: 2018: 14, 2019: 814, 2020: 640, 2021: 981, 2022: 998, 2023: 776, 2024: 762

Ejemplos al azar de la ventana, sin pasajes del gold (primeros 300 caracteres):

- `613_36` (2022-11-11): año y en noviembre se tendrá la primera caja terminada. Y el primer tren se entregará el 9 de julio del 2023 para el inicio de las pruebas de rodamiento en los talleres de Cancún, Quintana Roo. El Tren Maya ofrecerá servicio a pasajeros locales, turistas y transporte de carga. Con el Tren Maya habrá
- `826_2` (2022-05-01): el capital, las empresas, en los últimos tiempos la tecnología, llegaron a plantear que con el avance de la tecnología, con la robótica, con la automatización, ya ni se iba a utilizar la fuerza de trabajo. Nosotros pensamos distinto. Si no hay trabajadores, no hay desarrollo; si no hay trabajadores,
- `836_57` (2022-04-21): Cuando ellos quieran pueden venir. Y también hay que cuidar, como decía don Adolfo Ruiz Cortines, la investidura. Sería una reunión con ellos, ahí sí no podrían estar ustedes; después sí, que ellos les declaren. Porque yo tengo que defender el proyecto de transformación y no me puedo exponer. Porque

## Aranceles y acuerdo migratorio con Estados Unidos (2019)

- Términos semilla: aranceles, trump, migrantes, acuerdo migratorio
- Ventana sugerida: 2019-05-01 a 2019-07-31
- Pregunta sugerida: Qué países y funcionarios, qué porcentajes, qué fechas y cifras de migrantes
- Pasajes por término (todo el corpus): `aranceles` 238, `trump` 1,100, `migrantes` 2,372, `acuerdo migratorio` 8
- Discursos distintos: 1,063 en todo el corpus, 94 en la ventana
- Pasajes por año: 2018: 25, 2019: 1,028, 2020: 522, 2021: 454, 2022: 479, 2023: 560, 2024: 468

Ejemplos al azar de la ventana, sin pasajes del gold (primeros 300 caracteres):

- `1963_11` (2019-07-14): justicia no tiene nada que temer. Pero imagínense cuántos ahorros, ya no hay aviones privados, helicópteros privados. Calderón le compró a Peña un avión, se lo dejó comprado, de 25 metros de ancho, por 70 de largo, para 280 pasajeros. Nada más piensen en un autobús grande, cuando mucho se trasladan 
- `2037_5` (2019-05-31): creo que va a haber una rectificación, si no de inmediato, la tiene que haber, porque estas medidas no convienen a los mexicanos, pero tampoco a los estadounidenses. Esa es mi apreciación. Y los gobernantes tenemos que hacerles caso a los ciudadanos, tenemos que escuchar la voz de los ciudadanos, la
- `2038_33` (2019-05-30): Sí. No podíamos nosotros, no podíamos dar un paso hacia adelante, este paso definitivo, si no hubiese habido esta decisión de quitar los aranceles, que ayuda mucho a la industria y significa inversión y significa empleos, en una circunstancia mundial que ustedes ya conocen de predominio en el discur

## Jóvenes Construyendo el Futuro

- Términos semilla: jovenes construyendo el futuro, aprendices, becarios
- Ventana sugerida: 2019-01-01 a 2024-09-30
- Pregunta sugerida: Qué dependencias y empresas, cuántos jóvenes, qué montos de beca y en qué estados
- Pasajes por término (todo el corpus): `jovenes construyendo el futuro` 990, `aprendices` 677, `becarios` 109
- Discursos distintos: 782 en todo el corpus, 773 en la ventana
- Pasajes por año: 2018: 18, 2019: 516, 2020: 226, 2021: 184, 2022: 182, 2023: 198, 2024: 115

Ejemplos al azar de la ventana, sin pasajes del gold (primeros 300 caracteres):

- `119_58` (2024-06-21): los pueblos, en los lugares apartados. A ver si no te mandan el número de bancos que hay, sobre todo las sucursales. Entonces, como por primera vez en mucho tiempo se entregan los fondos de manera directa a los beneficiarios de Programas de Bienestar, necesitábamos tener oficinas, sucursales del Ban
- `493_40` (2023-03-13): abandonan la escuela porque todos los estudiantes de nivel medio superior tienen su beca, cuatro millones 500 mil, y estamos entregando en total 11 millones de becas para estudiantes de familias pobres. Y ya son dos millones 500 mil jóvenes que están trabajando como aprendices; que el que no estudia
- `1286_15` (2021-01-08): tenían tampoco posibilidad de trabajo y por eso muchos tomaron el camino de las conductas antisociales. Ahora hay becas para que estudien los hijos de campesinos, de obreros, de familias humildes, que nadie se quede con la oportunidad de estudiar. Y también hay oportunidad de trabajo, existe el prog

## Huracán Otis en Acapulco

- Términos semilla: otis, acapulco, huracan
- Ventana sugerida: 2023-10-20 a 2024-06-30
- Pregunta sugerida: Qué dependencias, qué lugares, qué montos de apoyo y qué fechas
- Pasajes por término (todo el corpus): `otis` 462, `acapulco` 1,346, `huracan` 883
- Discursos distintos: 740 en todo el corpus, 120 en la ventana
- Pasajes por año: 2018: 3, 2019: 205, 2020: 284, 2021: 281, 2022: 284, 2023: 816, 2024: 461

Ejemplos al azar de la ventana, sin pasajes del gold (primeros 300 caracteres):

- `259_8` (2023-12-20): tipo de acciones, tenemos tres drones, como lo dije anteriormente, una ecosonda transportada en una embarcación menor, 60 buzos han estado operando y a la fecha llevamos 982 inmersiones para la búsqueda que estamos realizando. Las embarcaciones localizadas desde el día 2 de noviembre al 19 de diciem
- `273_12` (2023-12-08): de Bienestar para saber en dónde está el módulo más cercano a su domicilio. ¿Qué hay que presentar para el registro? Identificación oficial con fotografía vigente, el acta de nacimiento legible, la CURP, el comprobante de domicilio y, muy importante también, dejarnos un número de teléfono para que a
- `298_34` (2023-11-13): 48 fallecidos, y de los desaparecidos o personas no localizadas ya sólo falta por localizar 26. ¿Por qué no hubo tantas desgracias? Desde luego, uno que pierda la vida duele. Pero ¿a qué se atribuye esto, si fue un huracán fuertísimo y que además entra por la bahía, por una zona muy poblada de un mi

## Mexicana de Aviación

- Términos semilla: mexicana de aviacion, aerolinea, mexicana
- Ventana sugerida: 2023-01-01 a 2024-09-30
- Pregunta sugerida: Qué dependencias, qué montos de compra, qué fechas y qué rutas
- Pasajes por término (todo el corpus): `mexicana de aviacion` 116, `aerolinea` 188, `mexicana` 3,991
- Discursos distintos: 1,256 en todo el corpus, 375 en la ventana
- Pasajes por año: 2018: 15, 2019: 599, 2020: 795, 2021: 633, 2022: 765, 2023: 762, 2024: 544

Ejemplos al azar de la ventana, sin pasajes del gold (primeros 300 caracteres):

- `240_37` (2024-01-09): oficial mexicana.gob.mx hasta el mes de junio de este año. Estos 14 días de operaciones han permitido conocer que los destinos con mayor demanda son, podemos ver, en tercer lugar, Mérida, con 344 pasajeros; en segundo lugar, Tijuana con 421, y en primer lugar Tulum con 738 pasajeros. Cabe resaltar q
- `382_10` (2023-08-10): reservaciones, mecánicos, tienen experiencia y la nueva línea aérea, Mexicana de Aviación, los necesita. Nos da muchísimo gusto que ahora, después de muchos años, cuando ustedes vuelvan y levanten la cara, y vean un avión y sepan que ese avión es de Mexicana de Aviación. Y solamente se fue a la hist
- `517_38` (2023-02-16): para que ya no llegaran los patos, los pájaros, las aves. ¿Dónde estaban? ¿Cuántos amparos se presentaron? Ninguno. ¿Saben cuántos amparos se han presentado en la construcción del Tren Maya? Cincuenta, más los que se acumulen. En la construcción del aeropuerto ‘Felipe Ángeles’, también como 50. Crea

## Operativo de Culiacán y Ovidio Guzmán ("culiacanazo", nombre alterno)

- Términos semilla: culiacan, ovidio, culiacanazo
- Ventana sugerida: 2019-10-17 a 2023-06-30
- Pregunta sugerida: Qué fuerzas y funcionarios, qué lugares, qué fechas y cuántos elementos
- Pasajes por término (todo el corpus): `culiacan` 655, `ovidio` 96, `culiacanazo` 5
- Discursos distintos: 325 en todo el corpus, 242 en la ventana
- Pasajes por año: 2019: 153, 2020: 116, 2021: 84, 2022: 144, 2023: 154, 2024: 78

Ejemplos al azar de la ventana, sin pasajes del gold (primeros 300 caracteres):

- `1043_9` (2021-09-10): entregando becas a estudiantes de familias de escasos recursos económicos. Se va a seguir apoyando al campo con los Precios de Garantía. Vamos a continuar con el programa Sembrando Vida. Vamos también a seguir mejorando la situación económica, social, de todo el pueblo de Sinaloa con obras de infrae
- `1788_20` (2019-11-01): otro sentido, él está aquí, en la Ciudad de México, aquí coordina los esfuerzos; él no participó en la operación en Culiacán. Quien llevaba el mando o quien realizó es otro elemento militar, pero que ese obviamente no podemos dar el nombre porque hay una investigación de por medio y para el debido p
- `1810_25` (2019-10-18): Gracias, señor presidente. Secretario, gobernador, compañeros. Buenos días. Arturo Paramo, Grupo Imagen. Sobre el tema de Culiacán. Si nos pudiese precisar, por favor, quién fue el que tomó la orden o quienes fueron los que tomaron la orden de liberar al hijo de Joaquín Guzmán Loera. ¿Fue alguno de 

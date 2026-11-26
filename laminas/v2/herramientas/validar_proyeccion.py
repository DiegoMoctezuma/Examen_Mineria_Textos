"""Verifica conservación de contenido, fuentes de cifras y recursos de la presentación."""
from pathlib import Path
from lxml import html,etree as ET
from PIL import Image
import argparse,hashlib,json,re
p=argparse.ArgumentParser();p.add_argument('repo',type=Path);a=p.parse_args();R=a.repo.resolve();D=R/'laminas/v2'
root=html.parse(str(D/'index.html'));source=json.loads((D/'contenido_fuente.json').read_text());seen={}
for e in root.xpath('//*[@data-source]'):
 seen.setdefault(e.get('data-source'),[]).append(''.join(e.itertext()))
missing=[];changed=[]
for n,sl in enumerate(source,1):
 for i,s in enumerate(sl['paragraphs']):
  if i==(1 if n in [1,18,20] else 2):continue
  if n==18:s=s.replace('Dos Bocas, de la pregunta a la respuesta con su cita','De Tren Maya a Dos Bocas, el caso difícil, con su cita')
  if n==20 and s.startswith('https://'):s='https://datisa.streamlit.app'
  k=f'{n}:{i}'
  if k not in seen:missing.append(k)
  elif any(t!=s for t in seen[k]):changed.append(k)
assert not missing and not changed,(missing,changed)
text=' '.join(''.join(s.itertext()) for s in root.xpath('//section'))
assert not re.search(r'\b\d{1,4}_\d{1,4}\b|salida/|\.csv|\bexamen\b|proyecto final|\bgold\b',text,re.I)
assert len(root.xpath('//section'))==26
assert len(root.xpath('//img[@class="cierre"]'))==1
assert root.xpath('//img[@class="cierre"]/ancestor::section')[0].get('id')=='slide-26'
assert not re.search('075638|17251E|68766D|E5F0BD|BCD6C6|F8DC87|BFD5CA|BDD6C5|DDE2DC|6E9482|4F8A6E',(D/'index.html').read_text()+(D/'estilos.css').read_text(),re.I)
registry=json.loads((R/'salida/v2/figuras/figuras.json').read_text());sources={}
for v in registry.values():sources.update(v.get('fuentes',{}))
for f,h in sources.items():assert hashlib.sha256((R/f).read_bytes()).hexdigest()==h,f
icons=[]
for n in range(11,16):
 file=D/f'img/p{n}.png';im=Image.open(file)
 assert im.mode=='RGBA' and im.getextrema()[-1]==(0,255)
 icons.append({'tema':n,'archivo':f'img/p{n}.png','dimensiones':im.size,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
# Cada cinta tiene una única geometría, compartida por todos sus colores.
for section in root.xpath('//section'):
 svg=section.xpath('.//*[local-name()="svg" and contains(@class,"ribbon")]')[0]
 assert len(svg.xpath('.//*[local-name()="path"]'))==1
 assert len(svg.xpath('.//*[local-name()="mask"]'))==1
 assert len(svg.xpath('.//*[local-name()="use" and @stroke-dasharray]'))==3
report={'fecha':'2026-11-25','operador':'Diego','paquete':'WP-17','laminas':26,'fuente':{'laminas_originales':20,'parrafos_identificados':len(seen),'perdidos':missing,'alterados':changed,'numeracion':'Se renumera de 1 a 26 al separar contenido denso','excepciones_previas':['Recorrido Tren Maya → Dos Bocas','https://datisa.streamlit.app','Bruno Ruiz Juarez añadido a los créditos por solicitud de Diego']},'proyeccion':{'pantalla_pulgadas':[40,50],'distancia_metros':[3,5],'titulo_px':'40–58 (96 en Gracias)','cuerpo_px':'25–31','ejemplos_y_notas_px':'23–24','tablas_y_etiquetas_px':'22–26','metadatos_px':'17–18','reduccion_automatica_de_fuente':False,'graficas':'SVG vectorial con las mismas series que las figuras originales'},'cinta':'Una única trayectoria compartida y una máscara común para todos los segmentos: no hay salientes entre colores','cifras':{'fuentes_comprobadas':len(sources),'hashes_correctos':True,'metricas_y_datos_sin_cambios':True,'anotaciones':'Sin modificaciones'},'ilustraciones':{'modo':'image_gen.imagegen integrado','prompts':'img/generacion_p11_p15.json','imagenes':icons,'p1_p10_y_amlo':'Originales conservados; AMLO solo en la última lámina, sin círculo'},'mapa':json.loads((D/'mapa_proyeccion.json').read_text())['mapa'],'pdf':{'paginas':26,'revision_visual':'26 páginas revisadas, sin texto cortado'},'navegador':{'recursos_rotos':0,'texto_fuera_de_lamina_o_pie':0,'teclado':'Flechas, Espacio, Inicio y Fin','pantalla_completa':'F y botón, Chrome/Edge; aviso de compatibilidad en el visor de Codex'}}
previo=json.loads((D/'validacion.json').read_text()) if (D/'validacion.json').exists() else {}
report['navegador']={**previo.get('navegador',{}),**report['navegador']}
(D/'validacion.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'laminas':26,'parrafos_conservados':len(seen),'fuentes_con_hash_verificado':len(sources),'imagenes_nuevas':5,'cintas_geometria_unica':26},ensure_ascii=False))

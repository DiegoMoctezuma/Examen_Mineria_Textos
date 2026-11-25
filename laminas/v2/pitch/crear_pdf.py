from pathlib import Path
import sys,json,math,re,html
from collections import Counter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor,Color,white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph,Table,TableStyle
from reportlab.lib.styles import ParagraphStyle
from pypdf import PdfReader
from lxml import html as LH
from contenido import PITCH,DEMO

BASE=Path(__file__).resolve().parent
R=BASE.parents[2]
D=R/'laminas/v2';O=BASE
allocation=json.loads((BASE/'reparto.json').read_text())
roles=allocation['roles'];seconds=allocation['slide_seconds']
owners={n:role for role in roles for n in role['slides']}
short={r['name']:r['name'].split()[0] for r in roles}
short['Diego Rafael Moctezuma Ramirez']='Diego'
root=LH.parse(str(D/'index.html'))
titles={int(s.get('id').split('-')[-1]):' '.join(s.xpath('./h1')[0].itertext()).strip() for s in root.xpath('//section')}
assert len(owners)==26 and set(owners)==set(range(1,27))
assert sorted(len(r['slides']) for r in roles)==[5,5,5,5,6]
assert max(r['seconds'] for r in roles)-min(r['seconds'] for r in roles)==25
assert all(sum(seconds[n-1] for n in r['slides'])==r['seconds'] for r in roles)

fontdir=D/'fonts'
pdfmetrics.registerFont(TTFont('Noto',str(fontdir/'NotoSans-Regular.ttf')))
pdfmetrics.registerFont(TTFont('NotoB',str(fontdir/'NotoSans-Bold.ttf')))
pdfmetrics.registerFontFamily('Noto',normal='Noto',bold='NotoB',italic='Noto',boldItalic='NotoB')
W,H=A4;M=42;CW=W-2*M
C=HexColor('#611232');G=HexColor('#A57F2C');INK=HexColor('#404041');TINT=HexColor('#F3ECE0');PALE=HexColor('#DDC9A3')
styles={
 'title':ParagraphStyle('title',fontName='NotoB',fontSize=25,leading=31,textColor=C),
 'subtitle':ParagraphStyle('subtitle',fontName='Noto',fontSize=12,leading=17,textColor=INK),
 'cardtitle':ParagraphStyle('cardtitle',fontName='NotoB',fontSize=14,leading=18,textColor=C),
 'body':ParagraphStyle('body',fontName='Noto',fontSize=11.7,leading=16.4,textColor=INK),
 'small':ParagraphStyle('small',fontName='Noto',fontSize=9.8,leading=13.4,textColor=INK),
 'note':ParagraphStyle('note',fontName='Noto',fontSize=10.1,leading=13.6,textColor=INK),
 'cell':ParagraphStyle('cell',fontName='Noto',fontSize=10.4,leading=14.3,textColor=INK),
 'cellhead':ParagraphStyle('cellhead',fontName='NotoB',fontSize=10.3,leading=13.8,textColor=white),
}
def esc(s):return html.escape(str(s)).replace('–','-').replace('—','-').replace('→','a')
def para(text,x,y,width,sty='body',raw=False):
 p=Paragraph(text if raw else esc(text),styles[sty]);_,height=p.wrap(width,2000);p.drawOn(c,x,y-height);return y-height
def time(s):return f'{s//60}:{s%60:02d}'
def spans(nums):
 groups=[];start=prev=nums[0]
 for n in nums[1:]:
  if n==prev+1:prev=n
  else:groups.append(str(start) if start==prev else f'{start} a {prev}');start=prev=n
 groups.append(str(start) if start==prev else f'{start} a {prev}')
 return ', '.join(groups)
timeline=[];elapsed=0
for n,dur in enumerate(seconds,1):timeline.append((elapsed,elapsed+dur));elapsed+=dur
blocks=[]
for n in range(1,27):
 if blocks and blocks[-1]['name']==owners[n]['name'] and blocks[-1]['slides'][-1]==n-1:blocks[-1]['slides'].append(n)
 else:blocks.append({'name':owners[n]['name'],'slides':[n]})
pages=2+sum(math.ceil(len(r['slides'])/2) for r in roles)+1
assert pages==18
output=O/'Pitch_Datisa_equipo_26_diapositivas.pdf'
c=canvas.Canvas(str(output),pagesize=A4,pageCompression=1)
c.setTitle('Datisa | Pitch del equipo para 26 diapositivas')
c.setAuthor('Equipo Datisa')
c.setSubject('Guion oral con reparto aleatorio equilibrado y tiempos estimados')
page=0
def newpage(section,name=''):
 global page
 if page:c.showPage()
 page+=1
 c.setFillColor(C);c.rect(0,H-9,W,9,fill=1,stroke=0)
 c.setFillColor(C);c.setFont('NotoB',10);c.drawString(M,H-34,'DATISA  /  PITCH DEL EQUIPO')
 c.setFillColor(INK);c.setFont('Noto',9);c.drawRightString(W-M,H-34,'25 de noviembre de 2026')
 c.setStrokeColor(PALE);c.setLineWidth(.7);c.line(M,35,W-M,35)
 c.setFillColor(INK);c.setFont('Noto',8.5);c.drawString(M,23,section)
 c.drawRightString(W-M,23,f'{page} / {pages}')
 if name:c.bookmarkPage(name)
 return H-66
def table(data,widths,y,head=True,rowheights=None):
 converted=[]
 for i,row in enumerate(data):converted.append([Paragraph(esc(cell),styles['cellhead' if i==0 and head else 'cell']) for cell in row])
 tb=Table(converted,colWidths=widths,rowHeights=rowheights,hAlign='LEFT')
 cmds=[('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),9),('LINEBELOW',(0,0),(-1,0),.8,C)]
 if head:cmds += [('BACKGROUND',(0,0),(-1,0),C)]
 for i in range(1,len(data)):
  if i%2:cmds.append(('BACKGROUND',(0,i),(-1,i),TINT))
 tb.setStyle(TableStyle(cmds));_,hh=tb.wrap(CW,1500);tb.drawOn(c,M,y-hh);return y-hh

y=newpage('Reparto y tiempos previstos','reparto')
c.addOutlineEntry('Reparto y tiempos','reparto',0)
y=para('Un guion para los cinco integrantes',M,y,CW,'title')-13
y=para('Numeración de la presentación HTML vigente: 26 diapositivas. Reparto aleatorio por bloques, equilibrado por cantidad y por tiempo previsto.',M,y,CW,'subtitle')-22
c.setFillColor(TINT);c.roundRect(M,y-69,CW,69,7,fill=1,stroke=0)
c.setFillColor(C);c.setFont('NotoB',25);c.drawString(M+16,y-31,'18:50')
c.setFont('NotoB',11);c.drawString(M+135,y-25,'Tiempo total previsto')
c.setFont('Noto',10.5);c.drawString(M+135,y-44,'Incluye 2:30 de demo y deja 1:10 hasta los 20:00.')
y-=91
rows=[['Integrante','Diapositivas','Núm.','Tiempo']]
for r in roles:rows.append([r['name'],spans(r['slides']),str(len(r['slides'])),time(r['seconds'])])
y=table(rows,[191,193,57,CW-441],y)-22
y=para('Cómo quedó el sorteo',M,y,CW,'cardtitle')-9
y=para('Cuatro integrantes tienen cinco diapositivas y uno tiene seis. La diferencia entre el turno total más corto y el más largo es de 25 segundos. Se conservaron juntos los pasos de una misma explicación y se dio menos carga adicional a quien hace la demo.',M,y,CW,'body')-16
y=para('Estos tiempos son objetivos para ensayar, no una medición real. Incluyen señalar las gráficas y pasar la palabra. El ensayo cronometrado sigue pendiente.',M,y,CW,'small')-12
y=para(f'Sorteo reproducible: semilla {allocation["seed"]}. Se eligió al azar una de {allocation["feasible_partitions"]} particiones válidas y se barajaron los cinco nombres. Este reparto sustituye al reparto anterior del guion de 20 láminas.',M,y,CW,'small')
assert y>50,('cover',y)

y=newpage('Orden de intervención','orden')
c.addOutlineEntry('Orden de intervención','orden',0)
y=para('Orden de intervención',M,y,CW,'title')-12
y=para('Mantengan la secuencia de las diapositivas. Los apartados siguientes agrupan el guion de cada persona para que pueda preparar sus intervenciones.',M,y,CW,'subtitle')-18
rows=[['Diapositivas','Habla','Tiempo acumulado']]
for b in blocks:
 lo,hi=b['slides'][0],b['slides'][-1]
 rows.append([spans(b['slides']),short[b['name']],f'{time(timeline[lo-1][0])} a {time(timeline[hi-1][1])}'])
y=table(rows,[140,190,CW-330],y)-17
y=para('Uso del guion: lean únicamente el apartado «Para decir». «Señala», «Ten presente» y «Paso siguiente» son apoyos para preparar la exposición. La demo detallada está en la última página.',M,y,CW,'small')
assert y>45,('order',y)

def card(n,x,top,width,height):
 c.setStrokeColor(PALE);c.setLineWidth(.8);c.roundRect(x,top-height,width,height,6,fill=0,stroke=1)
 c.setFillColor(C);c.roundRect(x+12,top-37,37,25,4,fill=1,stroke=0)
 c.setFillColor(white);c.setFont('NotoB',12);c.drawCentredString(x+30.5,top-29,f'{n:02d}')
 title=titles[n]
 # La indicación de parte se conserva, con un espacio claro al extraer el encabezado HTML.
 title=re.sub(r'(?<=[a-záéíóú])(?=\d)', ' ',title)
 yy=para(title,x+59,top-14,width-74,'cardtitle')
 yy=min(yy,top-43)-7
 a,b=timeline[n-1]
 yy=para(f'Duración: {time(seconds[n-1])}   |   Momento previsto: {time(a)} a {time(b)}',x+15,yy,width-30,'small')-9
 yy=para('<b>Para decir</b>',x+15,yy,width-30,'note',True)-3
 yy=para(PITCH[n]['voz'],x+15,yy,width-30,'body')-8
 for label,key in [('Señala','senalar'),('Ten presente','clave')]:
  yy=para(f'<b>{label}:</b> '+esc(PITCH[n][key]),x+15,yy,width-30,'note',True)-5
 if n<26:
  nextname=short[owners[n+1]['name']]
  handoff=(f'Continúas tú con la diapositiva {n+1}.' if owners[n+1]['name']==owners[n]['name'] else f'Pasa la palabra a {nextname}: «{nextname}, continuamos contigo».')
 else:handoff='Deja la lámina de agradecimiento visible y abre el espacio de preguntas.'
 yy=para('<b>Paso siguiente:</b> '+esc(handoff),x+15,yy,width-30,'note',True)
 if yy<top-height+10:raise RuntimeError(f'No cabe la ficha {n}: faltan {top-height+10-yy:.1f} puntos')
 return yy

for ri,r in enumerate(roles):
 for part in range(0,len(r['slides']),2):
  anchor=f'integrante-{ri}' if part==0 else ''
  y=newpage('Guion de '+short[r['name']],anchor)
  if part==0:c.addOutlineEntry(r['name'],anchor,0)
  y=para(r['name'],M,y,CW,'cardtitle')-5
  y=para(f'Diapositivas {spans(r["slides"])}  |  {len(r["slides"])} láminas  |  {time(r["seconds"])} en total',M,y,CW,'small')-16
  space=y-52;hh=(space-14)/2
  for j,n in enumerate(r['slides'][part:part+2]):card(n,M,y-j*(hh+14),CW,hh)
  if len(r['slides'][part:part+2])==1:
   yy=y-hh-35
   yy=para('Apuntes para el ensayo',M+12,yy,CW-24,'cardtitle')-20
   c.setStrokeColor(PALE)
   for z in range(5):c.line(M+12,yy-28*z,W-M-12,yy-28*z)

y=newpage('Recorrido de la demo','demo')
c.addOutlineEntry('Demo de 2:30','demo',0)
y=para('Demo en vivo: 2:30',M,y,CW,'title')-10
y=para('Responsable: '+owners[24]['name']+f'. Corresponde a la diapositiva 24 y al tramo global de {time(timeline[23][0])} a {time(timeline[23][1])}.',M,y,CW,'subtitle')-13
rows=[['Tiempo de demo','Acción','Qué mostrar o decir']]+[list(row) for row in DEMO]
y=table(rows,[86,116,CW-202],y)-18
y=para('Preparación',M,y,CW,'cardtitle')-8
y=para('Abrir https://datisa.streamlit.app antes de comenzar y hacer una consulta para evitar la carga inicial. Tener lista la versión local de la demo. Si solo se muestra una salida guardada, anunciar que es una salida guardada.',M,y,CW,'note')-12
y=para('En la consulta libre pública se utilizan reglas. El F1 de 82.7 % corresponde al sistema combinado evaluado, no a una medición de esa consulta libre. Si el público no propone una consulta, decir: «Usaré una consulta preparada».',M,y,CW,'note')
assert y>48,('demo',y)
assert page==pages,(page,pages)
c.save()
reader=PdfReader(str(output));assert len(reader.pages)==pages
alltext='\n'.join(p.extract_text() or '' for p in reader.pages)
for r in roles:assert r['name'] in alltext
for n in range(1,27):assert PITCH[n]['voz'][:25] in alltext
metadata={'reparto':allocation,'diapositivas':{str(n):{'titulo':titles[n],'integrante':owners[n]['name'],'segundos':seconds[n-1],**PITCH[n]} for n in range(1,27)},'demo':DEMO,'paginas_pdf':pages,'ensayo':'pendiente; todos los tiempos son objetivos estimados'}
(BASE/'pitch_equipo.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'pdf':str(output),'paginas':pages,'tiempo_previsto':time(sum(seconds)),'rangos':[{r['name']:time(r['seconds'])} for r in roles],'palabras_para_decir':sum(len(p['voz'].split()) for p in PITCH.values())},ensure_ascii=False))

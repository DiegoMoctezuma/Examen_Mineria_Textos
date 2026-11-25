"""Presentación para pantalla de 40–50 pulgadas a 3–5 m. Solo cambia la presentación."""
from pathlib import Path
import argparse, html, json, math, re
from PIL import ImageFont

ap=argparse.ArgumentParser();ap.add_argument('repo',type=Path);a=ap.parse_args()
R=a.repo.resolve();D=R/'laminas/v2'
S=json.loads((D/'contenido_fuente.json').read_text())
F=json.loads((D/'figuras/datos_figuras.json').read_text())
P={'guinda':'#611232','acento':'#9D2449','dorado':'#A57F2C','claro':'#DDC9A3','gris':'#98989A','texto':'#404041','tinte':'#F3ECE0'}
topics=['Tren Maya','Vacunas COVID-19','Dos Bocas','Aeropuerto Felipe Ángeles','Sembrando Vida','Huachicol','Pensión de adultos mayores','Salario mínimo','Banco del Bienestar','Tren Interoceánico','Guardia Nacional','IMSS-Bienestar','Reforma eléctrica','Jóvenes Construyendo el Futuro','Acapulco tras Otis']
E=html.escape
pages=[];mapping=[]
def value(n,i):
    s=S[n-1]['paragraphs'][i]
    if n==18:s=s.replace('Dos Bocas, de la pregunta a la respuesta con su cita','De Tren Maya a Dos Bocas, el caso difícil, con su cita')
    if n==20 and s.startswith('https://'):s='https://datisa.streamlit.app'
    return s
def t(n,i,tag='p',cls=''):
    return f'<{tag} class="{cls}" data-source="{n}:{i}">{E(value(n,i))}</{tag}>'
def trace(name,i=0):return F[name]['figura']['data'][i]
def figtable(name):return trace(name)['cells']['values']
def ribbon(uid,dark=False):
    # Todos los colores usan el MISMO trazado y están recortados por una única máscara.
    path='M343 -45C61 137 57 278 229 371S542 491 450 767'
    col=P['acento'] if dark else P['guinda']
    return f'''<svg class="ribbon {'hero-ribbon' if dark else 'corner-ribbon'}" viewBox="0 0 430 720" fill="none" aria-hidden="true"><defs><path id="cinta-{uid}" d="{path}" pathLength="100"/><mask id="banda-{uid}" maskUnits="userSpaceOnUse" x="-100" y="-100" width="800" height="1000"><use href="#cinta-{uid}" stroke="white" stroke-width="62"/></mask></defs><g mask="url(#banda-{uid})" stroke-width="66" stroke-linecap="butt"><use href="#cinta-{uid}" stroke="{col}"/><use href="#cinta-{uid}" stroke="{P['claro']}" stroke-dasharray="23 77" stroke-dashoffset="-28"/><use href="#cinta-{uid}" stroke="{P['dorado']}" stroke-dasharray="23 77" stroke-dashoffset="-51"/><use href="#cinta-{uid}" stroke="{P['gris']}" stroke-dasharray="26 74" stroke-dashoffset="-74"/></g></svg>'''
def badge(n,size=80):
    return f'<span class="topic-icon" style="--frame:{P["dorado"] if n%2==0 else P["guinda"]};width:{size}px;height:{size}px"><img src="img/p{n}.png" alt="{E(topics[n-1])}"></span>'
def make(n,body,footer=None,extra='',dark=False,title=None):
    k=len(pages)+1
    head=t(n,0,'div','eyebrow')
    title_index=2 if n in [1,18,20] else 1
    if title is None:title=t(n,title_index,'h1')
    else:title=f'<h1>{title}</h1>'
    foot=t(n,footer,'div','takeaway') if footer is not None else ''
    pages.append(f'<section class="slide {"dark" if dark else "light"} {extra}" id="slide-{k}" data-origin="{n}" aria-label="Diapositiva {k}">{ribbon(k,dark)}{head}{title}{body}{foot}<span class="page-number">{k:02d} / TOTAL</span></section>')
    mapping.append({'lamina':k,'origen':n})
def team(n,start,end):return '<div class="team">'+''.join(t(n,i) for i in range(start,end))+'</div>'
def metric(n,ids,cls=''):
    return '<article class="metric '+cls+'">'+t(n,ids[0],'div','metric-value')+''.join(t(n,i,'p','metric-label' if j==0 else 'metric-note') for j,i in enumerate(ids[1:]))+'</article>'

fonts={}
def wrap(text,width,size=24,bold=False):
    key=(size,bold)
    if key not in fonts:fonts[key]=ImageFont.truetype(str(D/'fonts'/('NotoSans-Bold.ttf' if bold else 'NotoSans-Regular.ttf')),size)
    font=fonts[key];lines=[]
    for line in re.split('<br>|\n',text):
        current=''
        for w in line.split():
            trial=(current+' '+w).strip()
            if current and font.getlength(trial)>width:lines.append(current);current=w
            else:current=trial
        if current:lines.append(current)
    return lines or ['']
def st(x,y,text,size=24,color=None,anchor='start',weight=400,width=None,line=1.13):
    lines=wrap(text,width,size,weight==700) if width else [text]
    return f'<text x="{x:.2f}" y="{y:.2f}" fill="{color or P["texto"]}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}">'+''.join(f'<tspan x="{x:.2f}" dy="{0 if i==0 else size*line:.2f}">{E(q)}</tspan>' for i,q in enumerate(lines))+'</text>'
def rect(x,y,w,h,color,rx=0):return f'<rect x="{x:.2f}" y="{y:.2f}" width="{max(0,w):.2f}" height="{h:.2f}" fill="{color}" rx="{rx}"/>'
def line(x1,y1,x2,y2,color=None,width=1):return f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{color or P["gris"]}" stroke-width="{width}"/>'
def svg(w,h,content,name):
    return f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-label="{E(name)}" style="font-family:Noto Sans,Arial,sans-serif">{content}</svg>'
def fmt(v):return f'{v:,.0f}'
def axis(x,y,w,maximum,ticks,title,log=False):
    out=''
    for v in ticks:
        p=math.log10(max(v,1))/math.log10(maximum) if log else v/maximum
        xx=x+w*p
        out+=line(xx,40,xx,y,'#E8E8E8')+st(xx,y+27,fmt(v),22,anchor='middle')
    return out+line(x,y,x+w,y)+st(x+w/2,y+64,title,23,anchor='middle')
def hbars(name,w=770,h=420,label=270,maxval=None,ticks=None,reverse=True,kind='simple',labelsize=24):
    data=F[name]['figura']['data'];bars=[d for d in data if d['type']=='bar']
    labels=bars[0]['y'];order=list(range(len(labels)))
    if reverse:order.reverse()
    arrays=[b['x'] for b in bars]
    stacked=kind=='stack'
    maximum=maxval or max(sum(float(v[i]) for v in arrays) if stacked else max(float(v[i]) for v in arrays) for i in order)*1.14
    left=label+12;plot=w-left-74;bottom=h-72;top=18
    rows=[max(34,len(wrap(labels[i],label-8,labelsize))*labelsize*1.1+8) for i in order]
    factor=min(1,(bottom-top)/sum(rows));rows=[v*factor for v in rows]
    if ticks is None:
        if maximum>1000:ticks=[0,1000,2000,3000] if maximum<5000 else [0,10000,20000,30000]
        elif maximum>100:ticks=[0,500,1000] if maximum>800 else [0,50,100]
        else:ticks=[0,20,40,60] if maximum>60 else [0,2,4]
    out=axis(left,bottom,plot,maximum,[v for v in ticks if v<=maximum], 'Errores' if name=='s8_errores_patrones' else ('Valores en la tabla' if name=='s9_estados_respuesta' else ('% de fragmentos' if name=='s4d_idf' else 'Veces')))
    y=top
    for i,rh in zip(order,rows):
        lines=wrap(labels[i],label-8,labelsize)
        yy=y+rh/2-(len(lines)-1)*labelsize*.55+labelsize*.34
        out+=st(label-8,yy,labels[i],labelsize,anchor='end',width=label-8)
        start=0
        for j,b in enumerate(bars):
            val=float(arrays[j][i]);colors=b['marker']['color'];c=colors[i] if isinstance(colors,list) else colors
            xx=left+(start/maximum)*plot
            out+=rect(xx,y+rh/2-11,plot*val/maximum,22,c)
            start+=val
        labeltext=str(bars[0].get('text',[fmt(float(v)) for v in arrays[0]])[i]) if len(bars)==1 else fmt(start)
        out+=st(left+(start/maximum)*plot+9,y+rh/2+8,labeltext,24,width=75)
        y+=rh
    return svg(w,h,out,name)
def legend(items,cls=''):
    return '<div class="legend '+cls+'">'+''.join(f'<span><i style="background:{c}"></i>{E(n)}</span>' for c,n in items)+'</div>'

# 1. Portada. Los nombres son metadatos, separados del mensaje principal.
make(1,'<div class="cover-sub">'+t(1,3)+'</div>'+team(1,4,10)+t(1,10,'div','date'),dark=True,extra='cover')
# 2. Corpus.
cx=trace('s2a_corpus');co=''
for j,i in enumerate([2,1,0]):
    y=40+j*127;c=cx['marker']['color'][i]
    co+=st(0,y,cx['y'][i],26,weight=700)+rect(0,y+18,cx['x'][i]/2294*560,36,c)+st(580,y+47,fmt(cx['x'][i]),32,P['guinda'],weight=700)
    if i==1:co+=st(0,y+91,'4 duplicados exactos y 1 casi duplicado fuera',22)
make(2,'<div class="body columns corpus"><div>'+svg(770,430,co,'Etapas del corpus')+'</div><div class="metrics-stack">'+metric(2,[4,5,6])+metric(2,[7,8,9])+'</div></div>',3)
# 3. Cuatro pasos. El catálogo pasa a una lámina propia.
groups=[[4,5,6,7,8],[9,10,11,12,13],[14,15,16,17,18,19],[20,21,22,23,24]]
steps=''
for g in groups:
    steps+='<article class="pipeline-step"><div class="step-title">'+t(3,g[0],'b')+t(3,g[1],'h2')+'</div>'+t(3,g[2],'p','step-description')+'<div class="step-example">'+t(3,g[3],'p','example-label')+''.join(t(3,i) for i in g[4:])+'</div></article>'
make(3,'<div class="body pipeline">'+steps+'</div>',extra='pipeline-page')
catalog='<div class="body catalog">'+''.join('<article>'+badge(i,76)+'<div><small>P'+str(i)+'</small><strong>'+E(s)+'</strong></div></article>' for i,s in enumerate(topics,1))+'</div>'
make(3,catalog,title=t(3,3,'span'),extra='catalog-page')
# 4. Acotaciones.
make(4,'<div class="body columns"><div>'+hbars('s2b_acotaciones',h=435,label=300,labelsize=22)+'</div><div class="metrics-stack">'+metric(4,[3,4,5])+metric(4,[6,7,8])+'</div></div>',9)
# 5. Fragmentación.
make(5,'<div class="body metric-grid">'+''.join(metric(5,g) for g in [[3,4,5],[6,7,8],[9,10,11],[12,13,14]])+'</div>',15)
# 6. Tokenización en dos vistas. Se conservan todas las palabras del ejemplo.
tok=figtable('s4c_tokenizacion')
for indices in [[0,1],[2,3,4]]:
    rows=''.join('<article class="token-row"><h2>'+E(tok[0][i])+'</h2><p>'+E(tok[1][i])+'</p></article>' for i in indices)
    make(6,'<div class="body token-rows '+('long-tokens' if len(indices)==2 else '')+'">'+rows+'</div>',3 if len(indices)==3 else None,extra='token-page',title=t(6,1,'span')+f'<small class="title-part">{1 if indices[0]==0 else 2} de 2</small>')
# 7. Raíz/lema. Agrupar forma y frecuencia reduce columnas sin perder valores.
tab=figtable('stem_lema');rows=''
for i in range(len(tab[0])):
    rows+='<tr'+(' class="highlight"' if i<2 else '')+'><td>'+E(tab[0][i])+'</td><td>'+E(tab[1][i])+' <span>· '+E(tab[2][i])+'</span></td><td>'+E(tab[3][i])+' <span>· '+E(tab[4][i])+'</span></td></tr>'
stem='<table class="stem-table"><thead><tr><th>Palabra</th><th>Raíz · fragmentos</th><th>Lema · fragmentos</th></tr></thead><tbody>'+rows+'</tbody></table>'
make(7,'<div class="body stem-body">'+stem+'<div class="inline-metrics">'+metric(7,[3,4,5])+metric(7,[6,7,8])+'</div></div>',9)
# 8. Índice invertido: mismos nueve postings, ahora texto vectorial de 22–24 px.
tab=figtable('r09_indice_invertido');ind=''
for i in range(3):
    ind+='<article class="posting-row"><div><h2>'+E(tab[0][i])+'</h2><p>'+E(tab[1][i])+' fragmentos</p><strong>idf '+E(tab[2][i])+'</strong></div><div class="postings">'+''.join('<p>'+E(q)+'</p>' for q in tab[3][i].split('<br>'))+'</div></article>'
make(8,'<div class="body postings-body">'+ind+'</div>',3)
# 9. idf.
idf=trace('s4d_idf');out=''
for j,i in enumerate([3,2,1,0]):
    y=35+j*85;v=idf['x'][i]
    out+=st(0,y+20,idf['y'][i],26,weight=700)+rect(175,y-6,v/5.2*335,32,P['claro'])+st(525,y+20,idf['text'][i],24)
make(9,'<div class="body columns"><div>'+svg(770,420,out,'Frecuencia e idf')+'</div><div class="metrics-stack">'+metric(9,[4,5,6])+metric(9,[7,8,9])+'</div></div>',3)
# 10. Todas las comparaciones booleanas: no se usan barras de 0.8 para representar cero.
b0,b1=trace('r07_booleano',0),trace('r07_booleano',1)
rows=''
for i in reversed(range(15)):
    cells=''
    for b in [b0,b1]:
        real=int(str(b['text'][i]).replace(',',''));width=math.log10(max(real,1))/math.log10(35078)*100
        cells+='<td><span class="boolean-track"><i style="width:'+str(width)+'%;background:'+b['marker']['color']+'"></i></span><strong>'+E(b['text'][i])+'</strong></td>'
    rows+='<tr><th>'+E(b0['y'][i])+'</th>'+cells+'</tr>'
make(10,'<div class="body tall boolean-body"><table class="boolean-table"><thead><tr><th>Pregunta</th><th>Todas las palabras (Y)</th><th>Cualquier palabra (O)</th></tr></thead><tbody>'+rows+'</tbody></table></div>',extra='boolean-page')
make(10,'<div class="body three-columns boolean-cases">'+''.join(metric(10,g) for g in [[4,5,6],[7,8,9],[10,11,12]])+'</div>',3)
# 11. Juicios humanos.
make(11,'<div class="body metric-grid">'+''.join(metric(11,g) for g in [[4,5,6],[7,8,9],[10,11,12],[13,14,15]])+'</div>',3)
# 12. AP y MAP.
aptrace=trace('s5a_ap_explicado');out='';bw=60
for i,txt in enumerate(aptrace['text']):
    hit='precisión' in txt;x=9+i*72
    out+=rect(x,26,bw,188,P['acento'] if hit else P['claro'])+st(x+bw/2,252,str(i+1),26,anchor='middle')
    if hit:out+=st(x+bw/2,129,txt.split('<br>')[-1],26,'#FFFFFF',anchor='middle',weight=700)
out+=st(365,298,'Posición en los 10 primeros',24,anchor='middle')
aph='<div class="ap-main">'+badge(3,66)+svg(740,320,out,'Precisión por posición')+legend([(P['acento'],'Relevante'),(P['claro'],'No relevante')])+'<p class="formula">AP = (1/2 + 2/3 + 3/6 + 4/10) / 8<br><strong>AP = 25.8 %</strong></p></div>'
models='<div class="model-summary">'+t(12,4,'h2')
for i in [5,7,9,11]:models+='<div class="model-row">'+t(12,i)+t(12,i+1,'strong')+'</div>'
models+=t(12,13,'p','model-note')+t(12,14,'p','winner')+'</div>'
make(12,'<div class="body ap-columns">'+aph+models+'</div>',3,extra='ap-page')
# 13. Cuatro variantes, quince preguntas: dos gráficos para que los nombres no se inclinen.
querytraces=F['s6_ap_por_consulta']['figura']['data']
for part,inds in enumerate([list(range(8)),list(range(8,15))]):
    w=840;h=400;left=330;plot=470;top=18;rowh=39 if part==0 else 44;out=''
    for v in [0,25,50,75,100]:out+=line(left+plot*v/100,10,left+plot*v/100,top+rowh*len(inds),'#E8E8E8')+st(left+plot*v/100,top+rowh*len(inds)+30,str(v),22,anchor='middle')
    for j,i in enumerate(inds):
        cy=top+j*rowh
        label_lines=wrap(querytraces[0]['x'][i],left-20,22)
        ly=cy+rowh/2-(len(label_lines)-1)*22*.565+22*.34
        out+=st(left-14,ly,querytraces[0]['x'][i],22,anchor='end',width=left-20)
        for k,b in enumerate(querytraces):out+=rect(left,cy+k*9,plot*b['y'][i]/100,7,b['marker']['color'])
    out+=st(left+plot/2,top+rowh*len(inds)+66,'Precisión promedio (AP), %',23,anchor='middle')
    names=['TF-IDF · raíz','BM25 · raíz','TF-IDF · lema','BM25 · lema']
    chart=legend([(tr['marker']['color'],name) for tr,name in zip(querytraces,names)],'query-legend')+svg(w,h,out,'Precisión promedio por pregunta')
    case='<div class="query-case">'+badge(1 if part==0 else 3,94)+metric(13,[4,5,6] if part==0 else [7,8,9])+'</div>'
    make(13,'<div class="body query-columns"><div>'+chart+'</div>'+case+'</div>',3,extra='query-page',title=t(13,1,'span')+f'<small class="title-part">{1 if part==0 else 9}–{8 if part==0 else 15} de 15</small>')
# 14. Enfoques y selección del NER.
rules='<div class="recognition">'+t(14,4,'h2')+'<article>'+t(14,5,'h3')+t(14,6,'p','method')+t(14,7,'p','quote')+'</article><article>'+t(14,8,'h3')+t(14,9,'p','method')+t(14,10,'p','quote')+'</article></div>'
models='<div class="selection">'+t(14,11,'h2')+t(14,12,'p','definition')
for ix in [13,15,17,19]:
    number=float(value(14,ix+1).split()[0]);models+='<div class="selection-row">'+t(14,ix)+f'<div class="selection-track"><i style="width:{number/70*100}%"></i></div>'+t(14,ix+1,'strong')+'</div>'
models+='</div>'
make(14,'<div class="body equal-columns">'+rules+models+'</div>',3)
# 15. F1 y referencias, SVG con error bar y marcadores de las mismas series.
ff=F['s7a_f1_con_referencias']['figura']['data'];out='';left=55;bottom=294;plotw=1070;ph=235
for v in [0,25,50,75,100]:out+=line(left,bottom-v/100*ph,left+plotw,bottom-v/100*ph,'#E8E8E8')+st(left-8,bottom-v/100*ph+8,str(v),22,anchor='end')
for i,n in enumerate(ff[0]['x']):
    cx=left+plotw/6*(i+.5);val=ff[0]['y'][i];c=P['guinda'] if i==5 else P['acento']
    out+=rect(cx-50,bottom-val/100*ph,100,val/100*ph,c)+st(cx,bottom-12,ff[0]['text'][i],24,'#FFFFFF',anchor='middle',weight=700)+st(cx,bottom+32,n,24,anchor='middle',width=175)
    for ser in ff[2:]:
        v=ser['y'][i]
        if v is None:continue
        yy=bottom-v/100*ph
        if ser['marker']['symbol']=='diamond':out+=f'<path d="M{cx} {yy-8}l8 8-8 8-8-8Z" fill="{P["dorado"]}" stroke="{P["texto"]}"/>'
        else:out+=line(cx-7,yy-7,cx+7,yy+7,P['texto'],3)+line(cx-7,yy+7,cx+7,yy-7,P['texto'],3)
    if i==5:
        yy=bottom-val/100*ph;lo=yy+ff[1]['error_y']['arrayminus'][0]/100*ph;hi=yy-ff[1]['error_y']['array'][0]/100*ph
        out+=line(cx,lo,cx,hi,P['texto'],3)+line(cx-12,lo,cx+12,lo,P['texto'],3)+line(cx-12,hi,cx+12,hi,P['texto'],3)
out+=st(left+plotw/2,bottom+87,'Tipo de entidad · F1 (%)',23,anchor='middle')
chart=legend([(P['acento'],'Sistema'),(P['dorado'],'◆ Acuerdo humano'),(P['gris'],'× Solo diccionario')])+svg(1168,405,out,'F1 por tipo con referencias')
make(15,'<div class="body f1-chart-body">'+chart+'</div>',3,title=t(15,1,'span')+'<small class="title-part">1 de 2</small>')
make(15,'<div class="body three-columns f1-comparison">'+''.join(metric(15,g) for g in [[4,5,6],[7,8,9],[10,11,12]])+'</div>',3,title=t(15,1,'span')+'<small class="title-part">2 de 2</small>')
# 16. Errores.
err=legend([(P['acento'],'Detecciones de más'),(P['dorado'],'Entidades que faltaron')])+hbars('s8_errores_patrones',h=385,label=290,maxval=72,ticks=[0,20,40,60],kind='stack',labelsize=24)
make(16,'<div class="body columns error-columns"><div>'+err+'</div><div class="metrics-stack error-cases">'+metric(16,[4,5,6])+metric(16,[7,8,9])+'</div></div>',3)
# 17. Tabla completa de estados y ejemplos en páginas distintas.
data=F['s9_estados_respuesta']['figura']['data'];out='';w=1168;left=405;plot=670;top=8;rh=24
for v in [0,20,40,60]:out+=line(left+plot*v/65,top,left+plot*v/65,top+15*rh,'#E8E8E8')+st(left+plot*v/65,top+15*rh+27,str(v),22,anchor='middle')
for j,i in enumerate(reversed(range(15))):
    y=top+j*rh;out+=st(left-14,y+18,data[0]['y'][i],22,anchor='end');start=0
    for b in data:
        v=b['x'][i];out+=rect(left+start/65*plot,y+1,v/65*plot,18,b['marker']['color']);start+=v
out+=st(left+plot/2,top+15*rh+63,'Valores en la tabla',23,anchor='middle')
make(17,'<div class="body evidence-chart">'+legend([(P['acento'],'Respaldado'),(P['dorado'],'Ambiguo'),(P['gris'],'Sin evidencia')])+svg(w,440,out,'Estados de los datos por pregunta')+'</div>',3,extra='evidence-chart-page')
examples='<div class="body evidence-examples"><div class="evidence-total">'+t(17,4,'strong')+'<div>'+t(17,5)+t(17,6)+'</div></div><div class="three-columns">'
for ids,bn in [([7,8,9,10],9),([11,12,13,14],3),([15,16,17,18],1)]:
    examples+='<article class="evidence-case">'+badge(bn,65)+t(17,ids[0],'h2')+t(17,ids[1],'p','case-statement')+t(17,ids[2],'p','case-quote')+t(17,ids[3],'p','case-source')+'</article>'
make(17,examples+'</div></div>',extra='evidence-example-page')
# 18. Demostración.
demo=''
for ids in [[3,4,5],[6,7,8],[9,10,11]]:demo+='<article>'+t(18,ids[0],'b')+'<div>'+t(18,ids[1],'h2')+t(18,ids[2])+'</div></article>'
make(18,'<div class="body demo-steps">'+demo+'</div>',dark=True,extra='demo-page')
# 19. Siguientes pasos.
nexts=''
for ids in [[4,5,6,7,8],[9,10,11,12,13],[14,15,16,17,18]]:
    nexts+='<article>'+t(19,ids[0],'b','next-number')+t(19,ids[1],'h2')+t(19,ids[2],'p','next-problem')+'<div class="next-action">'+t(19,ids[3],'h3')+t(19,ids[4])+'</div></article>'
make(19,'<div class="body three-columns next-steps">'+nexts+'</div>',3)
# 20. Cierre, único lugar con AMLO.
make(20,'<div class="closing-sub">'+t(20,3)+'</div>'+team(20,4,10)+f'<a class="demo-url" data-source="20:10" href="{value(20,10)}" target="_blank" rel="noopener">{E(value(20,10))}</a><img class="cierre" src="img/cierre.png" alt="Muñeco de AMLO haciendo un corazón con las manos">',dark=True,extra='closing')

total=len(pages);pages=[p.replace('TOTAL',str(total)) for p in pages]
css=(Path(__file__).with_name('proyeccion.css')).read_text()
js=(Path(__file__).with_name('proyeccion.js')).read_text()
(D/'estilos.css').write_text(css);(D/'presentacion.js').write_text(js)
(D/'index.html').write_text('''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#611232"><title>Datisa · Presentación para proyección</title><link rel="icon" href="data:,"><link rel="stylesheet" href="estilos.css"></head><body><main id="viewport"><div id="deck">'''+''.join(pages)+'''</div></main><nav id="controls" aria-label="Controles de presentación"><button id="prev" aria-label="Diapositiva anterior" title="Anterior · ←">←</button><span id="counter" aria-live="polite"></span><button id="next" aria-label="Diapositiva siguiente" title="Siguiente · →">→</button><button id="fullscreen" aria-label="Pantalla completa" title="Pantalla completa · F">⛶</button><button id="print" aria-label="Imprimir o guardar PDF" title="Imprimir o guardar PDF">⎙</button></nav><div id="hint">← → / Espacio · F pantalla completa</div><div id="progress" aria-hidden="true"></div><script src="presentacion.js"></script></body></html>''')
(D/'mapa_proyeccion.json').write_text(json.dumps({'laminas':total,'pantalla_pulgadas':[40,50],'distancia_metros':[3,5],'mapa':mapping},ensure_ascii=False,indent=2)+'\n')
print(f'{total} láminas para proyección; datos y contenido de las 20 originales conservados.')

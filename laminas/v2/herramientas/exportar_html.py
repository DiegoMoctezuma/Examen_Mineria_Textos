"""Exportación HTML editable del texto aprobado, sin modificar el PPTX de origen."""
from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
import argparse, hashlib, html, json, posixpath, shutil

ap = argparse.ArgumentParser()
ap.add_argument('repo', type=Path)
args = ap.parse_args()
R = args.repo.resolve()
D = R / 'laminas/v2'
D.mkdir(parents=True, exist_ok=True)
for folder in ['img','figuras','fonts']:
    (D/folder).mkdir(exist_ok=True)
NS = {'a':'http://schemas.openxmlformats.org/drawingml/2006/main', 'p':'http://schemas.openxmlformats.org/presentationml/2006/main', 'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
Q = lambda n: '{'+NS['r']+'}'+n
esc = html.escape
COLORS = {'075638':'611232','17251E':'404041','68766D':'6B6B6D','E5F0BD':'DDC9A3','BCD6C6':'DDC9A3','F8DC87':'A57F2C','BFD5CA':'DDC9A3','FFF8F0':'F3ECE0','BDD6C5':'F3ECE0','DDE2DC':'E8E8E8','6E9482':'A57F2C','4F8A6E':'9D2449'}
def color(el, default='404041'):
    c = el.find('a:solidFill/a:srgbClr',NS) if el is not None else None
    v = c.get('val') if c is not None else default
    return '#'+COLORS.get(v,v)
def rels(z, f):
    path=posixpath.dirname(f)+'/_rels/'+posixpath.basename(f)+'.rels'
    return {e.get('Id'):posixpath.normpath(posixpath.dirname(f)+'/'+e.get('Target')) for e in E.fromstring(z.read(path)) if e.get('TargetMode')!='External'}
def ordered(z):
    p=E.fromstring(z.read('ppt/presentation.xml'));rr=rels(z,'ppt/presentation.xml')
    return [rr[s.get(Q('id'))] for s in p.findall('p:sldIdLst/p:sldId',NS)]
def box(e):
    x=e.find('.//a:xfrm',NS)
    if x is None:return None
    o=x.find('a:off',NS);s=x.find('a:ext',NS)
    if o is None or s is None:return None
    return [float(o.get('x'))/9525,float(o.get('y'))/9525,float(s.get('cx'))/9525,float(s.get('cy'))/9525]
def pos(b):return f'left:{b[0]:.2f}px;top:{b[1]:.2f}px;width:{b[2]:.2f}px;height:{b[3]:.2f}px;'
def paragraphs(e):
    return [''.join(p.xpath('.//a:t/text()',namespaces=NS)) for p in e.findall('.//a:p',NS) if p.xpath('.//a:t/text()',namespaces=NS)]
def curve(dark=False):
    # Cinta segmentada: curva continua con cambios de color, nunca una imagen de fondo.
    bg='#9D2449' if dark else '#611232'
    return f'''<svg class="ribbon {'hero-ribbon' if dark else 'corner-ribbon'}" viewBox="0 0 430 720" fill="none" aria-hidden="true"><path d="M343 -45C61 137 57 278 229 371S542 491 450 767" stroke="{bg}" stroke-width="62"/><path d="M140 198C104 278 147 327 229 371" stroke="#DDC9A3" stroke-width="62"/><path d="M229 371C306 413 372 423 411 473" stroke="#A57F2C" stroke-width="62"/><path d="M411 473C459 535 474 627 450 767" stroke="#98989A" stroke-width="62"/><path d="M-10 697H178" stroke="#A57F2C" stroke-width="10"/><path d="M178 697H330" stroke="#DDC9A3" stroke-width="10"/></svg>'''
topics=['Tren Maya','Vacunas COVID-19','Dos Bocas','Aeropuerto Felipe Ángeles','Sembrando Vida','Huachicol','Pensión de adultos mayores','Salario mínimo','Banco del Bienestar','Tren Interoceánico','Guardia Nacional','IMSS-Bienestar','Reforma eléctrica','Jóvenes Construyendo el Futuro','Acapulco tras Otis']
def badge(n, style='', catalog=False):
    return f'''<span class="topic-icon {'catalog-icon' if catalog else 'example-icon'}" style="--frame:var(--{"dorado" if n%2==0 else "guinda"});{style}" data-topic="{n}"><span class="placeholder">P{n}</span><img src="img/p{n}.png" alt="{esc(topics[n-1])}" onerror="this.remove()" onload="this.previousElementSibling.hidden=true"></span>'''

z1=ZipFile(R/'laminas/Presentacion_Mineria_de_Textos.pptx')
for n in range(1,11): (D/f'img/p{n}.png').write_bytes(z1.read(f'ppt/media/image{n+2}.png'))
(D/'img/cierre.png').write_bytes(z1.read('ppt/media/image13.png'))
# Las fuentes se incluyen en fonts/ con sus licencias; no se descargan durante la exportación.
for name in ['Montserrat-Regular.otf','Montserrat-Bold.otf','NotoSans-Regular.ttf','NotoSans-Bold.ttf']:
    if not (D/'fonts'/name).exists():raise FileNotFoundError('Falta la fuente local: '+name)

z=ZipFile(R/'laminas/Presentacion_Mineria_de_Textos_v2.pptx')
# Mapa de las figuras por nombre: siempre se usa el PNG completo, sin recortes.
image_map=json.loads(Path(__file__).with_name('mapa_origen.json').read_text())
source=[]; audit=[];slides=[]
for number,f in enumerate(ordered(z),1):
    root=E.fromstring(z.read(f));rr=rels(z,f);texts=[];parts=[]
    dark=number in [1,18,20]
    for e in root.findall('p:cSld/p:spTree/*',NS):
        b=box(e)
        if b is None:continue
        ps=paragraphs(e);texts.extend(ps)
        if number==3:continue
        blip=e.find('.//a:blip',NS)
        if blip is not None:
            media=rr[blip.get(Q('embed'))]
            if media in ['ppt/media/image1.png','ppt/media/image2.png']:continue
            name=image_map.get(media)
            if name is None:raise RuntimeError('Figura no identificada: '+media)
            if number==2:b=[59.5,193,841,397]
            if number==12:b=[59.5,183.4,802.6,407]
            parts.append(f'<img class="figure element" style="{pos(b)}" src="../../salida/v2/figuras/{name}" alt="{esc(name.removesuffix(".png").replace("_"," "))}" data-figure="{name}">')
            audit.append({'slide':number,'figure':name})
            continue
        sp=e.find('p:spPr',NS)
        if sp is None:continue
        fill=sp.find('a:solidFill',NS);ln=sp.find('a:ln',NS)
        shape=''
        if fill is not None:
            bg=color(sp)
            if bg=='#A57F2C' and b[3]>80:bg='#F3ECE0'
            shape+='background:'+bg+';'
        if ln is not None and ln.find('a:solidFill',NS) is not None:
            shape+=f'border:{float(ln.get("w","0"))/9525:.2f}px solid {color(ln)};'
        geom=sp.find('a:prstGeom',NS)
        if geom is not None and geom.get('prst')=='roundRect':shape+='border-radius:12px;'
        if not ps:
            if shape:parts.append(f'<div aria-hidden="true" class="element shape" style="{pos(b)}{shape}"></div>')
            continue
        tx=e.find('p:txBody',NS);body=tx.find('a:bodyPr',NS)
        anchor=body.get('anchor','t');justify={'ctr':'center','b':'flex-end'}.get(anchor,'flex-start')
        pad='padding:'+ ' '.join(f'{int(body.get(k,"0"))/9525:.2f}px' for k in ['tIns','rIns','bIns','lIns'])+';'
        content=[];maxsize=0
        for p in tx.findall('a:p',NS):
            if not p.xpath('.//a:t/text()',namespaces=NS):continue
            pr=p.find('a:pPr',NS);de=p.find('a:pPr/a:defRPr',NS)
            if de is None:de=tx.find('a:lstStyle/a:defPPr/a:defRPr',NS)
            align=pr.get('algn','l') if pr is not None else 'l'
            align={'l':'left','r':'right','ctr':'center','just':'justify'}.get(align,'left')
            runs=[]
            for run in p:
                if E.QName(run).localname=='br':runs.append('<br>');continue
                t=run.find('a:t',NS)
                if t is None:continue
                rp=run.find('a:rPr',NS)
                if rp is None:rp=de
                size=float(rp.get('sz',de.get('sz','1600') if de is not None else '1600'))/100*4/3
                maxsize=max(maxsize,size)
                font='Montserrat' if size>=30 or rp.get('b')=='1' else 'Noto Sans'
                text=t.text or ''
                if number==18:text=text.replace('Dos Bocas, de la pregunta a la respuesta con su cita','De Tren Maya a Dos Bocas, el caso difícil, con su cita')
                if number==20 and text.startswith('https://'):text='https://datisa.streamlit.app'
                fg=color(rp,color(de).lstrip(chr(35)))
                if not dark and size>=30:fg='#611232'
                style=f'font-family:{font};font-size:{size:.2f}px;font-weight:{700 if rp.get("b")=="1" else 400};color:{fg};'
                if text.startswith('https://'):runs.append(f'<a href="{esc(text)}" style="{style}" target="_blank" rel="noopener">{esc(text)}</a>')
                else:runs.append(f'<span style="{style}">{esc(text)}</span>')
            if runs:content.append(f'<p style="text-align:{align}">'+''.join(runs)+'</p>')
        # La portada reserva una columna real a la cinta: el título deja de atravesarla.
        if number==1:
            if any('Encontrar en segundos' in p for p in ps):b=[54,150,810,210]
            elif any('Un buscador' in p for p in ps):b=[54,390,730,65]
        if number==20 and ps==['Gracias']:b=[54,190,740,180]
        classes='element text'+(' headline' if maxsize>=30 else '')
        parts.append(f'<div class="{classes}" data-source-text style="{pos(b)}{shape}{pad}justify-content:{justify};">'+''.join(content)+'</div>')
    source.append({'slide':number,'paragraphs':texts})
    if number==3:
        parts=[f'<div class="eyebrow" data-source-text>{texts[0]}</div><h1 data-source-text>{texts[1]}</h1><p class="catalog-intro" data-source-text>{texts[3]}</p>']
        parts.append('<div class="topics" aria-label="Quince temas del sistema">'+''.join(f'<div class="topic">{badge(n,catalog=True)}<span class="topic-label"><small>P{n}</small><span class="topic-name">{esc(topic)}</span></span></div>' for n,topic in enumerate(topics,1))+'</div>')
        groups=[texts[4:9],texts[9:14],texts[14:20],texts[20:25]]
        parts.append('<div class="steps">')
        for group in groups:
            parts.append('<article class="step"><div class="step-heading"><span data-source-text>'+group[0]+'</span><h2 data-source-text>'+group[1]+'</h2></div><p data-source-text>'+esc(group[2])+'</p><div class="step-example">'+''.join('<p data-source-text>'+esc(t)+'</p>' for t in group[3:])+(badge(3,'right:0;top:0;width:26px;height:26px;') if group[0]=='1' else '')+'</div></article>')
        parts.append('</div><span class="page-number" data-source-text>03</span>')
    if number==12:parts.append(badge(3,'left:790px;top:177px;width:63px;height:63px;'))
    if number==13:
        parts.append(badge(1,'left:879px;top:192px;width:63px;height:63px;'))
        parts.append(badge(3,'left:879px;top:418px;width:63px;height:63px;'))
    if number==17:parts.append(badge(9,'left:648px;top:296px;width:63px;height:63px;'))
    if number==20:parts.append('<img class="cierre" src="img/cierre.png" alt="Muñeco de AMLO haciendo un corazón con las manos">')
    slides.append(f'<section class="slide {"dark" if dark else "light"} slide-{number}" id="slide-{number}" aria-label="Diapositiva {number}">{curve(dark)}'+''.join(parts)+'</section>')

css='''@font-face{font-family:Montserrat;src:url(fonts/Montserrat-Regular.otf);font-weight:400;font-display:block}@font-face{font-family:Montserrat;src:url(fonts/Montserrat-Bold.otf);font-weight:700;font-display:block}@font-face{font-family:"Noto Sans";src:url(fonts/NotoSans-Regular.ttf);font-weight:400;font-display:block}@font-face{font-family:"Noto Sans";src:url(fonts/NotoSans-Bold.ttf);font-weight:700;font-display:block}
:root{--guinda:#611232;--guinda-acento:#9D2449;--dorado:#A57F2C;--dorado-claro:#DDC9A3;--gris:#98989A;--texto:#404041;--fondo:#FFFFFF;--tinte:#F3ECE0;--secundario:#6B6B6D;--scale:1}
*{box-sizing:border-box}html,body{margin:0;height:100%;overflow:hidden}body{background:#404041;font-family:"Noto Sans",Arial,sans-serif;color:var(--texto)}button,a{-webkit-tap-highlight-color:transparent}button{font:inherit}#viewport{height:100%;width:100%;position:relative}#deck{width:1280px;height:720px;position:absolute;left:50%;top:50%;transform:translate(-50%,-50%) scale(var(--scale));transform-origin:center;flex:none}.slide{position:absolute;inset:0;width:1280px;height:720px;background:var(--fondo);overflow:hidden;visibility:hidden;opacity:0;transition:opacity 140ms ease}.slide.active{visibility:visible;opacity:1}.slide.dark{background:var(--guinda);color:white}.element{position:absolute}.text{display:flex;flex-direction:column;line-height:1.12;overflow:visible}.text p{margin:0;flex:none}.text a{color:inherit;text-decoration:none}.text a:hover{text-decoration:underline}.figure{object-fit:contain}.ribbon{position:absolute;pointer-events:none}.hero-ribbon{right:0;top:0;width:430px;height:720px;opacity:.83}.corner-ribbon{width:175px;height:293px;right:-8px;top:-144px;opacity:.55}.slide-20 .hero-ribbon{opacity:.42}.cierre{position:absolute;width:305px;height:380px;object-fit:contain;right:62px;top:234px;filter:drop-shadow(0 8px 0 rgba(0,0,0,.08))}.topic-icon{display:inline-grid;place-items:center;position:relative;border-radius:50%;background:var(--dorado-claro);color:var(--guinda);overflow:hidden;flex:none}.topic-icon::after{content:"";position:absolute;inset:0;border:5px solid var(--frame,var(--guinda));border-radius:50%;pointer-events:none;box-shadow:inset 0 0 0 2px var(--dorado)}.topic-icon img{width:100%;height:100%;object-fit:contain;position:absolute;inset:0;clip-path:circle(45% at 50% 50%)}.placeholder{font-family:Montserrat,Arial,sans-serif;font-size:20px;font-weight:700}.placeholder[hidden]{display:none}.example-icon{position:absolute}.eyebrow{position:absolute;left:48px;top:23px;font:700 13px Montserrat;color:var(--guinda);letter-spacing:1.2px}.slide h1{position:absolute;left:48px;top:67px;margin:0;width:1100px;font:700 34px/1.12 Montserrat;color:var(--guinda)}.catalog-intro{position:absolute;left:56px;top:127px;margin:0;font-size:18px}.topics{position:absolute;left:56px;right:56px;top:170px;height:248px;display:grid;grid-template-columns:repeat(5,1fr);grid-template-rows:repeat(3,1fr);column-gap:13px;row-gap:6px}.topic{display:flex;align-items:center;gap:12px}.catalog-icon{width:63px;height:63px}.topic-label{display:flex;flex-direction:column;gap:2px}.topic-label small{font-size:10.5px;color:var(--secundario);line-height:1}.topic-name{font-size:14px;line-height:1.17;font-weight:700;max-width:143px}.steps{position:absolute;left:56px;right:56px;top:446px;height:221px;display:grid;grid-template-columns:repeat(4,1fr);gap:24px}.step{border-top:3px solid var(--dorado);padding-top:12px;position:relative}.step-heading{display:flex;align-items:baseline;gap:12px;color:var(--guinda)}.step-heading>span{font:700 28px Montserrat}.step h2{font:700 21px Montserrat;margin:0}.step>p{font-size:15px;line-height:1.23;margin:7px 0 12px;min-height:55px}.step-example{position:relative;border-left:2px solid var(--dorado-claro);padding-left:11px;font-size:13.5px;line-height:1.18}.step-example p{margin:0 0 4px}.step-example p:first-child{font-weight:700;color:var(--guinda)}.page-number{position:absolute;right:48px;bottom:17px;font-size:12px;color:var(--secundario)}
#controls{position:fixed;bottom:14px;left:50%;transform:translateX(-50%);display:flex;align-items:center;gap:7px;padding:5px 8px;background:rgba(64,64,65,.94);border:1px solid #98989A;border-radius:30px;color:white;opacity:0;transition:opacity 140ms;z-index:10}#controls:hover,#controls:focus-within,body.show-controls #controls{opacity:1}#controls button{background:none;border:0;color:white;cursor:pointer;min-width:34px;height:30px;border-radius:20px}#controls button:hover,#controls button:focus-visible{background:#611232;outline:2px solid #DDC9A3}#counter{font-size:12px;min-width:48px;text-align:center}#hint{position:fixed;top:12px;left:50%;transform:translateX(-50%);padding:7px 14px;color:white;background:#404041;border-radius:16px;font-size:12px;transition:opacity 140ms;opacity:0;pointer-events:none;z-index:10}body.show-controls #hint{opacity:1}#progress{position:fixed;bottom:0;left:0;height:3px;background:var(--dorado);transition:width 140ms ease;z-index:9}body:fullscreen #viewport{background:#404041}button:disabled{opacity:.35;cursor:default}
@media(prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
@media print{@page{size:13.333333in 7.5in;margin:0}html,body{width:1280px;height:auto;overflow:visible;background:white!important}#viewport{display:block;height:auto}#deck{position:static;width:1280px;height:auto;transform:none!important}.slide{position:relative;visibility:visible!important;opacity:1!important;display:block!important;break-after:page;page-break-after:always;print-color-adjust:exact;-webkit-print-color-adjust:exact;transition:none!important}.slide:last-child{break-after:auto;page-break-after:auto}#controls,#hint,#progress{display:none!important}}
'''
js='''(() => {
  "use strict";
  const slides=[...document.querySelectorAll('.slide')];
  const counter=document.querySelector('#counter');
  const prev=document.querySelector('#prev'), next=document.querySelector('#next');
  let index=0, timer;
  function resize(){document.documentElement.style.setProperty('--scale',Math.min(innerWidth/1280,innerHeight/720));}
  function show(n,update=true){index=Math.max(0,Math.min(slides.length-1,n));slides.forEach((s,i)=>{s.classList.toggle('active',i===index);s.setAttribute('aria-hidden',String(i!==index));s.inert=i!==index});counter.textContent=`${index+1} / ${slides.length}`;prev.disabled=index===0;next.disabled=index===slides.length-1;document.querySelector('#progress').style.width=`${(index+1)/slides.length*100}%`;if(update)history.replaceState(null,'',`#${index+1}`);}
  function fromHash(){const n=parseInt(location.hash.slice(1),10);show(Number.isFinite(n)?n-1:0,false);}
  function controls(){document.body.classList.add('show-controls');clearTimeout(timer);timer=setTimeout(()=>document.body.classList.remove('show-controls'),2400);}
  async function fullscreen(){try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen();}catch(e){controls();}}
  prev.onclick=()=>show(index-1);next.onclick=()=>show(index+1);document.querySelector('#fullscreen').onclick=fullscreen;document.querySelector('#print').onclick=()=>window.print();
  addEventListener('keydown',e=>{if(e.target.closest('input,textarea,select'))return;if(e.key===' '&&e.target.closest('button,a'))return;if(['ArrowRight','ArrowDown',' ','PageDown'].includes(e.key)){e.preventDefault();show(index+1)}else if(['ArrowLeft','ArrowUp','PageUp','Backspace'].includes(e.key)){e.preventDefault();show(index-1)}else if(e.key==='Home'){e.preventDefault();show(0)}else if(e.key==='End'){e.preventDefault();show(slides.length-1)}else if(e.key.toLowerCase()==='f'){e.preventDefault();fullscreen()}else if(e.key==='Escape'){controls()}});
  let touchX=0;addEventListener('touchstart',e=>{touchX=e.changedTouches[0].clientX},{passive:true});addEventListener('touchend',e=>{const dx=e.changedTouches[0].clientX-touchX;if(Math.abs(dx)>50)show(index+(dx<0?1:-1));else controls()},{passive:true});
  addEventListener('hashchange',fromHash);addEventListener('resize',resize);addEventListener('mousemove',controls);addEventListener('focusin',controls);
  // El texto aprobado conserva su tamaño salvo ajuste mínimo por métricas tipográficas del navegador.
  async function fit(){await document.fonts.ready;document.querySelectorAll('.text').forEach(el=>{let tries=0;while((el.scrollHeight>el.clientHeight+1||el.scrollWidth>el.clientWidth+1)&&tries++<9){el.querySelectorAll('span,a').forEach(s=>s.style.fontSize=(parseFloat(s.style.fontSize)*.985)+'px')}});document.documentElement.dataset.ready='true';}
  addEventListener('beforeprint',()=>slides.forEach(s=>s.inert=false));addEventListener('afterprint',()=>show(index,false));
  resize();fromHash();controls();fit();
})();
'''
(D/'estilos.css').write_text(css)
(D/'presentacion.js').write_text(js)
(D/'index.html').write_text('''<!doctype html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#611232"><title>Datisa · Buscar, extraer, responder</title><link rel="icon" href="data:,"><link rel="stylesheet" href="estilos.css"></head><body><main id="viewport"><div id="deck">'''+''.join(slides)+'''</div></main><nav id="controls" aria-label="Controles de presentación"><button id="prev" aria-label="Diapositiva anterior" title="Anterior · ←">←</button><span id="counter" aria-live="polite"></span><button id="next" aria-label="Diapositiva siguiente" title="Siguiente · →">→</button><button id="fullscreen" aria-label="Pantalla completa" title="Pantalla completa · F">⛶</button><button id="print" aria-label="Imprimir o guardar PDF" title="Imprimir o guardar PDF">⎙</button></nav><div id="hint">← → / Espacio · F pantalla completa</div><div id="progress" aria-hidden="true"></div><script src="presentacion.js"></script></body></html>''')
(D/'contenido_fuente.json').write_text(json.dumps(source,ensure_ascii=False,indent=2)+'\n')
(D/'mapa_figuras.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'slides':len(slides),'figures_mapped':len(audit),'out':str(D)},ensure_ascii=False))

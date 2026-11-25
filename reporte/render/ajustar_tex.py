from pathlib import Path
import re
p=Path('render/pandoc_original.tex')
s=p.read_text()
b=chr(92)
s=s.replace(b+'begin{document}', b+'usepackage{float}'+b+'usepackage{xurl}'+b+'usepackage{needspace}'+chr(10)+b+'begin{document}')
s=s.replace(b+'begin{figure}',b+'begin{figure}[H]')
s=s.replace(b+'caption{Figura', b+'caption*{Figura')
s=s.replace('width=0.88'+b+'textwidth,height=7cm', 'width=0.88'+b+'textwidth,height=7.6cm,keepaspectratio')
s=s.replace('width=0.88'+b+'textwidth,height=6.7cm', 'width=0.88'+b+'textwidth,height=6.7cm,keepaspectratio')
# Columna ancha para nombres y anchura fija para ternas métricas.
repartos={1:[.20,.29,.51],2:[.69,.31],6:[.16]+[.14]*6,8:[.315,.06,.06,.065]*2}
patron=r'(\\begin\{longtable\}.*?\\end\{longtable\})'
def tabla(i,t):
    if i in repartos:
        cuotas=iter(repartos[i])
        t=re.sub(r'\\real\{[0-9.]+\}',lambda _: b+'real{'+str(next(cuotas))+'}',t)
    return '{'+(b+'fontspec{Liberation Sans}' if i==6 else '')+b+'small\n'+t+'\n}'
partes=re.split(patron,s,flags=re.S)
assert len(partes)==17
for i,n in enumerate(range(1,len(partes),2),1):
    partes[n]=tabla(i,partes[n])
s=''.join(partes)
s=s.replace(b+'textbf{Tabla 2.',b+'Needspace{8'+b+'baselineskip}'+b+'textbf{Tabla 2.')
s=s.replace(b+'textbf{Tabla 4.',b+'Needspace{14'+b+'baselineskip}'+b+'textbf{Tabla 4.')
s=s.replace(b+'textbf{Tabla 8.',b+'Needspace{7'+b+'baselineskip}'+b+'textbf{Tabla 8.')
s=re.sub(r'(?m)('+re.escape(b+'emph{Fuentes:')+r'[\s\S]*?)(?=\.\})', lambda m: re.sub(r'(?:salida|data)/[a-zA-Z0-9_/.'+re.escape(b)+r'-]+(?:csv|json|md)',lambda path: b+'nolinkurl{'+path.group().replace(b+'_','_')+'}',m[0]),s)

s=s.replace(b+'setlength{'+b+'parskip}{4pt}',b+'setlength{'+b+'parskip}{4pt}')
s=re.sub(re.escape(b+'emph{')+r'(Fuentes?:[^}]*?)\}',lambda m: '{'+b+'small '+b+'emph{'+m[1]+'}}',s)
figuras=re.split(r'(\\begin\{figure\}\[H\].*?\\end\{figure\})',s,flags=re.S)
for i in range(1,len(figuras),2):
    if 's6_ap_por_consulta' in figuras[i]:
        figuras[i]='{'+b+'setlength{'+b+'intextsep}{3pt}'+b+'captionsetup{skip=3pt}'+figuras[i]+b+'par}'
s=''.join(figuras)
s=s.replace('10 000','10~000')
s=re.sub(r'IC del\s+95\s+'+re.escape(b+'%'), lambda _: 'IC del~95~'+b+'%', s)
Path('render/reporte_v2.tex').write_text(s)

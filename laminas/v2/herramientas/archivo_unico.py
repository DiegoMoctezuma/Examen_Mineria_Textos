"""Incluye los recursos locales en un HTML autónomo. Solo usa la biblioteca estándar."""
from pathlib import Path
import argparse,base64,html,re
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('html',type=Path)
a=p.parse_args();source=a.html.resolve();folder=source.parent
css=(folder/'estilos.css').read_text(encoding='utf-8')
def font(m):
    f=folder/m[1];mime='font/otf' if f.suffix=='.otf' else 'font/ttf'
    return 'url(data:'+mime+';base64,'+base64.b64encode(f.read_bytes()).decode()+')'
css=re.sub(r'url\((fonts/[^)]+)\)',font,css)
s=source.read_text(encoding='utf-8').replace('<link rel="stylesheet" href="estilos.css">','<style>'+css+'</style>').replace('<script src="presentacion.js"></script>','<script>'+(folder/'presentacion.js').read_text(encoding='utf-8')+'</script>')
def image(m):
    f=(folder/m[1]).resolve()
    if not f.exists():return m[0]  # P11–P15 mantienen su marcador y su sustitución automática.
    return 'src="data:image/png;base64,'+base64.b64encode(f.read_bytes()).decode()+'"'
s=re.sub(r'src="((?:img/|../../salida/)[^"]+)"',image,s)
licenses='\n\n'.join(f.read_text(encoding='utf-8') for f in (folder/'fonts').glob('*.txt'))
s=s.replace('</body>','<template id="font-licenses">'+html.escape(licenses)+'</template></body>')
out=folder/'Presentacion_Datisa_v2.html';out.write_text(s,encoding='utf-8');print(out)

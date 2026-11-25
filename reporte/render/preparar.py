from pathlib import Path
import re

md = Path("reporte_v2.md").read_text()
b = chr(92)

def extraer(patron, texto):
    m = re.search(patron, texto, re.S)
    assert m, patron
    return m[1]

def portada(m):
    bloque = m[1]
    tipo = extraer(r'<p class="tipo">(.*?)</p>', bloque)
    titulo = extraer(r'<h1>(.*?)</h1>', bloque).replace(" sobre ", b+"newline sobre ", 1)
    equipo = extraer(r'<p class="equipo">(.*?)</p>', bloque)
    nombres = re.findall(r'<li>(.*?)</li>', bloque)
    fecha = extraer(r'<time[^>]*>(.*?)</time>', bloque)
    url = extraer(r'<a href="([^"]+)">', bloque).replace("_", b+"_")
    enlace = fecha + r" \enspace·\enspace \href{" + url + "}{Repositorio del proyecto}"
    assert len(nombres)==5
    return "\n"+b+"cabecera"+"".join("{"+x+"}" for x in [tipo,titulo,equipo,*nombres,enlace])+"\n"

md = re.sub(r'<header class="cabecera-articulo">(.*?)</header>', portada, md, flags=re.S)
md = re.sub(r'<p class="nota">(.*?)</p>', r'*\1*', md)
def figura(m):
    ruta, pie = m.groups()
    altura = "7cm" if "Figura 2." in pie else "6.7cm"
    return f"![{pie}]({ruta}){{width=88% height={altura}}}"
md = re.sub(r'<figure[^>]*><img src="([^"]+)"[^>]*><figcaption>(.*?)</figcaption></figure>',
            figura, md)
Path("render/entrada.md").write_text(md)

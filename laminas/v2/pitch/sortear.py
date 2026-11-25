"""Reproduce el sorteo con restricciones. --nuevo crea otra semilla, sin sobrescribir el reparto."""
from pathlib import Path
import argparse,itertools,json,random,secrets

TIEMPOS=[20,50,50,20,45,50,30,35,45,45,40,30,35,50,60,30,30,55,40,30,50,30,50,150,45,15]
BLOQUES=[[2,3],[5,6],[7,8,9],[10,11],[12,13],[14,15],[16,17],[18,19],[21,22,23],[25]]
NOMBRES=['Leo Yahir Carpio Angeles','Arturo Jaramillo Salmerón','Gonzalo Sebastian Mera Montiel','Diego Rafael Moctezuma Ramirez','Luis Ramirez Maza']

def sortear(semilla):
    viables=[]
    for k in range(1,5):
        for ids in itertools.combinations(range(len(BLOQUES)),k):
            slides=sorted(sum([BLOQUES[i] for i in ids],[]))
            duracion=sum(TIEMPOS[i-1] for i in slides)
            if len(slides) in [5,6] and 210<=duracion<=235:
                viables.append((set(ids),slides,duracion))
    soluciones=[]
    def cubrir(restantes,elegidos):
        if not restantes:
            if len(elegidos)==4:soluciones.append(elegidos)
            return
        primero=min(restantes)
        for grupo in viables:
            if primero in grupo[0] and grupo[0]<=restantes:
                cubrir(restantes-grupo[0],elegidos+[grupo])
    cubrir(set(range(len(BLOQUES))),[])
    rng=random.Random(semilla)
    elegida=rng.choice(soluciones)
    roles=[{'slides':[1,4,20,24,26],'seconds':235}]+[{'slides':g[1],'seconds':g[2]} for g in elegida]
    nombres=NOMBRES.copy();rng.shuffle(nombres)
    for rol,nombre in zip(roles,nombres):rol['name']=nombre
    return {'seed':semilla,'feasible_partitions':len(soluciones),'total_seconds':sum(TIEMPOS),'slide_seconds':TIEMPOS,'roles':roles}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--semilla',type=int)
    p.add_argument('--nuevo',action='store_true')
    p.add_argument('--salida',type=Path)
    args=p.parse_args()
    guardado=json.loads(Path(__file__).with_name('reparto.json').read_text())
    semilla=secrets.randbits(32) if args.nuevo else (args.semilla if args.semilla is not None else guardado['seed'])
    resultado=sortear(semilla)
    if not args.nuevo and semilla==guardado['seed']:
        assert all(resultado[k]==guardado[k] for k in resultado),'El sorteo no coincide con el guardado'
    texto=json.dumps(resultado,ensure_ascii=False,indent=2)+'\n'
    if args.salida:
        if args.salida.exists():raise FileExistsError('La salida ya existe; usa un nombre nuevo')
        args.salida.write_text(texto)
    else:print(texto,end='')

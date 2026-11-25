"""Exporta los datos ya evaluados a SVG/HTML de proyección; no recalcula métricas."""
from pathlib import Path
import importlib.util,json,sys,hashlib,base64,math
import numpy as np
R=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(R/'src'))
spec=importlib.util.spec_from_file_location('figuras_script',R/'scripts/11b_figuras_v2.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def normalizar(v):
    if isinstance(v,np.ndarray):return [normalizar(x) for x in v.tolist()]
    if isinstance(v,np.generic):return normalizar(v.item())
    if isinstance(v,float) and not math.isfinite(v):return None
    if isinstance(v,dict) and 'bdata' in v and 'dtype' in v:
        return normalizar(np.frombuffer(base64.b64decode(v['bdata']),dtype=v['dtype']))
    if isinstance(v,dict):return {k:normalizar(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [normalizar(x) for x in v]
    return v
cx=m.Contexto();out={}
for nombre,fn in m.FIGURAS.items():
    fig,version,usadas=fn(cx)
    out[nombre]={'version':version,'figura':normalizar(fig.to_dict())}
path=R/'laminas/v2/figuras/datos_figuras.json'
path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(path)

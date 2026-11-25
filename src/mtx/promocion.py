"""Promoción de los seis CSV v2 a la raíz (PRD v2 D28, WP-14, `make promover-v2`).

La entrega v2 lleva en la raíz los seis CSV de v2: `ranking.csv` con las 4 variantes del
preprocesamiento ganador y nombres de v1 (D28), los juicios agregados por mayoría, sus resultados
IR, las entidades v2, el gold oficial v2 y sus resultados IE. Son copias byte a byte de
`salida/v2/`, y la promoción queda registrada en `salida/v2/promocion_raiz.json` con el sha256 de
cada archivo.

v1 no se pierde: sus seis CSV siguen en `salida/` y `anotaciones/` (de donde la raíz era copia) y
en la etiqueta `v1.0-entrega`. Desde la promoción, los objetivos de v1 que escriben en la raíz
(`make ranking`, `make evaluar-ir`, `make extraer`, `make evaluar-ie`) se niegan a correr:
`bloquear_v1()`.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from mtx import config

NOMBRES = ("ranking.csv", "juicios_relevancia.csv", "resultados_ir.csv", "entidades.csv",
           "gold_entidades.csv", "resultados_ie.csv")
REQUISITOS = ("data/v2/mejor_modelo.json", "salida/v2/05_robustez.csv",
              "salida/v2/09_referencias_f1.csv", "anotaciones/cierre_juicios_v2.json",
              "anotaciones/cierre_gold_v2.json")


def registro(raiz: Path = config.RAIZ) -> Path:
    return raiz / "salida" / "v2" / "promocion_raiz.json"


def raiz_es_v2(raiz: Path = config.RAIZ) -> bool:
    return registro(raiz).exists()


def bloquear_v1(objetivo: str, raiz: Path = config.RAIZ) -> None:
    """Detiene un objetivo de v1 que escribe en la raíz cuando la raíz ya es v2."""
    if raiz_es_v2(raiz):
        raise SystemExit(
            f"`make {objetivo}` es de v1 y escribiría en la raíz, que desde la promoción tiene los "
            "CSV v2 (salida/v2/promocion_raiz.json). v1 se reproduce desde su etiqueta: "
            "`git worktree add ../v1 v1.0-entrega`.")


def _sha(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


@dataclass
class Informe:
    ok: bool
    errores: list[str] = field(default_factory=list)
    copiados: list[str] = field(default_factory=list)


def promover(raiz: Path = config.RAIZ) -> Informe:
    """Copia los seis CSV de `salida/v2/` a la raíz y registra sus sha256. No toca nada si falta
    un requisito; volver a promover con los mismos archivos deja todo igual."""
    v2 = raiz / "salida" / "v2"
    faltan = [r for r in REQUISITOS if not (raiz / r).exists()]
    faltan += [f"salida/v2/{n}" for n in NOMBRES if not (v2 / n).exists()]
    if faltan:
        return Informe(False, [f"falta {f} (cierres y `make all-v2`)" for f in faltan])
    copiados = []
    for n in NOMBRES:
        destino = raiz / n
        if not destino.exists() or destino.read_bytes() != (v2 / n).read_bytes():
            shutil.copyfile(v2 / n, destino)
            copiados.append(n)
    p = subprocess.run(["git", "rev-parse", "HEAD"], cwd=raiz, capture_output=True, text=True,
                       check=False)
    previo = json.loads(registro(raiz).read_text(encoding="utf-8")) if raiz_es_v2(raiz) else {}
    nuevo = {"regla": "D28: la raíz lleva los seis CSV de v2, copia byte a byte de salida/v2/",
             "sha256": {n: _sha(raiz / n) for n in NOMBRES},
             "sha256_mejor_modelo_v2": _sha(raiz / "data" / "v2" / "mejor_modelo.json")}
    if {k: previo.get(k) for k in nuevo} != nuevo:
        nuevo = {"fecha": datetime.now().isoformat(timespec="seconds"),
                 "commit": p.stdout.strip(), **nuevo}
        registro(raiz).write_text(json.dumps(nuevo, ensure_ascii=False, indent=2) + "\n",
                                  encoding="utf-8")
    return Informe(True, copiados=copiados)


def verificar(raiz: Path = config.RAIZ) -> list[str]:
    """Problemas de la raíz promovida: cada CSV debe ser copia de `salida/v2/` y coincidir con el
    sha256 registrado."""
    reg = json.loads(registro(raiz).read_text(encoding="utf-8"))
    det = []
    for n in NOMBRES:
        ruta, origen = raiz / n, raiz / "salida" / "v2" / n
        if not ruta.exists():
            det.append(f"{n}: falta en la raíz")
        elif not origen.exists() or origen.read_bytes() != ruta.read_bytes():
            det.append(f"{n}: no es copia de salida/v2/{n} (`make promover-v2`)")
        elif reg.get("sha256", {}).get(n) != _sha(ruta):
            det.append(f"{n}: no coincide con salida/v2/promocion_raiz.json (`make promover-v2`)")
    return det

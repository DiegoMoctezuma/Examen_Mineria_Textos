"""Manifiesto de ejecución (D18): una entrada por script con hashes de entradas y salidas, commit
del código y duración. `salida/manifiesto_ejecucion.json` y `salida/tiempos_ejecucion.json`."""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path

from mtx import config

MANIFIESTO = config.DIR_SALIDA / "manifiesto_ejecucion.json"
TIEMPOS = config.DIR_SALIDA / "tiempos_ejecucion.json"


def sha256(ruta: Path) -> str:
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def git(*args: str) -> str:
    r = subprocess.run(["git", *args], cwd=config.RAIZ, capture_output=True, text=True,
                       check=False)
    return r.stdout.strip()


def _rel(ruta: Path) -> str:
    try:
        return str(Path(ruta).resolve().relative_to(config.RAIZ))
    except ValueError:
        return str(ruta)


def registrar(paso: str, entradas: list[Path], salidas: list[Path], segundos: float,
              extra: dict | None = None) -> None:
    """Agrega o reemplaza la entrada `paso` en ambos archivos."""
    man = json.loads(MANIFIESTO.read_text(encoding="utf-8")) if MANIFIESTO.exists() else {}
    man[paso] = {"fecha": datetime.now().isoformat(timespec="seconds"),
                 "commit": git("rev-parse", "--short", "HEAD"),
                 "arbol_limpio": git("status", "--porcelain", "--", "src", "scripts",
                                     "config") == "",
                 "entradas": {_rel(p): sha256(p) for p in entradas},
                 "salidas": {_rel(p): sha256(p) for p in salidas}, **(extra or {})}
    MANIFIESTO.write_text(json.dumps(man, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
    tie = json.loads(TIEMPOS.read_text(encoding="utf-8")) if TIEMPOS.exists() else {}
    tie[paso] = round(segundos, 2)
    TIEMPOS.write_text(json.dumps(tie, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

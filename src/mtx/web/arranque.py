"""Arranque de la demo en el servidor: descarga los artefactos pesados que no están en git.

En local no hace nada (los archivos ya están en `data/`). En Streamlit Community Cloud baja de un
repositorio de datos de Hugging Face los archivos de `artefactos_demo.json`, en la revisión fijada
ahí, y comprueba su sha256 antes de usarlos. Si el repositorio es privado, el token va en los
secretos de la app como `HF_TOKEN` (nunca en git).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

MANIFIESTO = Path(__file__).with_name("artefactos_demo.json")


def sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def faltantes(raiz: Path, manifiesto: dict) -> list[str]:
    return [p for p in manifiesto["archivos"] if not (raiz / p).exists()]


def asegurar_artefactos(raiz: Path, manifiesto_ruta: Path = MANIFIESTO) -> list[str]:
    """Descarga lo que falte y verifica su sha256. Devuelve las rutas descargadas."""
    if not manifiesto_ruta.exists():
        return []
    m = json.loads(manifiesto_ruta.read_text(encoding="utf-8"))
    pendientes = faltantes(raiz, m)
    if not pendientes:
        return []
    from huggingface_hub import hf_hub_download
    for ruta in pendientes:
        hf_hub_download(m["repo_id"], ruta, repo_type="dataset", revision=m["revision"],
                        local_dir=raiz)
        esperado = m["archivos"][ruta]
        if sha256(raiz / ruta) != esperado:
            (raiz / ruta).unlink()
            raise RuntimeError(f"{ruta}: el sha256 no coincide con artefactos_demo.json")
    return pendientes

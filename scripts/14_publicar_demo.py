"""14 · Empaqueta los artefactos pesados de la demo web y los sube a Hugging Face (PRD v2 WP-15).

`uv run python scripts/14_publicar_demo.py --repo USUARIO/NOMBRE` revisa y muestra qué subiría.
Con `--subir` crea (si no existe) el repositorio de datos y sube los archivos; después escribe
`src/mtx/web/artefactos_demo.json` con la revisión y los sha256, que la app usa al arrancar en el
servidor (`web/arranque.py`). Nunca sube nada sin `--subir`. El token es el de `hf auth login`.

Solo van los archivos que la demo necesita y que no están en git (índice, TF-IDF y pasajes); antes
de subirlos se comprueba que correspondan a `data/indice_meta.json`.
"""
from __future__ import annotations

import argparse
import json
import sys

from mtx import config, corpus
from mtx.web import arranque
from mtx.web import datos as D

ARCHIVOS = ["data/pasajes.parquet", "data/indice.pkl", "data/tokens.parquet", "data/tfidf.pkl",
            "data/tfidf_X.npz"]


def verificar() -> list[str]:
    """Errores de correspondencia con `data/indice_meta.json` (vacío si todo cuadra)."""
    import pandas as pd

    meta = json.loads(config.INDICE_META.read_text(encoding="utf-8"))
    errores = []
    for ruta in ARCHIVOS:
        if not (config.RAIZ / ruta).exists():
            errores.append(f"Falta {ruta}: correr `make corpus indice`")
    if errores:
        return errores
    if arranque.sha256(config.INDICE_PKL) != meta["sha256_indice"]:
        errores.append("data/indice.pkl no corresponde a indice_meta.json")
    if arranque.sha256(config.TFIDF_PKL) != meta["tfidf"]["sha256_pkl"]:
        errores.append("data/tfidf.pkl no corresponde a indice_meta.json")
    if corpus.hash_pasajes(pd.read_parquet(config.PASAJES_PARQUET)) != meta["sha256_pasajes"]:
        errores.append("data/pasajes.parquet no corresponde a indice_meta.json")
    # tokens: lo verifica `cargar_buscador` al arrancar; tfidf_X.npz: el zip guarda fechas y su
    # sha256 cambia en cada `make indice`, así que se fija el de la copia subida.
    return errores


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", required=True, help="repositorio de datos, p. ej. usuario/datisa-demo")
    ap.add_argument("--publico", action="store_true",
                    help="crearlo público (por omisión, privado: la app necesita HF_TOKEN)")
    ap.add_argument("--subir", action="store_true", help="subir de verdad")
    a = ap.parse_args()

    errores = verificar()
    for e in errores:
        print(f"ERROR: {e}")
    if errores:
        return 1
    hashes = {r: arranque.sha256(config.RAIZ / r) for r in ARCHIVOS}
    total = sum((config.RAIZ / r).stat().st_size for r in ARCHIVOS) / 1e6
    print(f"Versión de datos de la demo: {D.version_datos()}")
    print(f"Archivos ({total:.0f} MB) → dataset {a.repo} "
          f"({'público' if a.publico else 'privado'}):")
    for r, h in hashes.items():
        print(f"  {r}  {(config.RAIZ / r).stat().st_size / 1e6:6.1f} MB  {h[:12]}")
    if not a.subir:
        print("\nNo se subió nada. Repite con --subir para publicarlos.")
        return 0

    from huggingface_hub import HfApi
    api = HfApi()
    api.create_repo(a.repo, repo_type="dataset", private=not a.publico, exist_ok=True)
    info = api.upload_folder(repo_id=a.repo, repo_type="dataset", folder_path=config.RAIZ,
                             allow_patterns=ARCHIVOS,
                             commit_message="Artefactos de la demo web (WP-15)")
    revision = info.oid
    manifiesto = {"repo_id": a.repo, "revision": revision, "version_datos": D.version_datos(),
                  "archivos": hashes}
    arranque.MANIFIESTO.write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2) + "\n",
                                   encoding="utf-8")
    print(f"\nSubido en la revisión {revision}. Manifiesto: {arranque.MANIFIESTO.relative_to(config.RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Configuración común de pytest.

`make setup` descarga las stopwords de NLTK en `.nltk_data/` (en la raíz del repo), una ruta que
NLTK no busca por omisión. Se agrega aquí para que la prueba que compara el respaldo versionado
`config/stopwords_es.txt` con NLTK no se salte. Sin esa carpeta, la prueba se salta como antes.
"""
from __future__ import annotations

from pathlib import Path

DIR_NLTK = Path(__file__).resolve().parents[1] / ".nltk_data"

if DIR_NLTK.is_dir():
    try:
        import nltk
    except ImportError:  # pragma: no cover
        pass
    else:
        if str(DIR_NLTK) not in nltk.data.path:
            nltk.data.path.append(str(DIR_NLTK))

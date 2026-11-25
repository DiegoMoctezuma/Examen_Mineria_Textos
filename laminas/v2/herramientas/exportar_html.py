"""Genera la versión vigente para proyección (26 láminas, contenido aprobado conservado)."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name('proyeccion.py')),run_name='__main__')

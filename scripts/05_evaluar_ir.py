"""05 · Evaluación de IR (PRD §6.6, D08). `make evaluar-ir`.

Exige juicios completos y válidos en anotaciones/juicios_relevancia.csv; si faltan, imprime lo
pendiente y sale con código 1 sin escribir nada. Si pasan, los copia a la raíz y produce:

- resultados_ir.csv (raíz y salida/): salida íntegra de `kit/evaluar.py ir` (cifra oficial);
- salida/05_juicios_con_ventana.csv, 05_resultados_ir_ventana.csv y 05_relevantes_por_ventana.csv
  (vista complementaria);
- salida/05_ir_por_consulta.csv y 05_ir_ganador_por_consulta.csv (etiquetas calculadas);
- data/mejor_modelo.json (D08), reporte/figuras/ir_*.png y salida/05_registro_evaluacion.json.
"""
from __future__ import annotations

import sys

from mtx import config, evaluacion


def main() -> int:
    inf = evaluacion.ejecutar_ir()
    if not inf.ok:
        print("No se evalúa. Pendiente:", *inf.errores, sep="\n- ")
        if any("Cobertura incompleta" in e for e in inf.errores):
            print("\nTermina los juicios en `make app` (pestaña Juicios) y vuelve a correr "
                  "`make evaluar-ir`.")
        return 1
    m = inf.mejor
    print(f"Mejor modelo (D08): {m['modelo']} con MAP {m['MAP']:.4f}; alternativa "
          f"{m['alternativa']} con {m['MAP_alternativa']:.4f}.")
    for a in inf.avisos:
        print(f"AVISO: {a}")
    print("Escritos:", *(str(p.relative_to(config.RAIZ)) if p.is_relative_to(config.RAIZ)
                         else str(p) for p in inf.escritos), sep="\n- ")
    return 0


if __name__ == "__main__":
    sys.exit(main())

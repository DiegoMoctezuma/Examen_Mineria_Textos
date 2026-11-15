"""Gold v2: doble anotación ciega, dos pasadas, adjudicación y acuerdo (PRD v2 D31 a D33, WP-09).

Archivos en `anotaciones/gold_v2/` (solo la app los escribe; cada quien el suyo):

- `<anotador>.csv`: `passage_id,tipo,texto,inicio,fin,pasada`. Pasada 1: PER, ORG, LOC y MONTO;
  pasada 2: solo FECHA (D33).
- `<anotador>_estado.csv`: `passage_id,texto_sha256,pasada,estado,n_entidades,revision`.
- `adjudicado_<adjudicador>.csv`: los candidatos de cada pasaje adjudicado
  (`passage_id,pasada,tipo,texto,inicio,fin,propuesta,decision`). `propuesta` es `ambos` (los dos
  anotadores coinciden en tipo e intervalo) o el id de quien la propuso; `decision` es `incluir`,
  `excluir` o vacío (pendiente). Un archivo por adjudicador, para que cada quien integre solo el
  suyo por su rama `anotacion/<id>`; el gold oficial (`gold_oficial()`) los une.
- `adjudicado_<adjudicador>_estado.csv`: `passage_id,pasada,estado,huella,revision`. La huella
  fija las dos anotaciones que se adjudicaron: si una cambia, la adjudicación queda obsoleta.

Modo ciego: quien anota solo lee su archivo (y, en la parte `v1`, su propio gold v1 como
contexto); quien adjudica lee los dos archivos de las partes que adjudica. Nada aquí lee
predicciones del sistema (`salida/entidades*.csv`, `data/cache_ner/`).
"""
from __future__ import annotations

import hashlib
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from mtx import anotadores, config
from mtx import gold as G
from mtx.app import componentes as C

SUBDIR = "gold_v2"
TIPOS_PASADA = {1: ("PER", "ORG", "LOC", "MONTO"), 2: ("FECHA",)}
COLUMNAS_GOLD = ["passage_id", "tipo", "texto", "inicio", "fin", "pasada"]
COLUMNAS_ESTADO = ["passage_id", "texto_sha256", "pasada", "estado", "n_entidades", "revision"]
COLUMNAS_ADJ = ["passage_id", "pasada", "tipo", "texto", "inicio", "fin", "propuesta", "decision"]
COLUMNAS_ESTADO_ADJ = ["passage_id", "pasada", "estado", "huella", "revision"]
AMBOS, INCLUIR, EXCLUIR = "ambos", "incluir", "excluir"
ABIERTO, CERRADO = G.ABIERTO, G.CERRADO
ETIQUETA_FECHA = "reglas-fecha-v2"


# =========================================================================== configuración


@dataclass(frozen=True)
class Parte:
    id: str
    nombre: str
    manifiesto: Path
    anotadores: tuple[str, ...]
    adjudicador: str | None
    pasadas: tuple[int, ...]

    @property
    def doble(self) -> bool:
        return len(self.anotadores) == 2


@dataclass(frozen=True)
class ConfigGold:
    partes: dict[str, Parte]
    no_anotan: tuple[str, ...]
    pasada_2_sin_etiqueta: bool


def dir_anotaciones() -> Path:
    return Path(os.environ.get("MTX_ANOTACIONES", config.DIR_ANOTACIONES))


def cargar_config(ruta: Path | None = None, dir_anot: Path | None = None) -> ConfigGold:
    """Partes del gold v2 de `config/v2/anotadores.yaml`. `ValueError` si rompe una regla de
    D31: ids desconocidos, adjudicador que también anota, parte doble sin adjudicador, alguien de
    `no_anotan` con un papel, o una persona que anota dos partes que se adjudican entre sí."""
    ruta = ruta or anotadores.ruta_anotadores()
    dir_anot = Path(dir_anot or dir_anotaciones())
    lista = anotadores.cargar_anotadores(ruta)
    datos = config.cargar_yaml(ruta.name, ruta.parent).get("gold") or {}
    no_anotan = tuple(datos.get("no_anotan") or ())
    partes = {}
    for pid, d in (datos.get("partes") or {}).items():
        an = tuple(d["anotadores"])
        adj = d.get("adjudicador")
        pasadas = tuple(int(x) for x in d.get("pasadas", (1, 2)))
        for quien in an + ((adj,) if adj else ()):
            if quien not in lista:
                raise ValueError(f"Parte {pid}: anotador desconocido {quien!r}")
            if quien in no_anotan:
                raise ValueError(f"Parte {pid}: {quien} no anota ni adjudica gold (D31, D33)")
        if len(set(an)) != len(an) or len(an) not in (1, 2):
            raise ValueError(f"Parte {pid}: hacen falta 1 o 2 anotadores distintos")
        if len(an) == 2 and not adj:
            raise ValueError(f"Parte {pid}: una parte con doble anotación necesita adjudicador")
        if adj and adj in an:
            raise ValueError(f"Parte {pid}: el adjudicador no puede anotar la parte")
        if not set(pasadas) <= set(TIPOS_PASADA):
            raise ValueError(f"Parte {pid}: pasadas válidas 1 y 2")
        partes[str(pid)] = Parte(str(pid), str(d.get("nombre", pid)), dir_anot / d["manifiesto"],
                                 an, adj, pasadas)
    return ConfigGold(partes, no_anotan, bool(datos.get("pasada_2_sin_etiqueta", False)))


def etiqueta_existe(nombre: str) -> bool:
    r = subprocess.run(["git", "tag", "-l", nombre], cwd=config.RAIZ, capture_output=True,
                       text=True, check=False)
    return bool(r.stdout.strip())


def pasada_abierta(cfg: ConfigGold, pasada: int) -> bool:
    """La pasada 1 está abierta desde el sorteo; la 2 (FECHA) con `reglas-fecha-v2` (D33) o con
    el recorte declarado en la configuración."""
    if pasada == 1:
        return True
    return cfg.pasada_2_sin_etiqueta or etiqueta_existe(ETIQUETA_FECHA)


def manifiesto(parte: Parte) -> pd.DataFrame | None:
    if not parte.manifiesto.exists():
        return None
    return pd.read_csv(parte.manifiesto, dtype={"passage_id": str, "texto_sha256": str,
                                                "query_id": str})


def partes_de_anotador(cfg: ConfigGold, anotador: str) -> list[Parte]:
    return [p for p in cfg.partes.values() if anotador in p.anotadores]


def partes_de_adjudicador(cfg: ConfigGold, adjudicador: str) -> list[Parte]:
    return [p for p in cfg.partes.values() if p.adjudicador == adjudicador]


def parte_de_pasaje(cfg: ConfigGold, pid: str, anotador: str | None = None) -> Parte | None:
    """La parte (del anotador, si se da) cuyo manifiesto contiene `pid`."""
    for p in cfg.partes.values():
        if anotador and anotador not in p.anotadores:
            continue
        m = manifiesto(p)
        if m is not None and pid in set(m["passage_id"]):
            return p
    return None


# =========================================================================== rutas y lectura


def ruta_gold(dir_anot: Path, anotador: str) -> Path:
    return Path(dir_anot) / SUBDIR / f"{anotador}.csv"


def ruta_estado(dir_anot: Path, anotador: str) -> Path:
    return Path(dir_anot) / SUBDIR / f"{anotador}_estado.csv"


def ruta_adj(dir_anot: Path, adjudicador: str) -> Path:
    return Path(dir_anot) / SUBDIR / f"adjudicado_{adjudicador}.csv"


def ruta_estado_adj(dir_anot: Path, adjudicador: str) -> Path:
    return Path(dir_anot) / SUBDIR / f"adjudicado_{adjudicador}_estado.csv"


def _leer(ruta: Path, columnas: list[str], enteros: tuple[str, ...]) -> pd.DataFrame:
    if not ruta.exists():
        return pd.DataFrame({c: pd.Series(dtype=int if c in enteros else object)
                             for c in columnas})
    df = pd.read_csv(ruta, dtype=str, keep_default_na=False)
    for c in enteros:
        df[c] = df[c].astype(int)
    return df[columnas]


def _csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, lineterminator="\n").encode("utf-8")


def leer_gold(dir_anot: Path, anotador: str) -> pd.DataFrame:
    return _leer(ruta_gold(dir_anot, anotador), COLUMNAS_GOLD, ("inicio", "fin", "pasada"))


def leer_estado(dir_anot: Path, anotador: str) -> pd.DataFrame:
    return _leer(ruta_estado(dir_anot, anotador), COLUMNAS_ESTADO,
                 ("pasada", "n_entidades", "revision"))


def leer_adj(dir_anot: Path, adjudicador: str) -> pd.DataFrame:
    return _leer(ruta_adj(dir_anot, adjudicador), COLUMNAS_ADJ, ("pasada", "inicio", "fin"))


def leer_estado_adj(dir_anot: Path, adjudicador: str) -> pd.DataFrame:
    return _leer(ruta_estado_adj(dir_anot, adjudicador), COLUMNAS_ESTADO_ADJ,
                 ("pasada", "revision"))


def estado_de(estado: pd.DataFrame, pid: str, pasada: int) -> str:
    f = estado[(estado["passage_id"] == pid) & (estado["pasada"] == pasada)]
    return f["estado"].iloc[0] if len(f) else ABIERTO


def _sha_estado(estado: pd.DataFrame, pid: str, pasada: int) -> str | None:
    f = estado[(estado["passage_id"] == pid) & (estado["pasada"] == pasada)]
    return f["texto_sha256"].iloc[0] if len(f) else None


def contexto_v1(dir_anot: Path, parte: Parte, pid: str) -> pd.DataFrame:
    """En la parte `v1` (pasada 2 de FECHA sobre el gold v1, D33), las entidades no FECHA del
    gold v1 de ese pasaje, de solo lectura: son del mismo autor y sirven de contexto."""
    cols = ["passage_id", "tipo", "texto", "inicio", "fin"]
    ruta = Path(dir_anot) / "gold_entidades.csv"
    if parte.id != "v1" or not ruta.exists():
        return pd.DataFrame(columns=cols)
    g = pd.read_csv(ruta, dtype={"passage_id": str, "texto": str}, keep_default_na=False)
    return g[(g["passage_id"] == pid) & (g["tipo"] != "FECHA")][cols].reset_index(drop=True)


# =========================================================================== anotación


def adjudicacion_iniciada(dir_anot: Path, parte: Parte, pid: str, pasada: int) -> bool:
    """Una vez que el adjudicador guardó algo de ese pasaje y pasada, nadie lo reanota."""
    if not parte.adjudicador:
        return False
    adj = leer_adj(dir_anot, parte.adjudicador)
    return bool(((adj["passage_id"] == pid) & (adj["pasada"] == pasada)).any())


@dataclass
class SesionAnotador:
    """Escrituras de una persona sobre su archivo, con las reglas de D31 y D33."""
    dir_anot: Path
    anotador: str
    cfg: ConfigGold

    def token(self) -> str:
        return (C.sha256_ruta(ruta_gold(self.dir_anot, self.anotador))
                + C.sha256_ruta(ruta_estado(self.dir_anot, self.anotador)))

    def cargar(self) -> tuple[pd.DataFrame, pd.DataFrame, str]:
        return (leer_gold(self.dir_anot, self.anotador),
                leer_estado(self.dir_anot, self.anotador), self.token())

    def _comprobar(self, pid: str, pasada: int, tipo: str | None = None) -> Parte:
        parte = parte_de_pasaje(self.cfg, pid, self.anotador)
        if parte is None:
            raise ValueError(f"{pid} no está en ninguna parte asignada a {self.anotador}")
        if pasada not in parte.pasadas:
            raise ValueError(f"La parte {parte.nombre} no tiene pasada {pasada}")
        if not pasada_abierta(self.cfg, pasada):
            raise ValueError("La pasada 2 (FECHA) se abre con la etiqueta `reglas-fecha-v2` "
                             "(D33)")
        if tipo is not None and tipo not in TIPOS_PASADA[pasada]:
            raise ValueError(f"En la pasada {pasada} solo se anota "
                             f"{', '.join(TIPOS_PASADA[pasada])}")
        if adjudicacion_iniciada(self.dir_anot, parte, pid, pasada):
            raise ValueError("Este pasaje ya está en adjudicación: no se reanota")
        return parte

    def _guardar(self, gold: pd.DataFrame, estado: pd.DataFrame, tok: str, pid: str,
                 pasada: int, sha: str, nuevo_estado: str | None) -> str:
        if self.token() != tok:
            raise C.ConflictoEdicion("editado desde otra pestaña: recarga antes de guardar.")
        gold = gold.sort_values(["passage_id", "pasada", "inicio", "fin", "tipo"]).reset_index(
            drop=True)
        n = int(((gold["passage_id"] == pid) & (gold["pasada"] == pasada)).sum())
        clave = (estado["passage_id"] == pid) & (estado["pasada"] == pasada)
        previo = estado[clave]
        rev = int(previo["revision"].iloc[0]) + 1 if len(previo) else 1
        est = nuevo_estado or ABIERTO  # cualquier cambio reabre: hay que revisarlo completo
        fila = pd.DataFrame([{"passage_id": pid, "texto_sha256": sha, "pasada": pasada,
                              "estado": est, "n_entidades": n, "revision": rev}])
        estado = pd.concat([estado[~clave], fila], ignore_index=True).sort_values(
            ["passage_id", "pasada"]).reset_index(drop=True)[COLUMNAS_ESTADO]
        C.escribir_atomico(ruta_gold(self.dir_anot, self.anotador), _csv(gold[COLUMNAS_GOLD]))
        C.escribir_atomico(ruta_estado(self.dir_anot, self.anotador), _csv(estado))
        return self.token()

    def _filas_validacion(self, gold: pd.DataFrame, parte: Parte, pid: str) -> pd.DataFrame:
        """Todas las entidades del pasaje (ambas pasadas y el contexto v1): no se solapan."""
        propias = gold[gold["passage_id"] == pid][["tipo", "texto", "inicio", "fin"]]
        ctx = contexto_v1(self.dir_anot, parte, pid)[["tipo", "texto", "inicio", "fin"]]
        return pd.concat([propias, ctx], ignore_index=True)

    def agregar(self, tok: str, pid: str, pasada: int, texto: str, sha: str, tipo: str,
                ini: int, fin: int) -> str:
        parte = self._comprobar(pid, pasada, tipo)
        gold, estado, _ = self.cargar()
        err = G.errores_span(texto, self._filas_validacion(gold, parte, pid), tipo, ini, fin)
        if err:
            raise ValueError("; ".join(err))
        fila = pd.DataFrame([{"passage_id": pid, "tipo": tipo, "texto": texto[ini:fin],
                              "inicio": ini, "fin": fin, "pasada": pasada}])
        return self._guardar(pd.concat([gold, fila], ignore_index=True), estado, tok, pid,
                             pasada, sha, None)

    def reemplazar(self, tok: str, pid: str, pasada: int, texto: str, sha: str,
                   filas: list[dict]) -> str:
        """Edición de la tabla de la pasada actual (tipo, límites, borrado), validada junta."""
        parte = self._comprobar(pid, pasada)
        gold, estado, _ = self.cargar()
        resto = gold[~((gold["passage_id"] == pid) & (gold["pasada"] == pasada))]
        base = self._filas_validacion(resto, parte, pid)
        nuevas = []
        for f in filas:
            ini, fin, tipo = int(f["inicio"]), int(f["fin"]), f["tipo"]
            if tipo not in TIPOS_PASADA[pasada]:
                raise ValueError(f"En la pasada {pasada} solo se anota "
                                 f"{', '.join(TIPOS_PASADA[pasada])}")
            err = G.errores_span(texto, base, tipo, ini, fin)
            if err:
                raise ValueError("; ".join(err))
            fila = {"passage_id": pid, "tipo": tipo, "texto": texto[ini:fin], "inicio": ini,
                    "fin": fin, "pasada": pasada}
            nuevas.append(fila)
            base = pd.concat([base, pd.DataFrame([fila])[["tipo", "texto", "inicio", "fin"]]],
                             ignore_index=True)
        gold = pd.concat([resto, pd.DataFrame(nuevas, columns=COLUMNAS_GOLD)], ignore_index=True)
        return self._guardar(gold, estado, tok, pid, pasada, sha, None)

    def marcar(self, tok: str, pid: str, pasada: int, sha: str, cerrado: bool) -> str:
        """"Pasaje revisado completo" (válido con cero entidades) o reabrir."""
        self._comprobar(pid, pasada)
        gold, estado, _ = self.cargar()
        return self._guardar(gold, estado, tok, pid, pasada, sha,
                             CERRADO if cerrado else ABIERTO)


# =========================================================================== adjudicación


def _filas(dir_anot: Path, anotador: str, pid: str, pasada: int) -> pd.DataFrame:
    g = leer_gold(dir_anot, anotador)
    return g[(g["passage_id"] == pid) & (g["pasada"] == pasada)]


def listo_para_adjudicar(dir_anot: Path, parte: Parte, pid: str, pasada: int,
                         sha: str | None = None) -> bool:
    """Los dos anotadores cerraron ese pasaje y pasada (con el hash de texto vigente)."""
    for a in parte.anotadores:
        est = leer_estado(dir_anot, a)
        if estado_de(est, pid, pasada) != CERRADO:
            return False
        if sha is not None and _sha_estado(est, pid, pasada) != sha:
            return False
    return True


def huella(dir_anot: Path, parte: Parte, pid: str, pasada: int) -> str:
    """sha256 de las dos anotaciones del pasaje y pasada, en el orden de la configuración."""
    h = hashlib.sha256()
    for a in parte.anotadores:
        f = _filas(dir_anot, a, pid, pasada).sort_values(["inicio", "fin", "tipo"])
        h.update(a.encode())
        h.update(_csv(f[["tipo", "inicio", "fin"]]))
    return h.hexdigest()


def candidatos(dir_anot: Path, parte: Parte, pid: str, pasada: int) -> pd.DataFrame:
    """Unión de las dos anotaciones: `tipo, texto, inicio, fin, propuesta, grupo`. Coincidencia
    = mismo tipo e intervalo (`ambos`). `grupo` numera los desacuerdos que se solapan entre sí,
    para mostrarlos juntos; las coincidencias tienen grupo 0."""
    a1, a2 = parte.anotadores
    f1, f2 = _filas(dir_anot, a1, pid, pasada), _filas(dir_anot, a2, pid, pasada)
    k = lambda f: (f.tipo, int(f.inicio), int(f.fin))
    s1 = {k(f): f.texto for f in f1.itertuples()}
    s2 = {k(f): f.texto for f in f2.itertuples()}
    filas = []
    for clave in sorted(set(s1) | set(s2), key=lambda c: (c[1], c[2], c[0])):
        prop = AMBOS if clave in s1 and clave in s2 else (a1 if clave in s1 else a2)
        filas.append({"tipo": clave[0], "texto": s1.get(clave, s2.get(clave)),
                      "inicio": clave[1], "fin": clave[2], "propuesta": prop, "grupo": 0})
    df = pd.DataFrame(filas, columns=["tipo", "texto", "inicio", "fin", "propuesta", "grupo"])
    g, fin_grupo = 0, -1
    for i in df.index[df["propuesta"] != AMBOS]:  # ya ordenados por inicio
        ini, fin = int(df.at[i, "inicio"]), int(df.at[i, "fin"])
        if ini >= fin_grupo:
            g, fin_grupo = g + 1, fin
        else:
            fin_grupo = max(fin_grupo, fin)
        df.at[i, "grupo"] = g
    return df


@dataclass
class SesionAdjudicador:
    dir_anot: Path
    adjudicador: str
    cfg: ConfigGold

    def token(self) -> str:
        return (C.sha256_ruta(ruta_adj(self.dir_anot, self.adjudicador))
                + C.sha256_ruta(ruta_estado_adj(self.dir_anot, self.adjudicador)))

    def cargar(self) -> tuple[pd.DataFrame, pd.DataFrame, str]:
        return (leer_adj(self.dir_anot, self.adjudicador),
                leer_estado_adj(self.dir_anot, self.adjudicador), self.token())

    def _parte(self, pid: str, pasada: int, sha: str) -> Parte:
        parte = next((p for p in partes_de_adjudicador(self.cfg, self.adjudicador)
                      if (m := manifiesto(p)) is not None and pid in set(m["passage_id"])), None)
        if parte is None:
            raise ValueError(f"{self.adjudicador} no adjudica el pasaje {pid}")
        if self.adjudicador in parte.anotadores:
            raise ValueError("El adjudicador no puede ser anotador del pasaje")
        if not listo_para_adjudicar(self.dir_anot, parte, pid, pasada, sha):
            raise ValueError("Los dos anotadores aún no cierran este pasaje en esta pasada")
        return parte

    def decisiones(self, adj: pd.DataFrame, pid: str, pasada: int) -> dict:
        f = adj[(adj["passage_id"] == pid) & (adj["pasada"] == pasada)]
        return {(r.tipo, int(r.inicio), int(r.fin), r.propuesta): r.decision
                for r in f.itertuples()}

    def _guardar(self, tok: str, parte: Parte, pid: str, pasada: int, decs: dict,
                 nuevo_estado: str) -> str:
        if self.token() != tok:
            raise C.ConflictoEdicion("editado desde otra pestaña: recarga antes de guardar.")
        adj, estado, _ = self.cargar()
        cand = candidatos(self.dir_anot, parte, pid, pasada)
        filas = [{"passage_id": pid, "pasada": pasada, "tipo": c.tipo, "texto": c.texto,
                  "inicio": int(c.inicio), "fin": int(c.fin), "propuesta": c.propuesta,
                  "decision": INCLUIR if c.propuesta == AMBOS else
                  decs.get((c.tipo, int(c.inicio), int(c.fin), c.propuesta), "")}
                 for c in cand.itertuples()]
        clave = (adj["passage_id"] == pid) & (adj["pasada"] == pasada)
        adj = pd.concat([adj[~clave], pd.DataFrame(filas, columns=COLUMNAS_ADJ)],
                        ignore_index=True).sort_values(
            ["passage_id", "pasada", "inicio", "fin", "tipo", "propuesta"]).reset_index(drop=True)
        ce = (estado["passage_id"] == pid) & (estado["pasada"] == pasada)
        rev = int(estado.loc[ce, "revision"].iloc[0]) + 1 if ce.any() else 1
        fila = pd.DataFrame([{"passage_id": pid, "pasada": pasada, "estado": nuevo_estado,
                              "huella": huella(self.dir_anot, parte, pid, pasada),
                              "revision": rev}])
        estado = pd.concat([estado[~ce], fila], ignore_index=True).sort_values(
            ["passage_id", "pasada"]).reset_index(drop=True)[COLUMNAS_ESTADO_ADJ]
        C.escribir_atomico(ruta_adj(self.dir_anot, self.adjudicador), _csv(adj[COLUMNAS_ADJ]))
        C.escribir_atomico(ruta_estado_adj(self.dir_anot, self.adjudicador), _csv(estado))
        return self.token()

    def decidir(self, tok: str, pid: str, pasada: int, sha: str, tipo: str, ini: int, fin: int,
                propuesta: str, decision: str) -> str:
        if decision not in (INCLUIR, EXCLUIR, ""):
            raise ValueError(f"Decisión no válida: {decision!r}")
        parte = self._parte(pid, pasada, sha)
        adj, _, _ = self.cargar()
        decs = self.decisiones(adj, pid, pasada)
        decs[(tipo, int(ini), int(fin), propuesta)] = decision
        return self._guardar(tok, parte, pid, pasada, decs, ABIERTO)

    def marcar(self, tok: str, pid: str, pasada: int, sha: str, texto: str,
               cerrado: bool) -> str:
        parte = self._parte(pid, pasada, sha)
        adj, _, _ = self.cargar()
        decs = self.decisiones(adj, pid, pasada)
        if cerrado:
            err = errores_adjudicacion(candidatos(self.dir_anot, parte, pid, pasada), decs, texto)
            if err:
                raise ValueError("; ".join(err))
        return self._guardar(tok, parte, pid, pasada, decs, CERRADO if cerrado else ABIERTO)


def errores_adjudicacion(cand: pd.DataFrame, decs: dict, texto: str) -> list[str]:
    """Para cerrar un pasaje: todo desacuerdo decidido y lo incluido sin solapes ni duplicados."""
    err, incluidas = [], pd.DataFrame(columns=["tipo", "texto", "inicio", "fin"])
    pendientes = 0
    for c in cand.itertuples():
        d = INCLUIR if c.propuesta == AMBOS else decs.get(
            (c.tipo, int(c.inicio), int(c.fin), c.propuesta), "")
        if d == "":
            pendientes += 1
        elif d == INCLUIR:
            e = G.errores_span(texto, incluidas, c.tipo, int(c.inicio), int(c.fin))
            if e:
                err.append(f"«{c.texto}» ({c.tipo}): {'; '.join(e)}")
            incluidas = pd.concat([incluidas, pd.DataFrame([{
                "tipo": c.tipo, "texto": c.texto, "inicio": int(c.inicio), "fin": int(c.fin)}])],
                ignore_index=True)
    if pendientes:
        err.insert(0, f"Faltan {pendientes} desacuerdos por decidir")
    return err


# =========================================================================== gold oficial y acuerdo


def gold_oficial(cfg: ConfigGold, dir_anot: Path | None = None) -> pd.DataFrame:
    """Gold v2 de los pasajes ya resueltos: en partes dobles, lo que coincide más lo que el
    adjudicador incluyó (pasajes con adjudicación cerrada y vigente); en la parte `v1`, lo que
    anotó su único anotador en pasajes cerrados. Columnas `parte` + `COLUMNAS_GOLD`."""
    dir_anot = Path(dir_anot or dir_anotaciones())
    out = []
    for p in cfg.partes.values():
        if p.doble:
            adj, est = leer_adj(dir_anot, p.adjudicador), leer_estado_adj(dir_anot, p.adjudicador)
            for r in est[est["estado"] == CERRADO].itertuples():
                if r.huella != huella(dir_anot, p, r.passage_id, r.pasada):
                    continue
                f = adj[(adj["passage_id"] == r.passage_id) & (adj["pasada"] == r.pasada)
                        & (adj["decision"] == INCLUIR)]
                out.append(f.assign(parte=p.id))
        else:
            a = p.anotadores[0]
            g, est = leer_gold(dir_anot, a), leer_estado(dir_anot, a)
            m = manifiesto(p)
            ids = set(m["passage_id"]) if m is not None else set()
            cerr = {(r.passage_id, r.pasada) for r in est.itertuples()
                    if r.estado == CERRADO and r.passage_id in ids}
            out.append(g[[(x, y) in cerr for x, y in zip(g["passage_id"], g["pasada"])]]
                       .assign(parte=p.id))
    cols = ["parte"] + COLUMNAS_GOLD
    out = [o[cols] for o in out if len(o)]
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=cols)


COLUMNAS_ACUERDO = ["parte", "pasada", "tipo", "anotador_1", "anotador_2", "pasajes",
                    "n_anotador_1", "n_anotador_2", "coincidencias", "f1"]


def _f1(c: int, n1: int, n2: int) -> float:
    return round(2 * c / (n1 + n2), 4) if n1 + n2 else float("nan")


def acuerdo(cfg: ConfigGold, dir_anot: Path | None = None) -> tuple[pd.DataFrame, list[str]]:
    """Techo humano (D31): F1 exacto (tipo e intervalo) entre los dos anotadores, antes de
    adjudicar, por parte, pasada y tipo, con fila `micro` por parte y parte `todas`. Solo entra
    una parte y pasada cuando los dos cerraron todos sus pasajes; las demás van en `pendientes`."""
    dir_anot = Path(dir_anot or dir_anotaciones())
    filas, pendientes, total = [], [], {}
    for p in cfg.partes.values():
        if not p.doble:
            continue
        m = manifiesto(p)
        if m is None:
            pendientes.append(f"{p.nombre}: falta el manifiesto")
            continue
        ids = list(m["passage_id"])
        for pasada in p.pasadas:
            if not pasada_abierta(cfg, pasada):
                continue
            faltan = {a: sum(estado_de(leer_estado(dir_anot, a), i, pasada) != CERRADO
                             for i in ids) for a in p.anotadores}
            if any(faltan.values()):
                pendientes.append(f"{p.nombre}, pasada {pasada}: faltan " + ", ".join(
                    f"{n} de {a}" for a, n in faltan.items() if n))
                continue
            g = {a: leer_gold(dir_anot, a) for a in p.anotadores}
            sets = {a: {(r.passage_id, r.tipo, int(r.inicio), int(r.fin))
                        for r in g[a][(g[a]["pasada"] == pasada)
                                      & g[a]["passage_id"].isin(ids)].itertuples()}
                    for a in p.anotadores}
            a1, a2 = p.anotadores
            for tipo in TIPOS_PASADA[pasada] + ("micro",):
                s1 = {x for x in sets[a1] if tipo == "micro" or x[1] == tipo}
                s2 = {x for x in sets[a2] if tipo == "micro" or x[1] == tipo}
                c = len(s1 & s2)
                filas.append({"parte": p.id, "pasada": pasada, "tipo": tipo, "anotador_1": a1,
                              "anotador_2": a2, "pasajes": len(ids), "n_anotador_1": len(s1),
                              "n_anotador_2": len(s2), "coincidencias": c,
                              "f1": _f1(c, len(s1), len(s2))})
                t = total.setdefault((pasada, tipo), [0, 0, 0, 0])
                t[0] += len(ids)
                t[1] += len(s1)
                t[2] += len(s2)
                t[3] += c
    for (pasada, tipo), (n_p, n1, n2, c) in sorted(total.items()):
        filas.append({"parte": "todas", "pasada": pasada, "tipo": tipo, "anotador_1": "",
                      "anotador_2": "", "pasajes": n_p, "n_anotador_1": n1, "n_anotador_2": n2,
                      "coincidencias": c, "f1": _f1(c, n1, n2)})
    return pd.DataFrame(filas, columns=COLUMNAS_ACUERDO), pendientes


# =========================================================================== validación


def validar_gold_v2(cfg: ConfigGold, pasajes: pd.DataFrame, dir_anot: Path | None = None,
                    pasadas: tuple[int, ...] = (1, 2),
                    excluir_v1: set[str] | None = None) -> G.ValidacionGold:
    """Comprobación para el cierre del gold v2 (`cierre_gold_v2.json`, vie 20). `pasajes`:
    `passage_id, texto, texto_sha256`. `pasadas`: las que deben estar terminadas. `excluir_v1`:
    ámbito IE de v1, del que las partes nuevas deben ser disjuntas."""
    dir_anot = Path(dir_anot or dir_anotaciones())
    v = G.ValidacionGold()
    info = pasajes.set_index("passage_id")
    mans: dict[str, pd.DataFrame] = {}
    for p in cfg.partes.values():
        m = manifiesto(p)
        if m is None:
            v.errores.append(f"{p.nombre}: falta {p.manifiesto.name}")
            continue
        mans[p.id] = m
        if not m["passage_id"].is_unique:
            v.errores.append(f"{p.nombre}: IDs repetidos en el manifiesto")
        for pid, sha in zip(m["passage_id"], m["texto_sha256"]):
            if pid not in info.index:
                v.errores.append(f"{pid} no existe en data/pasajes.parquet")
            elif info.at[pid, "texto_sha256"] != sha:
                v.errores.append(f"{pid}: el texto cambió desde el sorteo (hash distinto)")
    nuevas = [i for i in mans if i != "v1"]
    for i, a in enumerate(nuevas):
        for b in nuevas[i + 1:]:
            if set(mans[a]["passage_id"]) & set(mans[b]["passage_id"]):
                v.errores.append(f"Las partes {a} y {b} no son disjuntas")
        if "v1" in mans and set(mans[a]["passage_id"]) & set(mans["v1"]["passage_id"]):
            v.errores.append(f"La parte {a} comparte pasajes con el gold v1")
        if excluir_v1 and set(mans[a]["passage_id"]) & excluir_v1:
            v.errores.append(f"La parte {a} tiene pasajes del ámbito IE de v1")

    personas = sorted({a for p in cfg.partes.values() for a in p.anotadores})
    for a in personas:
        ruta = ruta_gold(dir_anot, a)
        if ruta.exists():
            if list(pd.read_csv(ruta, nrows=0).columns) != COLUMNAS_GOLD:
                v.errores.append(f"{ruta.name}: columnas distintas de {COLUMNAS_GOLD}")
                continue
            if ruta.read_bytes()[:3] == b"\xef\xbb\xbf":
                v.errores.append(f"{ruta.name} tiene BOM")
        g = leer_gold(dir_anot, a)
        mias = {pid: p for p in partes_de_anotador(cfg, a) if p.id in mans
                for pid in mans[p.id]["passage_id"]}
        fuera = sorted(set(g["passage_id"]) - set(mias))
        if fuera:
            v.errores.append(f"{a}: entidades de pasajes que no le tocan: {fuera[:5]}")
        for r in g.itertuples():
            if r.pasada not in TIPOS_PASADA or r.tipo not in TIPOS_PASADA[r.pasada]:
                v.errores.append(f"{a}: {r.passage_id} tiene {r.tipo} en la pasada {r.pasada}")
            elif r.passage_id in mias and r.pasada not in mias[r.passage_id].pasadas:
                v.errores.append(f"{a}: {r.passage_id} no tiene pasada {r.pasada}")
        rotas = sum(1 for r in g.itertuples()
                    if not r.texto or r.passage_id not in info.index
                    or not (0 <= r.inicio < r.fin <= len(info.at[r.passage_id, "texto"]))
                    or info.at[r.passage_id, "texto"][r.inicio:r.fin] != r.texto)
        if rotas:
            v.errores.append(f"{a}: {rotas} filas rompen el invariante de offsets")
        if g.duplicated(["passage_id", "tipo", "inicio", "fin"]).any():
            v.errores.append(f"{a}: filas duplicadas en (passage_id, tipo, inicio, fin)")
        for pid, gp in g.groupby("passage_id"):
            gp = gp.sort_values(["inicio", "fin"])
            if (gp["inicio"].to_numpy()[1:] < gp["fin"].to_numpy()[:-1]).any():
                v.errores.append(f"{a}: {pid} tiene entidades solapadas o anidadas")
        est = leer_estado(dir_anot, a)
        for p in partes_de_anotador(cfg, a):
            if p.id not in mans:
                continue
            for pasada in set(p.pasadas) & set(pasadas):
                ids = list(mans[p.id]["passage_id"])
                n = sum(estado_de(est, i, pasada) == CERRADO for i in ids)
                if n < len(ids):
                    v.errores.append(f"{a}, {p.nombre}, pasada {pasada}: cerrados {n} de "
                                     f"{len(ids)}")
                for pid, sha in zip(mans[p.id]["passage_id"], mans[p.id]["texto_sha256"]):
                    s = _sha_estado(est, pid, pasada)
                    if s is not None and s != sha:
                        v.errores.append(f"{a}: {pid} cerrado con otro hash de texto")

    for p in cfg.partes.values():
        if not p.doble or p.id not in mans:
            continue
        est = leer_estado_adj(dir_anot, p.adjudicador)
        adj = leer_adj(dir_anot, p.adjudicador)
        for pasada in set(p.pasadas) & set(pasadas):
            for pid in mans[p.id]["passage_id"]:
                f = est[(est["passage_id"] == pid) & (est["pasada"] == pasada)]
                if f.empty or f["estado"].iloc[0] != CERRADO:
                    v.errores.append(f"{p.nombre}, pasada {pasada}: {pid} sin adjudicar")
                    continue
                if f["huella"].iloc[0] != huella(dir_anot, p, pid, pasada):
                    v.errores.append(f"{p.nombre}: la adjudicación de {pid} (pasada {pasada}) "
                                     "es obsoleta: una anotación cambió después")
                d = adj[(adj["passage_id"] == pid) & (adj["pasada"] == pasada)]
                if (d["decision"] == "").any():
                    v.errores.append(f"{p.nombre}: {pid} con desacuerdos sin decidir")
    of = gold_oficial(cfg, dir_anot)
    n_nuevos = sum(len(mans[i]) for i in nuevas)
    vacios = n_nuevos - of[of["parte"] != "v1"]["passage_id"].nunique()
    if vacios > 0:
        v.avisos.append(f"{vacios} pasajes nuevos sin entidades en el gold oficial: el kit no "
                        "los evalúa (P04)")
    v.esperados = n_nuevos
    return v

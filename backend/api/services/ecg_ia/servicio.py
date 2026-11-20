"""Servicio de inferencia ECG para Django.

Flujo: .zip con el par WFDB (.hea + .dat) -> lectura y validación -> normalización ->
CNN 1D -> sigmoide -> umbrales por clase. Los artefactos (pesos + configuración)
vienen de la corrida `runs/baseline` del repositorio del modelo.

Los puntajes son experimentales y no están calibrados clínicamente.
"""

from __future__ import annotations

import json
import logging
import re
import tempfile
import threading
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np
import torch

from .red import construir_red
from .senal import ORDEN_DERIVACIONES, ErrorECG, leer_ecg, normalizar

log = logging.getLogger(__name__)

DIR_ARTEFACTOS = Path(__file__).resolve().parent / "artefactos"
CLASES = ("NORM", "MI", "STTC", "CD", "HYP")

MAX_ZIP_BYTES = 5 * 1024 * 1024
MAX_DESCOMPRIMIDO_BYTES = 20 * 1024 * 1024
MAX_MIEMBROS = 20
_NOMBRE_SEGURO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}$")


class ErrorPaquete(Exception):
    """El .zip no contiene un par WFDB utilizable. `mensaje` es apto para el participante."""

    def __init__(self, mensaje: str):
        self.mensaje = mensaje
        super().__init__(mensaje)


# -----------------------------------------------------------------------------
# Paquete .zip
# -----------------------------------------------------------------------------

def _miembros_utiles(zf: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    infos = zf.infolist()
    if len(infos) > MAX_MIEMBROS:
        raise ErrorPaquete("El .zip tiene demasiados archivos. Incluya solo el .hea y el .dat del ECG.")
    if sum(i.file_size for i in infos) > MAX_DESCOMPRIMIDO_BYTES:
        raise ErrorPaquete("El contenido del .zip es demasiado grande para un ECG de 10 segundos.")
    miembros: dict[str, zipfile.ZipInfo] = {}
    for info in infos:
        ruta = PurePosixPath(info.filename.replace("\\", "/"))
        if info.is_dir() or "__MACOSX" in ruta.parts or ruta.name.startswith("."):
            continue
        nombre = ruta.name
        if not _NOMBRE_SEGURO.match(nombre):
            raise ErrorPaquete(f"Nombre de archivo no admitido dentro del .zip: {nombre!r}.")
        if nombre in miembros:
            raise ErrorPaquete(f"El .zip contiene dos archivos llamados {nombre}.")
        miembros[nombre] = info
    return miembros


def _archivos_declarados(texto_hea: str) -> list[str]:
    """Nombres de archivo de datos declarados en un encabezado WFDB."""
    lineas = [l.strip() for l in texto_hea.splitlines() if l.strip() and not l.lstrip().startswith("#")]
    if not lineas:
        raise ErrorPaquete("El encabezado .hea está vacío.")
    partes = lineas[0].split()
    try:
        n_senales = int(partes[1])
    except (IndexError, ValueError) as exc:
        raise ErrorPaquete("El encabezado .hea no tiene el formato WFDB esperado.") from exc
    lineas_senal = lineas[1 : 1 + n_senales]
    if n_senales < 1 or len(lineas_senal) != n_senales:
        raise ErrorPaquete("El encabezado .hea está incompleto: no describe todas sus derivaciones.")
    return sorted({l.split()[0] for l in lineas_senal})


def inspeccionar_zip(archivo) -> str:
    """Valida la estructura del .zip sin extraerlo. Devuelve el nombre del .hea."""
    tamano = getattr(archivo, "size", None)
    if tamano is not None and tamano > MAX_ZIP_BYTES:
        raise ErrorPaquete("El archivo supera 5 MB. Un ECG de 10 s en WFDB ocupa unos pocos KB.")
    try:
        archivo.seek(0)
        with zipfile.ZipFile(archivo) as zf:
            miembros = _miembros_utiles(zf)
            heas = [n for n in miembros if n.lower().endswith(".hea")]
            if len(heas) != 1:
                raise ErrorPaquete("El .zip debe contener exactamente un archivo de encabezado .hea.")
            texto = zf.read(miembros[heas[0]]).decode("utf-8", errors="replace")
            faltantes = [n for n in _archivos_declarados(texto) if n not in miembros]
            if faltantes:
                raise ErrorPaquete(
                    f"Falta {', '.join(faltantes)} en el .zip. Incluya el .hea junto con su .dat."
                )
            return heas[0]
    except zipfile.BadZipFile as exc:
        raise ErrorPaquete("El archivo no es un .zip válido.") from exc
    finally:
        try:
            archivo.seek(0)
        except Exception:  # noqa: BLE001
            pass


def extraer_zip(archivo, destino: Path) -> Path:
    """Extrae solo el par WFDB (por nombre base, sin rutas) y devuelve la ruta del .hea."""
    nombre_hea = inspeccionar_zip(archivo)
    with zipfile.ZipFile(archivo) as zf:
        for nombre, info in _miembros_utiles(zf).items():
            if nombre.lower().endswith((".hea", ".dat")):
                (destino / nombre).write_bytes(zf.read(info))
    return destino / nombre_hea


# -----------------------------------------------------------------------------
# Modelo
# -----------------------------------------------------------------------------

@dataclass
class ResultadoModelo:
    puntajes: dict[str, float]
    etiquetas: list[str]
    umbrales: dict[str, float]
    version: str
    tiempo_ms: int


class ModeloECG:
    def __init__(self, directorio: Path = DIR_ARTEFACTOS):
        cfg = json.loads((directorio / "inference_config.json").read_text(encoding="utf-8"))
        if list(cfg["lead_order"]) != list(ORDEN_DERIVACIONES) or list(cfg["class_order"]) != list(CLASES):
            raise RuntimeError("La configuración del modelo no coincide con el orden de derivaciones/clases")
        if not cfg.get("publishable", False):
            raise RuntimeError("El modelo está marcado como no publicable: " + "; ".join(cfg.get("blocked_reasons", [])))
        self.config = cfg
        self.version = str(cfg["model_version"])
        self.fs = int(cfg["sample_rate_hz"])
        self.media = np.asarray(cfg["normalization"]["mean"], dtype=np.float32)
        self.desviacion = np.asarray(cfg["normalization"]["std"], dtype=np.float32)
        self.umbrales = {c: float(cfg["thresholds"][c]) for c in CLASES}
        self.red = construir_red(cfg["architecture"])
        estado = torch.load(directorio / cfg.get("weights_file", "model_state_dict.pt"), map_location="cpu", weights_only=True)
        self.red.load_state_dict(estado)
        self.red.eval()
        self._lock = threading.Lock()

    def predecir(self, senal_mv: np.ndarray) -> ResultadoModelo:
        t0 = time.perf_counter()
        x = torch.from_numpy(normalizar(senal_mv, self.media, self.desviacion)[None])
        with self._lock, torch.inference_mode():
            puntajes = torch.sigmoid(self.red(x)).float().numpy()[0]
        if puntajes.shape != (len(CLASES),) or not np.all(np.isfinite(puntajes)):
            raise RuntimeError("El modelo devolvió puntajes inválidos")
        etiquetas = [c for c, s in zip(CLASES, puntajes) if s >= np.float32(self.umbrales[c])]
        return ResultadoModelo(
            puntajes={c: float(s) for c, s in zip(CLASES, puntajes)},
            etiquetas=etiquetas,
            umbrales=dict(self.umbrales),
            version=self.version,
            tiempo_ms=int(round((time.perf_counter() - t0) * 1000)),
        )


_modelo: ModeloECG | None = None
_modelo_lock = threading.Lock()


def obtener_modelo() -> ModeloECG:
    """Carga el modelo una sola vez por proceso."""
    global _modelo
    if _modelo is None:
        with _modelo_lock:
            if _modelo is None:
                _modelo = ModeloECG()
                log.info("Modelo ECG %s cargado (%d Hz)", _modelo.version, _modelo.fs)
    return _modelo


def analizar_zip(archivo) -> ResultadoModelo:
    """Extrae, valida y analiza un .zip WFDB. Lanza ErrorPaquete o ErrorECG si no es válido."""
    modelo = obtener_modelo()
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="ecg_") as tmp:
        ruta_hea = extraer_zip(archivo, Path(tmp))
        senal = leer_ecg(ruta_hea, modelo.fs)
    resultado = modelo.predecir(senal)
    resultado.tiempo_ms = int(round((time.perf_counter() - t0) * 1000))
    return resultado


def leer_senal_zip(archivo) -> dict[str, Any]:
    """Señal validada en mV para dibujar el trazado: 12 derivaciones en orden estándar.

    Usa la misma lectura que el modelo, así el trazado corresponde a lo que se analizó.
    """
    fs = obtener_modelo().fs
    with tempfile.TemporaryDirectory(prefix="ecg_") as tmp:
        senal = leer_ecg(extraer_zip(archivo, Path(tmp)), fs)
    return {
        "frecuencia_hz": fs,
        "unidades": "mV",
        "derivaciones": list(ORDEN_DERIVACIONES),
        # 3 decimales (1 µV) bastan para dibujar y reducen el JSON a ~80 KB.
        "mv": np.round(senal.astype(np.float64), 3).tolist(),
    }


# -----------------------------------------------------------------------------
# Integración con CasosECG
# -----------------------------------------------------------------------------

MENSAJE_ERROR_INTERNO = "No fue posible procesar el ECG por un error interno. Intente de nuevo o avise al equipo."


def procesar_caso(caso) -> Any:
    """Ejecuta el modelo sobre `caso.archivo_ecg` y guarda el resultado o el error en el caso."""
    from django.utils import timezone

    from api.models import EstadoProcesamientoECG

    try:
        with caso.archivo_ecg.open("rb") as fh:
            resultado = analizar_zip(fh)
    except (ErrorPaquete, ErrorECG) as exc:
        caso.estado_procesamiento = EstadoProcesamientoECG.ERROR
        caso.mensaje_error = exc.mensaje
    except Exception:  # noqa: BLE001
        log.exception("Error inesperado al procesar el caso ECG %s", caso.pk)
        caso.estado_procesamiento = EstadoProcesamientoECG.ERROR
        caso.mensaje_error = MENSAJE_ERROR_INTERNO
    else:
        p = resultado.puntajes
        caso.norm_prob, caso.mi_prob, caso.sttc_prob = p["NORM"], p["MI"], p["STTC"]
        caso.cd_prob, caso.hyp_prob = p["CD"], p["HYP"]
        caso.etiquetas_ia = resultado.etiquetas
        caso.umbrales_ia = resultado.umbrales
        caso.version_modelo = resultado.version
        caso.tiempo_procesamiento_ms = resultado.tiempo_ms
        caso.procesado_en = timezone.now()
        caso.estado_procesamiento = EstadoProcesamientoECG.COMPLETADO
        caso.mensaje_error = ""
    caso.save()
    return caso

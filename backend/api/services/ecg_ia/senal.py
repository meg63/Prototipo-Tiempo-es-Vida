"""Lectura WFDB, validación y normalización (SRS DAT-06, DAT-07).

Copia de inferencia de `cuidaecg.signals`. Un mismo archivo debe producir la misma
señal preprocesada que en el entrenamiento: no cambiar sin actualizar el modelo.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import wfdb

ORDEN_DERIVACIONES = ("I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6")
_ORDEN_MINUSCULAS = [d.lower() for d in ORDEN_DERIVACIONES]
DURACION_S = 10
STD_EPS = 1e-6
UNIDAD_A_MV = {"mv": 1.0, "uv": 1e-3, "µv": 1e-3, "μv": 1e-3, "nv": 1e-6, "v": 1e3}

# Mensajes para el participante, por motivo de rechazo.
MENSAJES = {
    "archivo_faltante": "Falta el archivo .dat que acompaña al encabezado .hea.",
    "encabezado_ilegible": "No se pudo leer el encabezado .hea del ECG.",
    "wfdb_ilegible": "No se pudo leer la señal del ECG (archivo dañado o incompleto).",
    "frecuencia": "El ECG está grabado a {detalle}; el modelo trabaja a {fs} Hz.",
    "derivaciones_duplicadas": "El archivo repite derivaciones ({detalle}).",
    "derivaciones_faltantes": "Faltan derivaciones ({detalle}). Se necesitan las 12 derivaciones estándar.",
    "canales_inesperados": "El archivo trae canales distintos de las 12 derivaciones estándar ({detalle}).",
    "duracion": "El ECG debe durar 10 segundos ({detalle}).",
    "unidades": "No se reconocen las unidades de voltaje del archivo ({detalle}).",
    "valores_invalidos": "La señal contiene valores vacíos o inválidos.",
    "derivacion_plana": "Una derivación no tiene señal (está plana): {detalle}.",
}


class ErrorECG(Exception):
    """ECG que no cumple el contrato del modelo. `mensaje` es apto para el participante."""

    def __init__(self, motivo: str, detalle: str = "", fs: int | None = None):
        self.motivo = motivo
        self.detalle = detalle
        plantilla = MENSAJES.get(motivo, "El ECG no es válido.")
        self.mensaje = plantilla.format(detalle=detalle or "sin detalle", fs=fs)
        super().__init__(f"{motivo}: {detalle}" if detalle else motivo)


def leer_ecg(ruta_hea: Path, fs_esperada: int) -> np.ndarray:
    """Devuelve el ECG en mV, orden canónico, forma [12, T], float32."""
    ruta_hea = Path(ruta_hea)
    base = ruta_hea.with_suffix("")
    if not ruta_hea.is_file():
        raise ErrorECG("archivo_faltante", ruta_hea.name)
    try:
        encabezado = wfdb.rdheader(str(base))
    except Exception as exc:
        raise ErrorECG("encabezado_ilegible", str(exc)) from exc
    for nombre in sorted(set(encabezado.file_name or [])):
        if not (ruta_hea.parent / nombre).is_file():
            raise ErrorECG("archivo_faltante", nombre)
    try:
        registro = wfdb.rdrecord(str(base), physical=True, return_res=64)
    except Exception as exc:
        raise ErrorECG("wfdb_ilegible", str(exc)) from exc

    if float(registro.fs) != float(fs_esperada):
        raise ErrorECG("frecuencia", f"{float(registro.fs):g} Hz", fs_esperada)

    nombres = [str(n).strip().lower() for n in (registro.sig_name or [])]
    duplicadas = sorted({n for n in nombres if nombres.count(n) > 1})
    if duplicadas:
        raise ErrorECG("derivaciones_duplicadas", ", ".join(duplicadas))
    faltantes = [ORDEN_DERIVACIONES[i] for i, n in enumerate(_ORDEN_MINUSCULAS) if n not in nombres]
    if faltantes:
        raise ErrorECG("derivaciones_faltantes", ", ".join(faltantes))
    if len(nombres) != len(ORDEN_DERIVACIONES):
        extra = [n for n in nombres if n not in _ORDEN_MINUSCULAS]
        raise ErrorECG("canales_inesperados", ", ".join(extra))

    senal = registro.p_signal
    esperadas = int(fs_esperada * DURACION_S)
    if senal is None or senal.ndim != 2 or senal.shape[1] != len(ORDEN_DERIVACIONES):
        raise ErrorECG("wfdb_ilegible", "sin señal física")
    if senal.shape[0] != esperadas:
        raise ErrorECG("duracion", f"{senal.shape[0]} muestras en lugar de {esperadas}")

    unidades = [str(u).strip().lower() for u in (registro.units or [])]
    if len(unidades) != len(ORDEN_DERIVACIONES) or any(u not in UNIDAD_A_MV for u in unidades):
        raise ErrorECG("unidades", ", ".join(map(str, registro.units or [])) or "sin unidades")
    factores = np.array([UNIDAD_A_MV[u] for u in unidades])

    orden = [nombres.index(n) for n in _ORDEN_MINUSCULAS]
    mv = (senal * factores[None, :])[:, orden].T
    if not np.all(np.isfinite(mv)):
        raise ErrorECG("valores_invalidos")
    planas = [ORDEN_DERIVACIONES[i] for i in range(len(ORDEN_DERIVACIONES)) if np.ptp(mv[i]) == 0.0]
    if planas:
        raise ErrorECG("derivacion_plana", ", ".join(planas))
    return np.ascontiguousarray(mv, dtype=np.float32)


def normalizar(senal_mv: np.ndarray, media, desviacion) -> np.ndarray:
    """(x - media) / max(desviación, 1e-6) por derivación."""
    media = np.asarray(media, dtype=np.float32)[:, None]
    desv = np.maximum(np.asarray(desviacion, dtype=np.float32), np.float32(STD_EPS))[:, None]
    return ((np.asarray(senal_mv, dtype=np.float32) - media) / desv).astype(np.float32, copy=False)

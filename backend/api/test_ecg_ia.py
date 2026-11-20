"""Integración del modelo ECG: .zip WFDB -> modelo -> CasosECG."""

from __future__ import annotations

import io
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import wfdb
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from .models import CasosECG, Consentimiento, CustomUser, RolUsuario
from .services.ecg_ia import ErrorPaquete, analizar_zip, inspeccionar_zip
from .services.ecg_ia.senal import ORDEN_DERIVACIONES

FS = 100
CLASES = ["NORM", "MI", "STTC", "CD", "HYP"]
MEDIA_TMP = tempfile.mkdtemp(prefix="tv_media_test_")


def senal_sintetica(seed: int = 0) -> np.ndarray:
    """Latidos gaussianos simples, [1000, 12] en mV (no tiene valor clínico)."""
    rng = np.random.default_rng(seed)
    t = np.arange(FS * 10) / FS
    sig = np.zeros((len(t), 12))
    for beat in np.arange(0.3, 10, 0.85):
        qrs = np.exp(-0.5 * ((t - beat) / 0.012) ** 2)
        onda_t = 0.3 * np.exp(-0.5 * ((t - beat - 0.28) / 0.05) ** 2)
        sig += (qrs + onda_t)[:, None] * np.linspace(0.5, 1.2, 12)[None, :]
    return sig + rng.normal(0, 0.03, size=sig.shape)


def zip_wfdb(nombre="00001_lr", senal=None, nombres=None, incluir_dat=True, fs=FS) -> bytes:
    senal = senal_sintetica() if senal is None else senal
    nombres = nombres or [d.upper() for d in ORDEN_DERIVACIONES]
    with tempfile.TemporaryDirectory() as tmp:
        wfdb.wrsamp(
            nombre, fs=fs, units=["mV"] * len(nombres), sig_name=nombres, p_signal=senal,
            fmt=["16"] * len(nombres), adc_gain=[1000.0] * len(nombres), baseline=[0] * len(nombres),
            write_dir=tmp,
        )
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.write(Path(tmp) / f"{nombre}.hea", f"{nombre}.hea")
            if incluir_dat:
                zf.write(Path(tmp) / f"{nombre}.dat", f"carpeta/{nombre}.dat")
        return buf.getvalue()


class ServicioECGTests(TestCase):
    def test_analiza_zip_valido(self):
        res = analizar_zip(io.BytesIO(zip_wfdb()))
        self.assertEqual(list(res.puntajes), CLASES)
        self.assertTrue(all(0.0 <= v <= 1.0 for v in res.puntajes.values()))
        esperadas = [c for c in CLASES if res.puntajes[c] >= res.umbrales[c]]
        self.assertEqual(res.etiquetas, esperadas)
        self.assertEqual(res.version, "baseline-001")

    def test_resultado_determinista(self):
        a = analizar_zip(io.BytesIO(zip_wfdb()))
        b = analizar_zip(io.BytesIO(zip_wfdb()))
        self.assertEqual(a.puntajes, b.puntajes)

    def test_rechaza_zip_incompleto_o_invalido(self):
        with self.assertRaisesMessage(ErrorPaquete, "Falta 00001_lr.dat"):
            inspeccionar_zip(io.BytesIO(zip_wfdb(incluir_dat=False)))
        with self.assertRaisesMessage(ErrorPaquete, "no es un .zip válido"):
            inspeccionar_zip(io.BytesIO(b"no soy un zip"))
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("x.hea", "x 12 100 1000\n")  # declara 12 señales y no lista ninguna
        with self.assertRaisesMessage(ErrorPaquete, "incompleto"):
            inspeccionar_zip(io.BytesIO(buf.getvalue()))

    def test_rutas_del_zip_no_escapan_del_directorio_temporal(self):
        original = zipfile.ZipFile(io.BytesIO(zip_wfdb()))
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            for info in original.infolist():
                zf.writestr("../../" + Path(info.filename).name, original.read(info))
        from .services.ecg_ia.servicio import extraer_zip

        with tempfile.TemporaryDirectory() as tmp:
            destino = Path(tmp) / "dentro"
            destino.mkdir()
            hea = extraer_zip(io.BytesIO(buf.getvalue()), destino)
            self.assertEqual(hea.parent, destino)
            self.assertEqual(sorted(p.name for p in Path(tmp).rglob("*") if p.is_file()),
                             ["00001_lr.dat", "00001_lr.hea"])
            self.assertTrue(all(p.parent == destino for p in Path(tmp).rglob("*") if p.is_file()))


@override_settings(MEDIA_ROOT=MEDIA_TMP)
class CargaECGAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.paciente = CustomUser.objects.create_user(
            username="ecg@example.test", email="ecg@example.test", password="Temporal-2026-Segura!",
            nombre="Paciente ECG", codigo_participante="P-ECG-01", edad=50, rol=RolUsuario.PACIENTE,
        )
        Consentimiento.objects.create(
            paciente=self.paciente, acepta_tratamiento_datos=True, acepta_piloto_no_clinico=True
        )
        token = Token.objects.create(user=self.paciente)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def subir(self, contenido: bytes, nombre="caso.zip"):
        return self.client.post(
            "/api/ecg/",
            {
                "caso_asignado": "PTBXL-1",
                "confirma_prueba": "true",
                "archivo_ecg": SimpleUploadedFile(nombre, contenido, content_type="application/zip"),
            },
            format="multipart",
        )

    def test_carga_valida_ejecuta_el_modelo(self):
        r = self.subir(zip_wfdb())
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertEqual(r.data["estado_procesamiento"], "COMPLETADO", r.data)
        self.assertEqual(r.data["mensaje_error"], "")
        for campo in ("norm_prob", "mi_prob", "sttc_prob", "cd_prob", "hyp_prob"):
            self.assertTrue(0.0 <= r.data[campo] <= 1.0)
        self.assertEqual(r.data["version_modelo"], "baseline-001")
        self.assertEqual(set(r.data["umbrales_ia"]), set(CLASES))
        self.assertIsNotNone(r.data["tiempo_procesamiento_ms"])
        self.assertIsNone(r.data["prioridad_ia"])  # pendiente de la regla clínica
        filas = r.data["resultados_por_superclase"]
        self.assertEqual([f["superclase"] for f in filas], CLASES)
        self.assertEqual([f["superclase"] for f in filas if f["activada"]], r.data["etiquetas_ia"])

        detalle = self.client.get(f"/api/ecg/{r.data['id']}/")
        self.assertEqual(detalle.data["norm_prob"], r.data["norm_prob"])

    def test_ecg_invalido_queda_en_error_con_mensaje(self):
        senal = senal_sintetica()
        senal[:, 8] = 0.0  # V3 plana
        r = self.subir(zip_wfdb(senal=senal))
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertEqual(r.data["estado_procesamiento"], "ERROR")
        self.assertIn("V3", r.data["mensaje_error"])
        self.assertIsNone(r.data["norm_prob"])

    def test_frecuencia_distinta_queda_en_error(self):
        senal = np.repeat(senal_sintetica(), 5, axis=0)  # 5000 muestras
        r = self.subir(zip_wfdb(senal=senal, fs=500))
        self.assertEqual(r.data["estado_procesamiento"], "ERROR")
        self.assertIn("100 Hz", r.data["mensaje_error"])

    def test_senal_para_el_trazado(self):
        senal_original = senal_sintetica(seed=3)
        caso = self.subir(zip_wfdb(senal=senal_original)).data
        r = self.client.get(f"/api/ecg/{caso['id']}/senal/")
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        self.assertEqual(r.data["frecuencia_hz"], FS)
        self.assertEqual(r.data["unidades"], "mV")
        self.assertEqual(r.data["derivaciones"], list(ORDEN_DERIVACIONES))
        mv = np.array(r.data["mv"])
        self.assertEqual(mv.shape, (12, FS * 10))
        # Cuantización WFDB de 16 bits (1 µV) + redondeo a 3 decimales.
        np.testing.assert_allclose(mv, senal_original.T, atol=2e-3)

    def test_senal_de_otro_paciente_no_es_visible(self):
        caso = self.subir(zip_wfdb()).data
        otro = CustomUser.objects.create_user(
            username="otro@example.test", email="otro@example.test", password="Temporal-2026-Segura!",
            nombre="Otro", codigo_participante="P-ECG-02", edad=60, rol=RolUsuario.PACIENTE,
        )
        Consentimiento.objects.create(paciente=otro, acepta_tratamiento_datos=True, acepta_piloto_no_clinico=True)
        cliente = APIClient()
        cliente.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=otro).key}")
        self.assertEqual(cliente.get(f"/api/ecg/{caso['id']}/senal/").status_code, status.HTTP_404_NOT_FOUND)

    def test_senal_de_ecg_invalido_explica_el_motivo(self):
        senal = senal_sintetica()
        senal[:, 8] = 0.0
        caso = self.subir(zip_wfdb(senal=senal)).data
        r = self.client.get(f"/api/ecg/{caso['id']}/senal/")
        self.assertEqual(r.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("V3", r.data["detail"])

    def test_zip_sin_dat_se_rechaza_sin_crear_caso(self):
        r = self.subir(zip_wfdb(incluir_dat=False))
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(".dat", str(r.data["archivo_ecg"]))
        self.assertEqual(CasosECG.objects.count(), 0)

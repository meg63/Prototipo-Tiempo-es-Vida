from datetime import timedelta, time
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from api.models import (
    CustomUser,
    EvaluacionPeriodica,
    PerfilCardiovascular,
    RecomendacionCatalogo,
    RecomendacionMostrada,
    RegistroDiario,
)
from api.services.rules_engine import evaluar_habitos_y_sintomas


class MotorReglasTests(TestCase):
    def setUp(self):
        call_command("cargar_recomendaciones", verbosity=0)
        self.hoy = timezone.localdate()
        self.paciente = CustomUser.objects.create_user(
            username="reglas@example.test",
            email="reglas@example.test",
            password="Temporal-2026-Segura!",
            nombre="Paciente reglas",
            codigo_participante="P-REGLAS-01",
            edad=45,
            sexo="Prefiero no decirlo",
            rol="PACIENTE",
        )
        self.perfil = self.crear_perfil()

    def crear_perfil(self, **extras):
        data = {
            "paciente": self.paciente,
            "peso_kg": Decimal("70.00"),
            "estatura_cm": 170,
            "presion_arterial": "No sé",
            "condiciones_diagnosticadas": ["ninguna"],
            "toma_medicamentos": "NO",
            "antecedentes_familiares": "NO_SE",
            "frutas_verduras_dia": "2_4",
            "sal_procesados": "CASI_NUNCA",
            "bebidas_azucaradas": "CASI_NUNCA",
            "actividad_min_semana": "60_149",
            "horas_sentado": "6_8",
            "horas_sueno_promedio": "Entre 7 y 9",
            "estres_dos_semanas": "ALGUNOS_DIAS",
            "tabaquismo": "NUNCA",
            "alcohol_semana": "NUNCA",
            "sintomas_ahora": ["Ninguno"],
            "sintomas_ultimo_mes": ["Ninguno"],
            "parq_completado": True,
            "parq_requiere_revision": False,
            "ejercicio_supervisado_indicado": False,
            "restriccion_liquidos_medica": False,
        }
        data.update(extras)
        return PerfilCardiovascular.objects.create(**data)

    def crear_registro(self, dias_atras, **campos):
        fecha = self.hoy - timedelta(days=dias_atras)
        return RegistroDiario.objects.create(
            paciente=self.paciente,
            fecha=fecha,
            **campos,
        )

    @staticmethod
    def codigos(resultado):
        return {x["codigo"] for x in resultado["recomendaciones_generadas"]}

    def test_carga_banco_oficial_de_30_recomendaciones(self):
        call_command("cargar_recomendaciones", verbosity=0)
        codigos = set(RecomendacionCatalogo.objects.filter(activa=True).values_list("codigo", flat=True))
        self.assertTrue(set(f"AL-{n:02d}" for n in range(1, 6)).issubset(codigos))
        self.assertTrue(set(f"HI-{n:02d}" for n in range(1, 6)).issubset(codigos))
        self.assertTrue(set(f"AF-{n:02d}" for n in range(1, 6)).issubset(codigos))
        self.assertTrue(set(f"SU-{n:02d}" for n in range(1, 6)).issubset(codigos))
        self.assertTrue(set(f"ES-{n:02d}" for n in range(1, 6)).issubset(codigos))
        self.assertTrue(set(f"TA-{n:02d}" for n in range(1, 6)).issubset(codigos))
        self.assertEqual(len(codigos), 30)

    def test_r01_incompleto_bloquea_recomendaciones_de_actividad(self):
        self.perfil.parq_completado = None
        self.perfil.save()
        for n in range(3):
            self.crear_registro(n, actividad_moderada_minutos=10, actividad_vigorosa_minutos=0)
        resultado = evaluar_habitos_y_sintomas(self.paciente, persistir=False, fecha=self.hoy)
        self.assertIn("R-01", {a["regla"] for a in resultado["alertas"]})
        self.assertNotIn("AF-01", self.codigos(resultado))

    def test_r02_respeta_minimo_de_tres_registros(self):
        for n in range(2):
            self.crear_registro(n, actividad_moderada_minutos=10, actividad_vigorosa_minutos=0)
        resultado = evaluar_habitos_y_sintomas(self.paciente, persistir=False, fecha=self.hoy)
        self.assertNotIn("AF-01", self.codigos(resultado))
        self.assertTrue(any("R-02/R-03/R-04" == x["regla"] for x in resultado["reglas_omitidas"]))

        self.crear_registro(2, actividad_moderada_minutos=10, actividad_vigorosa_minutos=0)
        resultado = evaluar_habitos_y_sintomas(self.paciente, persistir=False, fecha=self.hoy)
        self.assertIn("AF-01", self.codigos(resultado))

    def test_r04_muestra_refuerzo_y_fuerza_si_no_hay_fortalecimiento(self):
        for n in range(3):
            self.crear_registro(
                n,
                actividad_moderada_minutos=60,
                actividad_vigorosa_minutos=0,
                fortalecimiento_muscular=False,
            )
        resultado = evaluar_habitos_y_sintomas(self.paciente, persistir=False, fecha=self.hoy)
        self.assertIn("AF-05", self.codigos(resultado))
        self.assertIn("AF-03", self.codigos(resultado))

    def test_r11_exige_cuatro_dias_para_la_condicion_de_cuatro_de_siete(self):
        for n in range(3):
            self.crear_registro(n, ultraprocesados_veces=2, bebidas_azucaradas_cantidad=1)
        resultado = evaluar_habitos_y_sintomas(self.paciente, persistir=False, fecha=self.hoy)
        self.assertNotIn("AL-03", self.codigos(resultado))

        self.crear_registro(3, ultraprocesados_veces=2, bebidas_azucaradas_cantidad=1)
        resultado = evaluar_habitos_y_sintomas(self.paciente, persistir=False, fecha=self.hoy)
        self.assertIn("AL-03", self.codigos(resultado))
        self.assertIn("AL-04", self.codigos(resultado))

    def test_r12_restriccion_de_liquidos_prioriza_hi05_y_oculta_metas(self):
        self.perfil.restriccion_liquidos_medica = True
        self.perfil.save()
        for n in range(3):
            self.crear_registro(n, vasos_agua=1)
        resultado = evaluar_habitos_y_sintomas(self.paciente, persistir=False, fecha=self.hoy)
        codigos = self.codigos(resultado)
        self.assertIn("HI-05", codigos)
        self.assertTrue({"HI-01", "HI-02", "HI-03", "HI-04"}.isdisjoint(codigos))

    def test_r16_suprime_recomendaciones_cuantitativas_para_mayores_de_60(self):
        self.paciente.edad = 65
        self.paciente.save()
        for n in range(3):
            self.crear_registro(n, horas_sueno=Decimal("6.0"), vasos_agua=1)
        resultado = evaluar_habitos_y_sintomas(self.paciente, persistir=False, fecha=self.hoy)
        codigos = self.codigos(resultado)
        self.assertIn("R-16", {a["regla"] for a in resultado["alertas"]})
        self.assertTrue({"AF-01", "AF-02", "AF-03", "AF-04", "AF-05", "SU-01", "HI-01", "HI-02", "HI-03", "HI-04"}.isdisjoint(codigos))

    def test_r13_alerta_inmediata_suspende_otras_recomendaciones(self):
        resultado = evaluar_habitos_y_sintomas(
            self.paciente,
            necesito_ayuda_ahora=True,
            persistir=False,
            fecha=self.hoy,
        )
        self.assertEqual({a["regla"] for a in resultado["alertas"]}, {"R-13"})
        self.assertEqual(resultado["recomendaciones_generadas"], [])
        self.assertTrue(resultado["alertas"][0]["suspender_mensajes_motivacionales"])

    def test_r06_usa_tres_mediciones_y_rango_de_edad(self):
        for n, hora in enumerate((time(22, 0), time(23, 30), time(0, 30))):
            self.crear_registro(n, horas_sueno=Decimal("6.5"), hora_acostarse_real=hora)
        resultado = evaluar_habitos_y_sintomas(self.paciente, persistir=False, fecha=self.hoy)
        self.assertIn("SU-01", self.codigos(resultado))
        self.assertIn("SU-02", self.codigos(resultado))

    def test_r07_dificultad_de_sueno_semanal_activa_su03(self):
        for n in range(3):
            self.crear_registro(n)
        EvaluacionPeriodica.objects.create(
            paciente=self.paciente,
            fecha_registro=self.hoy,
            periodo_inicio=self.hoy - timedelta(days=6),
            periodo_fin=self.hoy,
            dificultad_sueno_noches=3,
        )
        resultado = evaluar_habitos_y_sintomas(self.paciente, persistir=False, fecha=self.hoy)
        self.assertIn("SU-03", self.codigos(resultado))

    def test_r08_no_repite_su05_dentro_de_90_dias(self):
        EvaluacionPeriodica.objects.create(
            paciente=self.paciente,
            fecha_registro=self.hoy,
            ronquidos_pausas_somnolencia="SI",
        )
        primera = evaluar_habitos_y_sintomas(self.paciente, persistir=True, fecha=self.hoy)
        self.assertIn("SU-05", self.codigos(primera))
        segunda = evaluar_habitos_y_sintomas(self.paciente, persistir=True, fecha=self.hoy)
        self.assertNotIn("SU-05", self.codigos(segunda))
        self.assertEqual(
            RecomendacionMostrada.objects.filter(paciente=self.paciente, recomendacion__codigo="SU-05").count(),
            1,
        )

    def test_r10_frutas_bajas_y_poco_acceso_activa_al01_y_al02(self):
        self.perfil.poco_acceso_fruta = True
        self.perfil.save()
        for n in range(3):
            self.crear_registro(n, frutas_verduras_porciones=1)
        resultado = evaluar_habitos_y_sintomas(self.paciente, persistir=False, fecha=self.hoy)
        self.assertIn("AL-01", self.codigos(resultado))
        self.assertIn("AL-02", self.codigos(resultado))

    def test_r14_tres_dias_de_estres_alto_activa_es01(self):
        for n in range(3):
            self.crear_registro(n, estres_nivel=4)
        resultado = evaluar_habitos_y_sintomas(self.paciente, persistir=False, fecha=self.hoy)
        self.assertIn("ES-01", self.codigos(resultado))
        self.assertNotIn("ES-02", self.codigos(resultado))

    def test_r15_fumador_y_deseo_de_dejarlo(self):
        self.perfil.tabaquismo = "DIARIO"
        self.perfil.quiere_dejar_fumar = True
        self.perfil.save()
        resultado = evaluar_habitos_y_sintomas(self.paciente, persistir=False, fecha=self.hoy)
        self.assertIn("TA-01", self.codigos(resultado))
        self.assertIn("TA-03", self.codigos(resultado))
    def test_r03_actividad_entre_60_y_149_activa_af02(self):
        for n in range(3):
            self.crear_registro(n, actividad_moderada_minutos=30, actividad_vigorosa_minutos=0)
        resultado = evaluar_habitos_y_sintomas(self.paciente, persistir=False, fecha=self.hoy)
        self.assertIn("AF-02", self.codigos(resultado))

    def test_r05_necesita_cuatro_dias_con_ocho_horas_sentado(self):
        for n in range(3):
            self.crear_registro(n, horas_sentado=Decimal("8"))
        resultado = evaluar_habitos_y_sintomas(self.paciente, persistir=False, fecha=self.hoy)
        self.assertNotIn("AF-04", self.codigos(resultado))

        self.crear_registro(3, horas_sentado=Decimal("8"))
        resultado = evaluar_habitos_y_sintomas(self.paciente, persistir=False, fecha=self.hoy)
        self.assertIn("AF-04", self.codigos(resultado))

    def test_r09_promedio_mayor_a_nueve_devuelve_mensaje_neutral(self):
        for n in range(3):
            self.crear_registro(n, horas_sueno=Decimal("10.0"))
        resultado = evaluar_habitos_y_sintomas(self.paciente, persistir=False, fecha=self.hoy)
        self.assertTrue(any(m["regla"] == "R-09" for m in resultado["mensajes"]))

    def test_r14_cinco_dias_de_estres_alto_activa_es02_y_es04(self):
        for n in range(5):
            self.crear_registro(n, estres_nivel=5)
        resultado = evaluar_habitos_y_sintomas(self.paciente, persistir=False, fecha=self.hoy)
        self.assertIn("ES-01", self.codigos(resultado))
        self.assertIn("ES-02", self.codigos(resultado))
        self.assertIn("ES-04", self.codigos(resultado))

    def test_r15_de_uno_a_cinco_cigarrillos_activa_ta02(self):
        self.perfil.tabaquismo = "DIARIO"
        self.perfil.save()
        for n in range(3):
            self.crear_registro(n, cigarrillos_hoy=3)
        resultado = evaluar_habitos_y_sintomas(self.paciente, persistir=False, fecha=self.hoy)
        self.assertIn("TA-01", self.codigos(resultado))
        self.assertIn("TA-02", self.codigos(resultado))


from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from .models import (
    CasosECG,
    Consentimiento,
    CustomUser,
    PerfilCardiovascular,
    RecomendacionCatalogo,
    RecomendacionMostrada,
    RegistroDiario,
    RolUsuario,
)


class APITiempoEsVidaTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.paciente = CustomUser.objects.create_user(
            username="paciente@example.test",
            email="paciente@example.test",
            password="Temporal-2026-Segura!",
            nombre="Paciente de prueba",
            codigo_participante="P-TEST-01",
            edad=45,
            sexo="Prefiero no decirlo",
            rol=RolUsuario.PACIENTE,
        )
        self.token = Token.objects.create(user=self.paciente)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def aceptar_consentimiento(self):
        return self.client.post(
            "/api/consentimiento/",
            {
                "acepta_tratamiento_datos": True,
                "acepta_piloto_no_clinico": True,
            },
            format="json",
        )

    def crear_perfil(self):
        return self.client.put(
            "/api/perfil/",
            {
                "peso_kg": "70.00",
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
                "hora_despertar": "06:30:00",
                "hora_acostarse": "22:30:00",
            },
            format="json",
        )

    def test_health_is_public(self):
        self.client.credentials()
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "ok")

    def test_me_requires_token_and_returns_public_user(self):
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], self.paciente.email)
        self.assertNotIn("password", response.data)

    def test_personal_health_data_requires_consent(self):
        response = self.client.get("/api/perfil/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_consent_and_profile_can_be_saved(self):
        consent = self.aceptar_consentimiento()
        self.assertEqual(consent.status_code, status.HTTP_201_CREATED)

        profile = self.crear_perfil()
        self.assertEqual(profile.status_code, status.HTTP_200_OK, profile.data)
        self.assertIn("imc", profile.data)
        self.assertEqual(profile.data["imc"], "24.2")

    def test_morning_and_night_surveys_share_one_daily_record(self):
        self.aceptar_consentimiento()
        self.crear_perfil()

        morning = self.client.post(
            "/api/habitos/manana/",
            {
                "horas_sueno_anoche": "7_9",
                "despertares_noche": "NINGUNO",
                "idas_bano_noche": "NINGUNA",
                "sensacion_despertar": "DESCANSADO",
                "hora_acostarse_anoche": "22_23",
            },
            format="json",
        )
        self.assertEqual(morning.status_code, status.HTTP_200_OK, morning.data)

        night = self.client.post(
            "/api/habitos/noche/",
            {
                "siesta_tarde": "NO",
                "caminata_hoy": "10_20",
                "ejercicio_hoy": "SUAVE",
                "sentado_mas_6h": False,
                "frutas_verduras_hoy": "1_2",
                "fritos_paquete_hoy": "NO",
                "bebida_azucarada_hoy": "NO",
                "vasos_agua_respuesta": "3_5",
                "sal_extra_hoy": "NO",
                "estres_hoy": "MEDIO",
                "sintoma_hoy": False,
            },
            format="json",
        )
        self.assertEqual(night.status_code, status.HTTP_200_OK, night.data)
        history = self.client.get("/api/habitos/?periodo=7")
        self.assertEqual(history.status_code, status.HTTP_200_OK)
        self.assertEqual(len(history.data), 1)

    def test_ecg_upload_is_saved_pending_without_running_ai(self):
        self.aceptar_consentimiento()
        upload = SimpleUploadedFile("caso-prueba.csv", b"contenido-de-prueba", content_type="text/csv")
        response = self.client.post(
            "/api/ecg/",
            {
                "caso_asignado": "PTBXL-TEST-01",
                "confirma_prueba": "true",
                "archivo_ecg": upload,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["estado_procesamiento"], "PENDIENTE")
        self.assertIsNone(response.data["norm_prob"])

    def test_recommendation_display_and_clarity(self):
        self.aceptar_consentimiento()
        recommendation = RecomendacionCatalogo.objects.create(
            codigo="AF-TEST",
            categoria=RecomendacionCatalogo.Categoria.ACTIVIDAD_FISICA,
            situacion_identificada="Prueba de endpoint",
            texto_recomendacion="Esta es una recomendación de prueba.",
            activa=True,
        )
        response = self.client.post(
            "/api/recomendaciones/mostrar/",
            {"recomendacion_codigo": recommendation.codigo, "regla_codigo": "R-02"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        shown_id = response.data["id"]

        clarity = self.client.patch(
            f"/api/recomendaciones/{shown_id}/claridad/",
            {"respuesta_claridad": RecomendacionMostrada.Claridad.SI},
            format="json",
        )
        self.assertEqual(clarity.status_code, status.HTTP_200_OK, clarity.data)
        self.assertEqual(clarity.data["respuesta_claridad"], "SI")

    def test_registration_does_not_allow_professional_role(self):
        self.client.credentials()
        response = self.client.post(
            "/api/auth/register/",
            {
                "email": "nuevo@example.test",
                "nombre": "Nuevo participante",
                "codigo_participante": "P-TEST-02",
                "edad": 50,
                "sexo": "Prefiero no decirlo",
                "password": "Temporal-2026-Segura!",
                "password_confirmation": "Temporal-2026-Segura!",
                "rol": "PROFESIONAL",
                "is_staff": True,
                "is_superuser": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["usuario"]["rol"], RolUsuario.PACIENTE)
        created = CustomUser.objects.get(email="nuevo@example.test")
        self.assertFalse(created.is_staff)
        self.assertFalse(created.is_superuser)


class APIPermisosProfesionalTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.professional = CustomUser.objects.create_user(
            username="profesional@example.test",
            email="profesional@example.test",
            password="Temporal-2026-Segura!",
            nombre="Profesional de prueba",
            rol=RolUsuario.PROFESIONAL,
        )
        token = Token.objects.create(user=self.professional)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_professional_can_open_cases_list(self):
        response = self.client.get("/api/profesional/casos/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_patient_cannot_open_professional_cases(self):
        patient = CustomUser.objects.create_user(
            username="otro@example.test",
            email="otro@example.test",
            password="Temporal-2026-Segura!",
            nombre="Otro paciente",
            codigo_participante="P-TEST-03",
            edad=42,
            rol=RolUsuario.PACIENTE,
        )
        token = Token.objects.create(user=patient)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = self.client.get("/api/profesional/casos/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class APISeguridadAutenticacionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.patient = CustomUser.objects.create_user(
            username="seguridad-paciente@example.test",
            email="seguridad-paciente@example.test",
            password="Temporal-2026-Segura!",
            nombre="Paciente Seguridad",
            codigo_participante="P-SEC-01",
            edad=48,
            rol=RolUsuario.PACIENTE,
        )
        self.token = Token.objects.create(user=self.patient)
        self.headers = {"HTTP_AUTHORIZATION": f"Token {self.token.key}"}

    def test_anonymous_user_cannot_access_protected_endpoint(self):
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_rotates_token_and_invalidates_previous_token(self):
        old_key = self.token.key
        response = self.client.post(
            "/api/auth/login/",
            {"email": self.patient.email, "password": "Temporal-2026-Segura!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        new_key = response.data["token"]
        self.assertNotEqual(old_key, new_key)

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {old_key}")
        old_response = self.client.get("/api/auth/me/")
        self.assertEqual(old_response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {new_key}")
        new_response = self.client.get("/api/auth/me/")
        self.assertEqual(new_response.status_code, status.HTTP_200_OK)

    def test_logout_revokes_token(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        response = self.client.post("/api/auth/logout/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        after_logout = self.client.get("/api/auth/me/")
        self.assertEqual(after_logout.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_is_staff_patient_is_not_a_professional(self):
        staff_patient = CustomUser.objects.create_user(
            username="staff-paciente@example.test",
            email="staff-paciente@example.test",
            password="Temporal-2026-Segura!",
            nombre="Paciente con flag staff",
            codigo_participante="P-SEC-02",
            edad=51,
            rol=RolUsuario.PACIENTE,
            is_staff=True,
        )
        staff_token = Token.objects.create(user=staff_patient)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {staff_token.key}")
        response = self.client.get("/api/profesional/casos/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_professional_cannot_access_patient_personal_health_endpoints(self):
        professional = CustomUser.objects.create_user(
            username="profesional-seguridad@example.test",
            email="profesional-seguridad@example.test",
            password="Temporal-2026-Segura!",
            nombre="Profesional",
            rol=RolUsuario.PROFESIONAL,
        )
        professional_token = Token.objects.create(user=professional)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {professional_token.key}")
        response = self.client.get("/api/perfil/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patient_cannot_read_another_patients_daily_record(self):
        Consentimiento.objects.create(
            paciente=self.patient,
            acepta_tratamiento_datos=True,
            acepta_piloto_no_clinico=True,
        )
        other_patient = CustomUser.objects.create_user(
            username="otro-paciente-seguridad@example.test",
            email="otro-paciente-seguridad@example.test",
            password="Temporal-2026-Segura!",
            nombre="Otro paciente",
            codigo_participante="P-SEC-03",
            edad=44,
            rol=RolUsuario.PACIENTE,
        )
        other_record = RegistroDiario.objects.create(paciente=other_patient)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        response = self.client.get(f"/api/habitos/{other_record.pk}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

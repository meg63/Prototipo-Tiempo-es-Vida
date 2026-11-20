from datetime import timedelta

from django.contrib.auth import authenticate, get_user_model, logout
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from .services.ecg_ia import ErrorECG, ErrorPaquete, leer_senal_zip, procesar_caso
from .services.rules_engine import evaluar_habitos_y_sintomas


from .models import (
    CasosECG,
    Consentimiento,
    EstadoProcesamientoECG,
    EstadoRevisionECG,
    EvaluacionPeriodica,
    PerfilCardiovascular,
    RecomendacionCatalogo,
    RecomendacionMostrada,
    RegistroDiario,
)
from .serializers import (
    CasoECGProfesionalSerializer,
    ConsentimientoSerializer,
    EncuestaMananaSerializer,
    EncuestaNocheSerializer,
    EvaluacionPeriodicaSerializer,
    InicioSesionSerializer,
    MostrarRecomendacionSerializer,
    PerfilCardiovascularSerializer,
    RegistroDiarioSerializer,
    RegistroUsuarioSerializer,
    RecomendacionCatalogoSerializer,
    RecomendacionMostradaSerializer,
    RespuestaClaridadSerializer,
    ResultadoECGSerializer,
    RevisionProfesionalSerializer,
    UsuarioPublicoSerializer,
)
from .permissions import EsPaciente, EsProfesional, TieneConsentimiento

User = get_user_model()



class VistaAutenticada(APIView):
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]


class HealthAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({"status": "ok", "service": "Tiempo es Vida API"})


# -----------------------------------------------------------------------------
# Autenticación
# -----------------------------------------------------------------------------

class RegistroUsuarioAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_register"

    def post(self, request):
        serializer = RegistroUsuarioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Registro público: el serializer asigna siempre rol PACIENTE.
        # La creación de usuario y su token se hacen en una misma transacción.
        with transaction.atomic():
            user = serializer.save()
            token = Token.objects.create(user=user)
        return Response(
            {"token": token.key, "usuario": UsuarioPublicoSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


class InicioSesionAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_login"

    def post(self, request):
        serializer = InicioSesionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()
        password = serializer.validated_data["password"]

        try:
            user_record = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response(
                {"detail": "Correo o contraseña incorrectos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(request, username=user_record.username, password=password)
        if user is None or not user.is_active:
            return Response(
                {"detail": "Correo o contraseña incorrectos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Rotar el token al iniciar sesión invalida una credencial anterior
        # que pudiera haberse filtrado. Esta implementación mantiene un token
        # activo por usuario (comportamiento de DRF authtoken).
        with transaction.atomic():
            Token.objects.filter(user=user).delete()
            token = Token.objects.create(user=user)
        return Response({"token": token.key, "usuario": UsuarioPublicoSerializer(user).data})


class CerrarSesionAPIView(VistaAutenticada):
    def post(self, request):
        # Revoca el token usado y también cierra una sesión Django si se
        # autenticó mediante SessionAuthentication.
        Token.objects.filter(user=request.user).delete()
        logout(request._request)
        return Response({"detail": "Sesión cerrada."}, status=status.HTTP_200_OK)


class UsuarioActualAPIView(VistaAutenticada):
    def get(self, request):
        return Response(UsuarioPublicoSerializer(request.user).data)


# -----------------------------------------------------------------------------
# Consentimiento y perfil
# -----------------------------------------------------------------------------

class ConsentimientoAPIView(VistaAutenticada):
    permission_classes = [IsAuthenticated, EsPaciente]

    def get(self, request):
        consentimiento = get_object_or_404(Consentimiento, paciente=request.user)
        return Response(ConsentimientoSerializer(consentimiento).data)

    def post(self, request):
        if Consentimiento.objects.filter(paciente=request.user).exists():
            return Response(
                {"detail": "Ya existe un consentimiento registrado para este usuario."},
                status=status.HTTP_409_CONFLICT,
            )
        serializer = ConsentimientoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        consentimiento = serializer.save(paciente=request.user)
        return Response(ConsentimientoSerializer(consentimiento).data, status=status.HTTP_201_CREATED)


class PerfilCardiovascularAPIView(VistaAutenticada):
    permission_classes = [IsAuthenticated, EsPaciente, TieneConsentimiento]

    def get(self, request):
        perfil = get_object_or_404(PerfilCardiovascular, paciente=request.user)
        return Response(PerfilCardiovascularSerializer(perfil).data)

    def put(self, request):
        perfil = PerfilCardiovascular.objects.filter(paciente=request.user).first()
        serializer = PerfilCardiovascularSerializer(instance=perfil, data=request.data)
        serializer.is_valid(raise_exception=True)
        perfil = serializer.save(paciente=request.user)
        motor = evaluar_habitos_y_sintomas(request.user)
        data = dict(PerfilCardiovascularSerializer(perfil).data)
        data["motor_recomendaciones"] = motor
        return Response(data, status=status.HTTP_200_OK)


    def patch(self, request):
        perfil = get_object_or_404(PerfilCardiovascular, paciente=request.user)
        serializer = PerfilCardiovascularSerializer(instance=perfil, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        perfil = serializer.save()
        motor = evaluar_habitos_y_sintomas(request.user)
        data = dict(PerfilCardiovascularSerializer(perfil).data)
        data["motor_recomendaciones"] = motor
        return Response(data)



# -----------------------------------------------------------------------------
# Registro diario e historial
# -----------------------------------------------------------------------------

class EncuestaMananaAPIView(VistaAutenticada):
    permission_classes = [IsAuthenticated, EsPaciente, TieneConsentimiento]

    def post(self, request):
        serializer = EncuestaMananaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        hoy = timezone.localdate()

        with transaction.atomic():
            registro, _ = RegistroDiario.objects.get_or_create(
                paciente=request.user,
                fecha=hoy,
            )
            for campo, valor in serializer.validated_data.items():
                setattr(registro, campo, valor)
            registro.manana_completada_en = timezone.now()
            registro.save()
        motor = evaluar_habitos_y_sintomas(request.user)

        return Response(
            {"detail": "Encuesta de la mañana guardada.", "registro": RegistroDiarioSerializer(registro).data,"motor_recomendaciones":motor},
            status=status.HTTP_200_OK,
        )


class EncuestaNocheAPIView(VistaAutenticada):
    permission_classes = [IsAuthenticated, EsPaciente, TieneConsentimiento]

    def post(self, request):
        serializer = EncuestaNocheSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        hoy = timezone.localdate()

        with transaction.atomic():
            registro, _ = RegistroDiario.objects.get_or_create(
                paciente=request.user,
                fecha=hoy,
            )
            for campo, valor in serializer.validated_data.items():
                setattr(registro, campo, valor)
            registro.noche_completada_en = timezone.now()
            registro.save()
        motor = evaluar_habitos_y_sintomas(request.user)

        return Response(
            {
                "detail": "Encuesta de la noche guardada.",
                "alerta_urgencias": bool(registro.sintoma_hoy),
                "mensaje_urgencias": (
                    "Si presenta síntomas actuales, busque atención de urgencias o llame al 123."
                    if registro.sintoma_hoy else None
                ),
                "registro": RegistroDiarioSerializer(registro).data,
                "motor_recomendaciones": motor,
            },
            status=status.HTTP_200_OK,
        )


class HistorialHabitosAPIView(VistaAutenticada):
    permission_classes = [IsAuthenticated, EsPaciente, TieneConsentimiento]

    def get(self, request):
        queryset = RegistroDiario.objects.filter(paciente=request.user)
        periodo = request.query_params.get("periodo", "7")
        if periodo in {"7", "30"}:
            queryset = queryset.filter(fecha__gte=timezone.localdate() - timedelta(days=int(periodo) - 1))
        elif periodo != "todo":
            return Response(
                {"periodo": "Use 7, 30 o todo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        categoria = request.query_params.get("categoria")
        filtros = {
            "sueno": Q(horas_sueno_anoche__isnull=False) | Q(horas_sueno__isnull=False),
            "actividad_fisica": Q(ejercicio_hoy__isnull=False) | Q(actividad_moderada_minutos__isnull=False) | Q(actividad_vigorosa_minutos__isnull=False),
            "alimentacion_hidratacion": Q(frutas_verduras_hoy__isnull=False) | Q(frutas_verduras_porciones__isnull=False) | Q(vasos_agua__isnull=False),
            "estres_bienestar": Q(estres_hoy__isnull=False) | Q(estres_nivel__isnull=False),
            "tabaco_alcohol_medicamentos": Q(fumo_hoy__isnull=False) | Q(alcohol_hoy__isnull=False) | Q(medicamentos_hoy__isnull=False),
        }
        if categoria:
            if categoria not in filtros:
                return Response(
                    {"categoria": f"Categoría no válida. Opciones: {', '.join(filtros)}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            queryset = queryset.filter(filtros[categoria])

        desde_raw = request.query_params.get("desde")
        hasta_raw = request.query_params.get("hasta")
        desde = parse_date(desde_raw) if desde_raw else None
        hasta = parse_date(hasta_raw) if hasta_raw else None
        if desde_raw and desde is None:
            return Response({"desde": "Use el formato AAAA-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        if hasta_raw and hasta is None:
            return Response({"hasta": "Use el formato AAAA-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        if desde and hasta and desde > hasta:
            return Response({"detail": "La fecha inicial no puede ser posterior a la fecha final."}, status=status.HTTP_400_BAD_REQUEST)
        if desde:
            queryset = queryset.filter(fecha__gte=desde)
        if hasta:
            queryset = queryset.filter(fecha__lte=hasta)

        return Response(RegistroDiarioSerializer(queryset, many=True).data)


class RegistroDiarioDetalleAPIView(VistaAutenticada):
    permission_classes = [IsAuthenticated, EsPaciente, TieneConsentimiento]

    def get(self, request, pk):
        registro = get_object_or_404(RegistroDiario, pk=pk, paciente=request.user)
        return Response(RegistroDiarioSerializer(registro).data)


# -----------------------------------------------------------------------------
# Evaluaciones periódicas
# -----------------------------------------------------------------------------

class EvaluacionesPeriodicasAPIView(VistaAutenticada):
    permission_classes = [IsAuthenticated, EsPaciente, TieneConsentimiento]

    def get(self, request):
        evaluaciones = EvaluacionPeriodica.objects.filter(paciente=request.user)
        return Response(EvaluacionPeriodicaSerializer(evaluaciones, many=True).data)

    def post(self, request):
        serializer = EvaluacionPeriodicaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        evaluacion = serializer.save(paciente=request.user)
        motor = evaluar_habitos_y_sintomas(request.user)

        data = dict(EvaluacionPeriodicaSerializer(evaluacion).data)
        data["motor_recomendaciones"] = motor
        return Response(data, status=status.HTTP_201_CREATED)



# -----------------------------------------------------------------------------
# Carga, análisis con el modelo de IA y consulta de ECG
# -----------------------------------------------------------------------------

class CasosECGPacienteAPIView(VistaAutenticada):
    permission_classes = [IsAuthenticated, EsPaciente, TieneConsentimiento]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        casos = CasosECG.objects.filter(paciente=request.user)
        return Response(ResultadoECGSerializer(casos, many=True, context={"request": request}).data)

    def post(self, request):
        serializer = ResultadoECGSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        caso = serializer.save(paciente=request.user)
        # Inferencia síncrona: el modelo tarda milisegundos en CPU (meta del piloto < 3 min).
        # Si el ECG no es válido, el caso queda en ERROR con un mensaje para el participante.
        procesar_caso(caso)
        return Response(
            ResultadoECGSerializer(caso, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class CasoECGDetallePacienteAPIView(VistaAutenticada):
    permission_classes = [IsAuthenticated, EsPaciente, TieneConsentimiento]

    def get(self, request, pk):
        caso = get_object_or_404(CasosECG, pk=pk, paciente=request.user)
        return Response(ResultadoECGSerializer(caso, context={"request": request}).data)


class CasoECGSenalPacienteAPIView(VistaAutenticada):
    """Señal de 12 derivaciones (mV) del ECG del paciente, para dibujar el trazado."""

    permission_classes = [IsAuthenticated, EsPaciente, TieneConsentimiento]

    def get(self, request, pk):
        caso = get_object_or_404(CasosECG, pk=pk, paciente=request.user)
        try:
            with caso.archivo_ecg.open("rb") as archivo:
                senal = leer_senal_zip(archivo)
        except (ErrorPaquete, ErrorECG) as exc:
            return Response({"detail": exc.mensaje}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except FileNotFoundError:
            return Response(
                {"detail": "El archivo de este ECG ya no está disponible en el servidor."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(senal)


# -----------------------------------------------------------------------------
# Recomendaciones: catálogo, entrega al usuario y claridad
# -----------------------------------------------------------------------------

class CatalogoRecomendacionesAPIView(VistaAutenticada):
    permission_classes = [IsAuthenticated, EsPaciente, TieneConsentimiento]

    def get(self, request):
        queryset = RecomendacionCatalogo.objects.filter(activa=True)
        categoria = request.query_params.get("categoria")
        if categoria:
            queryset = queryset.filter(categoria=categoria)
        return Response(RecomendacionCatalogoSerializer(queryset, many=True).data)
    
class GenerarRecomendacionesAPIView(VistaAutenticada):
    permission_classes = [IsAuthenticated, EsPaciente, TieneConsentimiento]

    def post(self, request):
        solicitar_ayuda = request.data.get("necesito_ayuda_ahora", False)
        texto_libre = request.data.get("texto_libre", "")

        if not isinstance(solicitar_ayuda, bool):
            return Response(
                {"necesito_ayuda_ahora": "Debe ser true o false."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(texto_libre, str) or len(texto_libre) > 1000:
            return Response(
                {"texto_libre": "Debe ser texto de máximo 1000 caracteres."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        resultado = evaluar_habitos_y_sintomas(
            request.user,
            necesito_ayuda_ahora=solicitar_ayuda,
            texto_libre=texto_libre,
        )
        return Response(resultado, status=status.HTTP_200_OK)


class RecomendacionesMostradasAPIView(VistaAutenticada):
    permission_classes = [IsAuthenticated, EsPaciente, TieneConsentimiento]

    def get(self, request):
        queryset = RecomendacionMostrada.objects.filter(paciente=request.user).select_related("recomendacion")
        return Response(RecomendacionMostradaSerializer(queryset, many=True).data)

    def post(self, request):
        input_serializer = MostrarRecomendacionSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        data = input_serializer.validated_data
        recomendacion = get_object_or_404(
            RecomendacionCatalogo,
            codigo=data["recomendacion_codigo"],
            activa=True,
        )
        registro = None
        if data.get("registro_diario_id") is not None:
            registro = get_object_or_404(
                RegistroDiario,
                pk=data["registro_diario_id"],
                paciente=request.user,
            )

        try:
            with transaction.atomic():
                mostrada = RecomendacionMostrada.objects.create(
                    paciente=request.user,
                    recomendacion=recomendacion,
                    registro_diario=registro,
                    regla_codigo=data.get("regla_codigo", ""),
                )
        except IntegrityError:
            return Response(
                {"detail": "Esta recomendación ya fue registrada para el usuario en la fecha actual."},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(RecomendacionMostradaSerializer(mostrada).data, status=status.HTTP_201_CREATED)


class ClaridadRecomendacionAPIView(VistaAutenticada):
    permission_classes = [IsAuthenticated, EsPaciente, TieneConsentimiento]

    def patch(self, request, pk):
        mostrada = get_object_or_404(RecomendacionMostrada, pk=pk, paciente=request.user)
        serializer = RespuestaClaridadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mostrada.respuesta_claridad = serializer.validated_data["respuesta_claridad"]
        mostrada.fecha_respuesta = timezone.now()
        mostrada.save(update_fields=["respuesta_claridad", "fecha_respuesta"])
        return Response(RecomendacionMostradaSerializer(mostrada).data)


# -----------------------------------------------------------------------------
# Panel profesional
# -----------------------------------------------------------------------------

class CasosProfesionalListaAPIView(VistaAutenticada):
    permission_classes = [IsAuthenticated, EsProfesional]

    def get(self, request):
        queryset = CasosECG.objects.select_related("paciente", "revisado_por").all()
        estado = request.query_params.get("estado")
        prioridad = request.query_params.get("prioridad")
        busqueda = request.query_params.get("buscar")
        if estado:
            queryset = queryset.filter(estado_revision=estado)
        if prioridad:
            queryset = queryset.filter(prioridad_ia=prioridad)
        if busqueda:
            queryset = queryset.filter(
                Q(paciente__codigo_participante__icontains=busqueda)
                | Q(paciente__nombre__icontains=busqueda)
                | Q(caso_asignado__icontains=busqueda)
            )
        return Response(CasoECGProfesionalSerializer(queryset, many=True).data)


class CasoProfesionalDetalleAPIView(VistaAutenticada):
    permission_classes = [IsAuthenticated, EsProfesional]

    def get(self, request, pk):
        caso = get_object_or_404(
            CasosECG.objects.select_related("paciente", "revisado_por"), pk=pk
        )
        return Response(CasoECGProfesionalSerializer(caso).data)


class RevisionProfesionalAPIView(VistaAutenticada):
    permission_classes = [IsAuthenticated, EsProfesional]

    def post(self, request, pk):
        caso = get_object_or_404(CasosECG, pk=pk)
        serializer = RevisionProfesionalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # No se permite validar un resultado que aún no ha sido procesado.
        # La integración real con IA se hará en una etapa posterior.
        if caso.estado_procesamiento != EstadoProcesamientoECG.COMPLETADO:
            return Response(
                {"detail": "El caso todavía no tiene un resultado de procesamiento para revisar."},
                status=status.HTTP_409_CONFLICT,
            )

        data = serializer.validated_data
        ahora = timezone.now()
        caso.revisado_por = request.user
        caso.fecha_revision = ahora
        caso.notas_medico = data.get("notas_medico", caso.notas_medico)

        if caso.inicio_revision:
            caso.tiempo_revision_seg = max(0, int((ahora - caso.inicio_revision).total_seconds()))

        if data["accion"] == "VALIDAR":
            caso.estado_revision = EstadoRevisionECG.VALIDADO
        else:
            caso.estado_revision = EstadoRevisionECG.MODIFICADO
            caso.superclases_modificadas = data["superclases_modificadas"]

        caso.save()
        return Response(CasoECGProfesionalSerializer(caso).data)

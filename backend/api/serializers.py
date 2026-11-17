from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from decimal import Decimal
from rest_framework import serializers

from .models import (
    CasosECG,
    Consentimiento,
    EvaluacionPeriodica,
    PerfilCardiovascular,
    RecomendacionCatalogo,
    RecomendacionMostrada,
    RegistroDiario,
)

User = get_user_model()


class UsuarioPublicoSerializer(serializers.ModelSerializer):
    """Campos de usuario que pueden devolverse al frontend. Nunca incluye password."""

    class Meta:
        model = User
        fields = (
            "id", "email", "nombre", "codigo_participante", "edad", "sexo", "rol"
        )
        read_only_fields = fields


class RegistroUsuarioSerializer(serializers.Serializer):
    email = serializers.EmailField()
    nombre = serializers.CharField(max_length=60)
    codigo_participante = serializers.CharField(max_length=60)
    edad = serializers.IntegerField(min_value=35, max_value=99)
    sexo = serializers.ChoiceField(
        choices=(
            ("Femenino", "Femenino"),
            ("Masculino", "Masculino"),
            ("Prefiero no decirlo", "Prefiero no decirlo"),
        ),
        required=False,
        allow_blank=True,
    )
    password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)
    password_confirmation = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Ya existe una cuenta con este correo.")
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("El correo ya está registrado como nombre de usuario.")
        return value

    def validate_codigo_participante(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("El código de participante es obligatorio.")
        if User.objects.filter(codigo_participante__iexact=value).exists():
            raise serializers.ValidationError("Este código de participante ya está asignado.")
        return value

    def validate_nombre(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("El nombre o alias es obligatorio.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirmation"]:
            raise serializers.ValidationError({"password_confirmation": "Las contraseñas no coinciden."})
        try:
            validate_password(attrs["password"])
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirmation")
        password = validated_data.pop("password")
        email = validated_data["email"]
        # AbstractUser conserva username; usamos el correo como identificador de acceso.
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            rol="PACIENTE",  # El registro público nunca puede crear profesionales.
            **{key: value for key, value in validated_data.items() if key != "email"},
        )
        return user


class InicioSesionSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class ConsentimientoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consentimiento
        fields = ("id", "acepta_tratamiento_datos", "acepta_piloto_no_clinico", "fecha_consentimiento")
        read_only_fields = ("id", "fecha_consentimiento")

    def validate(self, attrs):
        tratamiento = attrs.get(
            "acepta_tratamiento_datos",
            getattr(self.instance, "acepta_tratamiento_datos", False),
        )
        piloto = attrs.get(
            "acepta_piloto_no_clinico",
            getattr(self.instance, "acepta_piloto_no_clinico", False),
        )
        if not tratamiento or not piloto:
            raise serializers.ValidationError(
                "Para continuar deben aceptarse el tratamiento de datos y el carácter experimental del piloto."
            )
        return attrs


class PerfilCardiovascularSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerfilCardiovascular
        exclude = ("paciente",)
        read_only_fields = ("id", "imc", "creado_en", "actualizado_en")

    def _validar_lista(self, value, opciones, nombre_campo, opcion_ninguna):
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise serializers.ValidationError("Debe enviarse una lista de textos.")
        desconocidas = set(value) - opciones
        if desconocidas:
            raise serializers.ValidationError(
                f"Opciones no permitidas: {', '.join(sorted(desconocidas))}."
            )
        if not value:
            raise serializers.ValidationError("Seleccione al menos una opción.")
        if opcion_ninguna in value and len(value) > 1:
            raise serializers.ValidationError(
                "La opción 'Ninguna' no puede combinarse con otras opciones."
            )
        return value

    def validate_condiciones_diagnosticadas(self, value):
        return self._validar_lista(
            value, PerfilCardiovascular.CONDICIONES, "condiciones_diagnosticadas", "ninguna"
        )

    def validate_sintomas_ahora(self, value):
        return self._validar_lista(
            value, PerfilCardiovascular.SINTOMAS_ACTUALES, "sintomas_ahora", "Ninguno"
        )

    def validate_sintomas_ultimo_mes(self, value):
        return self._validar_lista(
            value, PerfilCardiovascular.SINTOMAS_ULTIMO_MES, "sintomas_ultimo_mes", "Ninguno"
        )


class RegistroDiarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistroDiario
        exclude = ("paciente",)
        read_only_fields = ("id", "fecha", "manana_completada_en", "noche_completada_en", "creado_en", "actualizado_en")


class EncuestaMananaSerializer(serializers.Serializer):
    horas_sueno_anoche = serializers.ChoiceField(choices=RegistroDiario.HorasSuenoEncuesta.choices)
    despertares_noche = serializers.ChoiceField(choices=RegistroDiario.Despertares.choices)
    idas_bano_noche = serializers.ChoiceField(choices=RegistroDiario.IdasBano.choices)
    sensacion_despertar = serializers.ChoiceField(choices=RegistroDiario.SensacionDespertar.choices)
    hora_acostarse_anoche = serializers.ChoiceField(
        choices=RegistroDiario.HoraAcostarseEncuesta.choices,
        required=False,
        allow_null=True,
    )


class EncuestaNocheSerializer(serializers.Serializer):
    # Preguntas de la encuesta funcional de la noche.
    siesta_tarde = serializers.ChoiceField(choices=RegistroDiario.Siesta.choices)
    caminata_hoy = serializers.ChoiceField(choices=RegistroDiario.Caminata.choices)
    ejercicio_hoy = serializers.ChoiceField(choices=RegistroDiario.Ejercicio.choices)
    sentado_mas_6h = serializers.BooleanField()
    frutas_verduras_hoy = serializers.ChoiceField(choices=RegistroDiario.FrutasVerduras.choices)
    fritos_paquete_hoy = serializers.ChoiceField(choices=RegistroDiario.FrecuenciaComidaProcesada.choices)
    bebida_azucarada_hoy = serializers.ChoiceField(choices=RegistroDiario.BebidaAzucarada.choices)
    vasos_agua_respuesta = serializers.ChoiceField(choices=RegistroDiario.VasosAguaRespuesta.choices)
    sal_extra_hoy = serializers.ChoiceField(choices=RegistroDiario.SalExtra.choices)
    estres_hoy = serializers.ChoiceField(choices=RegistroDiario.EstresEncuesta.choices)
    sintoma_hoy = serializers.BooleanField()

    # Preguntas condicionales del perfil y variables ampliadas del catálogo.
    fumo_hoy = serializers.ChoiceField(choices=RegistroDiario.FumoHoy.choices, required=False, allow_null=True)
    alcohol_hoy = serializers.ChoiceField(choices=RegistroDiario.AlcoholHoy.choices, required=False, allow_null=True)
    medicamentos_hoy = serializers.ChoiceField(choices=RegistroDiario.MedicamentosHoy.choices, required=False, allow_null=True)
    frutas_verduras_porciones = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    ultraprocesados_veces = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    bebidas_azucaradas_cantidad = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    vasos_agua = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    actividad_moderada_minutos = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    actividad_vigorosa_minutos = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    fortalecimiento_muscular = serializers.BooleanField(required=False, allow_null=True)
    horas_sentado = serializers.DecimalField(
    required=False,
    allow_null=True,
    max_digits=3,
    decimal_places=1,
    min_value=Decimal("0"),
    max_value=Decimal("16")
    )   

    horas_sueno = serializers.DecimalField(
    required=False,
    allow_null=True,
    max_digits=3,
    decimal_places=1,
    min_value=Decimal("3"),
    max_value=Decimal("12")
                                )
    estres_nivel = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=5)
    cigarrillos_hoy = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    uso_vapeador = serializers.BooleanField(required=False, allow_null=True)
    uso_narguile = serializers.BooleanField(required=False, allow_null=True)
    uso_puro = serializers.BooleanField(required=False, allow_null=True)
    uso_otro_producto_tabaco = serializers.BooleanField(required=False, allow_null=True)
    exposicion_humo_ajeno = serializers.BooleanField(required=False, allow_null=True)

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            perfil = getattr(user, "perfil_cardiovascular", None)
            if perfil:
                if perfil.tabaquismo in {"OCASIONAL", "DIARIO"} and not attrs.get("fumo_hoy"):
                    raise serializers.ValidationError({"fumo_hoy": "Esta pregunta es obligatoria según su perfil."})
                if perfil.alcohol_semana not in (None, "NUNCA") and not attrs.get("alcohol_hoy"):
                    raise serializers.ValidationError({"alcohol_hoy": "Esta pregunta es obligatoria según su perfil."})
                if perfil.toma_medicamentos not in (None, "NO") and not attrs.get("medicamentos_hoy"):
                    raise serializers.ValidationError({"medicamentos_hoy": "Esta pregunta es obligatoria según su perfil."})
        return attrs


class EvaluacionPeriodicaSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluacionPeriodica
        exclude = ("paciente",)
        read_only_fields = ("id", "creado_en")

    def validate(self, attrs):
        keys = ("pss4_item_1", "pss4_item_2", "pss4_item_3", "pss4_item_4")
        presentes = [key for key in keys if attrs.get(key) is not None]
        if presentes and len(presentes) != 4:
            raise serializers.ValidationError(
                "Para registrar el PSS-4 deben enviarse sus cuatro respuestas (0 a 4)."
            )
        otras_mediciones = (
            attrs.get("dificultad_sueno_noches"),
            attrs.get("ronquidos_pausas_somnolencia"),
        )
        if not presentes and all(value is None for value in otras_mediciones):
            raise serializers.ValidationError("Registre al menos una medición periódica.")
        return attrs


class ResultadoECGSerializer(serializers.ModelSerializer):
    resultados_por_superclase = serializers.SerializerMethodField()

    class Meta:
        model = CasosECG
        fields = (
            "id", "caso_asignado", "archivo_ecg", "confirma_prueba", "fecha_carga",
            "estado_procesamiento", "mensaje_error", "estado_revision", "prioridad_ia",
            "norm_prob", "mi_prob", "sttc_prob", "cd_prob", "hyp_prob",
            "resultados_por_superclase", "aviso_limitaciones",
        )
        read_only_fields = (
            "id", "fecha_carga", "estado_procesamiento", "mensaje_error", "estado_revision",
            "prioridad_ia", "norm_prob", "mi_prob", "sttc_prob", "cd_prob", "hyp_prob",
            "resultados_por_superclase", "aviso_limitaciones",
        )

    def get_resultados_por_superclase(self, obj):
        return obj.obtener_resultados_por_superclase()

    def validate(self, attrs):
        if not attrs.get("confirma_prueba", getattr(self.instance, "confirma_prueba", False)):
            raise serializers.ValidationError({"confirma_prueba": "Debe confirmar que es un caso de prueba y no un ECG propio."})
        if not attrs.get("caso_asignado", getattr(self.instance, "caso_asignado", "")):
            raise serializers.ValidationError({"caso_asignado": "Seleccione el caso asignado por el equipo."})
        return attrs


class CasoECGProfesionalSerializer(serializers.ModelSerializer):
    paciente_nombre = serializers.CharField(source="paciente.nombre", read_only=True)
    codigo_participante = serializers.CharField(source="paciente.codigo_participante", read_only=True)
    resultados_por_superclase = serializers.SerializerMethodField()

    class Meta:
        model = CasosECG
        fields = (
            "id", "paciente_nombre", "codigo_participante", "caso_asignado", "archivo_ecg",
            "fecha_carga", "estado_procesamiento", "estado_revision", "prioridad_ia",
            "norm_prob", "mi_prob", "sttc_prob", "cd_prob", "hyp_prob",
            "resultados_por_superclase", "etiqueta_referencia", "superclases_modificadas",
            "notas_medico", "revisado_por", "fecha_revision", "tiempo_revision_seg",
            "aviso_limitaciones",
        )
        read_only_fields = fields

    def get_resultados_por_superclase(self, obj):
        return obj.obtener_resultados_por_superclase()


class RevisionProfesionalSerializer(serializers.Serializer):
    accion = serializers.ChoiceField(choices=(("VALIDAR", "Validar"), ("MODIFICAR", "Modificar")))
    superclases_modificadas = serializers.ListField(
        child=serializers.ChoiceField(choices=tuple((x, x) for x in CasosECG.NOMBRES_SUPERCLASE)),
        required=False,
        allow_empty=True,
    )
    notas_medico = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs["accion"] == "MODIFICAR" and not attrs.get("superclases_modificadas"):
            raise serializers.ValidationError({"superclases_modificadas": "Indique las superclases corregidas."})
        return attrs


class RecomendacionCatalogoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecomendacionCatalogo
        fields = ("id", "codigo", "categoria", "situacion_identificada", "texto_recomendacion", "activa")
        read_only_fields = fields


class RecomendacionMostradaSerializer(serializers.ModelSerializer):
    codigo = serializers.CharField(source="recomendacion.codigo", read_only=True)
    categoria = serializers.CharField(source="categoria_snapshot", read_only=True)
    situacion_identificada = serializers.CharField(source="situacion_snapshot", read_only=True)
    texto_recomendacion = serializers.CharField(source="texto_snapshot", read_only=True)

    class Meta:
        model = RecomendacionMostrada
        fields = (
            "id", "codigo", "categoria", "situacion_identificada", "texto_recomendacion",
            "regla_codigo", "fecha_mostrada", "respuesta_claridad", "fecha_respuesta",
        )
        read_only_fields = fields


class MostrarRecomendacionSerializer(serializers.Serializer):
    recomendacion_codigo = serializers.CharField(max_length=10)
    regla_codigo = serializers.CharField(max_length=10, required=False, allow_blank=True)
    registro_diario_id = serializers.IntegerField(required=False, allow_null=True)


class RespuestaClaridadSerializer(serializers.Serializer):
    respuesta_claridad = serializers.ChoiceField(choices=RecomendacionMostrada.Claridad.choices)

from decimal import Decimal, ROUND_HALF_UP

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


# -----------------------------------------------------------------------------
# Opciones reutilizables
# -----------------------------------------------------------------------------

class RolUsuario(models.TextChoices):
    PACIENTE = "PACIENTE", "Paciente"
    PROFESIONAL = "PROFESIONAL", "Profesional"


class SexoRegistrado(models.TextChoices):
    FEMENINO = "Femenino", "Femenino"
    MASCULINO = "Masculino", "Masculino"
    PREFIERO_NO_DECIRLO = "Prefiero no decirlo", "Prefiero no decirlo"


class SiNoNoSe(models.TextChoices):
    SI = "SI", "Sí"
    NO = "NO", "No"
    NO_SE = "NO_SE", "No sé"


class EstadoRevisionECG(models.TextChoices):
    PENDIENTE = "PENDIENTE", "Pendiente"
    VALIDADO = "VALIDADO", "Validado"
    MODIFICADO = "MODIFICADO", "Modificado"


class EstadoProcesamientoECG(models.TextChoices):
    PENDIENTE = "PENDIENTE", "Pendiente"
    VALIDANDO = "VALIDANDO", "Validando"
    PROCESANDO = "PROCESANDO", "Procesando"
    COMPLETADO = "COMPLETADO", "Completado"
    ERROR = "ERROR", "Error"


class PrioridadECG(models.TextChoices):
    ALTA = "ALTA", "Alta"
    MEDIA = "MEDIA", "Media"
    BAJA = "BAJA", "Baja"


# -----------------------------------------------------------------------------
# 1. Usuario
# -----------------------------------------------------------------------------

class CustomUser(AbstractUser):
    """Usuario de la plataforma. username se conserva por compatibilidad Django.

    En el servicio de registro se debe asignar username=email para que el acceso
    pueda realizarse con el correo mientras se conserva el modelo AbstractUser.
    """

    email = models.EmailField(unique=True)
    nombre = models.CharField(max_length=60, blank=True, default="")
    codigo_participante = models.CharField(
        max_length=60,
        unique=True,
        null=True,
        blank=True,
        help_text="Código entregado por el equipo, por ejemplo P01 a P10."
    )
    edad = models.PositiveSmallIntegerField(null=True, blank=True)
    sexo = models.CharField(
        max_length=25,
        choices=SexoRegistrado.choices,
        blank=True,
        default="",
    )
    rol = models.CharField(
        max_length=15,
        choices=RolUsuario.choices,
        default=RolUsuario.PACIENTE,
    )

    def clean(self):
        super().clean()
        errores = {}

        if self.rol == RolUsuario.PACIENTE:
            if not self.nombre or not self.nombre.strip():
                errores["nombre"] = "El nombre o alias es obligatorio."
            if not self.codigo_participante:
                errores["codigo_participante"] = "El código de participante es obligatorio."
            if self.edad is None or not 35 <= self.edad <= 99:
                errores["edad"] = "El piloto admite participantes de 35 a 99 años."

        if errores:
            raise ValidationError(errores)

    def __str__(self):
        return self.nombre or self.email or self.username


# -----------------------------------------------------------------------------
# 2. Consentimiento informado
# -----------------------------------------------------------------------------

class Consentimiento(models.Model):
    paciente = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="consentimiento",
    )
    acepta_tratamiento_datos = models.BooleanField(default=False)
    acepta_piloto_no_clinico = models.BooleanField(default=False)
    fecha_consentimiento = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Consentimiento informado"
        verbose_name_plural = "Consentimientos informados"

    def clean(self):
        super().clean()
        if not self.acepta_tratamiento_datos or not self.acepta_piloto_no_clinico:
            raise ValidationError(
                "Para guardar el consentimiento deben aceptarse las dos condiciones."
            )

    def save(self, *args, **kwargs):
        # Un consentimiento solo se persiste cuando ambas casillas fueron aceptadas.
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Consentimiento de {self.paciente}"


# -----------------------------------------------------------------------------
# 3. Perfil cardiovascular
# -----------------------------------------------------------------------------

class PerfilCardiovascular(models.Model):
    class Medicamentos(models.TextChoices):
        TODOS_DIAS = "TODOS_DIAS", "Sí, todos los días"
        A_VECES_OLVIDA = "A_VECES_OLVIDA", "Sí, pero a veces se me olvidan"
        NO = "NO", "No"

    class AntecedentesFamiliares(models.TextChoices):
        SI = "SI", "Sí"
        NO = "NO", "No"
        NO_SE = "NO_SE", "No sé"

    class FrutasVerdurasPerfil(models.TextChoices):
        CERO_UNA = "0_1", "0 a 1"
        DOS_CUATRO = "2_4", "2 a 4"
        CINCO_MAS = "5_MAS", "5 o más"

    class SalProcesados(models.TextChoices):
        CASI_NUNCA = "CASI_NUNCA", "Casi nunca"
        ALGUNAS_VECES = "ALGUNAS_VECES", "Algunas veces por semana"
        TODOS_DIAS = "TODOS_DIAS", "Todos los días"

    class BebidasAzucaradasPerfil(models.TextChoices):
        CASI_NUNCA = "CASI_NUNCA", "Casi nunca"
        UNA_TRES_SEMANA = "1_3_SEMANA", "1 a 3 veces por semana"
        TODOS_DIAS = "TODOS_DIAS", "Todos los días"

    class ActividadSemanal(models.TextChoices):
        MENOS_60 = "MENOS_60", "Menos de 60"
        ENTRE_60_149 = "60_149", "Entre 60 y 149"
        CIENTO_CINCUENTA_MAS = "150_MAS", "150 o más"

    class HorasSentadoPerfil(models.TextChoices):
        MENOS_6 = "MENOS_6", "Menos de 6"
        ENTRE_6_8 = "6_8", "6 a 8"
        MAS_8 = "MAS_8", "Más de 8"

    class HorasSuenoPerfil(models.TextChoices):
        MENOS_6 = "Menos de 6", "Menos de 6"
        ENTRE_6_7 = "Entre 6 y 7", "Entre 6 y 7"
        ENTRE_7_9 = "Entre 7 y 9", "Entre 7 y 9"
        MAS_9 = "Más de 9", "Más de 9"

    class EstresPerfil(models.TextChoices):
        CASI_NUNCA = "CASI_NUNCA", "Nunca o casi nunca"
        ALGUNOS_DIAS = "ALGUNOS_DIAS", "Algunos días"
        CASI_TODOS = "CASI_TODOS", "Casi todos los días"

    class TabaquismoPerfil(models.TextChoices):
        NUNCA = "NUNCA", "Nunca he fumado"
        LO_DEJE = "LO_DEJE", "Lo dejé"
        OCASIONAL = "OCASIONAL", "Sí, ocasionalmente"
        DIARIO = "DIARIO", "Sí, todos los días"

    class AlcoholPerfil(models.TextChoices):
        NUNCA = "NUNCA", "Nunca"
        UNA_DOS = "1_2", "1 a 2 veces"
        TRES_MAS = "3_MAS", "3 o más veces"

    CONDICIONES = {
        "hipertension",
        "diabetes",
        "colesterol_trigliceridos_altos",
        "enfermedad_cardiaca_infarto_previo",
        "ninguna",
    }
    SINTOMAS_ACTUALES = {
        "Dolor, presión u opresión en el pecho que dura más de unos minutos",
        "Dolor que se extiende al brazo, la mandíbula o la espalda",
        "Falta de aire de forma repentina",
        "Desmayo o mareo fuerte",
        "Ninguno",
    }
    SINTOMAS_ULTIMO_MES = {
        "Palpitaciones o latidos irregulares",
        "Cansancio o falta de aire al hacer esfuerzos que antes no te costaban",
        "Hinchazón en los tobillos o las piernas",
        "Ninguno",
    }

    paciente = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="perfil_cardiovascular",
    )

    peso_kg = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("30")), MaxValueValidator(Decimal("250"))],
    )
    estatura_cm = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(120), MaxValueValidator(220)],
    )
    imc = models.DecimalField(max_digits=5, decimal_places=1, editable=False)
    presion_arterial = models.CharField(
        max_length=20,
        help_text="Ejemplo: 130/85 o 'No sé'. Es un autorreporte.",
    )

    condiciones_diagnosticadas = models.JSONField(default=list)
    toma_medicamentos = models.CharField(
        max_length=30, choices=Medicamentos.choices, blank=True, null=True
    )
    antecedentes_familiares = models.CharField(
        max_length=20, choices=AntecedentesFamiliares.choices
    )
    frutas_verduras_dia = models.CharField(
        max_length=20, choices=FrutasVerdurasPerfil.choices, blank=True, null=True
    )
    sal_procesados = models.CharField(
        max_length=35, choices=SalProcesados.choices, blank=True, null=True
    )
    bebidas_azucaradas = models.CharField(
        max_length=35, choices=BebidasAzucaradasPerfil.choices, blank=True, null=True
    )
    actividad_min_semana = models.CharField(
        max_length=25, choices=ActividadSemanal.choices, blank=True, null=True
    )
    horas_sentado = models.CharField(
        max_length=20, choices=HorasSentadoPerfil.choices, blank=True, null=True
    )
    horas_sueno_promedio = models.CharField(
        max_length=50, choices=HorasSuenoPerfil.choices
    )
    estres_dos_semanas = models.CharField(
        max_length=30, choices=EstresPerfil.choices, blank=True, null=True
    )
    tabaquismo = models.CharField(max_length=50, choices=TabaquismoPerfil.choices)
    alcohol_semana = models.CharField(
        max_length=25, choices=AlcoholPerfil.choices, blank=True, null=True
    )

    sintomas_ahora = models.JSONField(default=list)
    sintomas_ultimo_mes = models.JSONField(default=list)
    hora_despertar = models.TimeField(null=True, blank=True)
    hora_acostarse = models.TimeField(null=True, blank=True)
    # Datos de seguridad y contexto requeridos por R-01, R-10, R-12, R-15 y R-16.
    # None significa "no informado"; no debe tratarse como False.
    parq_completado = models.BooleanField(null=True, blank=True, default=None)
    parq_requiere_revision = models.BooleanField(null=True, blank=True, default=None)
    ejercicio_supervisado_indicado = models.BooleanField(null=True, blank=True, default=None)

    restriccion_liquidos_medica = models.BooleanField(null=True, blank=True, default=None)
    insuficiencia_cardiaca = models.BooleanField(null=True, blank=True, default=None)
    enfermedad_renal = models.BooleanField(null=True, blank=True, default=None)
    embarazo = models.BooleanField(null=True, blank=True, default=None)

    poco_acceso_fruta = models.BooleanField(null=True, blank=True, default=None)
    interes_hidratacion = models.BooleanField(null=True, blank=True, default=None)
    quiere_dejar_fumar = models.BooleanField(null=True, blank=True, default=None)


    creado_en = models.DateTimeField(default=timezone.now, editable=False)
    actualizado_en = models.DateTimeField(default=timezone.now)

    def clean(self):
        super().clean()
        errores = {}

        listas = (
            ("condiciones_diagnosticadas", self.CONDICIONES),
            ("sintomas_ahora", self.SINTOMAS_ACTUALES),
            ("sintomas_ultimo_mes", self.SINTOMAS_ULTIMO_MES),
        )
        for campo, opciones in listas:
            valores = getattr(self, campo, None)
            if not isinstance(valores, list):
                errores[campo] = "Debe enviarse una lista de opciones."
                continue
            if not all(isinstance(valor, str) for valor in valores):
                errores[campo] = "Cada selección debe ser un texto."
                continue
            desconocidos = set(valores) - opciones
            if desconocidos:
                errores[campo] = f"Contiene opciones no permitidas: {sorted(desconocidos)}."
            if not valores:
                errores[campo] = "Seleccione al menos una opción."
            if "ninguna" in valores and len(valores) > 1:
                errores[campo] = "La opción 'ninguna' no puede combinarse con otras opciones."

        obligatorios = [
            "peso_kg", "estatura_cm", "presion_arterial",
            "condiciones_diagnosticadas", "toma_medicamentos",
            "antecedentes_familiares", "frutas_verduras_dia", "sal_procesados",
            "bebidas_azucaradas", "actividad_min_semana", "horas_sentado",
            "horas_sueno_promedio", "estres_dos_semanas", "tabaquismo",
            "alcohol_semana", "sintomas_ahora", "sintomas_ultimo_mes",
        ]
        for campo in obligatorios:
            valor = getattr(self, campo, None)
            if valor is None or valor == "":
                errores.setdefault(campo, "Este dato es obligatorio para completar el perfil.")

        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.peso_kg is not None and self.estatura_cm:
            altura_m = Decimal(self.estatura_cm) / Decimal("100")
            self.imc = (self.peso_kg / (altura_m * altura_m)).quantize(
                Decimal("0.1"), rounding=ROUND_HALF_UP
            )
        self.actualizado_en = timezone.now()
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = set(kwargs["update_fields"]) | {"actualizado_en", "imc"}
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Perfil cardiovascular de {self.paciente}"


# -----------------------------------------------------------------------------
# 4. Registro diario: encuesta de mañana + encuesta de noche + catálogo diario
# -----------------------------------------------------------------------------

class RegistroDiario(models.Model):
    class HorasSuenoEncuesta(models.TextChoices):
        MENOS_5 = "MENOS_5", "Menos de 5"
        ENTRE_5_6 = "5_6", "5–6"
        ENTRE_6_7 = "6_7", "6–7"
        ENTRE_7_9 = "7_9", "7–9"
        MAS_9 = "MAS_9", "Más de 9"

    class Despertares(models.TextChoices):
        NINGUNO = "NINGUNO", "No"
        UNA_VEZ = "UNA_VEZ", "1 vez"
        DOS_TRES = "DOS_TRES", "2 o 3 veces"
        MUCHAS = "MUCHAS", "Muchas veces"

    class IdasBano(models.TextChoices):
        NINGUNA = "NINGUNA", "No"
        UNA = "UNA", "1 vez"
        DOS_MAS = "DOS_MAS", "2 o más veces"

    class SensacionDespertar(models.TextChoices):
        DESCANSADO = "DESCANSADO", "Descansado(a)"
        REGULAR = "REGULAR", "Más o menos"
        CANSADO = "CANSADO", "Cansado(a)"

    class HoraAcostarseEncuesta(models.TextChoices):
        ANTES_10 = "ANTES_22", "Antes de las 10 p. m."
        ENTRE_10_11 = "22_23", "10–11 p. m."
        ENTRE_11_12 = "23_00", "11 p. m.–12 a. m."
        DESPUES_12 = "DESPUES_00", "Después de las 12"

    class Siesta(models.TextChoices):
        NO = "NO", "No"
        MENOS_30 = "MENOS_30", "Menos de 30 min"
        ENTRE_30_60 = "30_60", "30 a 60 min"
        MAS_60 = "MAS_60", "Más de 1 hora"

    class Caminata(models.TextChoices):
        NO = "NO", "No"
        ENTRE_10_20 = "10_20", "10–20 min"
        ENTRE_20_30 = "20_30", "20–30 min"
        MAS_30 = "MAS_30", "Más de 30 min"

    class Ejercicio(models.TextChoices):
        NO = "NO", "No"
        SUAVE = "SUAVE", "Sí, suave"
        MODERADO = "MODERADO", "Sí, moderado"
        INTENSO = "INTENSO", "Sí, intenso"

    class FrutasVerduras(models.TextChoices):
        CERO = "0", "0"
        UNA_DOS = "1_2", "1–2"
        TRES_CUATRO = "3_4", "3–4"
        CINCO_MAS = "5_MAS", "5 o más"

    class FrecuenciaComidaProcesada(models.TextChoices):
        NO = "NO", "No"
        UNA = "UNA", "Una vez"
        VARIAS = "VARIAS", "Varias veces"

    class BebidaAzucarada(models.TextChoices):
        NO = "NO", "No"
        UN_VASO = "UN_VASO", "1 vaso"
        DOS_MAS = "DOS_MAS", "2 o más"

    class SalExtra(models.TextChoices):
        NO = "NO", "No"
        UN_POCO = "UN_POCO", "Un poco"
        BASTANTE = "BASTANTE", "Sí, bastante"

    class EstresEncuesta(models.TextChoices):
        BAJO = "BAJO", "Bajo"
        MEDIO = "MEDIO", "Medio"
        ALTO = "ALTO", "Alto"

    class VasosAguaRespuesta(models.TextChoices):
        CERO_DOS = "0_2", "0–2"
        TRES_CINCO = "3_5", "3–5"
        SEIS_OCHO = "6_8", "6–8"
        MAS_OCHO = "MAS_8", "Más de 8"

    class FumoHoy(models.TextChoices):
        NO = "NO", "No"
        ENTRE_1_5 = "1_5", "1–5 cigarrillos"
        MAS_5 = "MAS_5", "Más de 5"

    class AlcoholHoy(models.TextChoices):
        NO = "NO", "No"
        ENTRE_1_2 = "1_2", "1–2 tragos"
        TRES_MAS = "3_MAS", "3 o más"

    class MedicamentosHoy(models.TextChoices):
        SI = "SI", "Sí"
        OLVIDO = "OLVIDO", "Se me olvidó"

    paciente = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="registros_diarios",
    )
    fecha = models.DateField(default=timezone.localdate)

    # Encuesta de la mañana
    horas_sueno_anoche = models.CharField(
        max_length=20, choices=HorasSuenoEncuesta.choices, null=True, blank=True
    )
    despertares_noche = models.CharField(
        max_length=20, choices=Despertares.choices, null=True, blank=True
    )
    idas_bano_noche = models.CharField(
        max_length=20, choices=IdasBano.choices, null=True, blank=True
    )
    sensacion_despertar = models.CharField(
        max_length=20, choices=SensacionDespertar.choices, null=True, blank=True
    )
    hora_acostarse_anoche = models.CharField(
        max_length=20, choices=HoraAcostarseEncuesta.choices, null=True, blank=True
    )
     # Hora real para medir la variabilidad diaria de la hora de acostarse (R-06/SU-02).
    hora_acostarse_real = models.TimeField(null=True, blank=True)

    manana_completada_en = models.DateTimeField(null=True, blank=True)

    # Encuesta de la noche
    siesta_tarde = models.CharField(
        max_length=20, choices=Siesta.choices, null=True, blank=True
    )
    caminata_hoy = models.CharField(
        max_length=20, choices=Caminata.choices, null=True, blank=True
    )
    ejercicio_hoy = models.CharField(
        max_length=20, choices=Ejercicio.choices, null=True, blank=True
    )
    sentado_mas_6h = models.BooleanField(null=True, blank=True)
    frutas_verduras_hoy = models.CharField(
        max_length=20, choices=FrutasVerduras.choices, null=True, blank=True
    )
    fritos_paquete_hoy = models.CharField(
        max_length=20, choices=FrecuenciaComidaProcesada.choices, null=True, blank=True
    )
    bebida_azucarada_hoy = models.CharField(
        max_length=20, choices=BebidaAzucarada.choices, null=True, blank=True
    )
    vasos_agua_respuesta = models.CharField(
        max_length=20, choices=VasosAguaRespuesta.choices, null=True, blank=True
    )
    sal_extra_hoy = models.CharField(
        max_length=20, choices=SalExtra.choices, null=True, blank=True
    )
    estres_hoy = models.CharField(
        max_length=20, choices=EstresEncuesta.choices, null=True, blank=True
    )
    sintoma_hoy = models.BooleanField(null=True, blank=True)
    minutos_actividad = models.IntegerField(
        default=0,
        help_text="Total legado de minutos; se sincroniza con los minutos moderados y vigorosos si se registran.",
    )
    fumo_hoy = models.CharField(
        max_length=20, choices=FumoHoy.choices, null=True, blank=True
    )
    alcohol_hoy = models.CharField(
        max_length=20, choices=AlcoholHoy.choices, null=True, blank=True
    )
    medicamentos_hoy = models.CharField(
        max_length=20, choices=MedicamentosHoy.choices, null=True, blank=True
    )
    noche_completada_en = models.DateTimeField(null=True, blank=True)

    # Variables ampliadas del catálogo de mediciones (registro diario)
    frutas_verduras_porciones = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    ultraprocesados_veces = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    bebidas_azucaradas_cantidad = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    vasos_agua = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    actividad_moderada_minutos = models.PositiveIntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    actividad_vigorosa_minutos = models.PositiveIntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    fortalecimiento_muscular = models.BooleanField(null=True, blank=True)
    horas_sentado = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("16"))],
    )
    horas_sueno = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("3")), MaxValueValidator(Decimal("12"))],
    )
    estres_nivel = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Check-in diario de 1 (muy bajo) a 5 (muy alto). No es una escala diagnóstica.",
    )
    cigarrillos_hoy = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    uso_vapeador = models.BooleanField(null=True, blank=True)
    uso_narguile = models.BooleanField(null=True, blank=True)
    uso_puro = models.BooleanField(null=True, blank=True)
    uso_otro_producto_tabaco = models.BooleanField(null=True, blank=True)
    exposicion_humo_ajeno = models.BooleanField(null=True, blank=True)

    creado_en = models.DateTimeField(default=timezone.now, editable=False)
    actualizado_en = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["paciente", "fecha"],
                name="un_registro_diario_por_paciente_fecha",
            )
        ]
        ordering = ["-fecha", "-creado_en"]
        verbose_name = "Registro diario"
        verbose_name_plural = "Registros diarios"

    def clean(self):
        super().clean()
        errores = {}

        if self.manana_completada_en:
            campos_manana = [
                "horas_sueno_anoche", "despertares_noche", "idas_bano_noche",
                "sensacion_despertar",
            ]
            for campo in campos_manana:
                if not getattr(self, campo):
                    errores[campo] = "Complete esta respuesta antes de cerrar la encuesta de la mañana."

        if self.noche_completada_en:
            campos_noche = [
                "siesta_tarde", "caminata_hoy", "ejercicio_hoy", "sentado_mas_6h",
                "frutas_verduras_hoy", "fritos_paquete_hoy", "bebida_azucarada_hoy",
                "sal_extra_hoy", "estres_hoy", "sintoma_hoy",
            ]
            for campo in campos_noche:
                if getattr(self, campo) is None or getattr(self, campo) == "":
                    errores[campo] = "Complete esta respuesta antes de cerrar la encuesta de la noche."

            # Estas preguntas aparecen solo si el perfil indica que aplican.
            perfil = getattr(self.paciente, "perfil_cardiovascular", None)
            if perfil:
                if perfil.tabaquismo in {
                    PerfilCardiovascular.TabaquismoPerfil.OCASIONAL,
                    PerfilCardiovascular.TabaquismoPerfil.DIARIO,
                } and not self.fumo_hoy:
                    errores["fumo_hoy"] = "Esta respuesta es obligatoria porque indicó que fuma."
                if perfil.alcohol_semana and perfil.alcohol_semana != PerfilCardiovascular.AlcoholPerfil.NUNCA and not self.alcohol_hoy:
                    errores["alcohol_hoy"] = "Esta respuesta es obligatoria porque indicó consumo de alcohol."
                if perfil.toma_medicamentos and perfil.toma_medicamentos != PerfilCardiovascular.Medicamentos.NO and not self.medicamentos_hoy:
                    errores["medicamentos_hoy"] = "Esta respuesta es obligatoria porque indicó que toma medicamentos."

        if self.horas_sueno is not None:
            # El catálogo describe incrementos de media hora entre 3 y 12 horas.
            decimas = self.horas_sueno * 2
            if decimas != decimas.to_integral_value():
                errores["horas_sueno"] = "Registre el sueño en incrementos de 0,5 horas."

        if self.horas_sentado is not None:
            if self.horas_sentado != self.horas_sentado.to_integral_value():
                errores["horas_sentado"] = "Registre el tiempo sentado en horas enteras."

        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.actividad_moderada_minutos is not None or self.actividad_vigorosa_minutos is not None:
            self.minutos_actividad = (self.actividad_moderada_minutos or 0) + (self.actividad_vigorosa_minutos or 0)
        self.actualizado_en = timezone.now()
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = set(kwargs["update_fields"]) | {"actualizado_en", "minutos_actividad"}
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Registro de {self.paciente} - {self.fecha}"


# -----------------------------------------------------------------------------
# 5. Evaluaciones periódicas: sueño semanal, señales respiratorias y PSS-4
# -----------------------------------------------------------------------------

class EvaluacionPeriodica(models.Model):
    paciente = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="evaluaciones_periodicas",
    )
    fecha_registro = models.DateField(default=timezone.localdate)
    periodo_inicio = models.DateField(null=True, blank=True)
    periodo_fin = models.DateField(null=True, blank=True)

    # Catálogo: número de noches con dificultad para dormir (0 a 7), semanal.
    dificultad_sueno_noches = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(7)],
    )

    # Catálogo: ronquidos fuertes, pausas al respirar o sueño diurno.
    ronquidos_pausas_somnolencia = models.CharField(
        max_length=10,
        choices=SiNoNoSe.choices,
        null=True,
        blank=True,
    )

    # PSS-4: conservar las cuatro respuestas originales (0 a 4).
    # El cálculo del puntaje debe respetar la codificación oficial de los ítems inversos.
    pss4_item_1 = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(4)]
    )
    pss4_item_2 = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(4)]
    )
    pss4_item_3 = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(4)]
    )
    pss4_item_4 = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(4)]
    )

    creado_en = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["-fecha_registro", "-creado_en"]
        verbose_name = "Evaluación periódica"
        verbose_name_plural = "Evaluaciones periódicas"

    def clean(self):
        super().clean()
        if self.periodo_inicio and self.periodo_fin and self.periodo_inicio > self.periodo_fin:
            raise ValidationError({"periodo_fin": "La fecha final no puede ser anterior a la inicial."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Evaluación de {self.paciente} - {self.fecha_registro}"


# -----------------------------------------------------------------------------
# 6. Casos ECG y revisión profesional
# -----------------------------------------------------------------------------

class CasosECG(models.Model):
    NOMBRES_SUPERCLASE = {
        "NORM": "Patrón sin hallazgos destacados",
        "MI": "Patrón asociado a infarto",
        "STTC": "Cambios en el segmento ST/T",
        "CD": "Alteración en la conducción eléctrica",
        "HYP": "Patrón de hipertrofia",
    }

    paciente = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="casos_ecg",
    )
    caso_asignado = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Identificador del caso público PTB-XL asignado por el equipo.",
    )
    archivo_ecg = models.FileField(upload_to="ecgs/")
    confirma_prueba = models.BooleanField(default=False)
    fecha_carga = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(default=timezone.now)

    # Una probabilidad por superclase PTB-XL: pueden coexistir varias clases.
    norm_prob = models.FloatField(
        null=True, blank=True, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    mi_prob = models.FloatField(
        null=True, blank=True, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    sttc_prob = models.FloatField(
        null=True, blank=True, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    cd_prob = models.FloatField(
        null=True, blank=True, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    hyp_prob = models.FloatField(
        null=True, blank=True, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )

    estado_procesamiento = models.CharField(
        max_length=15,
        choices=EstadoProcesamientoECG.choices,
        default=EstadoProcesamientoECG.PENDIENTE,
    )
    mensaje_error = models.TextField(blank=True)

    # Campos de revisión del panel profesional.
    estado_revision = models.CharField(
        max_length=15,
        choices=EstadoRevisionECG.choices,
        default=EstadoRevisionECG.PENDIENTE,
    )
    prioridad_ia = models.CharField(
        max_length=10,
        choices=PrioridadECG.choices,
        null=True,
        blank=True,
    )
    etiqueta_referencia = models.JSONField(
    default=list,
    blank=True
)
    superclases_modificadas = models.JSONField(default=list, blank=True)
    notas_medico = models.CharField(max_length=500, blank=True)
    revisado_por = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="casos_ecg_revisados",
    )
    inicio_revision = models.DateTimeField(null=True, blank=True)
    fecha_revision = models.DateTimeField(null=True, blank=True)
    tiempo_revision_seg = models.PositiveIntegerField(null=True, blank=True)

    aviso_limitaciones = models.TextField(
        default="Resultado experimental con datos de PTB-XL. No es un diagnóstico."
    )

    class Meta:
        ordering = ["-fecha_carga"]
        verbose_name = "Caso ECG"
        verbose_name_plural = "Casos ECG"

    def clean(self):
        super().clean()
        errores = {}
        clases_validas = set(self.NOMBRES_SUPERCLASE.keys())

        for campo in ("etiqueta_referencia", "superclases_modificadas"):
            valores = getattr(self, campo, None)
            if not isinstance(valores, list):
                errores[campo] = "Debe enviarse una lista de superclases."
            elif not all(isinstance(valor, str) for valor in valores):
                errores[campo] = "Cada superclase debe ser un texto."
            elif set(valores) - clases_validas:
                errores[campo] = "Solo se permiten NORM, MI, STTC, CD y HYP."

        if self.estado_procesamiento in {
            EstadoProcesamientoECG.VALIDANDO,
            EstadoProcesamientoECG.PROCESANDO,
            EstadoProcesamientoECG.COMPLETADO,
        } and not self.confirma_prueba:
            errores["confirma_prueba"] = "Debe confirmar que el ECG corresponde a un caso de prueba."
        if self.estado_procesamiento in {
            EstadoProcesamientoECG.VALIDANDO,
            EstadoProcesamientoECG.PROCESANDO,
            EstadoProcesamientoECG.COMPLETADO,
        } and not self.caso_asignado:
            errores["caso_asignado"] = "Debe seleccionar el caso asignado por el equipo."

        if self.estado_revision in {
            EstadoRevisionECG.VALIDADO,
            EstadoRevisionECG.MODIFICADO,
        } and not self.revisado_por_id:
            errores["revisado_por"] = "Debe registrarse el profesional que revisó el caso."

        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        self.full_clean()
        self.actualizado_en = timezone.now()
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = set(kwargs["update_fields"]) | {"actualizado_en"}
        super().save(*args, **kwargs)

    def obtener_resultados_por_superclase(self):
        """Devuelve las cinco salidas con su nombre de orientación.

        No calcula nivel de riesgo: los umbrales de orientación se deben acordar
        con el equipo clínico y de IA antes de implementar esa clasificación.
        """
        probabilidades = {
            "NORM": self.norm_prob,
            "MI": self.mi_prob,
            "STTC": self.sttc_prob,
            "CD": self.cd_prob,
            "HYP": self.hyp_prob,
        }
        return [
            {
                "superclase": codigo,
                "nombre_orientacion": self.NOMBRES_SUPERCLASE[codigo],
                "probabilidad": probabilidades[codigo],
            }
            for codigo in self.NOMBRES_SUPERCLASE
        ]

    def __str__(self):
        return f"ECG {self.caso_asignado or self.pk} - {self.paciente}"


# -----------------------------------------------------------------------------
# 7. Catálogo de recomendaciones (banco administrado por el equipo)
# -----------------------------------------------------------------------------

class RecomendacionCatalogo(models.Model):
    class Categoria(models.TextChoices):
        ALIMENTACION = "ALIMENTACION", "Alimentación"
        HIDRATACION = "HIDRATACION", "Hidratación"
        ACTIVIDAD_FISICA = "ACTIVIDAD_FISICA", "Actividad física"
        SUENO = "SUENO", "Sueño"
        ESTRES = "ESTRES", "Estrés"
        TABAQUISMO = "TABAQUISMO", "Tabaquismo"

    codigo = models.CharField(max_length=10, unique=True)
    categoria = models.CharField(max_length=20, choices=Categoria.choices)
    situacion_identificada = models.TextField()
    texto_recomendacion = models.TextField()
    activa = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["categoria", "codigo"]
        verbose_name = "Recomendación del catálogo"
        verbose_name_plural = "Catálogo de recomendaciones"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} - {self.categoria}"


# -----------------------------------------------------------------------------
# 8. Recomendaciones mostradas al usuario y medición de claridad
# -----------------------------------------------------------------------------

class RecomendacionMostrada(models.Model):
    class Claridad(models.TextChoices):
        SI = "SI", "Sí"
        MAS_O_MENOS = "MAS_O_MENOS", "Más o menos"
        NO = "NO", "No"

    paciente = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="recomendaciones_recibidas",
    )
    recomendacion = models.ForeignKey(
        RecomendacionCatalogo,
        on_delete=models.PROTECT,
        related_name="veces_mostrada",
    )
    registro_diario = models.ForeignKey(
        RegistroDiario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recomendaciones_generadas",
    )
    regla_codigo = models.CharField(
        max_length=10,
        blank=True,
        help_text="Regla que activó la recomendación, por ejemplo R-02.",
    )
    fecha_mostrada = models.DateField(default=timezone.localdate)

    # Copia del contenido mostrado para conservar el histórico aunque el banco cambie.
    categoria_snapshot = models.CharField(max_length=20, blank=True)
    situacion_snapshot = models.TextField(blank=True)
    texto_snapshot = models.TextField(blank=True)

    respuesta_claridad = models.CharField(
        max_length=15,
        choices=Claridad.choices,
        null=True,
        blank=True,
    )
    fecha_respuesta = models.DateTimeField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["paciente", "recomendacion", "fecha_mostrada"],
                name="recomendacion_unica_por_paciente_y_dia",
            )
        ]
        ordering = ["-fecha_mostrada", "-creado_en"]
        verbose_name = "Recomendación mostrada"
        verbose_name_plural = "Recomendaciones mostradas"

    def clean(self):
        super().clean()
        if self.registro_diario_id and self.paciente_id:
            if self.registro_diario.paciente_id != self.paciente_id:
                raise ValidationError({"registro_diario": "El registro debe pertenecer al mismo paciente."})

    def save(self, *args, **kwargs):
        if self.recomendacion_id:
            if not self.categoria_snapshot:
                self.categoria_snapshot = self.recomendacion.categoria
            if not self.situacion_snapshot:
                self.situacion_snapshot = self.recomendacion.situacion_identificada
            if not self.texto_snapshot:
                self.texto_snapshot = self.recomendacion.texto_recomendacion
        if self.respuesta_claridad and not self.fecha_respuesta:
            self.fecha_respuesta = timezone.now()
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.recomendacion.codigo} para {self.paciente}"

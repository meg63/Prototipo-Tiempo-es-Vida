"""Motor R-01 a R-16 para Tiempo es Vida.

Fuente funcional: base de conocimiento, sección "Reglas para mostrar recomendaciones".
El motor no diagnostica ni calcula riesgo clínico. Solo selecciona mensajes preventivos.

Regla de calidad de datos:
- Las reglas agregadas sobre registros diarios de 7 días exigen al menos 3 días
  con la medición concreta disponible.
- Una regla cuya propia condición exige 4 o 5 días necesita esa cantidad de
  observaciones válidas; tener 3 no basta para afirmar que la condición se cumple.
- Reglas basadas en una declaración de perfil, una alerta inmediata o una
  evaluación periódica explícita no necesitan 3 registros diarios.
"""

from datetime import timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from api.models import (
    EvaluacionPeriodica,
    PerfilCardiovascular,
    RecomendacionCatalogo,
    RecomendacionMostrada,
    RegistroDiario,
)


# Parámetros identificados como configurables en el documento funcional.
VENTANA_DIAS = 7
MIN_REGISTROS_VENTANA = 3
DIAS_SEDENTARISMO = 4
HORAS_SEDENTARISMO = Decimal("8")
DIAS_ULTRAPROCESADOS = 4
ULTRAPROCESADOS_POR_DIA = 2
DIAS_BEBIDAS_AZUCARADAS = 4
BEBIDAS_AZUCARADAS_POR_DIA = 1
DIAS_ESTRES_ALTO = 3
DIAS_ESTRES_ALTO_PERSISTENTE = 5
UMBRAL_VASOS_AGUA = Decimal("4")  # Ejemplo parametrizable indicado en R-12.
DIAS_HIDRATACION = 3
DIAS_SUENO_DIFICIL_PERSISTENTE = 12  # 12 semanas consecutivas para SU-04.
DIAS_REPETICION_SU05 = 90  # Como máximo una vez por trimestre.

# El documento dice que el umbral alto del PSS-4 debe definirse con un clínico.
# Se deja desactivado deliberadamente: no se inventa un punto de corte.
PSS4_UMBRAL_ALTO = None

PRIORIDADES = {
    "R-01": 1, "R-02": 3, "R-03": 3, "R-04": 4,
    "R-05": 3, "R-06": 2, "R-07": 2, "R-08": 2,
    "R-09": 3, "R-10": 3, "R-11": 3, "R-12": 3,
    "R-13": 0, "R-14": 2, "R-15": 2, "R-16": 1,
}

# Representaciones aproximadas de intervalos utilizados por la interfaz actual.
# Se prefieren siempre las mediciones numéricas exactas si están disponibles.
FRUTAS_INTERVALO = {
    "0": Decimal("0"),
    "1_2": Decimal("1.5"),
    "3_4": Decimal("3.5"),
    "5_MAS": Decimal("5"),  # Límite inferior del intervalo "5 o más".
}
AGUA_INTERVALO = {
    "0_2": Decimal("1"),
    "3_5": Decimal("4"),
    "6_8": Decimal("7"),
    "MAS_8": Decimal("9"),  # Valor conservador representativo de "más de 8".
}
SUENO_INTERVALO = {
    "MENOS_5": Decimal("4.5"),
    "5_6": Decimal("5.5"),
    "6_7": Decimal("6.5"),
    "7_9": Decimal("8"),
    # MAS_9 no se promedia con intervalos porque su límite superior es abierto.
}


class _Evaluacion:
    def __init__(self):
        self.recomendaciones = {}  # codigo -> {codigo, regla_codigo, prioridad}
        self.alertas = []
        self.mensajes = []
        self.reglas_omitidas = []
        self.reglas_aplicadas = []

    def omitir(self, regla, motivo):
        self.reglas_omitidas.append({"regla": regla, "motivo": motivo})

    def aplicada(self, regla, detalle=None):
        item = {"regla": regla, "prioridad": PRIORIDADES.get(regla)}
        if detalle:
            item["detalle"] = detalle
        self.reglas_aplicadas.append(item)

    def agregar(self, codigo, regla):
        prioridad = PRIORIDADES.get(regla, 99)
        actual = self.recomendaciones.get(codigo)
        if actual is None or prioridad < actual["prioridad"]:
            self.recomendaciones[codigo] = {
                "codigo": codigo,
                "regla_codigo": regla,
                "prioridad": prioridad,
            }


# -----------------------------------------------------------------------------
# Funciones auxiliares para normalizar las mediciones existentes
# -----------------------------------------------------------------------------


def _registros_ventana(paciente, hoy):
    desde = hoy - timedelta(days=VENTANA_DIAS - 1)
    return list(
        RegistroDiario.objects.filter(
            paciente=paciente,
            fecha__gte=desde,
            fecha__lte=hoy,
        ).order_by("fecha")
    )


def _valor_frutas(registro):
    if registro.frutas_verduras_porciones is not None:
        return Decimal(registro.frutas_verduras_porciones)
    return FRUTAS_INTERVALO.get(registro.frutas_verduras_hoy)


def _valor_agua(registro):
    if registro.vasos_agua is not None:
        return Decimal(registro.vasos_agua)
    return AGUA_INTERVALO.get(registro.vasos_agua_respuesta)


def _valor_ultraprocesados(registro):
    if registro.ultraprocesados_veces is not None:
        return int(registro.ultraprocesados_veces)
    return {"NO": 0, "UNA": 1, "VARIAS": 2}.get(registro.fritos_paquete_hoy)


def _valor_bebidas_azucaradas(registro):
    if registro.bebidas_azucaradas_cantidad is not None:
        return int(registro.bebidas_azucaradas_cantidad)
    return {"NO": 0, "UN_VASO": 1, "DOS_MAS": 2}.get(registro.bebida_azucarada_hoy)


def _valor_sueno(registro):
    if registro.horas_sueno is not None:
        return Decimal(registro.horas_sueno), "numerico"
    categoria = registro.horas_sueno_anoche
    if categoria == "MAS_9":
        return None, "mayor_9"
    valor = SUENO_INTERVALO.get(categoria)
    return (valor, "intervalo") if valor is not None else (None, "sin_dato")


def _valor_actividad(registro):
    moderada = registro.actividad_moderada_minutos
    vigorosa = registro.actividad_vigorosa_minutos
    if moderada is not None or vigorosa is not None:
        return int(moderada or 0) + int(vigorosa or 0)
    # Compatibilidad con registros anteriores que sí guardaron minutos_actividad.
    if registro.minutos_actividad and registro.minutos_actividad > 0:
        return int(registro.minutos_actividad)
    return None  # No interpretar el default 0 como una respuesta explícita de cero.


def _valor_estres_alto(registro):
    if registro.estres_nivel is not None:
        return registro.estres_nivel >= 4
    # La interfaz actual ofrece Bajo/Medio/Alto, no la escala 1-5 completa.
    # "ALTO" se toma como señal de estrés alto, sin convertirlo en una puntuación.
    if registro.estres_hoy is not None:
        return registro.estres_hoy == "ALTO"
    return None


def _hora_acostarse_variabilidad_mayor_una_hora(registros):
    horas = [r.hora_acostarse_real for r in registros if getattr(r, "hora_acostarse_real", None)]
    if len(horas) < MIN_REGISTROS_VENTANA:
        return None
    minutos = sorted((h.hour * 60 + h.minute) for h in horas)
    # Arco circular mínimo: evita contar mal horarios alrededor de medianoche.
    gaps = [minutos[i + 1] - minutos[i] for i in range(len(minutos) - 1)]
    gaps.append((minutos[0] + 1440) - minutos[-1])
    dispersion = 1440 - max(gaps)
    return dispersion > 60


def _sueno_dificil_12_semanas(paciente, hoy):
    """True solo si hay reporte >=3 noches en cada una de las últimas 12 semanas completas."""
    inicio_semana_actual = hoy - timedelta(days=hoy.weekday())
    semanas_requeridas = {
        inicio_semana_actual - timedelta(weeks=offset)
        for offset in range(1, DIAS_SUENO_DIFICIL_PERSISTENTE + 1)
    }
    evaluaciones = EvaluacionPeriodica.objects.filter(
        paciente=paciente,
        dificultad_sueno_noches__gte=3,
    ).filter(fecha_registro__gte=hoy - timedelta(weeks=13))

    semanas_con_dificultad = set()
    for evaluacion in evaluaciones:
        fecha = evaluacion.periodo_fin or evaluacion.fecha_registro
        lunes = fecha - timedelta(days=fecha.weekday())
        if lunes in semanas_requeridas:
            semanas_con_dificultad.add(lunes)
    return semanas_requeridas.issubset(semanas_con_dificultad)


def _detectar_solicitud_ayuda(texto):
    if not texto:
        return False
    t = " ".join(str(texto).lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").split())
    frases = (
        "hacerme dano", "autolesion", "autolesionarme", "quitarme la vida",
        "suicid", "quiero morir", "no quiero seguir viviendo",
        "no puedo mas y quiero desaparecer", "hacerme algo",
    )
    return any(frase in t for frase in frases)


def _es_r16(paciente, perfil):
    if paciente.edad is not None and paciente.edad > 60:
        return True
    if perfil is None:
        return False
    condiciones = set(perfil.condiciones_diagnosticadas or [])
    return bool(
        "enfermedad_cardiaca_infarto_previo" in condiciones
        or getattr(perfil, "insuficiencia_cardiaca", None) is True
        or getattr(perfil, "enfermedad_renal", None) is True
        or getattr(perfil, "embarazo", None) is True
    )


def _agregar_recomendacion_si_disponible(resultado, codigo, regla):
    if RecomendacionCatalogo.objects.filter(codigo=codigo, activa=True).exists():
        resultado.agregar(codigo, regla)
    else:
        resultado.omitir(regla, f"El código {codigo} no está cargado o está inactivo en el catálogo.")


# -----------------------------------------------------------------------------
# Motor principal
# -----------------------------------------------------------------------------


def evaluar_habitos_y_sintomas(
    paciente,
    *,
    necesito_ayuda_ahora=False,
    texto_libre=None,
    persistir=True,
    fecha=None,
):
    """Evalúa R-01 a R-16 y registra idempotentemente las recomendaciones aplicables.

    R-01, R-13 y R-16 producen alertas del sistema, no registros del banco de 30,
    porque el documento no les asigna un código de recomendación del catálogo.
    """
    hoy = fecha or timezone.localdate()
    resultado = _Evaluacion()
    perfil = PerfilCardiovascular.objects.filter(paciente=paciente).first()
    registros = _registros_ventana(paciente, hoy)
    ultimo_registro = registros[-1] if registros else None

    # R-13: evento inmediato. Tiene prioridad 0 y suspende mensajes motivacionales.
    crisis = bool(necesito_ayuda_ahora) or _detectar_solicitud_ayuda(texto_libre)
    if crisis:
        resultado.alertas.append({
            "regla": "R-13",
            "prioridad": 0,
            "tipo": "ayuda_salud_mental",
            "mensaje": "Puede comunicarse con la línea nacional de teleorientación en salud mental 192, opción 4 (Colombia).",
            "suspender_mensajes_motivacionales": True,
        })
        resultado.aplicada("R-13", "Solicitud explícita de ayuda o indicio en texto libre.")
        return _serializar_resultado(
            paciente, hoy, resultado, persistir=False, ultimo_registro=ultimo_registro
        )

    # R-01: PAR-Q+ debe completarse completo y sin modificaciones fuera de la app.
    # Guardamos solo el estado de finalización/revisión; no reproducimos el cuestionario.
    parq_completado = getattr(perfil, "parq_completado", None) is True if perfil else False
    parq_requiere_revision = getattr(perfil, "parq_requiere_revision", None) is True if perfil else False
    ejercicio_supervisado = getattr(perfil, "ejercicio_supervisado_indicado", None) is True if perfil else False
    parq_aprobado_para_orientacion = (
        parq_completado
        and getattr(perfil, "parq_requiere_revision", None) is False
        and getattr(perfil, "ejercicio_supervisado_indicado", None) is False
    )
    bloquear_actividad = not parq_aprobado_para_orientacion
    if bloquear_actividad:
        resultado.alertas.append({
            "regla": "R-01",
            "prioridad": 1,
            "tipo": "precaucion_actividad_fisica",
            "mensaje": "Consulte a su médico o a un profesional del ejercicio antes de aumentar su actividad.",
            "motivo": (
                "Cribado de preparación física no completado."
                if not parq_completado else
                "El cribado requiere valoración o se indicó ejercicio supervisado."
            ),
        })
        resultado.aplicada("R-01", "Se bloquean recomendaciones de actividad física hasta completar/validar el cribado.")

    # R-16: condiciones en las que se limita el contenido cuantitativo.
    regla_16 = _es_r16(paciente, perfil)
    if regla_16:
        resultado.alertas.append({
            "regla": "R-16",
            "prioridad": 1,
            "tipo": "precaucion_clinica",
            "mensaje": "Siga las indicaciones de su equipo médico. Se mostrará únicamente contenido general mientras se validan clínicamente las metas.",
        })
        resultado.aplicada("R-16", "Se omiten metas numéricas de sueño, líquidos y ejercicio.")

    # Mediciones agregadas por día. Cada conjunto cuenta días con el dato, no filas vacías.
    actividades = [(r, _valor_actividad(r)) for r in registros]
    actividades_validas = [(r, v) for r, v in actividades if v is not None]
    total_actividad = sum(v for _, v in actividades_validas)

    # R-02, R-03 y R-04: minutos acumulados de actividad en siete días.
    if len(actividades_validas) < MIN_REGISTROS_VENTANA:
        resultado.omitir("R-02/R-03/R-04", f"Hay {len(actividades_validas)} días con minutos cuantificados; se requieren al menos {MIN_REGISTROS_VENTANA}.")
    else:
        if not bloquear_actividad and not regla_16:
            if total_actividad < 60:
                _agregar_recomendacion_si_disponible(resultado, "AF-01", "R-02")
                resultado.aplicada("R-02", f"Total semanal: {total_actividad} minutos (<60).")
            elif total_actividad < 150:
                _agregar_recomendacion_si_disponible(resultado, "AF-02", "R-03")
                resultado.aplicada("R-03", f"Total semanal: {total_actividad} minutos (60 a 149).")
            else:
                _agregar_recomendacion_si_disponible(resultado, "AF-05", "R-04")
                resultado.aplicada("R-04", f"Total semanal: {total_actividad} minutos (150 o más).")
                fuerza = [r.fortalecimiento_muscular for r in registros if r.fortalecimiento_muscular is not None]
                if len(fuerza) >= MIN_REGISTROS_VENTANA and not any(fuerza):
                    _agregar_recomendacion_si_disponible(resultado, "AF-03", "R-04")
                elif len(fuerza) < MIN_REGISTROS_VENTANA:
                    resultado.omitir("R-04/AF-03", "No hay al menos 3 registros de fortalecimiento muscular para comprobar su ausencia.")
        else:
            resultado.omitir("R-02/R-03/R-04", "R-01 o R-16 bloquea recomendaciones de actividad física.")

    # R-05: 8 horas o más sentado en al menos 4 de 7 días.
    sentado = [r.horas_sentado for r in registros if r.horas_sentado is not None]
    if len(sentado) < MIN_REGISTROS_VENTANA:
        resultado.omitir("R-05", f"Hay {len(sentado)} días con horas sentado cuantificadas; se requieren al menos {MIN_REGISTROS_VENTANA}.")
    elif len(sentado) < DIAS_SEDENTARISMO:
        resultado.omitir("R-05", f"Solo hay {len(sentado)} observaciones; se necesitan {DIAS_SEDENTARISMO} para evaluar la condición de 4 de 7 días.")
    elif sum(1 for x in sentado if x >= HORAS_SEDENTARISMO) >= DIAS_SEDENTARISMO:
        if not bloquear_actividad and not regla_16:
            _agregar_recomendacion_si_disponible(resultado, "AF-04", "R-05")
            resultado.aplicada("R-05", "8 horas o más sentado en al menos 4 días observados.")
        else:
            resultado.omitir("R-05", "R-01 o R-16 bloquea recomendaciones de actividad física.")

    # Sueño: se usan datos numéricos cuando existen; categorías son aproximaciones de los rangos visuales.
    sueno = [_valor_sueno(r) for r in registros]
    sueno_numerico = [v for v, tipo in sueno if tipo == "numerico"]
    sueno_intervalo = [v for v, tipo in sueno if tipo == "intervalo"]
    categorias_mas_9 = sum(1 for r in registros if r.horas_sueno_anoche == "MAS_9")
    mediciones_sueno_interpretables = sueno_numerico + sueno_intervalo
    hay_intervalos_abiertos = any(tipo == "mayor_9" for _, tipo in sueno)
    if len(mediciones_sueno_interpretables) >= MIN_REGISTROS_VENTANA and not hay_intervalos_abiertos:
        promedio_sueno = sum(mediciones_sueno_interpretables) / Decimal(len(mediciones_sueno_interpretables))
        fuente_sueno = (
            "numerico" if len(sueno_intervalo) == 0 else
            "mixto_con_intervalos_aproximados" if len(sueno_numerico) else
            "aproximado_por_intervalos"
        )
    else:
        promedio_sueno = None
        fuente_sueno = None

    # R-06: promedio menor a 7 horas, solo para personas de 18 a 60 años.
    if 18 <= (paciente.edad or 0) <= 60:
        if promedio_sueno is None:
            resultado.omitir("R-06", "Se requieren al menos 3 mediciones de sueño interpretables; no se promedia el intervalo abierto 'más de 9'.")
        elif promedio_sueno < Decimal("7"):
            if not regla_16:
                _agregar_recomendacion_si_disponible(resultado, "SU-01", "R-06")
                resultado.aplicada("R-06", f"Promedio {promedio_sueno} h; fuente: {fuente_sueno}.")
                variabilidad = _hora_acostarse_variabilidad_mayor_una_hora(registros)
                if variabilidad is True:
                    _agregar_recomendacion_si_disponible(resultado, "SU-02", "R-06")
                elif variabilidad is None:
                    resultado.omitir("R-06/SU-02", "No hay 3 horarios reales de acostarse para medir una variación mayor a una hora.")
            else:
                resultado.omitir("R-06", "R-16 bloquea metas numéricas de sueño.")
    else:
        resultado.omitir("R-06", "La regla aplica a usuarios de 18 a 60 años.")

    # R-07: dificultad para dormir en 3 o más noches de la semana; SU-04 tras 12 semanas consecutivas.
    evaluaciones_7d = list(
        EvaluacionPeriodica.objects.filter(
            paciente=paciente,
            fecha_registro__gte=hoy - timedelta(days=VENTANA_DIAS - 1),
            fecha_registro__lte=hoy,
            dificultad_sueno_noches__isnull=False,
        ).order_by("-fecha_registro")
    )
    evaluacion_sueno = evaluaciones_7d[0] if evaluaciones_7d else None
    if len(registros) < MIN_REGISTROS_VENTANA:
        resultado.omitir("R-07", f"Hay {len(registros)} registros diarios en la ventana; se requieren al menos {MIN_REGISTROS_VENTANA} además de la evaluación semanal.")
    elif evaluacion_sueno and evaluacion_sueno.dificultad_sueno_noches >= 3:
        _agregar_recomendacion_si_disponible(resultado, "SU-03", "R-07")
        resultado.aplicada("R-07", f"Dificultad reportada en {evaluacion_sueno.dificultad_sueno_noches} noches.")
        if _sueno_dificil_12_semanas(paciente, hoy):
            _agregar_recomendacion_si_disponible(resultado, "SU-04", "R-07")
    elif not evaluaciones_7d:
        resultado.omitir("R-07", "No hay evaluación semanal de dificultad de sueño en la ventana actual.")

    # R-08: ronquidos/pausas/somnolencia; como máximo una vez por trimestre.
    evaluacion_respiratoria = EvaluacionPeriodica.objects.filter(
        paciente=paciente,
        ronquidos_pausas_somnolencia="SI",
        fecha_registro__gte=hoy - timedelta(days=DIAS_REPETICION_SU05),
        fecha_registro__lte=hoy,
    ).order_by("-fecha_registro").first()
    ya_mostrada_su05 = RecomendacionMostrada.objects.filter(
        paciente=paciente,
        recomendacion__codigo="SU-05",
        fecha_mostrada__gte=hoy - timedelta(days=DIAS_REPETICION_SU05 - 1),
    ).exists()
    if evaluacion_respiratoria and not ya_mostrada_su05:
        _agregar_recomendacion_si_disponible(resultado, "SU-05", "R-08")
        resultado.aplicada("R-08", "Respuesta afirmativa a señales respiratorias; se respeta el límite trimestral.")

    # R-09: promedio mayor a 9 horas. En categorías solo es concluyente si todas son >9.
    promedio_mayor_9 = False
    if len(sueno_numerico) >= MIN_REGISTROS_VENTANA:
        promedio_mayor_9 = (sum(sueno_numerico) / Decimal(len(sueno_numerico))) > Decimal("9")
    else:
        registros_con_sueno_categoria = [r for r in registros if r.horas_sueno_anoche]
        sin_mediciones_numericas = not any(r.horas_sueno is not None for r in registros_con_sueno_categoria)
        if (
            sin_mediciones_numericas
            and len(registros_con_sueno_categoria) >= MIN_REGISTROS_VENTANA
            and all(r.horas_sueno_anoche == "MAS_9" for r in registros_con_sueno_categoria)
        ):
            promedio_mayor_9 = True
    if promedio_mayor_9:
        resultado.mensajes.append({
            "regla": "R-09",
            "tipo": "orientacion_neutral",
            "mensaje": "Dormir más de 9 horas puede ser normal en algunas personas; si le preocupa, consulte a su médico.",
        })
        resultado.aplicada("R-09", "Promedio superior a 9 horas.")

    # R-10: frutas y verduras, promedio menor a 3 en 7 días.
    frutas = [v for v in (_valor_frutas(r) for r in registros) if v is not None]
    promedio_frutas = (sum(frutas) / Decimal(len(frutas))) if len(frutas) >= MIN_REGISTROS_VENTANA else None
    if promedio_frutas is None:
        resultado.omitir("R-10", f"Hay {len(frutas)} días con dato de frutas/verduras; se requieren al menos {MIN_REGISTROS_VENTANA}.")
    elif promedio_frutas < Decimal("3"):
        _agregar_recomendacion_si_disponible(resultado, "AL-01", "R-10")
        if getattr(perfil, "poco_acceso_fruta", None) is True:
            _agregar_recomendacion_si_disponible(resultado, "AL-02", "R-10")
        resultado.aplicada("R-10", f"Promedio estimado/registrado: {promedio_frutas} porciones.")
    elif promedio_frutas >= Decimal("5"):
        # El documento pide refuerzo positivo, pero no proporciona un texto del banco.
        # Se devuelve como evento informativo, separado de las 30 recomendaciones oficiales.
        resultado.mensajes.append({
            "regla": "R-10",
            "tipo": "refuerzo_positivo_pendiente_validacion",
            "mensaje": "Sus registros muestran un promedio de 5 o más porciones de frutas y verduras al día.",
        })

    # R-11: ultraprocesados >=2 en 4/7 días; si bebidas azucaradas >=1 en 4/7, añadir AL-04.
    ultra = [_valor_ultraprocesados(r) for r in registros]
    ultra_validos = [v for v in ultra if v is not None]
    if len(ultra_validos) < MIN_REGISTROS_VENTANA:
        resultado.omitir("R-11", f"Hay {len(ultra_validos)} días con dato de ultraprocesados; se requieren al menos {MIN_REGISTROS_VENTANA}.")
    elif len(ultra_validos) < DIAS_ULTRAPROCESADOS:
        resultado.omitir("R-11", f"Se necesitan {DIAS_ULTRAPROCESADOS} observaciones para verificar la condición de 4 de 7 días.")
    elif sum(1 for v in ultra_validos if v >= ULTRAPROCESADOS_POR_DIA) >= DIAS_ULTRAPROCESADOS:
        _agregar_recomendacion_si_disponible(resultado, "AL-03", "R-11")
        resultado.aplicada("R-11", "Dos o más ultraprocesados en al menos 4 días observados.")
        bebidas = [_valor_bebidas_azucaradas(r) for r in registros]
        bebidas_validas = [v for v in bebidas if v is not None]
        if len(bebidas_validas) >= DIAS_BEBIDAS_AZUCARADAS and sum(1 for v in bebidas_validas if v >= BEBIDAS_AZUCARADAS_POR_DIA) >= DIAS_BEBIDAS_AZUCARADAS:
            _agregar_recomendacion_si_disponible(resultado, "AL-04", "R-11")

    # R-12: hidratación promedio en 3 días y restricción médica de líquidos.
    restriccion_liquidos = getattr(perfil, "restriccion_liquidos_medica", None) if perfil else None
    if restriccion_liquidos is True:
        _agregar_recomendacion_si_disponible(resultado, "HI-05", "R-12")
        resultado.aplicada("R-12", "La persona declaró restricción médica de líquidos; se ocultan metas de agua.")
    elif restriccion_liquidos is None:
        resultado.omitir("R-12", "No se ha declarado si existe restricción médica de líquidos; por precaución no se muestran metas de agua.")
    else:
        agua = [(r, _valor_agua(r)) for r in registros]
        agua_valida = [(r, v) for r, v in agua if v is not None]
        ultimos_tres = agua_valida[-DIAS_HIDRATACION:]
        if len(ultimos_tres) < MIN_REGISTROS_VENTANA:
            resultado.omitir("R-12", f"Hay {len(ultimos_tres)} días con dato de agua; se requieren 3.")
        else:
            promedio_agua = sum(v for _, v in ultimos_tres) / Decimal(len(ultimos_tres))
            if promedio_agua < UMBRAL_VASOS_AGUA:
                if not regla_16:
                    codigo_agua = "HI-04" if getattr(perfil, "interes_hidratacion", None) is True else "HI-01"
                    _agregar_recomendacion_si_disponible(resultado, codigo_agua, "R-12")
                    # HI-03 se activa solo cuando también se cumple la situación descrita en su ficha.
                    if promedio_frutas is not None and promedio_frutas < Decimal("3"):
                        _agregar_recomendacion_si_disponible(resultado, "HI-03", "R-12")
                    ejercicio_en_3_dias = any(
                        (r.ejercicio_hoy not in (None, "NO"))
                        or ((r.actividad_moderada_minutos or 0) > 0)
                        or ((r.actividad_vigorosa_minutos or 0) > 0)
                        for r, _ in ultimos_tres
                    )
                    if ejercicio_en_3_dias:
                        _agregar_recomendacion_si_disponible(resultado, "HI-02", "R-12")
                    resultado.aplicada("R-12", f"Promedio de agua en los últimos 3 registros: {promedio_agua} vasos; umbral parametrizado: {UMBRAL_VASOS_AGUA}.")
                else:
                    resultado.omitir("R-12", "R-16 bloquea metas numéricas de líquidos.")

    # R-13 ya se resolvió al inicio por prioridad 0.

    # R-14: estrés diario alto en 3/7 o 5/7 días. El PSS-4 queda sin umbral clínico.
    estres = [_valor_estres_alto(r) for r in registros]
    estres_validos = [v for v in estres if v is not None]
    if len(estres_validos) < MIN_REGISTROS_VENTANA:
        resultado.omitir("R-14", f"Hay {len(estres_validos)} días con dato de estrés; se requieren al menos {MIN_REGISTROS_VENTANA}.")
    else:
        dias_altos = sum(1 for v in estres_validos if v)
        if dias_altos >= DIAS_ESTRES_ALTO:
            _agregar_recomendacion_si_disponible(resultado, "ES-01", "R-14")
            resultado.aplicada("R-14", f"Estrés alto reportado en {dias_altos} de {len(estres_validos)} días observados.")
            if len(actividades_validas) >= MIN_REGISTROS_VENTANA and total_actividad < 60 and not bloquear_actividad and not regla_16:
                _agregar_recomendacion_si_disponible(resultado, "ES-03", "R-14")
        if dias_altos >= DIAS_ESTRES_ALTO_PERSISTENTE:
            _agregar_recomendacion_si_disponible(resultado, "ES-02", "R-14")
            _agregar_recomendacion_si_disponible(resultado, "ES-04", "R-14")

    # R-15: tabaquismo declarado, consumo registrado, otros productos y exposición/recaída.
    if perfil:
        fuma_actualmente = perfil.tabaquismo in {
            PerfilCardiovascular.TabaquismoPerfil.OCASIONAL,
            PerfilCardiovascular.TabaquismoPerfil.DIARIO,
        }
        registros_tabaco = [r for r in registros if r.cigarrillos_hoy is not None or r.fumo_hoy is not None]
        consumo_cigarrillos = [Decimal(r.cigarrillos_hoy) for r in registros if r.cigarrillos_hoy is not None]
        if fuma_actualmente or (perfil.tabaquismo == PerfilCardiovascular.TabaquismoPerfil.LO_DEJE and any((r.cigarrillos_hoy or 0) > 0 or r.fumo_hoy not in (None, "NO") for r in registros)):
            _agregar_recomendacion_si_disponible(resultado, "TA-01", "R-15")
            resultado.aplicada("R-15", "Consumo actual declarado o recaída registrada.")

        if len(consumo_cigarrillos) >= MIN_REGISTROS_VENTANA and Decimal("0") < (sum(consumo_cigarrillos) / Decimal(len(consumo_cigarrillos))) <= Decimal("5"):
            _agregar_recomendacion_si_disponible(resultado, "TA-02", "R-15")

        if getattr(perfil, "quiere_dejar_fumar", None) is True:
            _agregar_recomendacion_si_disponible(resultado, "TA-03", "R-15")

        campos_productos = ("uso_vapeador", "uso_narguile", "uso_puro", "uso_otro_producto_tabaco")
        # Una respuesta afirmativa directa sobre uso de otro producto basta; no es una media semanal.
        if any(
            getattr(r, f) is True for r in registros for f in campos_productos
        ):
            _agregar_recomendacion_si_disponible(resultado, "TA-04", "R-15")

        # La exposición declarada también es una condición puntual; no se promedia.
        exposicion = any(r.exposicion_humo_ajeno is True for r in registros)
        recaida = perfil.tabaquismo == PerfilCardiovascular.TabaquismoPerfil.LO_DEJE and any(
            (r.cigarrillos_hoy or 0) > 0 or r.fumo_hoy not in (None, "NO") for r in registros
        )
        if exposicion or recaida:
            _agregar_recomendacion_si_disponible(resultado, "TA-05", "R-15")
    else:
        resultado.omitir("R-15", "No existe perfil cardiovascular para evaluar tabaquismo.")

    # R-16 ya se evaluó al comienzo; aplica a todo el contenido cuantitativo.

    return _serializar_resultado(
        paciente, hoy, resultado, persistir=persistir, ultimo_registro=ultimo_registro
    )


def _serializar_resultado(paciente, hoy, resultado, *, persistir, ultimo_registro):
    seleccionadas = sorted(
        resultado.recomendaciones.values(),
        key=lambda item: (item["prioridad"], item["codigo"]),
    )
    mostradas = []
    creadas = 0

    if persistir:
        for item in seleccionadas:
            recomendacion = RecomendacionCatalogo.objects.filter(
                codigo=item["codigo"], activa=True
            ).first()
            if not recomendacion:
                continue
            try:
                with transaction.atomic():
                    mostrada, created = RecomendacionMostrada.objects.get_or_create(
                        paciente=paciente,
                        recomendacion=recomendacion,
                        fecha_mostrada=hoy,
                        defaults={
                            "registro_diario": ultimo_registro,
                            "regla_codigo": item["regla_codigo"],
                        },
                    )
            except IntegrityError:
                # Protección ante dos solicitudes simultáneas del mismo usuario/día.
                mostrada = RecomendacionMostrada.objects.get(
                    paciente=paciente,
                    recomendacion=recomendacion,
                    fecha_mostrada=hoy,
                )
                created = False
            creadas += int(created)
            mostradas.append({
                "id": mostrada.pk,
                "codigo": recomendacion.codigo,
                "categoria": mostrada.categoria_snapshot,
                "situacion_identificada": mostrada.situacion_snapshot,
                "texto_recomendacion": mostrada.texto_snapshot,
                "regla_codigo": mostrada.regla_codigo,
                "fecha_mostrada": mostrada.fecha_mostrada.isoformat(),
                "respuesta_claridad": mostrada.respuesta_claridad,
                "nueva": created,
                "prioridad": item["prioridad"],
            })

    return {
        "fecha_evaluacion": hoy.isoformat(),
        "ventana": {
            "dias": VENTANA_DIAS,
            "desde": (hoy - timedelta(days=VENTANA_DIAS - 1)).isoformat(),
            "hasta": hoy.isoformat(),
            "minimo_registros_diarios": MIN_REGISTROS_VENTANA,
        },
        "recomendaciones_generadas": mostradas if persistir else seleccionadas,
        "cantidad_nuevas": creadas,
        "alertas": resultado.alertas,
        "mensajes": resultado.mensajes,
        "reglas_aplicadas": sorted(resultado.reglas_aplicadas, key=lambda x: (x.get("prioridad", 99), x["regla"])),
        "reglas_omitidas": resultado.reglas_omitidas,
        "persistidas": persistir,
    }

from datetime import timedelta
from django.utils import timezone
from api.models import RegistroDiario, PerfilCardiovascular

def evaluar_habitos_y_sintomas(paciente):
    recomendaciones = []
    urgencia = False
    
    # R-13: Regla de Emergencia Inmediata
    perfil = PerfilCardiovascular.objects.filter(paciente=paciente).first()
    if perfil and "Dolor, presión u opresión en el pecho" in perfil.sintomas_ahora:
        return {"urgencia": True, "alerta": "Llamar al 123", "recomendaciones": []}

    hace_7_dias = timezone.now().date() - timedelta(days=7)
    registros = RegistroDiario.objects.filter(paciente=paciente, fecha__gte=hace_7_dias)

    actividad_total = sum([r.minutos_actividad for r in registros if r.minutos_actividad])
    
    # R-02 y R-03: Actividad Física
    if actividad_total < 60:
        recomendaciones.append({"categoria": "Actividad física", "texto": "Empiece con caminatas de 10 minutos. Cualquier cantidad es mejor que ninguna."})
    elif 60 <= actividad_total < 150:
        recomendaciones.append({"categoria": "Actividad física", "texto": "Va por buen camino: sume 10 a 15 minutos por semana hasta acercarse a 150 minutos."})

    # R-06: Sueño
    if perfil and perfil.horas_sueno_promedio in ['Menos de 6', 'Entre 6 y 7']:
        recomendaciones.append({"categoria": "Sueño", "texto": "Intente acostarse 15 a 30 minutos antes esta semana. La referencia para adultos es dormir 7 horas o más."})

    return {"urgencia": urgencia, "recomendaciones": recomendaciones}
from django.urls import path

from . import views

urlpatterns = [
    # Estado del servicio
    path("health/", views.HealthAPIView.as_view(), name="api-health"),

    # Autenticación
    path("auth/register/", views.RegistroUsuarioAPIView.as_view(), name="api-register"),
    path("auth/login/", views.InicioSesionAPIView.as_view(), name="api-login"),
    path("auth/logout/", views.CerrarSesionAPIView.as_view(), name="api-logout"),
    path("auth/me/", views.UsuarioActualAPIView.as_view(), name="api-me"),

    # Datos del participante
    path("consentimiento/", views.ConsentimientoAPIView.as_view(), name="api-consentimiento"),
    path("perfil/", views.PerfilCardiovascularAPIView.as_view(), name="api-perfil"),

    # Hábitos
    path("habitos/manana/", views.EncuestaMananaAPIView.as_view(), name="api-habitos-manana"),
    path("habitos/noche/", views.EncuestaNocheAPIView.as_view(), name="api-habitos-noche"),
    path("habitos/", views.HistorialHabitosAPIView.as_view(), name="api-habitos-lista"),
    path("habitos/<int:pk>/", views.RegistroDiarioDetalleAPIView.as_view(), name="api-habitos-detalle"),
    path("evaluaciones/", views.EvaluacionesPeriodicasAPIView.as_view(), name="api-evaluaciones"),

    # ECG del paciente: guarda el .zip WFDB y ejecuta el modelo de IA (services/ecg_ia).
    path("ecg/", views.CasosECGPacienteAPIView.as_view(), name="api-ecg-lista-crear"),
    path("ecg/<int:pk>/", views.CasoECGDetallePacienteAPIView.as_view(), name="api-ecg-detalle"),
    path("ecg/<int:pk>/senal/", views.CasoECGSenalPacienteAPIView.as_view(), name="api-ecg-senal"),

    # Recomendaciones
    path("catalogo-recomendaciones/", views.CatalogoRecomendacionesAPIView.as_view(), name="api-catalogo-recomendaciones"),
    path("recomendaciones/", views.RecomendacionesMostradasAPIView.as_view(), name="api-recomendaciones"),
    path("recomendaciones/mostrar/", views.RecomendacionesMostradasAPIView.as_view(), name="api-recomendacion-mostrar"),
    path("recomendaciones/generar/",views.GenerarRecomendacionesAPIView.as_view(),name="api-recomendaciones-generar",),
    path("recomendaciones/<int:pk>/claridad/", views.ClaridadRecomendacionAPIView.as_view(), name="api-recomendacion-claridad"),
   



    # Panel profesional
    path("profesional/casos/", views.CasosProfesionalListaAPIView.as_view(), name="api-profesional-casos"),
    path("profesional/casos/<int:pk>/", views.CasoProfesionalDetalleAPIView.as_view(), name="api-profesional-caso-detalle"),
    path("profesional/casos/<int:pk>/revision/", views.RevisionProfesionalAPIView.as_view(), name="api-profesional-caso-revision"),
]

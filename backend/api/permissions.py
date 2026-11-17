from rest_framework.permissions import BasePermission

from .models import Consentimiento, RolUsuario


class EsPaciente(BasePermission):
    """Permite operar únicamente a una cuenta cuyo rol de aplicación sea PACIENTE."""

    message = "Esta operación está disponible únicamente para cuentas de paciente."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "rol", None) == RolUsuario.PACIENTE
        )


class EsProfesional(BasePermission):
    """Permite el panel clínico solo a cuentas explícitamente marcadas PROFESIONAL.

    is_staff e is_superuser son indicadores administrativos de Django, no roles
    clínicos. No conceden acceso implícito a los datos de ECG.
    """

    message = "Esta operación está disponible únicamente para el personal profesional."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "rol", None) == RolUsuario.PROFESIONAL
        )


class TieneConsentimiento(BasePermission):
    """Exige las dos aceptaciones antes de acceder a información personal de salud."""

    message = "Antes de registrar o consultar datos de salud debe aceptar el consentimiento informado."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        return Consentimiento.objects.filter(
            paciente=user,
            acepta_tratamiento_datos=True,
            acepta_piloto_no_clinico=True,
        ).exists()


class EsPropietarioPaciente(BasePermission):
    """Permiso a nivel de objeto para recursos que contienen paciente_id.

    Las vistas actuales ya filtran los querysets por request.user; esta clase
    sirve para reforzar esa regla cuando una vista recupere objetos por separado.
    En ese caso debe invocarse self.check_object_permissions(request, objeto).
    """

    message = "No tiene permiso para acceder a información de otro participante."

    def has_object_permission(self, request, view, obj):
        user = request.user
        propietario_id = getattr(obj, "paciente_id", None)
        return bool(
            user
            and user.is_authenticated
            and propietario_id is not None
            and propietario_id == user.pk
        )

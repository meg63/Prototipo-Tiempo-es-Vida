from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser
from .models import PerfilCardiovascular



@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Administración de cuentas. Solo un superusuario administra roles."""

    ordering = ("email",)
    list_display = (
        "email",
        "nombre",
        "codigo_participante",
        "rol",
        "is_active",
        "is_staff",
    )
    list_filter = ("rol", "is_active", "is_staff")
    search_fields = ("email", "nombre", "codigo_participante", "username")

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            "Datos de la cuenta Tiempo es Vida",
            {
                "fields": (
                    "email",
                    "nombre",
                    "codigo_participante",
                    "edad",
                    "sexo",
                    "rol",
                )
            },
        ),
        (
            "Permisos administrativos de Django",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Fechas", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "nombre",
                    "codigo_participante",
                    "edad",
                    "sexo",
                    "rol",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    def has_module_permission(self, request):
        return bool(request.user.is_active and request.user.is_superuser)

    def has_view_permission(self, request, obj=None):
        return bool(request.user.is_active and request.user.is_superuser)

    def has_add_permission(self, request):
        return bool(request.user.is_active and request.user.is_superuser)

    def has_change_permission(self, request, obj=None):
        return bool(request.user.is_active and request.user.is_superuser)

    def has_delete_permission(self, request, obj=None):
        return bool(request.user.is_active and request.user.is_superuser)
@admin.register(PerfilCardiovascular)
class PerfilCardiovascularAdmin(admin.ModelAdmin):
    list_display = (
        "paciente",
        "parq_completado",
        "parq_requiere_revision",
        "ejercicio_supervisado_indicado",
        "restriccion_liquidos_medica",
    )
    search_fields = ("paciente__email", "paciente__nombre", "paciente__codigo_participante")
    list_filter = (
        "parq_completado",
        "parq_requiere_revision",
        "restriccion_liquidos_medica",
        "embarazo",
    )

    def has_module_permission(self, request):
        return bool(request.user.is_active and request.user.is_superuser)

    def has_view_permission(self, request, obj=None):
        return bool(request.user.is_active and request.user.is_superuser)

    def has_add_permission(self, request):
        return bool(request.user.is_active and request.user.is_superuser)

    def has_change_permission(self, request, obj=None):
        return bool(request.user.is_active and request.user.is_superuser)

    def has_delete_permission(self, request, obj=None):
        return bool(request.user.is_active and request.user.is_superuser)

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


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

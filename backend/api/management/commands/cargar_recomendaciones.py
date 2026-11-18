from django.core.management.base import BaseCommand

from api.models import RecomendacionCatalogo
from api.recommendations_data import RECOMMENDATIONS


class Command(BaseCommand):
    help = "Carga o actualiza el banco oficial de 30 recomendaciones de Tiempo es Vida."

    def handle(self, *args, **options):
        creadas = 0
        actualizadas = 0

        for item in RECOMMENDATIONS:
            _, created = RecomendacionCatalogo.objects.update_or_create(
                codigo=item["codigo"],
                defaults={
                    "categoria": item["categoria"],
                    "situacion_identificada": item["situacion_identificada"],
                    "texto_recomendacion": item["texto_recomendacion"],
                    "activa": True,
                },
            )
            if created:
                creadas += 1
            else:
                actualizadas += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Banco procesado: {creadas} creadas, {actualizadas} actualizadas, "
                f"{len(RECOMMENDATIONS)} códigos oficiales."
            )
        )
        oficiales = set(item["codigo"] for item in RECOMMENDATIONS)
        extras = RecomendacionCatalogo.objects.filter(activa=True).exclude(codigo__in=oficiales).count()
        if extras:
            self.stdout.write(
                self.style.WARNING(
                    f"Hay {extras} recomendaciones activas adicionales que no pertenecen al banco oficial. "
                    "No se desactivaron automáticamente."
                )
            )

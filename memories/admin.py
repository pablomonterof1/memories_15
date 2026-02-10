from django.contrib import admin
from .models import Evento, Momento, Foto


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "fecha", "token", "activo", "creado_en")
    list_filter = ("activo", "fecha")
    search_fields = ("nombre", "token")
    ordering = ("-fecha",)


@admin.register(Momento)
class MomentoAdmin(admin.ModelAdmin):
    list_display = ("evento", "orden", "emoji", "nombre", "activo")
    list_filter = ("evento", "activo")
    search_fields = ("nombre",)
    ordering = ("evento", "orden", "id")


@admin.register(Foto)
class FotoAdmin(admin.ModelAdmin):
    list_display = ("evento", "momento", "nombre_invitado", "visible", "destacada", "creado_en")
    list_filter = ("evento", "momento", "visible", "destacada", "creado_en")
    search_fields = ("nombre_invitado", "mensaje")
    ordering = ("-creado_en",)
    readonly_fields = ("creado_en",)

    actions = ("marcar_visible", "marcar_oculta", "marcar_destacada", "quitar_destacada")

    @admin.action(description="Marcar como visibles")
    def marcar_visible(self, request, queryset):
        queryset.update(visible=True)

    @admin.action(description="Marcar como ocultas")
    def marcar_oculta(self, request, queryset):
        queryset.update(visible=False)

    @admin.action(description="Marcar como destacadas")
    def marcar_destacada(self, request, queryset):
        queryset.update(destacada=True)

    @admin.action(description="Quitar destacadas")
    def quitar_destacada(self, request, queryset):
        queryset.update(destacada=False)

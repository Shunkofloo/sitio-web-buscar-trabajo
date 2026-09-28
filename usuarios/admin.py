from django.contrib import admin
from .models import PerfilPostulante, UsuarioSitio


class PerfilPostulanteInline(admin.StackedInline):
	model = PerfilPostulante
	extra = 0
	max_num = 1


@admin.register(PerfilPostulante)
class PerfilPostulanteAdmin(admin.ModelAdmin):
	list_display = ('usuario', 'correo', 'telefono', 'profesion')
	search_fields = ('usuario__usuario', 'usuario__nombre', 'correo', 'profesion')
	autocomplete_fields = ('usuario',)


@admin.register(UsuarioSitio)
class UsuarioSitioAdmin(admin.ModelAdmin):
	list_display = ('usuario', 'nombre', 'rol')
	list_filter = ('rol',)
	search_fields = ('usuario', 'nombre')
	inlines = (PerfilPostulanteInline,)

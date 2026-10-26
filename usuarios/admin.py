from django.contrib import admin
from .models import PerfilPostulante


@admin.register(PerfilPostulante)
class PerfilPostulanteAdmin(admin.ModelAdmin):
	list_display = ('nombre_completo', 'correo', 'telefono', 'profesion')
	search_fields = ('nombre_completo', 'correo', 'profesion')

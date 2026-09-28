from django.contrib import admin
from .models import CategoriaNoticia, Noticia


@admin.register(CategoriaNoticia)
class CategoriaNoticiaAdmin(admin.ModelAdmin):
	search_fields = ('nombre',)


@admin.register(Noticia)
class NoticiaAdmin(admin.ModelAdmin):
	list_display = ('titulo', 'categoria', 'fecha')
	list_filter = ('categoria', 'fecha')
	search_fields = ('titulo', 'resumen')

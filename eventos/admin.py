from django.contrib import admin
from .models import CategoriaOferta, Empresa, Evento, OfertaLaboral, Postulacion


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
	list_display = ('nombre', 'lugar', 'fecha')
	list_filter = ('fecha',)
	search_fields = ('nombre', 'lugar')


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
	list_display = ('nombre', 'ubicacion', 'correo_contacto', 'activa')
	list_filter = ('activa', 'ubicacion')
	search_fields = ('nombre', 'ubicacion', 'correo_contacto')


@admin.register(CategoriaOferta)
class CategoriaOfertaAdmin(admin.ModelAdmin):
	search_fields = ('nombre',)


class PostulacionInline(admin.TabularInline):
	model = Postulacion
	extra = 0
	fields = ('postulante', 'fecha_postulacion', 'estado')
	readonly_fields = ('fecha_postulacion',)


@admin.register(OfertaLaboral)
class OfertaLaboralAdmin(admin.ModelAdmin):
	list_display = ('titulo', 'empresa', 'categoria', 'modalidad', 'estado', 'fecha_publicacion')
	list_filter = ('estado', 'modalidad', 'categoria', 'empresa')
	search_fields = ('titulo', 'descripcion', 'ubicacion', 'empresa__nombre')
	autocomplete_fields = ('empresa', 'categoria')
	inlines = (PostulacionInline,)


@admin.register(Postulacion)
class PostulacionAdmin(admin.ModelAdmin):
	list_display = ('oferta', 'postulante', 'fecha_postulacion', 'estado')
	list_filter = ('estado', 'fecha_postulacion')
	search_fields = ('oferta__titulo', 'postulante__usuario__nombre', 'postulante__usuario__usuario')
	autocomplete_fields = ('oferta', 'postulante')
	list_select_related = ('oferta', 'postulante', 'postulante__usuario')

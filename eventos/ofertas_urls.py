from django.urls import path

from .views import (
	OfertaCrearView,
	OfertaEditarView,
	OfertaEliminarView,
	OfertaListaView,
)


urlpatterns = [
	path('', OfertaListaView.as_view(), name='oferta_lista'),
	path('crear/', OfertaCrearView.as_view(), name='oferta_crear'),
	path('<int:pk>/editar/', OfertaEditarView.as_view(), name='oferta_editar'),
	path('<int:pk>/eliminar/', OfertaEliminarView.as_view(), name='oferta_eliminar'),
]

from django.urls import path

from .views import (
	PostulacionCrearView,
	PostulacionDetalleView,
	PostulacionEstadoView,
	PostulacionListaView,
)


urlpatterns = [
	path('', PostulacionListaView.as_view(), name='postulacion_lista'),
	path('registrar/', PostulacionCrearView.as_view(), name='postulacion_crear'),
	path('<int:pk>/', PostulacionDetalleView.as_view(), name='postulacion_detalle'),
	path(
		'<int:pk>/estado/',
		PostulacionEstadoView.as_view(),
		name='postulacion_estado',
	),
]

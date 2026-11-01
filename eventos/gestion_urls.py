from django.urls import path

from .views import (
	EmpresaCrearView,
	EmpresaEditarView,
	EmpresaEliminarView,
	EmpresaListaView,
)


urlpatterns = [
	path('', EmpresaListaView.as_view(), name='empresa_lista'),
	path('crear/', EmpresaCrearView.as_view(), name='empresa_crear'),
	path('<int:pk>/editar/', EmpresaEditarView.as_view(), name='empresa_editar'),
	path('<int:pk>/eliminar/', EmpresaEliminarView.as_view(), name='empresa_eliminar'),
]

from django.urls import path

from .views import (
	IniciarSesionView,
	CerrarSesionView,
	ConfirmarRestablecimientoContrasenaView,
	RecuperarContrasenaEnviadaView,
	RecuperarContrasenaView,
	RestablecimientoContrasenaCompletoView,
	UsuarioCrearView,
	UsuarioEditarView,
	UsuarioEliminarView,
	UsuarioListaView,
	dashboard_administrador,
	dashboard_administrativo,
	dashboard_supervisor,
	redireccion_dashboard,
)

urlpatterns = [
	path('login/', IniciarSesionView.as_view(), name='usuarios_login'),
	path('logout/', CerrarSesionView.as_view(), name='usuarios_logout'),
	path('recuperar/', RecuperarContrasenaView.as_view(), name='usuarios_password_reset'),
	path(
		'recuperar/enviado/',
		RecuperarContrasenaEnviadaView.as_view(),
		name='usuarios_password_reset_done',
	),
	path(
		'restablecer/<uidb64>/<token>/',
		ConfirmarRestablecimientoContrasenaView.as_view(),
		name='usuarios_password_reset_confirm',
	),
	path(
		'restablecer/completo/',
		RestablecimientoContrasenaCompletoView.as_view(),
		name='usuarios_password_reset_complete',
	),
	path('gestion/', UsuarioListaView.as_view(), name='usuario_lista'),
	path('gestion/crear/', UsuarioCrearView.as_view(), name='usuario_crear'),
	path('gestion/<int:pk>/editar/', UsuarioEditarView.as_view(), name='usuario_editar'),
	path('gestion/<int:pk>/eliminar/', UsuarioEliminarView.as_view(), name='usuario_eliminar'),
	path('dashboard/', redireccion_dashboard, name='redireccion_dashboard'),
	path(
		'dashboard/administrador/',
		dashboard_administrador,
		name='usuarios_dashboard_administrador',
	),
	path(
		'dashboard/supervisor/',
		dashboard_supervisor,
		name='usuarios_dashboard_supervisor',
	),
	path(
		'dashboard/administrativo/',
		dashboard_administrativo,
		name='usuarios_dashboard_administrativo',
	),
]

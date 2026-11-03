from django.urls import path

from .views import (
	IniciarSesionView,
	CerrarSesionView,
	ConfirmarRecuperacionView,
	RecuperarContrasenaView,
	RegistroPublicoView,
	RestablecimientoContrasenaCompletoView,
	UsuarioCrearView,
	UsuarioEditarView,
	UsuarioEliminarView,
	UsuarioListaView,
	dashboard_administrador,
	dashboard_administrativo,
	dashboard_supervisor,
	redireccion_dashboard,
	perfil_usuario,
)

urlpatterns = [
	path('login/', IniciarSesionView.as_view(), name='usuarios_login'),
	path('logout/', CerrarSesionView.as_view(), name='usuarios_logout'),
	path('perfil/', perfil_usuario, name='usuarios_perfil'),
	path('registro/', RegistroPublicoView.as_view(), name='usuarios_registro'),
	path('recuperar/', RecuperarContrasenaView.as_view(), name='usuarios_password_reset'),
	path(
		'recuperar/codigo/',
		ConfirmarRecuperacionView.as_view(),
		name='usuarios_password_reset_codigo',
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
